# Screenshot Capture Fix

## Problem

The system was failing to capture screenshots from the Playwright container with the error:
```
Browser test failed to capture screenshot. Please ensure the game generates a valid index.html file.
```

## Root Cause

The issue was in how we were extracting binary PNG files from the Dagger container:

1. **Dagger's `.contents()` behavior**: When calling `.contents()` on a binary file, Dagger tries to decode it as UTF-8 text, which fails for PNG files
2. **Encoding errors**: Attempting to encode/decode binary data as `latin-1` or `ISO-8859-1` failed with:
   ```
   'latin-1' codec can't encode character '\ufffd' in position 0: ordinal not in range(256)
   ```
3. **Unicode replacement character**: The `\ufffd` character is inserted when UTF-8 decoding fails on binary data

## Solution

Use Dagger's `.export()` method instead of `.contents()` for binary files:

```python
# ❌ OLD (Failed for binary files)
screenshot_data = await executed_container.file("/app/screenshot.png").contents()
screenshot_bytes = screenshot_data.encode('latin-1')  # Fails!

# ✅ NEW (Works correctly)
import tempfile
from pathlib import Path

with tempfile.TemporaryDirectory() as tmpdir:
    tmp_screenshot = Path(tmpdir) / "screenshot.png"
    await executed_container.file("/app/screenshot.png").export(str(tmp_screenshot))
    screenshot_bytes = tmp_screenshot.read_bytes()
```

## Changes Made

### 1. Fixed `test_game.py` (lines 237-251)
- Use `.export()` to save container file to temporary location
- Read the exported file as bytes using `Path.read_bytes()`
- This avoids Dagger's text decoding completely

### 2. Improved error handling in JavaScript test script
- Screenshot capture now happens in separate try/catch block
- Always attempts to capture screenshot, even if page load fails
- Better error messages when screenshot capture fails

### 3. Added comprehensive test suite

#### Unit Tests (`tests/test_screenshot_capture.py`)
- `test_screenshot_capture_with_simple_html` - Basic HTML screenshot ✅
- `test_screenshot_capture_with_no_html` - Error handling when no index.html ✅
- `test_screenshot_capture_with_javascript_game` - PixiJS game screenshot ✅
- `test_screenshot_bytes_type` - Type validation ✅

#### Integration Tests (`tests/integration/test_full_screenshot_flow.py`)
- `test_full_screenshot_to_vlm_flow` - Full end-to-end flow with VLM ✅
- `test_screenshot_capture_failure_handling` - Error scenarios ✅
- `test_missing_index_html` - Missing file handling ✅

## Test Results

All tests pass successfully:

```bash
# Unit tests (4 tests)
python -m pytest tests/test_screenshot_capture.py -v
# Result: 4 passed in 477.56s

# Integration tests (8 tests)
python -m pytest tests/integration/test_full_screenshot_flow.py tests/integration/test_vlm_validation.py -v
# Result: 8 passed in 358.78s
```

## Key Improvements

### Before
- ❌ Screenshot extraction failed with encoding errors
- ❌ No clear error messages
- ❌ No tests to verify screenshot capture
- ❌ Agent couldn't validate games visually

### After
- ✅ Screenshot extraction works reliably
- ✅ Clear error messages with directory listings
- ✅ Comprehensive test coverage (12 tests total)
- ✅ Full VLM validation pipeline works end-to-end
- ✅ Debug screenshots saved to `temp/debug_images/`

## Example Output

### Successful Screenshot Capture
```
📝 Step 1: Creating game HTML file...
   HTML file created in workspace

🎭 Step 2: Running Playwright tests...

📊 Test Results:
   Success: True
   Errors: 0
   Console logs: 2
   Screenshot captured: True

✅ Screenshot captured: 269505 bytes

🤖 Step 3: Validating with VLM...

📋 VLM Validation:
   Valid: True
   Reason: The screenshot shows a colorful gradient background and a white box 
           with the text "Test Game" and "Game Running!". This aligns with the 
           prompt's request for a "simple test game with a colorful gradient 
           background."
```

## Technical Details

### Why `.export()` Works

1. **Direct file transfer**: `.export()` writes the container file directly to the host filesystem
2. **No encoding**: Bypasses Dagger's text encoding/decoding logic
3. **Binary safe**: Works perfectly for all binary formats (PNG, JPG, PDF, etc.)
4. **Temporary files**: Uses Python's `tempfile.TemporaryDirectory()` for automatic cleanup

### Binary Data Flow

```
Container (/app/screenshot.png)
    ↓ .export()
Temp File (/tmp/xyz/screenshot.png)
    ↓ Path.read_bytes()
Python bytes object
    ↓
PIL Image / VLM validation
```

## Future Considerations

1. **Performance**: `.export()` requires writing to disk, but the overhead is minimal (< 1s for typical screenshots)
2. **Disk space**: Temporary files are automatically cleaned up by Python's `tempfile` module
3. **Error handling**: Added detailed logging of container file listings for debugging
4. **Compatibility**: Solution works across all platforms (Linux, macOS, Windows)

## Related Files

- `test_game.py` - Screenshot extraction logic
- `utils.py` - Debug screenshot saving
- `agent_graph.py` - VLM validation integration
- `tests/test_screenshot_capture.py` - Unit tests
- `tests/integration/test_full_screenshot_flow.py` - Integration tests
- `tests/integration/test_vlm_validation.py` - VLM tests

## Commands to Verify Fix

```bash
# Run screenshot unit tests
python -m pytest tests/test_screenshot_capture.py -v

# Run full integration test with VLM
python -m pytest tests/integration/test_full_screenshot_flow.py::test_full_screenshot_to_vlm_flow -v -s

# Run all VLM-related tests
python -m pytest tests/integration/ -v -k "vlm or screenshot"
```

## Conclusion

The screenshot capture system now works reliably by using Dagger's `.export()` method for binary files. All 12 tests pass, confirming that:

- Screenshots are captured correctly from Playwright containers
- Binary data is preserved without corruption  
- VLM validation receives valid PNG images
- Error handling works for edge cases
- Debug screenshots are saved for troubleshooting

The agent can now successfully validate generated games using visual inspection with Gemini VLM! 🎉

