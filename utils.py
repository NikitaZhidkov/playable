"""
Utility functions for playable validation and debugging.
"""
import re
import logging
from typing import Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_playable_with_vlm(
    vlm_client,
    screenshot_bytes: bytes,
    console_logs: list[str],
    user_prompt: str,
    template_str: str
) -> Tuple[bool, str]:
    """
    Validate a playable using Vision Language Model.
    
    Args:
        vlm_client: VLMClient instance
        screenshot_bytes: PNG screenshot bytes from browser
        console_logs: List of console logs from browser
        user_prompt: Original user prompt that generated the playable
        template_str: Jinja2 template string for the validation prompt
    
    Returns:
        Tuple of (is_valid: bool, reason: str)
    """
    try:
        # Save debug screenshot with timestamp
        debug_image_path = _save_debug_screenshot(screenshot_bytes)
        logger.info(f"Debug screenshot saved to: {debug_image_path}")
        
        # Format console logs for display
        if console_logs:
            formatted_logs = "\n".join(console_logs)
        else:
            formatted_logs = "No console logs captured."
        
        logger.info(f"Validating playable with VLM. Console logs: {len(console_logs)} entries")
        
        # Call VLM with screenshot and prompt
        vlm_response = vlm_client.validate_with_screenshot(
            screenshot_bytes=screenshot_bytes,
            console_logs=formatted_logs,
            user_prompt=user_prompt,
            template_str=template_str
        )
        
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


def _save_debug_screenshot(screenshot_bytes: bytes) -> Path:
    """
    Save screenshot to temp folder with timestamp for debugging.
    
    Args:
        screenshot_bytes: PNG screenshot bytes
    
    Returns:
        Path to saved screenshot
    """
    try:
        # Create timestamp-based subfolder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = Path("temp") / "debug_images" / timestamp
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Save screenshot
        screenshot_path = debug_dir / "screenshot.png"
        screenshot_path.write_bytes(screenshot_bytes)
        
        logger.debug(f"Screenshot saved to: {screenshot_path}")
        return screenshot_path
        
    except Exception as e:
        logger.warning(f"Failed to save debug screenshot: {e}")
        # Return a placeholder path even if saving fails
        return Path("temp/debug_images/failed_to_save.png")


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

