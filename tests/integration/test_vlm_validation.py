"""
Integration test for VLM validation with real Gemini API calls.
Tests the full flow: screenshot capture -> VLM validation -> result parsing.
"""
import pytest
import asyncio
from pathlib import Path
from llm_client import VLMClient
from utils import validate_playable_with_vlm, _parse_vlm_response, _save_debug_screenshot
from playbook import PLAYABLE_VALIDATION_PROMPT
from PIL import Image
import io


@pytest.mark.asyncio
async def test_vlm_validation_with_real_screenshot():
    """
    Test VLM validation with a real screenshot and Gemini API call.
    This test requires GEMINI_API_KEY to be set in environment.
    """
    # Create a simple test image (red square)
    img = Image.new('RGB', (800, 600), color='red')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    screenshot_bytes = img_buffer.getvalue()
    
    # Verify we have bytes
    assert isinstance(screenshot_bytes, bytes), "Screenshot should be bytes"
    assert len(screenshot_bytes) > 0, "Screenshot should not be empty"
    
    # Initialize VLM client
    try:
        vlm_client = VLMClient()
    except ValueError as e:
        pytest.skip(f"Skipping test: {e}. Set GEMINI_API_KEY to run this test.")
    
    # Test data
    console_logs = [
        "[INFO] Game initialized",
        "[WARNING] Some warning message",
    ]
    user_prompt = "Create a simple red screen test"
    
    # Run validation
    is_valid, reason = validate_playable_with_vlm(
        vlm_client=vlm_client,
        screenshot_bytes=screenshot_bytes,
        console_logs=console_logs,
        user_prompt=user_prompt,
        template_str=PLAYABLE_VALIDATION_PROMPT
    )
    
    # Assertions
    assert isinstance(is_valid, bool), "is_valid should be a boolean"
    assert isinstance(reason, str), "reason should be a string"
    assert len(reason) > 0, "reason should not be empty"
    
    print(f"\n✅ VLM Validation Result:")
    print(f"   Valid: {is_valid}")
    print(f"   Reason: {reason}")


@pytest.mark.asyncio
async def test_parse_vlm_response_valid():
    """Test parsing a valid VLM response."""
    response_text = """
    <reason>the playable looks valid and matches the requirements</reason>
    <answer>yes</answer>
    """
    
    is_valid, reason = _parse_vlm_response(response_text)
    
    assert is_valid == True
    assert "valid" in reason.lower()


@pytest.mark.asyncio
async def test_parse_vlm_response_invalid():
    """Test parsing an invalid VLM response."""
    response_text = """
    <reason>there is nothing on the screenshot, blank page</reason>
    <answer>no</answer>
    """
    
    is_valid, reason = _parse_vlm_response(response_text)
    
    assert is_valid == False
    assert "nothing" in reason.lower()


@pytest.mark.asyncio
async def test_debug_screenshot_saving():
    """Test that debug screenshots are saved correctly."""
    # Create a test image
    img = Image.new('RGB', (100, 100), color='blue')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    screenshot_bytes = img_buffer.getvalue()
    
    # Save debug screenshot
    saved_path = _save_debug_screenshot(screenshot_bytes)
    
    # Assertions
    assert saved_path.exists(), "Debug screenshot should be saved"
    assert saved_path.suffix == '.png', "Screenshot should be PNG"
    assert "debug_images" in str(saved_path), "Should be in debug_images folder"
    
    # Verify the saved image is valid
    saved_img = Image.open(saved_path)
    assert saved_img.size == (100, 100)
    
    print(f"\n✅ Debug screenshot saved to: {saved_path}")


@pytest.mark.asyncio
async def test_bytes_type_handling():
    """Test that we properly handle bytes vs string for screenshots."""
    # Create test image bytes
    img = Image.new('RGB', (50, 50), color='green')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    screenshot_bytes = img_buffer.getvalue()
    
    # Test 1: bytes input (correct)
    assert isinstance(screenshot_bytes, bytes)
    image = Image.open(io.BytesIO(screenshot_bytes))
    assert image.size == (50, 50)
    
    # Test 2: string input (what we might get from Dagger)
    # Simulate what might come from Dagger if it returns string
    screenshot_string = screenshot_bytes.decode('latin-1')
    assert isinstance(screenshot_string, str)
    
    # Convert back to bytes
    converted_bytes = screenshot_string.encode('latin-1')
    image2 = Image.open(io.BytesIO(converted_bytes))
    assert image2.size == (50, 50)
    
    print("\n✅ Bytes/string conversion works correctly")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_vlm_validation_with_real_screenshot())
    asyncio.run(test_parse_vlm_response_valid())
    asyncio.run(test_parse_vlm_response_invalid())
    asyncio.run(test_debug_screenshot_saving())
    asyncio.run(test_bytes_type_handling())

