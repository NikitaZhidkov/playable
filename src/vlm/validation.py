"""
VLM validation utilities for playable testing and validation.
"""
import re
import io
import logging
from typing import Tuple
from pathlib import Path
from datetime import datetime
from PIL import Image
from jinja2 import Template

logger = logging.getLogger(__name__)


def validate_playable_with_vlm(
    vlm_client,
    screenshot_bytes: bytes,
    console_logs: list[str],
    user_prompt: str,
    template_str: str,
    session_id: str = None,
    is_feedback_mode: bool = False,
    original_prompt: str = None,
    test_run_id: str = None
) -> Tuple[bool, str]:
    """
    Validate a playable using Vision Language Model.
    
    Args:
        vlm_client: VLMClient instance
        screenshot_bytes: PNG screenshot bytes from browser
        console_logs: List of console logs from browser
        user_prompt: Original user prompt that generated the playable (or feedback if feedback mode)
        template_str: Jinja2 template string for the validation prompt
        session_id: Session ID for organizing debug files (optional)
        is_feedback_mode: Whether this is a feedback iteration (optional)
        original_prompt: Original game creation prompt (used in feedback mode, optional)
        test_run_id: Test run timestamp for organizing files (optional, will create new if None)
    
    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    try:
        # Save debug screenshot with timestamp
        debug_image_path = _save_debug_screenshot(screenshot_bytes, "main_validation", session_id, test_run_id)
        logger.info(f"Debug screenshot saved to: {debug_image_path}")
        
        # Format console logs for display
        if console_logs:
            formatted_logs = "\n".join(console_logs)
        else:
            formatted_logs = "No console logs captured."
        
        logger.info(f"Validating playable with VLM. Console logs: {len(console_logs)} entries")
        if is_feedback_mode:
            logger.info(f"Feedback mode: original='{original_prompt[:50]}...', feedback='{user_prompt[:50]}...'")
        
        # Render the template with context
        template = Template(template_str)
        rendered_prompt = template.render(
            user_prompt=user_prompt,
            console_logs=formatted_logs,
            is_feedback_mode=is_feedback_mode,
            original_prompt=original_prompt or user_prompt
        )
        
        logger.debug(f"Rendered VLM prompt: {rendered_prompt[:200]}...")
        
        # Call VLM with screenshot and rendered prompt
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        response = vlm_client.model.generate_content([rendered_prompt, image])
        vlm_response = response.text
        
        # Parse response to extract answer and reason
        is_valid, reason = _parse_vlm_response(vlm_response)
        
        if is_valid:
            logger.info(f"✅ VLM validation passed: {reason}")
        else:
            logger.warning(f"❌ VLM validation failed: {reason}")
        
        return is_valid, reason
        
    except Exception as e:
        error_msg = f"VLM validation error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def validate_test_case_with_vlm(
    vlm_client,
    screenshot_bytes: bytes,
    expected_output: str,
    template_str: str,
    test_case_name: str = "test_case",
    session_id: str = None,
    test_case_json: str = None,
    test_run_id: str = None
) -> Tuple[bool, str]:
    """
    Validate a test case using Vision Language Model.
    
    Args:
        vlm_client: VLMClient instance
        screenshot_bytes: PNG screenshot bytes from browser
        expected_output: Expected output description from test case
        template_str: Jinja2 template string for the validation prompt
        test_case_name: Name of the test case for logging/debugging
        session_id: Session ID for organizing debug files (optional)
        test_case_json: Test case JSON content to save alongside screenshot (optional)
        test_run_id: Test run timestamp for organizing files (optional, will create new if None)
    
    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    try:
        logger.info(f"Validating test case with VLM. Expected: {expected_output[:100]}...")
        
        # Save debug screenshot with test case name
        debug_image_path = _save_debug_screenshot(screenshot_bytes, test_case_name, session_id, test_run_id)
        logger.info(f"Debug screenshot for {test_case_name} saved to: {debug_image_path}")
        
        # Save test case JSON alongside screenshot if provided
        if test_case_json and session_id:
            _save_test_case_json(test_case_json, test_case_name, session_id, test_run_id)
            logger.info(f"Test case JSON for {test_case_name} saved to debug folder")
        
        # Render the prompt template
        template = Template(template_str)
        rendered_prompt = template.render(expected_output=expected_output)
        
        logger.debug(f"Rendered test case prompt: {rendered_prompt[:200]}...")
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        # Call VLM directly with the image and prompt
        # Note: We're not using validate_with_screenshot because we don't need console logs
        from src.vlm.client import VLMClient
        if not isinstance(vlm_client, VLMClient):
            # Create client if needed
            vlm_client = VLMClient()
        
        response = vlm_client.model.generate_content([rendered_prompt, image])
        vlm_response = response.text
        
        logger.info("VLM test case validation response received")
 
        # Parse response to extract answer and reason
        is_valid, reason = _parse_vlm_response(vlm_response)
        
        if is_valid:
            logger.info(f"✅ VLM test case validation passed: {reason}")
        else:
            logger.warning(f"❌ VLM test case validation failed: {reason}")
        
        return is_valid, reason
        
    except Exception as e:
        error_msg = f"VLM test case validation error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def save_test_case_error(
    test_case_name: str,
    expected_output: str,
    actual_output: str,
    error_message: str,
    session_id: str,
    test_run_id: str = None
) -> Path:
    """
    Save test case failure information for debugging.
    
    Args:
        test_case_name: Name of the test case (e.g., "test_case_1")
        expected_output: Expected output from test case
        actual_output: Actual output observed by VLM
        error_message: Full error message
        session_id: Session ID for organizing debug files
        test_run_id: Test run timestamp for organizing files (optional, will create new if None)
    
    Returns:
        Path to saved error file
    """
    try:
        # Get test run directory
        debug_dir = _get_test_run_dir(session_id, test_run_id)
        
        # Create error content
        error_content = f"""Test Case Failure Report
========================

Test Case: {test_case_name}
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Expected Output:
{expected_output}

Actual Output (VLM Observation):
{actual_output}

Error Message:
{error_message}
"""
        
        # Save error with simple naming: test_case_1_error.txt
        filename = f"{test_case_name}_error.txt"
        error_path = debug_dir / filename
        error_path.write_text(error_content, encoding='utf-8')
        
        logger.info(f"Test case error saved to: {error_path}")
        return error_path
        
    except Exception as e:
        logger.warning(f"Failed to save test case error: {e}")
        return Path("temp/test_cases/failed_to_save_error.txt")


