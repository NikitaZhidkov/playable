"""
Test case validator for test case execution and VLM validation.

This module handles the validation of test cases:
- Discovers test case files (test_case_*.json)
- Validates test case count and format
- Executes each test case with Playwright
- Validates test case results with VLM
"""
import logging
import json
from src.validators.base import ValidationResult
from test_game import validate_game_with_test_case
from src.vlm import validate_test_case_with_vlm, save_test_case_error, VLM_TEST_CASE_VALIDATION_PROMPT

logger = logging.getLogger(__name__)


async def validate_test_cases(
    workspace,
    playwright_container,
    vlm_client,
    session_id: str,
    test_run_id: str,
    retry_count: int = 0
) -> ValidationResult:
    """
    Discover and validate all test cases.
    
    This function performs the following steps:
    1. Discover test case files (test_case_*.json) at root level
    2. Validate test case count (require 1-5)
    3. For each test case in order (1 -> 5):
       a. Read and parse test case JSON
       b. Validate expectedOutput field exists
       c. Run test case with Playwright
       d. Validate result with VLM
    4. Stop on first failure to save time
    
    Args:
        workspace: The Dagger workspace container with the game
        playwright_container: PlaywrightContainer for running browser tests
        vlm_client: VLMClient for validation
        session_id: Current session ID for debugging
        test_run_id: Test run ID for organizing debug files
        retry_count: Current retry attempt number (default: 0)
    
    Returns:
        ValidationResult with:
            - passed=True if all test cases pass
            - passed=False with error_message if any test case fails
    
    Example:
        >>> result = await validate_test_cases(
        ...     workspace=workspace,
        ...     playwright_container=container,
        ...     vlm_client=vlm_client,
        ...     session_id="20231025_120000",
        ...     test_run_id="20231025_120030"
        ... )
        >>> if result.passed:
        ...     print("All test cases passed!")
        ... else:
        ...     print(f"Test case failed: {result.error_message}")
    """
    logger.info("=== Test Case Validator - Running Test Case Validation ===")
    
    # Discover test case files (at root level)
    try:
        test_case_files = await workspace.list_files("test_case_*.json")
        # Sort test cases to ensure they run in order (1 -> 5)
        test_case_files = sorted(test_case_files)
        logger.info(f"Found {len(test_case_files)} test case files (sorted): {test_case_files}")
    except Exception as e:
        logger.error(f"Error discovering test case files: {e}")
        test_case_files = []
    
    # Validate test case count (require 1-5)
    if len(test_case_files) == 0:
        logger.error("❌ No test cases found! At least 1 test case is required.")
        error_msg = "Test case validation failed: No test cases found. You must create 1-5 test cases at the ROOT level (test_case_1.json through test_case_5.json, same directory as index.html)."
        return ValidationResult(
            passed=False,
            error_message=error_msg,
            failures=["Missing test cases (required: 1-5)"],
            retry_count=retry_count + 1
        )
    
    if len(test_case_files) > 5:
        logger.warning(f"Found {len(test_case_files)} test cases, but maximum is 5. Using first 5.")
        test_case_files = test_case_files[:5]
    
    # Run each test case in order (1 -> 5)
    # Stop on first failure to save time
    for test_case_file in test_case_files:
        test_case_name = test_case_file.split('/')[-1].replace('.json', '')
        logger.info(f"Running test case: {test_case_name}")
        
        try:
            # Read test case JSON from workspace
            test_case_json = await workspace.read_file(test_case_file)
            test_case_data = json.loads(test_case_json)
            
            # Extract expected output
            expected_output = test_case_data.get("expectedOutput", "")
            if not expected_output:
                logger.warning(f"Test case {test_case_name} missing 'expectedOutput' field")
                failure_msg = f"{test_case_name}: Missing 'expectedOutput' field in test case JSON"
                
                # Save test case error for debugging
                save_test_case_error(
                    test_case_name=test_case_name,
                    expected_output="(missing)",
                    actual_output="N/A - test case validation error",
                    error_message=failure_msg,
                    session_id=session_id,
                    test_run_id=test_run_id
                )
                
                # Return with error
                error_msg = f"Test case validation failed: {failure_msg}\n\nPlease fix the test case and try again."
                return ValidationResult(
                    passed=False,
                    error_message=error_msg,
                    failures=[failure_msg],
                    retry_count=retry_count + 1
                )
            
            # Prepare fresh Playwright container for this test case
            test_case_container = playwright_container
            test_case_container.reset()
            test_case_container.copy_directory(
                workspace.container().directory(".")
            )
            
            # Run test with test case loaded
            test_case_result = await validate_game_with_test_case(
                container=test_case_container,
                test_case_json=test_case_json,
                test_case_name=test_case_name
            )
            
            # Check for errors in loading test case
            if test_case_result.errors:
                logger.warning(f"Test case {test_case_name} had errors: {test_case_result.errors}")
                failure_msg = f"{test_case_name}: {', '.join(test_case_result.errors)}"
                
                # Save test case error for debugging
                save_test_case_error(
                    test_case_name=test_case_name,
                    expected_output=expected_output,
                    actual_output="N/A - test case loading error",
                    error_message=failure_msg + "\n\nErrors:\n" + "\n".join(test_case_result.errors),
                    session_id=session_id,
                    test_run_id=test_run_id
                )
                
                # Return with error
                error_msg = f"Test case validation failed: {failure_msg}\n\nPlease fix the issues and try again."
                return ValidationResult(
                    passed=False,
                    error_message=error_msg,
                    failures=[failure_msg],
                    retry_count=retry_count + 1
                )
            
            # Validate with VLM
            is_test_case_valid, test_case_reason = validate_test_case_with_vlm(
                vlm_client=vlm_client,
                screenshot_bytes=test_case_result.screenshot_bytes,
                expected_output=expected_output,
                template_str=VLM_TEST_CASE_VALIDATION_PROMPT,
                test_case_name=test_case_name,
                session_id=session_id,
                test_case_json=test_case_json,
                test_run_id=test_run_id
            )
            
            if is_test_case_valid:
                logger.info(f"✅ Test case {test_case_name} passed")
                # Test case passed - continue to next test case
            else:
                logger.warning(f"❌ Test case {test_case_name} failed: {test_case_reason}")
                failure_msg = f"{test_case_name} failed: Expected '{expected_output}' but VLM observed '{test_case_reason}'"
                
                # Save test case error for debugging
                save_test_case_error(
                    test_case_name=test_case_name,
                    expected_output=expected_output,
                    actual_output=test_case_reason,
                    error_message=failure_msg,
                    session_id=session_id,
                    test_run_id=test_run_id
                )
                
                # Return with error (stop executing other test cases)
                logger.info(f"Test case retry attempt {retry_count + 1}/5")
                error_msg = f"Test case validation failed: {failure_msg}\n\nPlease fix the issues and update the test case if needed."
                return ValidationResult(
                    passed=False,
                    error_message=error_msg,
                    failures=[failure_msg],
                    retry_count=retry_count + 1
                )
                
        except Exception as e:
            logger.error(f"Error running test case {test_case_name}: {e}", exc_info=True)
            failure_msg = f"{test_case_name}: Error running test case: {str(e)}"
            
            # Save test case error for debugging
            save_test_case_error(
                test_case_name=test_case_name,
                expected_output=expected_output if 'expected_output' in locals() else "(unknown)",
                actual_output="N/A - exception occurred",
                error_message=failure_msg + f"\n\nException:\n{str(e)}",
                session_id=session_id,
                test_run_id=test_run_id
            )
            
            # Return with error
            error_msg = f"Test case validation failed: {failure_msg}\n\nPlease fix the error and try again."
            return ValidationResult(
                passed=False,
                error_message=error_msg,
                failures=[failure_msg],
                retry_count=retry_count + 1
            )
    
    # All tests passed!
    logger.info("✅ All test cases passed! Game is fully validated.")
    
    return ValidationResult(
        passed=True,
        error_message=None,
        failures=[],
        retry_count=0  # Reset retry count on success
    )

