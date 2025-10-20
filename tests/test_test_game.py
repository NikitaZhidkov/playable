"""
Unit tests for the test_game module.
"""
import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock
from test_game import GameTestResult, _parse_test_output, TEST_SCRIPT, validate_game_in_workspace


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestGameTestResult:
    """Tests for GameTestResult class."""
    
    def test_init_success(self):
        """Test GameTestResult initialization with success."""
        result = GameTestResult(success=True, errors=[])
        assert result.success is True
        assert result.errors == []
    
    def test_init_failure(self):
        """Test GameTestResult initialization with errors."""
        errors = ["Error 1", "Error 2"]
        result = GameTestResult(success=False, errors=errors)
        assert result.success is False
        assert result.errors == errors
    
    def test_repr(self):
        """Test string representation of GameTestResult."""
        result = GameTestResult(success=True, errors=[])
        repr_str = repr(result)
        assert "GameTestResult" in repr_str
        assert "success=True" in repr_str
        assert "errors=[]" in repr_str


class TestParseTestOutput:
    """Tests for _parse_test_output function."""
    
    def test_parse_successful_test(self):
        """Test parsing output from a successful test."""
        output = """
Page loaded: Test Game
__TEST_RESULT__{"success": true, "errors": []}__END__
"""
        result = _parse_test_output(output)
        assert result.success is True
        assert result.errors == []
    
    def test_parse_failed_test(self):
        """Test parsing output from a failed test."""
        errors = ["Error 1", "Error 2"]
        test_result = {"success": False, "errors": errors}
        output = f"__TEST_RESULT__{json.dumps(test_result)}__END__"
        
        result = _parse_test_output(output)
        assert result.success is False
        assert result.errors == errors
    
    def test_parse_test_with_console_errors(self):
        """Test parsing output with console errors."""
        errors = ["[ERROR] Console error message", "[WARNING] Console warning"]
        test_result = {"success": False, "errors": errors}
        output = f"""
Page loaded: Test Game
{json.dumps(test_result)}
__TEST_RESULT__{json.dumps(test_result)}__END__
"""
        result = _parse_test_output(output)
        assert result.success is False
        assert len(result.errors) == 2
        assert "[ERROR] Console error message" in result.errors
    
    def test_parse_missing_markers(self):
        """Test parsing output without result markers."""
        output = "Some output without markers"
        result = _parse_test_output(output)
        assert result.success is False
        assert len(result.errors) == 1
        assert "no result markers found" in result.errors[0]
    
    def test_parse_missing_start_marker(self):
        """Test parsing output with missing start marker."""
        output = "Some output without start marker __END__"
        result = _parse_test_output(output)
        assert result.success is False
        assert "no result markers found" in result.errors[0]
    
    def test_parse_missing_end_marker(self):
        """Test parsing output with missing end marker."""
        output = "__TEST_RESULT__{'success': true, 'errors': []}"
        result = _parse_test_output(output)
        assert result.success is False
        assert "no result markers found" in result.errors[0]
    
    def test_parse_invalid_json(self):
        """Test parsing output with invalid JSON."""
        output = "__TEST_RESULT__not valid json__END__"
        result = _parse_test_output(output)
        assert result.success is False
        assert "Failed to parse test output" in result.errors[0]
    
    def test_parse_complex_output(self):
        """Test parsing output with multiple console logs before result."""
        test_result = {"success": True, "errors": []}
        output = f"""
Console log 1
Console log 2
Console log 3
Page loaded: My Game
__TEST_RESULT__{json.dumps(test_result)}__END__
"""
        result = _parse_test_output(output)
        assert result.success is True
        assert result.errors == []
    
    def test_parse_test_execution_error(self):
        """Test parsing output from test execution error."""
        error_msg = "Test execution failed: Connection timeout"
        test_result = {"success": False, "errors": [error_msg]}
        output = f"__TEST_RESULT__{json.dumps(test_result)}__END__"
        
        result = _parse_test_output(output)
        assert result.success is False
        assert error_msg in result.errors


