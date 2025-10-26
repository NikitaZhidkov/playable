# Debug Screenshot Organization

## Overview

Debug screenshots and test case files are now organized by session ID in the `temp/` folder, making it easier to debug issues after work by grouping all debug artifacts for a specific session together.

## Directory Structure

Previously, debug screenshots were stored in:
```
temp/debug_images/<timestamp>/
  - screenshot_<timestamp>_<ms>.png
```

Now, debug files are organized by session:
```
temp/<session_id>/
  ├── screenshots/
  │   ├── main_validation_<timestamp>_<ms>.png
  │   ├── test_case_1_<timestamp>_<ms>.png
  │   ├── test_case_2_<timestamp>_<ms>.png
  │   └── ...
  └── test_cases/
      ├── test_case_1_<timestamp>.json
      ├── test_case_2_<timestamp>.json
      └── ...
```

Where `<session_id>` has the format: `YYYYMMDD_HHMMSS_<uuid>` (e.g., `20251025_120000_abc123`)

## What Gets Saved

### 1. Main Validation Screenshot
- **Location**: `temp/<session_id>/screenshots/main_validation_*.png`
- **When**: During initial VLM validation (before test cases)
- **Contents**: Screenshot of the game after initial generation
- **Note**: No test case JSON for this screenshot as it's the first validation

### 2. Test Case Screenshots
- **Location**: `temp/<session_id>/screenshots/test_case_N_*.png`
- **When**: During each test case validation
- **Contents**: Screenshot of the game with the test case state loaded

### 3. Test Case JSON Files
- **Location**: `temp/<session_id>/test_cases/test_case_N_*.json`
- **When**: During each test case validation
- **Contents**: The actual test case JSON that was used to load the game state

## Benefits

1. **Easy Debugging**: All debug artifacts for a session are in one place
2. **Session Correlation**: Match debug screenshots with game outputs in `games/<session_id>/`
3. **Test Case Tracking**: See exactly what test case data was used for each screenshot
4. **Chronological History**: Multiple runs of the same test case are timestamped

## Code Changes

### Modified Functions

1. **`_save_debug_screenshot()`** in `vlm_utils.py`
   - Added optional `session_id` parameter
   - Saves to `temp/<session_id>/screenshots/` when session_id provided
   - Falls back to old behavior (`temp/debug_images/<timestamp>/`) when session_id is None

2. **`_save_test_case_json()`** in `vlm_utils.py` (NEW)
   - Saves test case JSON to `temp/<session_id>/test_cases/`
   - Called during test case validation

3. **`validate_playable_with_vlm()`** in `vlm_utils.py`
   - Added optional `session_id` parameter
   - Passes session_id to `_save_debug_screenshot()`

4. **`validate_test_case_with_vlm()`** in `vlm_utils.py`
   - Added optional `session_id` and `test_case_json` parameters
   - Saves both screenshot and test case JSON
   - Passes session_id to `_save_debug_screenshot()`

5. **`check_state()` node** in `agent_graph.py`
   - Updated VLM validation calls to pass `session_id` from state

## Backward Compatibility

All parameters are optional with default values, so:
- Existing tests continue to work without changes
- When `session_id` is not provided, the old behavior is used
- No breaking changes to the API

## Example Usage

```python
from vlm_utils import validate_playable_with_vlm, validate_test_case_with_vlm

# Main validation with session tracking
is_valid, reason = validate_playable_with_vlm(
    vlm_client=vlm_client,
    screenshot_bytes=screenshot_bytes,
    console_logs=console_logs,
    user_prompt=user_prompt,
    template_str=template,
    session_id="20251025_120000_abc123"  # NEW: optional session_id
)
# Screenshot saved to: temp/20251025_120000_abc123/screenshots/main_validation_*.png

# Test case validation with session tracking
is_valid, reason = validate_test_case_with_vlm(
    vlm_client=vlm_client,
    screenshot_bytes=screenshot_bytes,
    expected_output=expected_output,
    template_str=template,
    test_case_name="test_case_1",
    session_id="20251025_120000_abc123",  # NEW: optional session_id
    test_case_json=test_case_json  # NEW: optional test case JSON
)
# Screenshot saved to: temp/20251025_120000_abc123/screenshots/test_case_1_*.png
# Test case saved to: temp/20251025_120000_abc123/test_cases/test_case_1_*.json
```

## Cleanup

Debug files in `temp/` can be cleaned up periodically:
```bash
# Remove all debug files older than 7 days
find temp -type d -mtime +7 -exec rm -rf {} +

# Remove debug files for a specific session
rm -rf temp/20251025_120000_abc123
```

