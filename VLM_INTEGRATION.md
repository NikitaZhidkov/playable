# VLM Screenshot Validation Integration

## Overview

This document describes the VLM (Vision Language Model) integration for validating playable games using Gemini's vision capabilities.

## What Was Implemented

### 1. VLMClient (llm_client.py)
- New `VLMClient` class that uses Google's Gemini API
- `validate_with_screenshot()` method that:
  - Accepts screenshot bytes, console logs, and user prompt
  - Renders Jinja2 template with validation prompt
  - Sends screenshot + prompt to Gemini
  - Returns validation response

### 2. Enhanced Playwright Testing (test_game.py)
- Updated `TEST_SCRIPT` to capture full-page screenshots
- Modified to capture all console logs (errors, warnings, info)
- Updated `GameTestResult` class with:
  - `console_logs`: List of all captured logs
  - `screenshot_bytes`: PNG screenshot from browser
- `validate_game_in_workspace()` now extracts screenshot from container

### 3. VLM Validation Logic (utils.py)
- `validate_playable_with_vlm()`: Main validation function
- `_parse_vlm_response()`: Parses `<answer>` and `<reason>` tags
- `_save_debug_screenshot()`: Saves screenshots to timestamped folders
- Uses Jinja2 template rendering for prompt customization
- Returns tuple of (is_valid: bool, reason: str)
- Debug images saved to: `temp/debug_images/YYYYMMDD_HHMMSS/screenshot.png`

### 3b. Validation Prompts (playbook.py)
- Contains `PLAYABLE_VALIDATION_PROMPT` template
- Uses Jinja2 syntax for dynamic content

### 4. Agent Graph Integration (agent_graph.py)
- `test_node()` now:
  1. Initializes VLMClient
  2. Runs Playwright tests to get screenshot + logs
  3. Calls VLM validation with all data
  4. On validation failure, sends feedback with:
     - VLM's reason for rejection
     - Full console logs
     - Retry count
  5. Maintains existing retry logic (max 5 attempts)

### 5. Environment Configuration (ENV_TEMPLATE.txt)
- Added `GEMINI_API_KEY` for Gemini API access
- Added `LLM_VISION_MODEL` for model selection (default: gemini-1.5-flash)

## How It Works

1. **Game Generation**: Agent generates playable game code
2. **Browser Testing**: Playwright runs the game in a container
3. **Screenshot Capture**: Full-page screenshot is saved
4. **Log Collection**: All console messages are captured
5. **VLM Validation**: Gemini analyzes screenshot + logs against user prompt
6. **Feedback Loop**: If validation fails, VLM's reason is sent back to the coding agent
7. **Retry Logic**: Agent attempts to fix issues (max 5 retries)

## Key Features

✅ **Visual Validation**: VLM can see what the game looks like
✅ **Context-Aware**: Considers original user prompt and console logs
✅ **No False Positives**: WebGL warnings and infrastructure issues are evaluated in context
✅ **Detailed Feedback**: VLM provides human-readable reasons for failures
✅ **Automatic Retry**: Failed validations trigger fixes with specific feedback
✅ **Debug Screenshots**: Every validation saves screenshots to timestamped folders for debugging

## Environment Variables Required

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key-here

# Optional (defaults to gemini-1.5-flash)
LLM_VISION_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
```

## Testing

The VLM validation replaces the previous error-based validation. The system now:
- Always captures screenshots and logs
- Always asks VLM for validation (even if no errors)
- Uses VLM's judgment as the source of truth
- Provides richer feedback to the coding agent

## Debug Screenshots

Every validation automatically saves a screenshot to help with debugging:

**Location**: `temp/debug_images/YYYYMMDD_HHMMSS/screenshot.png`

**Example**:
```
temp/debug_images/20251020_143052/screenshot.png
temp/debug_images/20251020_143145/screenshot.png
temp/debug_images/20251020_143230/screenshot.png
```

Each folder is timestamped with the exact time of validation, making it easy to:
- Review what the VLM saw
- Debug visual issues
- Track validation history
- Compare successful vs failed validations

**Note**: The `temp/` folder is gitignored and won't be committed to version control.

## Dependencies Added

- `google-generativeai==0.8.5` - Gemini API client
- `jinja2==3.1.6` - Template rendering
- `pillow==12.0.0` - Image processing

## Files Modified

1. `llm_client.py` - Added VLMClient class
2. `test_game.py` - Enhanced screenshot capture and log collection
3. `utils.py` - **NEW FILE** VLM validation logic and debug image saving
4. `playbook.py` - Simplified to only contain validation prompt template
5. `agent_graph.py` - Integrated VLM into test flow
6. `ENV_TEMPLATE.txt` - Documented new environment variables
7. `requirements.txt` - Added new dependencies
8. `.gitignore` - Added temp/ folder for debug images

## Example Validation Flow

```
User: "Create a tic-tac-toe game"
  ↓
Agent generates game code
  ↓
Playwright runs game in browser
  ↓
Screenshot + logs captured
  ↓
VLM validates:
  - Does it look like tic-tac-toe?
  - Does it match the user's request?
  - Are errors critical or just warnings?
  ↓
If valid: ✅ Success!
If invalid: ❌ Retry with specific feedback
```

## Advantages Over Previous Validation

### Before (Error-Based)
- ❌ Couldn't detect visual issues
- ❌ False positives from infrastructure warnings
- ❌ No semantic understanding of "correct"
- ❌ Generic error messages

### After (VLM-Based)
- ✅ Validates visual appearance
- ✅ Ignores infrastructure warnings in context
- ✅ Understands if game matches user intent
- ✅ Provides specific, actionable feedback

