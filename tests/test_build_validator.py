"""
Unit tests for build_validator.py
Tests TypeScript build validation logic in isolation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.validators.build_validator import validate_build
from src.validators.base import ValidationResult


@pytest.mark.asyncio
async def test_validate_build_success():
    """Test successful build with all checks passing."""
    # Create mock workspace
    workspace = Mock()
    
    # Mock successful type check
    type_check_result = Mock()
    type_check_result.exit_code = 0
    type_check_result.stdout = ""
    
    # Mock successful build
    build_result = Mock()
    build_result.exit_code = 0
    build_result.stdout = "Build completed"
    build_result.stderr = ""
    
    # Mock workspace operations
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        ["config.json", "MANIFEST.json", "test_case_1.json", "test_case_2.json", "src/"],
        ["bundle.html", "config.json", "MANIFEST.json", "test_case_1.json", "test_case_2.json"]
    ])
    workspace.read_file = AsyncMock(return_value="file content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is True
    assert result.error_message is None
    assert result.failures == []
    assert result.retry_count == 0
    assert result.workspace == workspace
    
    # Verify type check was called
    workspace.exec.assert_any_call(["npx", "tsc", "--noEmit"])
    # Verify build was called
    workspace.exec.assert_any_call(["npm", "run", "build"])
    # Verify files were copied
    assert workspace.write_file.call_count >= 5  # config, MANIFEST, 2 test cases, index.html


@pytest.mark.asyncio
async def test_validate_build_type_check_fails():
    """Test build fails when TypeScript type check fails."""
    workspace = Mock()
    
    # Mock failed type check
    type_check_result = Mock()
    type_check_result.exit_code = 1
    type_check_result.stdout = "error TS2322: Type 'string' is not assignable to type 'number'"
    
    workspace.exec = AsyncMock(return_value=type_check_result)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is False
    assert "TypeScript Type Check Failed" in result.error_message
    assert "TS2322" in result.error_message
    assert len(result.failures) == 1
    assert "type check failed" in result.failures[0].lower()
    assert result.retry_count == 1  # Incremented
    assert result.workspace is None
    
    # Verify only type check was called (build should not run)
    assert workspace.exec.call_count == 1


@pytest.mark.asyncio
async def test_validate_build_build_fails():
    """Test build fails when npm run build fails."""
    workspace = Mock()
    
    # Mock successful type check
    type_check_result = Mock()
    type_check_result.exit_code = 0
    type_check_result.stdout = ""
    
    # Mock failed build
    build_result = Mock()
    build_result.exit_code = 1
    build_result.stderr = "ERROR in ./src/Game.ts\nModule not found: Error: Can't resolve './missing'"
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is False
    assert "Build Failed" in result.error_message
    assert "Module not found" in result.error_message
    assert len(result.failures) == 1
    assert "Build failed" in result.failures[0]
    assert result.retry_count == 1
    assert result.workspace is None


@pytest.mark.asyncio
async def test_validate_build_no_test_cases():
    """Test build fails when no test case files exist."""
    workspace = Mock()
    
    # Mock successful type check and build
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    # Mock workspace with no test case files
    workspace.ls = AsyncMock(return_value=["config.json", "MANIFEST.json", "src/"])
    workspace.read_file = AsyncMock(return_value="file content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is False
    assert "No test cases found" in result.error_message
    assert result.failures == ["No test cases found"]
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_validate_build_no_html_output():
    """Test build fails when no HTML file is produced."""
    workspace = Mock()
    
    # Mock successful type check and build
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        ["config.json", "MANIFEST.json", "test_case_1.json", "src/"],
        ["config.json", "MANIFEST.json", "test_case_1.json"]  # No HTML files
    ])
    workspace.read_file = AsyncMock(return_value="file content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is False
    assert "Expected 1 HTML file" in result.error_message
    assert "found 0" in result.error_message
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_validate_build_multiple_html_files():
    """Test build fails when multiple HTML files are produced."""
    workspace = Mock()
    
    # Mock successful type check and build
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        ["config.json", "MANIFEST.json", "test_case_1.json", "src/"],
        ["bundle1.html", "bundle2.html", "config.json"]  # Multiple HTML files
    ])
    workspace.read_file = AsyncMock(return_value="file content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=2)
    
    # Assertions
    assert result.passed is False
    assert "Expected 1 HTML file" in result.error_message
    assert "found 2" in result.error_message
    assert "bundle1.html" in result.error_message
    assert "bundle2.html" in result.error_message
    assert result.retry_count == 3  # Was 2, incremented to 3


@pytest.mark.asyncio
async def test_validate_build_copies_all_test_cases():
    """Test that all test cases (1-5) are copied when they exist."""
    workspace = Mock()
    
    # Mock successful type check and build
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        [
            "config.json", "MANIFEST.json",
            "test_case_1.json", "test_case_2.json", "test_case_3.json",
            "test_case_4.json", "test_case_5.json", "src/"
        ],
        ["output.html"]
    ])
    workspace.read_file = AsyncMock(return_value="file content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is True
    
    # Verify all test cases were copied
    # Should have: config.json, MANIFEST.json, test_case_1-5 (7 files), plus index.html = 8 total
    assert workspace.write_file.call_count == 8
    
    # Verify specific test cases were copied
    calls = [str(call) for call in workspace.write_file.call_args_list]
    for i in range(1, 6):
        assert any(f"test_case_{i}.json" in call for call in calls)


@pytest.mark.asyncio
async def test_validate_build_partial_test_cases():
    """Test that build works with only some test cases (e.g., 1 and 2)."""
    workspace = Mock()
    
    # Mock successful type check and build
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        ["config.json", "MANIFEST.json", "test_case_1.json", "test_case_2.json", "src/"],
        ["output.html"]
    ])
    workspace.read_file = AsyncMock(return_value="file content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is True
    # Should copy: config.json, MANIFEST.json, test_case_1, test_case_2, index.html = 5 files
    assert workspace.write_file.call_count == 5


@pytest.mark.asyncio
async def test_validate_build_creates_index_html():
    """Test that built HTML is copied to index.html."""
    workspace = Mock()
    
    # Mock successful operations
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        ["config.json", "MANIFEST.json", "test_case_1.json"],
        ["Playable_Template_v1_20231025_Preview.html"]
    ])
    
    html_content = "<html><body>Game</body></html>"
    
    def read_file_side_effect(path):
        if path == "dist/Playable_Template_v1_20231025_Preview.html":
            return html_content
        return "other content"
    
    workspace.read_file = AsyncMock(side_effect=read_file_side_effect)
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation
    result = await validate_build(workspace, retry_count=0)
    
    # Assertions
    assert result.passed is True
    
    # Verify index.html was created with the right content
    calls = workspace.write_file.call_args_list
    index_html_call = [call for call in calls if "dist/index.html" in str(call)]
    assert len(index_html_call) == 1
    assert index_html_call[0][0][1] == html_content  # Check content matches


@pytest.mark.asyncio
async def test_validate_build_retry_count_increments():
    """Test that retry count increments correctly on failures."""
    workspace = Mock()
    
    # Mock failed type check
    type_check_result = Mock()
    type_check_result.exit_code = 1
    type_check_result.stdout = "Type error"
    
    workspace.exec = AsyncMock(return_value=type_check_result)
    
    # Run validation with existing retry count
    result = await validate_build(workspace, retry_count=3)
    
    # Assertions
    assert result.passed is False
    assert result.retry_count == 4  # 3 + 1


@pytest.mark.asyncio
async def test_validate_build_retry_count_resets_on_success():
    """Test that retry count resets to 0 on successful build."""
    workspace = Mock()
    
    # Mock successful operations
    type_check_result = Mock(exit_code=0, stdout="")
    build_result = Mock(exit_code=0, stdout="Build completed", stderr="")
    
    workspace.exec = AsyncMock(side_effect=[type_check_result, build_result])
    workspace.ls = AsyncMock(side_effect=[
        ["config.json", "MANIFEST.json", "test_case_1.json"],
        ["output.html"]
    ])
    workspace.read_file = AsyncMock(return_value="content")
    workspace.write_file = Mock(return_value=workspace)
    
    # Run validation with existing retry count
    result = await validate_build(workspace, retry_count=3)
    
    # Assertions
    assert result.passed is True
    assert result.retry_count == 0  # Reset to 0 on success

