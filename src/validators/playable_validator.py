"""
Playable validator for main VLM validation.

This module handles the validation of the main playable using VLM:
- Prepares Playwright container with built game
- Runs browser tests to capture screenshot and console logs
- Validates with VLM using the playable validation prompt
"""
import logging
from src.validators.base import ValidationResult
from test_game import validate_game_in_workspace, TEST_SCRIPT
from src.vlm import validate_playable_with_vlm, VLM_PLAYABLE_VALIDATION_PROMPT
from src.prompts import FEEDBACK_VALIDATION_FAILED

logger = logging.getLogger(__name__)


async def validate_playable(
    workspace,
    playwright_container,
    vlm_client,
    task_description: str,
    session_id: str,
    test_run_id: str,
    is_feedback_mode: bool = False,
    original_prompt: str = None,
    retry_count: int = 0
) -> ValidationResult:
    """
    Validate the main playable with VLM.
    
    This function performs the following steps:
    1. Prepare Playwright container with built game from dist/
    2. Run browser tests to capture screenshot and console logs
    3. Validate with VLM using playable validation prompt
    4. Return validation result with formatted error message if failed
    
    Args:
        workspace: The Dagger workspace container with the built game
        playwright_container: PlaywrightContainer for running browser tests
        vlm_client: VLMClient for validation
        task_description: User's original task description
        session_id: Current session ID for debugging
        test_run_id: Test run ID for organizing debug files
        is_feedback_mode: Whether in feedback mode (default: False)
        original_prompt: Original prompt if in feedback mode (default: None)
        retry_count: Current retry attempt number (default: 0)
    
    Returns:
        ValidationResult with:
            - passed=True if VLM validation passes
            - passed=False with formatted error_message if validation fails
    
    Example:
        >>> result = await validate_playable(
        ...     workspace=workspace,
        ...     playwright_container=container,
        ...     vlm_client=vlm_client,
        ...     task_description="Create a racing game",
        ...     session_id="20231025_120000",
        ...     test_run_id="20231025_120030"
        ... )
        >>> if result.passed:
        ...     print("Playable validated successfully!")
        ... else:
        ...     print(f"Validation failed: {result.error_message}")
    """
    logger.info("=== Playable Validator - Main VLM Validation ===")
    
    # Prepare Playwright container with game files
    logger.info("Preparing Playwright container with built game from dist/...")
    playwright_container.reset()  # Reset to clean state
    # Use built game from dist/ directory (after TypeScript compilation)
    playwright_container.copy_directory(
        workspace.container().directory("dist")
    ).with_test_script(TEST_SCRIPT)
    
    # Run browser tests to get screenshot and console logs
    logger.info("Running browser tests on generated game...")
    test_result = await validate_game_in_workspace(playwright_container)
    
    # Validate with VLM
    logger.info("Validating playable with VLM...")
    
    is_valid, reason = validate_playable_with_vlm(
        vlm_client=vlm_client,
        screenshot_bytes=test_result.screenshot_bytes,
        console_logs=test_result.console_logs,
        user_prompt=task_description,
        template_str=VLM_PLAYABLE_VALIDATION_PROMPT,
        session_id=session_id,
        is_feedback_mode=is_feedback_mode,
        original_prompt=original_prompt if is_feedback_mode else None,
        test_run_id=test_run_id
    )
    
    if not is_valid:
        logger.warning(f"❌ VLM validation failed: {reason}")
        
        # Format console logs for feedback
        if test_result.console_logs:
            console_logs_formatted = "  " + "\n  ".join(test_result.console_logs)
        else:
            console_logs_formatted = "  No console logs captured."
        
        # Create formatted error message for LLM with VLM reason and console logs
        error_message = FEEDBACK_VALIDATION_FAILED.format(
            reason=reason,
            console_logs=console_logs_formatted
        )
        
        return ValidationResult(
            passed=False,
            error_message=error_message,
            failures=[reason],
            retry_count=retry_count + 1
        )
    
    # VLM validation passed!
    logger.info("✅ VLM validation passed! Game is correct.")
    
    return ValidationResult(
        passed=True,
        error_message=None,
        failures=[],
        retry_count=0  # Reset retry count on success
    )

