"""
Unit tests for playable_validator.py
Tests VLM validation logic for main playable in isolation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.validators.playable_validator import validate_playable
from src.validators.base import ValidationResult


@pytest.mark.asyncio
async def test_validate_playable_success():
    """Test successful VLM validation."""
    # Create mocks
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    # Mock test result
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = ["Log 1", "Log 2"]
    
    # Mock validate_game_in_workspace
    with patch('src.validators.playable_validator.validate_game_in_workspace', 
               AsyncMock(return_value=test_result)):
        # Mock validate_playable_with_vlm to return success
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(True, "Playable looks good")):
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Create a racing game",
                session_id="test_session",
                test_run_id="test_run",
                is_feedback_mode=False,
                retry_count=0
            )
    
    # Assertions
    assert result.passed is True
    assert result.error_message is None
    assert result.failures == []
    assert result.retry_count == 0
    
    # Verify container was reset and prepared
    playwright_container.reset.assert_called_once()
    playwright_container.copy_directory.assert_called_once()
    playwright_container.with_test_script.assert_called_once()


@pytest.mark.asyncio
async def test_validate_playable_vlm_failure():
    """Test VLM validation failure."""
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    # Mock test result
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = ["Error: Game crashed", "Warning: Asset not loaded"]
    
    # Mock validate_game_in_workspace
    with patch('src.validators.playable_validator.validate_game_in_workspace',
               AsyncMock(return_value=test_result)):
        # Mock validate_playable_with_vlm to return failure
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(False, "The game shows a blank screen")):
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Create a racing game",
                session_id="test_session",
                test_run_id="test_run",
                is_feedback_mode=False,
                retry_count=0
            )
    
    # Assertions
    assert result.passed is False
    assert result.error_message is not None
    assert "blank screen" in result.error_message
    assert "Error: Game crashed" in result.error_message  # Console logs included
    assert result.failures == ["The game shows a blank screen"]
    assert result.retry_count == 1  # Incremented


@pytest.mark.asyncio
async def test_validate_playable_no_console_logs():
    """Test VLM validation failure with no console logs."""
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    # Mock test result with no console logs
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = []
    
    with patch('src.validators.playable_validator.validate_game_in_workspace',
               AsyncMock(return_value=test_result)):
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(False, "Game not working")):
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Create a game",
                session_id="test_session",
                test_run_id="test_run",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is False
    assert "No console logs captured" in result.error_message


@pytest.mark.asyncio
async def test_validate_playable_feedback_mode():
    """Test VLM validation in feedback mode with original prompt."""
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = ["Game loaded"]
    
    with patch('src.validators.playable_validator.validate_game_in_workspace',
               AsyncMock(return_value=test_result)) as mock_validate_game:
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(True, "Looks good")) as mock_vlm:
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Make it faster",
                session_id="test_session",
                test_run_id="test_run",
                is_feedback_mode=True,
                original_prompt="Create a racing game",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is True
    
    # Verify VLM was called with feedback mode parameters
    mock_vlm.assert_called_once()
    call_kwargs = mock_vlm.call_args[1]
    assert call_kwargs['is_feedback_mode'] is True
    assert call_kwargs['original_prompt'] == "Create a racing game"


@pytest.mark.asyncio
async def test_validate_playable_retry_count_increments():
    """Test that retry count increments on failure."""
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = []
    
    with patch('src.validators.playable_validator.validate_game_in_workspace',
               AsyncMock(return_value=test_result)):
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(False, "Failed")):
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Create a game",
                session_id="test_session",
                test_run_id="test_run",
                retry_count=2
            )
    
    # Assertions
    assert result.passed is False
    assert result.retry_count == 3  # 2 + 1


@pytest.mark.asyncio
async def test_validate_playable_retry_count_resets_on_success():
    """Test that retry count resets to 0 on success."""
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = []
    
    with patch('src.validators.playable_validator.validate_game_in_workspace',
               AsyncMock(return_value=test_result)):
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(True, "Success")):
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Create a game",
                session_id="test_session",
                test_run_id="test_run",
                retry_count=3
            )
    
    # Assertions
    assert result.passed is True
    assert result.retry_count == 0  # Reset to 0 on success


@pytest.mark.asyncio
async def test_validate_playable_console_logs_formatting():
    """Test that console logs are properly formatted in error message."""
    workspace = Mock()
    workspace.container = Mock(return_value=Mock(directory=Mock(return_value="dist_dir")))
    
    playwright_container = Mock()
    playwright_container.reset = Mock()
    playwright_container.copy_directory = Mock(return_value=playwright_container)
    playwright_container.with_test_script = Mock(return_value=playwright_container)
    
    vlm_client = Mock()
    
    test_result = Mock()
    test_result.screenshot_bytes = b"screenshot_data"
    test_result.console_logs = [
        "[INFO] Game initialized",
        "[ERROR] Failed to load asset",
        "[WARNING] Performance issue"
    ]
    
    with patch('src.validators.playable_validator.validate_game_in_workspace',
               AsyncMock(return_value=test_result)):
        with patch('src.validators.playable_validator.validate_playable_with_vlm',
                   return_value=(False, "Assets missing")):
            result = await validate_playable(
                workspace=workspace,
                playwright_container=playwright_container,
                vlm_client=vlm_client,
                task_description="Create a game",
                session_id="test_session",
                test_run_id="test_run",
                retry_count=0
            )
    
    # Assertions
    assert result.passed is False
    # Verify all console logs are in the error message with proper formatting
    assert "[INFO] Game initialized" in result.error_message
    assert "[ERROR] Failed to load asset" in result.error_message
    assert "[WARNING] Performance issue" in result.error_message