class TestTestScript:
    """Tests for the JavaScript test script."""
    
    def test_script_contains_required_elements(self):
        """Test that TEST_SCRIPT contains all required elements."""
        assert "chromium" in TEST_SCRIPT
        assert "playwright" in TEST_SCRIPT
        assert "__TEST_RESULT__" in TEST_SCRIPT
        assert "__END__" in TEST_SCRIPT
        assert "page.on('console'" in TEST_SCRIPT
        assert "page.on('pageerror'" in TEST_SCRIPT
        assert "page.on('requestfailed'" in TEST_SCRIPT
    
    def test_script_has_error_handling(self):
        """Test that TEST_SCRIPT has error handling."""
        assert "try" in TEST_SCRIPT
        assert "catch" in TEST_SCRIPT
        assert "finally" in TEST_SCRIPT
    
    def test_script_outputs_json(self):
        """Test that TEST_SCRIPT outputs JSON result."""
        assert "JSON.stringify" in TEST_SCRIPT
        assert "console.log" in TEST_SCRIPT


class TestIntegration:
    """Integration tests for the test_game module."""
    
    def test_successful_game_workflow(self):
        """Test the complete workflow for a successful game test."""
        # Simulate successful test output
        output = "__TEST_RESULT__" + json.dumps({
            "success": True,
            "errors": []
        }) + "__END__"
        
        result = _parse_test_output(output)
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_failed_game_workflow(self):
        """Test the complete workflow for a failed game test."""
        # Simulate failed test output with multiple errors
        errors = [
            "Uncaught exception: Cannot read property 'x' of undefined",
            "Failed to load resource: http://example.com/missing.png",
            "[ERROR] TypeError: app.init is not a function"
        ]
        output = "__TEST_RESULT__" + json.dumps({
            "success": False,
            "errors": errors
        }) + "__END__"
        
        result = _parse_test_output(output)
        assert result.success is False
        assert len(result.errors) == 3
        assert result.errors == errors


