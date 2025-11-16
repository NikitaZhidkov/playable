"""
Unit tests for test_case_validator.py
Tests test case validation logic in isolation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.validators.test_case_validator import validate_test_cases
from src.validators.base import ValidationResult
import json


@pytest.mark.asyncio
async def test_validate_test_cases_success():
    """Test successful test case validation with all test cases passing."""
    workspace = Mock()
    
    # Mock test case discovery
    workspace.list_files = AsyncMock(return_value=["test_case_1.json", "test_case_2.json"])
    
    # Mock test case file reading
    test_case_1 = json.dumps({"expectedOutput": "Score: 100", "input": {}})
    test_case_2 = json.dumps({"expectedOutput": "Level complete", "input": {}})
    workspace.read_file = AsyncMock(side_effect=[test_case_1, test_case_2])
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    # Mock playwright container
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock()
    
    # Mock test results
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot"
    test_result.errors = []
    
    vlm_client = Mock()
    
    # Mock validate_game_with_test_case
    with patch('src.validators.test_case_validator.validate_game_with_test_case',
               AsyncMock(return_value=test_result)):
        # Mock VLM validation to return success for both test cases
        with patch('src.validators.test_case_validator.validate_test_case_with_vlm',
                   side_effect=[(True, "Looks good"), (True, "Looks good")]):
            result = await validate_test_cases(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                session_id="test_session",
                test_run_id="test_run",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is True
    assert result.error_message is None
    assert result.failures == []
    assert result.retry_count == 0


@pytest.mark.asyncio
async def test_validate_test_cases_no_test_cases():
    """Test validation fails when no test cases are found."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=[])
    
    playwright_container = Mock()
    vlm_client = Mock()
    
    result = await validate_test_cases(
        workspace=workspace,
        playwright_container=playwright_container,
        vlm_client=vlm_client,
        session_id="test_session",
        test_run_id="test_run",
        retry_count=0
    )
    
    # Assertions
    assert result.passed is False
    assert "No test cases found" in result.error_message
    assert result.failures == ["Missing test cases (required: 1-5)"]
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_validate_test_cases_missing_expected_output():
    """Test validation fails when test case is missing expectedOutput field."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=["test_case_1.json"])
    
    # Test case without expectedOutput
    test_case = json.dumps({"input": {}})
    workspace.read_file = AsyncMock(return_value=test_case)
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    playwright_container = Mock()
    vlm_client = Mock()
    
    with patch('src.validators.test_case_validator.save_test_case_error'):
        result = await validate_test_cases(
            workspace=workspace,
            playwright_container=playwright_container,
            vlm_client=vlm_client,
            session_id="test_session",
            test_run_id="test_run",
            retry_count=0
        )
    
    # Assertions
    assert result.passed is False
    assert "Missing 'expectedOutput'" in result.error_message
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_validate_test_cases_loading_error():
    """Test validation fails when test case loading has errors."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=["test_case_1.json"])
    
    test_case = json.dumps({"expectedOutput": "Score: 100", "input": {}})
    workspace.read_file = AsyncMock(return_value=test_case)
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock()
    
    # Mock test result with errors
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot"
    test_result.errors = ["loadTestCase is not defined", "Failed to load test case"]
    
    vlm_client = Mock()
    
    with patch('src.validators.test_case_validator.validate_game_with_test_case',
               AsyncMock(return_value=test_result)):
        with patch('src.validators.test_case_validator.save_test_case_error'):
            result = await validate_test_cases(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                session_id="test_session",
                test_run_id="test_run",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is False
    assert "loadTestCase is not defined" in result.error_message
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_validate_test_cases_vlm_failure():
    """Test validation fails when VLM validation fails."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=["test_case_1.json"])
    
    test_case = json.dumps({"expectedOutput": "Score: 100", "input": {}})
    workspace.read_file = AsyncMock(return_value=test_case)
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot"
    test_result.errors = []
    
    vlm_client = Mock()
    
    with patch('src.validators.test_case_validator.validate_game_with_test_case',
               AsyncMock(return_value=test_result)):
        # Mock VLM to return failure
        with patch('src.validators.test_case_validator.validate_test_case_with_vlm',
                   return_value=(False, "Score shows 0 instead of 100")):
            with patch('src.validators.test_case_validator.save_test_case_error'):
                result = await validate_test_cases(
                    workspace=workspace,
                    playwright_container=playwright_container,
                    vlm_client=vlm_client,
                    session_id="test_session",
                    test_run_id="test_run",
                    retry_count=0
                )
    
    # Assertions
    assert result.passed is False
    assert "Score: 100" in result.error_message
    assert "Score shows 0 instead of 100" in result.error_message
    assert result.retry_count == 1


@pytest.mark.asyncio
async def test_validate_test_cases_stops_on_first_failure():
    """Test that validation stops on the first failing test case."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=["test_case_1.json", "test_case_2.json", "test_case_3.json"])
    
    test_case = json.dumps({"expectedOutput": "Test", "input": {}})
    workspace.read_file = AsyncMock(return_value=test_case)
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot"
    test_result.errors = []
    
    vlm_client = Mock()
    
    with patch('src.validators.test_case_validator.validate_game_with_test_case',
               AsyncMock(return_value=test_result)) as mock_validate:
        # First test passes, second fails
        with patch('src.validators.test_case_validator.validate_test_case_with_vlm',
                   side_effect=[(True, "OK"), (False, "Failed")]):
            with patch('src.validators.test_case_validator.save_test_case_error'):
                result = await validate_test_cases(
                    workspace=workspace,
                    playwright_container=playwright_container,
                    vlm_client=vlm_client,
                    session_id="test_session",
                    test_run_id="test_run",
                    retry_count=0
                )
    
    # Assertions
    assert result.passed is False
    # Should only run 2 test cases (stop after second fails)
    assert mock_validate.call_count == 2


@pytest.mark.asyncio
async def test_validate_test_cases_max_5_test_cases():
    """Test that maximum 5 test cases are validated."""
    workspace = Mock()
    # Provide 7 test cases
    workspace.list_files = AsyncMock(return_value=[
        "test_case_1.json", "test_case_2.json", "test_case_3.json",
        "test_case_4.json", "test_case_5.json", "test_case_6.json", "test_case_7.json"
    ])
    
    test_case = json.dumps({"expectedOutput": "Test", "input": {}})
    workspace.read_file = AsyncMock(return_value=test_case)
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot"
    test_result.errors = []
    
    vlm_client = Mock()
    
    with patch('src.validators.test_case_validator.validate_game_with_test_case',
               AsyncMock(return_value=test_result)) as mock_validate:
        with patch('src.validators.test_case_validator.validate_test_case_with_vlm',
                   return_value=(True, "OK")):
            result = await validate_test_cases(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                session_id="test_session",
                test_run_id="test_run",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is True
    # Should only run 5 test cases (max limit)
    assert mock_validate.call_count == 5


@pytest.mark.asyncio
async def test_validate_test_cases_retry_count_increments():
    """Test that retry count increments on failure."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=[])
    
    playwright_container = Mock()
    vlm_client = Mock()
    
    result = await validate_test_cases(
        workspace=workspace,
        playwright_container=playwright_container,
        vlm_client=vlm_client,
        session_id="test_session",
        test_run_id="test_run",
        retry_count=2
    )
    
    # Assertions
    assert result.passed is False
    assert result.retry_count == 3  # 2 + 1


@pytest.mark.asyncio
async def test_validate_test_cases_exception_handling():
    """Test that exceptions during test case execution are handled."""
    workspace = Mock()
    workspace.list_files = AsyncMock(return_value=["test_case_1.json"])
    
    test_case = json.dumps({"expectedOutput": "Test", "input": {}})
    workspace.read_file = AsyncMock(return_value=test_case)
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value=".")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock()
    
    vlm_client = Mock()
    
    # Mock validate_game_with_test_case to raise exception
    with patch('src.validators.test_case_validator.validate_game_with_test_case',
               AsyncMock(side_effect=Exception("Container crashed"))):
        with patch('src.validators.test_case_validator.save_test_case_error'):
            result = await validate_test_cases(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                session_id="test_session",
                test_run_id="test_run",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is False
    assert "Error running test case" in result.error_message
    assert "Container crashed" in result.error_message
    assert result.retry_count == 1