def _parse_vlm_response(response_text: str) -> Tuple[bool, str]:
    """
    Parse VLM response to extract answer and reason tags.
    
    Args:
        response_text: Raw response text from VLM
    
    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    try:
        # Extract <answer> tag
        answer_match = re.search(r'<answer>\s*(yes|no)\s*</answer>', response_text, re.IGNORECASE)
        if not answer_match:
            logger.warning(f"Could not find <answer> tag in VLM response: {response_text[:200]}...")
            return False, f"Invalid VLM response format: {response_text[:200]}..."
        
        answer = answer_match.group(1).lower()
        is_valid = answer == "yes"
        
        # Extract <reason> tag
        reason_match = re.search(r'<reason>\s*(.*?)\s*</reason>', response_text, re.IGNORECASE | re.DOTALL)
        if reason_match:
            reason = reason_match.group(1).strip()
        else:
            # Fallback: use the whole response if no reason tag found
            reason = response_text.strip()
            logger.warning(f"Could not find <reason> tag, using full response")
        
        return is_valid, reason
        
    except Exception as e:
        logger.error(f"Failed to parse VLM response: {e}", exc_info=True)
        return False, f"Failed to parse VLM response: {str(e)}"


def _get_test_run_dir(session_id: str, test_run_id: str = None) -> Path:
    """
    Get or create a test run directory for organizing debug files.
    
    Args:
        session_id: Session ID (game ID)
        test_run_id: Test run timestamp (if None, creates a new one)
    
    Returns:
        Path to test run directory
    """
    if not test_run_id:
        # Create new test run timestamp
        test_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    test_run_dir = Path("games") / session_id / "debug" / test_run_id
    test_run_dir.mkdir(parents=True, exist_ok=True)
    return test_run_dir


def _save_debug_screenshot(screenshot_bytes: bytes, name_prefix: str = "screenshot", session_id: str = None, test_run_id: str = None) -> Path:
    """
    Save screenshot to temp folder with timestamp for debugging.
    
    Args:
        screenshot_bytes: PNG screenshot bytes
        name_prefix: Prefix for the screenshot filename (default: "screenshot")
        session_id: Session ID for organizing debug files (optional)
        test_run_id: Test run timestamp for organizing files (optional, will create new if None)
    
    Returns:
        Path to saved screenshot
    """
    try:
        # If session_id provided, use new test run structure
        if session_id:
            debug_dir = _get_test_run_dir(session_id, test_run_id)
            
            # Use simpler naming for main validation vs test cases
            if name_prefix == "main_validation":
                filename = "debug_image.png"
            else:
                # For test cases: test_case_1_screenshot.png
                filename = f"{name_prefix}_screenshot.png"
        else:
            # Fallback to old timestamp-based structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_dir = Path("temp") / "debug_images" / timestamp
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            microseconds = datetime.now().strftime("%f")[:3]
            filename = f"{name_prefix}_{timestamp}_{microseconds}.png"
        
        screenshot_path = debug_dir / filename
        screenshot_path.write_bytes(screenshot_bytes)
        
        logger.debug(f"Screenshot saved to: {screenshot_path}")
        return screenshot_path
        
    except Exception as e:
        logger.warning(f"Failed to save debug screenshot: {e}")
        # Return a placeholder path even if saving fails
        return Path("temp/debug_images/failed_to_save.png")


def _save_test_case_json(test_case_json: str, test_case_name: str, session_id: str, test_run_id: str = None) -> Path:
    """
    Save test case JSON to temp folder for debugging.
    
    Args:
        test_case_json: Test case JSON content
        test_case_name: Name of the test case (e.g., "test_case_1")
        session_id: Session ID for organizing debug files
        test_run_id: Test run timestamp for organizing files (optional, will create new if None)
    
    Returns:
        Path to saved test case JSON
    """
    try:
        # Get test run directory
        debug_dir = _get_test_run_dir(session_id, test_run_id)
        
        # Save test case with simple naming: test_case_1.json
        filename = f"{test_case_name}.json"
        test_case_path = debug_dir / filename
        test_case_path.write_text(test_case_json, encoding='utf-8')
        
        logger.debug(f"Test case JSON saved to: {test_case_path}")
        return test_case_path
        
    except Exception as e:
        logger.warning(f"Failed to save test case JSON: {e}")
        return Path("temp/test_cases/failed_to_save.json")