@pytest.mark.asyncio
class TestGameFromWorkspace:
    """Tests for validate_game_in_workspace function."""
    
    def _setup_mock_container_chain(self, output, exit_code=0):
        """Helper to set up the complete mock container chain."""
        # Mock the container chain for Playwright
        # New chain: from_ -> with_directory -> with_workdir -> with_new_file(package.json) 
        #            -> with_exec(npm install) -> with_new_file(test-runner.js) -> with_exec(node)
        mock_base_container = MagicMock()
        mock_from_container = MagicMock()
        mock_with_dir_container = MagicMock()
        mock_workdir_container = MagicMock()
        mock_package_json_container = MagicMock()
        mock_npm_install_container = MagicMock()
        mock_test_script_container = MagicMock()
        mock_final_exec_container = MagicMock()
        
        mock_base_container.from_.return_value = mock_from_container
        mock_from_container.with_directory.return_value = mock_with_dir_container
        mock_with_dir_container.with_workdir.return_value = mock_workdir_container
        # First with_new_file (package.json)
        mock_workdir_container.with_new_file.return_value = mock_package_json_container
        # First with_exec (npm install)
        mock_package_json_container.with_exec.return_value = mock_npm_install_container
        # Second with_new_file (test-runner.js)
        mock_npm_install_container.with_new_file.return_value = mock_test_script_container
        # Second with_exec (node test-runner.js)
        mock_test_script_container.with_exec.return_value = mock_final_exec_container
        
        # Mock stdout and exit_code on the final container
        mock_final_exec_container.stdout = AsyncMock(return_value=output)
        mock_final_exec_container.exit_code = AsyncMock(return_value=exit_code)
        
        return mock_base_container
    
    async def test_successful_game_test(self):
        """Test validate_game_in_workspace with a successful game."""
        # Mock workspace and its dependencies
        mock_workspace = MagicMock()
        mock_client = MagicMock()
        mock_workspace.client = mock_client
        
        # Mock container chain
        mock_container = MagicMock()
        mock_workspace.container.return_value = mock_container
        mock_container.directory.return_value = MagicMock()
        
        # Mock stdout output
        successful_output = "__TEST_RESULT__" + json.dumps({
            "success": True,
            "errors": []
        }) + "__END__"
        
        mock_base_container = self._setup_mock_container_chain(successful_output, exit_code=0)
        mock_client.container.return_value = mock_base_container
        
        # Run the test
        result = await validate_game_in_workspace(mock_workspace)
        
        # Assertions
        assert result.success is True
        assert result.errors == []
        mock_client.container.assert_called_once()
        mock_base_container.from_.assert_called_once_with("mcr.microsoft.com/playwright:v1.49.0-jammy")
    
    async def test_failed_game_test(self):
        """Test validate_game_in_workspace with a failed game."""
        # Mock workspace
        mock_workspace = MagicMock()
        mock_client = MagicMock()
        mock_workspace.client = mock_client
        
        # Mock container chain
        mock_container = MagicMock()
        mock_workspace.container.return_value = mock_container
        mock_container.directory.return_value = MagicMock()
        
        # Mock failed test output
        errors = ["[ERROR] ReferenceError: PIXI is not defined"]
        failed_output = "__TEST_RESULT__" + json.dumps({
            "success": False,
            "errors": errors
        }) + "__END__"
        
        mock_base_container = self._setup_mock_container_chain(failed_output, exit_code=1)
        mock_client.container.return_value = mock_base_container
        
        # Run the test
        result = await validate_game_in_workspace(mock_workspace)
        
        # Assertions
        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0] == "[ERROR] ReferenceError: PIXI is not defined"
    
    async def test_container_execution_exception(self):
        """Test validate_game_in_workspace when container execution fails."""
        # Mock workspace
        mock_workspace = MagicMock()
        mock_client = MagicMock()
        mock_workspace.client = mock_client
        
        # Mock container that raises exception
        mock_client.container.side_effect = Exception("Docker daemon not running")
        
        # Run the test
        result = await validate_game_in_workspace(mock_workspace)
        
        # Assertions
        assert result.success is False
        assert len(result.errors) == 1
        assert "Failed to run containerized tests" in result.errors[0]
        assert "Docker daemon not running" in result.errors[0]
    
    async def test_malformed_output(self):
        """Test validate_game_in_workspace with malformed test output."""
        # Mock workspace
        mock_workspace = MagicMock()
        mock_client = MagicMock()
        mock_workspace.client = mock_client
        
        # Mock container chain
        mock_container = MagicMock()
        mock_workspace.container.return_value = mock_container
        mock_container.directory.return_value = MagicMock()
        
        # Mock malformed output (no markers)
        malformed_output = "Some random output without markers"
        
        mock_base_container = self._setup_mock_container_chain(malformed_output, exit_code=1)
        mock_client.container.return_value = mock_base_container
        
        # Run the test
        result = await validate_game_in_workspace(mock_workspace)
        
        # Assertions
        assert result.success is False
        assert len(result.errors) == 1
        assert "no result markers found" in result.errors[0]
    
    async def test_with_exec_called_correctly(self):
        """Test that with_exec is called with correct parameters."""
        # Mock workspace
        mock_workspace = MagicMock()
        mock_client = MagicMock()
        mock_workspace.client = mock_client
        
        # Mock container chain
        mock_container = MagicMock()
        mock_workspace.container.return_value = mock_container
        mock_container.directory.return_value = MagicMock()
        
        # Mock successful output
        output = "__TEST_RESULT__" + json.dumps({"success": True, "errors": []}) + "__END__"
        
        mock_base_container = self._setup_mock_container_chain(output, exit_code=0)
        mock_client.container.return_value = mock_base_container
        
        # Run the test
        await validate_game_in_workspace(mock_workspace)
        
        # Verify that container chain was set up correctly
        from dagger import ReturnType
        mock_base_container.from_.assert_called_once_with("mcr.microsoft.com/playwright:v1.49.0-jammy")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

