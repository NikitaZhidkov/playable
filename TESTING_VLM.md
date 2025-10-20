# VLM Integration Testing Guide

## Overview

This document describes the testing setup for VLM (Vision Language Model) screenshot validation.

## Test File

**Location**: `tests/integration/test_vlm_validation.py`

## Running Tests

### Run All VLM Tests
```bash
python -m pytest tests/integration/test_vlm_validation.py -v
```

### Run Specific Test
```bash
# Test with real Gemini API call
python -m pytest tests/integration/test_vlm_validation.py::test_vlm_validation_with_real_screenshot -v -s

# Test response parsing
python -m pytest tests/integration/test_vlm_validation.py::test_parse_vlm_response_valid -v

# Test bytes handling
python -m pytest tests/integration/test_vlm_validation.py::test_bytes_type_handling -v
```

## Tests Included

### 1. `test_vlm_validation_with_real_screenshot`
- **Purpose**: Full end-to-end test with real Gemini API call
- **Requirements**: `GEMINI_API_KEY` and `LLM_VISION_MODEL` in environment
- **What it tests**:
  - Creates a test image (red square)
  - Validates it's bytes type
  - Calls real Gemini API with VLM validation
  - Verifies response format (is_valid: bool, reason: str)
  - Prints actual VLM response

### 2. `test_parse_vlm_response_valid`
- **Purpose**: Test parsing valid VLM responses
- **What it tests**:
  - Parses `<answer>yes</answer>` correctly
  - Extracts reason from `<reason>` tags
  - Returns `is_valid=True`

### 3. `test_parse_vlm_response_invalid`
- **Purpose**: Test parsing invalid VLM responses
- **What it tests**:
  - Parses `<answer>no</answer>` correctly
  - Extracts reason from `<reason>` tags
  - Returns `is_valid=False`

### 4. `test_debug_screenshot_saving`
- **Purpose**: Test debug screenshot functionality
- **What it tests**:
  - Screenshots are saved to timestamped folders
  - Path format: `temp/debug_images/YYYYMMDD_HHMMSS/screenshot.png`
  - Saved images are valid PNG files
  - Images can be reopened and verified

### 5. `test_bytes_type_handling`
- **Purpose**: Test bytes vs string conversion
- **What it tests**:
  - Handles bytes input correctly
  - Converts string to bytes using latin-1 encoding
  - Preserves binary data through conversion
  - Images remain valid after conversion

## Fixes Applied

### Issue: TypeError in VLM validation
**Error**: `TypeError: a bytes-like object is required, not 'str'`

**Root Cause**: Dagger's `.contents()` method sometimes returns strings instead of bytes for binary files.

**Solution Applied** (`test_game.py` line 220-226):
```python
# Dagger .contents() returns bytes directly for binary files
screenshot_data = await executed_container.file("/app/screenshot.png").contents()
# Ensure we have bytes, not string
if isinstance(screenshot_data, str):
    screenshot_bytes = screenshot_data.encode('latin-1')  # Preserve binary data
else:
    screenshot_bytes = screenshot_data
```

### Issue: Protobuf version conflict
**Error**: `google-generativeai` requires `protobuf<6.0.0`, but `protobuf==6.32.1` was specified

**Solution**: Updated `requirements.txt` to use `protobuf==5.29.5`

## Test Results

All tests pass successfully:

```
============================= test session starts ==============================
collected 5 items

test_vlm_validation_with_real_screenshot PASSED [ 20%]
test_parse_vlm_response_valid PASSED [ 40%]
test_parse_vlm_response_invalid PASSED [ 60%]
test_debug_screenshot_saving PASSED [ 80%]
test_bytes_type_handling PASSED [100%]

============================== 5 passed in 4.88s
```

## Example VLM Response

When testing with a red screen:

```
✅ VLM Validation Result:
   Valid: True
   Reason: The screenshot shows a solid red screen, which fulfills the 
           prompt's request for a "simple red screen test." The console 
           logs are informational and a warning, neither of which indicate 
           a failure in the frontend code's ability to render a red screen.
```

## Debug Screenshots

Debug screenshots are automatically saved during validation:

```bash
$ ls -lh temp/debug_images/*/screenshot.png
-rw-r--r--  1 user  staff   2.7K Oct 20 22:56 temp/debug_images/20251020_225650/screenshot.png
-rw-r--r--  1 user  staff   287B Oct 20 22:57 temp/debug_images/20251020_225732/screenshot.png
```

Each timestamp folder contains the screenshot that was sent to the VLM for validation.

## Environment Requirements

### Required
- `GEMINI_API_KEY` - Your Gemini API key
- `LLM_VISION_MODEL` - Model name (defaults to "gemini-1.5-flash")

### Optional
Set in `.env` file or export in shell:
```bash
export GEMINI_API_KEY="your-key-here"
export LLM_VISION_MODEL="gemini-1.5-flash"
```

## Integration with Main System

These tests verify the core components used by the agent:

1. **VLMClient** (`llm_client.py`) - Gemini API integration
2. **Validation Logic** (`utils.py`) - VLM validation orchestration
3. **Screenshot Handling** (`test_game.py`) - Playwright screenshot capture
4. **Debug Saving** (`utils.py`) - Timestamped screenshot storage

## Continuous Testing

To ensure the system works correctly:

1. Run these tests after any changes to VLM integration
2. Check debug screenshots in `temp/debug_images/` if validation fails
3. Monitor VLM responses for quality of feedback
4. Verify protobuf version compatibility when updating dependencies

## Notes

- Tests use real API calls (costs apply for Gemini API usage)
- `temp/` folder is gitignored and won't be committed
- Screenshots are saved with microsecond precision timestamps
- latin-1 encoding preserves all byte values (0-255) for PNG data

