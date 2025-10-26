# VLM Module Refactoring

## Overview

Reorganized all VLM (Vision Language Model) related code into a dedicated `src/vlm/` module, similar to the `src/containers/` structure.

## Changes Made

### New Module Structure

Created `src/vlm/` folder with the following files:

1. **`client.py`** - VLM client for Gemini API
   - `VLMClient` class (moved from `llm_client.py`)
   - Handles interaction with Google's Gemini Vision API
   - Provides `validate_with_screenshot()` method

2. **`validation.py`** - VLM validation functions
   - `validate_playable_with_vlm()` - Main game validation
   - `validate_test_case_with_vlm()` - Test case validation
   - `save_test_case_error()` - Error logging
   - Helper functions:
     - `_parse_vlm_response()` - Parse VLM XML responses
     - `_save_debug_screenshot()` - Save debug screenshots
     - `_save_test_case_json()` - Save test case files
     - `_get_test_run_dir()` - Manage test run directories

3. **`prompts.py`** - VLM prompt templates
   - `VLM_PLAYABLE_VALIDATION_PROMPT` - Main game validation prompt
   - `VLM_TEST_CASE_VALIDATION_PROMPT` - Test case validation prompt

4. **`__init__.py`** - Module exports
   - Exports all public classes and functions
   - Provides clean import interface

### Files Modified

1. **`src/agent_graph.py`**
   - Updated imports to use `from src.vlm import ...`
   - Now imports VLMClient, validation functions, and prompts from vlm module

2. **`src/llm_client.py`**
   - Removed `VLMClient` class (moved to vlm module)
   - Removed unused imports (genai, Template, Image, io)

3. **`src/playbook.py`**
   - Removed VLM validation prompts (moved to vlm module)

4. **`src/asset_manager.py`**
   - Updated import: `from src.vlm import VLMClient`

5. **Test Files Updated:**
   - `tests/integration/test_vlm_validation.py`
   - `tests/integration/test_test_case_flow.py`
   - `tests/integration/test_full_screenshot_flow.py`
   - `tests/test_test_case_validation.py`
   - All updated to import from `src.vlm`

### Files Deleted

- **`src/vlm_utils.py`** - All functionality moved to `src/vlm/` module

## New Import Pattern

### Before
```python
from src.llm_client import VLMClient
from src.vlm_utils import validate_playable_with_vlm, validate_test_case_with_vlm, save_test_case_error
from src.playbook import VLM_PLAYABLE_VALIDATION_PROMPT, VLM_TEST_CASE_VALIDATION_PROMPT
```

### After
```python
from src.vlm import (
    VLMClient,
    validate_playable_with_vlm,
    validate_test_case_with_vlm,
    save_test_case_error,
    VLM_PLAYABLE_VALIDATION_PROMPT,
    VLM_TEST_CASE_VALIDATION_PROMPT
)
```

For internal functions:
```python
from src.vlm.validation import _parse_vlm_response, _save_debug_screenshot
```

## Benefits

1. **Better Organization**: All VLM-related code is now in one place
2. **Cleaner Imports**: Single import source for all VLM functionality
3. **Separation of Concerns**: VLM logic separated from LLM client and general utilities
4. **Consistent Structure**: Matches the `containers/` module pattern
5. **Easier Maintenance**: Clear module boundaries make code easier to understand and modify

## Testing

All existing tests pass with the new import structure:
- ✅ VLM validation tests
- ✅ Test case validation tests
- ✅ Full screenshot flow tests
- ✅ All imports verified working

## Module Structure Comparison

```
src/
├── containers/          # Container management
│   ├── __init__.py
│   ├── base_container.py
│   ├── workspace.py
│   └── playwright_container.py
├── vlm/                # VLM functionality (NEW)
│   ├── __init__.py
│   ├── client.py
│   ├── validation.py
│   └── prompts.py
├── agent_graph.py
├── llm_client.py
└── ...
```

This refactoring follows the same organizational pattern established with the `containers` module.

