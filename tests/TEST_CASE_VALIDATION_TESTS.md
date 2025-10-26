# Test Case Validation Tests

This document describes the unit and integration tests for the test case validation functionality.

## Test Files

### 1. `tests/test_test_case_validation.py` - Unit Tests

**Purpose:** Test individual components of the test case validation system.

**Tests included:**

- **`test_validate_game_with_test_case_basic`** - Tests basic test case loading and validation
- **`test_validate_game_with_test_case_missing_function`** - Tests error handling when `window.loadTestCase` is missing
- **`test_validate_game_with_test_case_invalid_json`** - Tests handling of invalid JSON in test cases
- **`test_test_script_with_test_case_defined`** - Verifies `TEST_SCRIPT_WITH_TEST_CASE` is properly defined
- **`test_save_debug_screenshot_with_prefix`** - Tests screenshot saving with custom name prefixes
- **`test_parse_vlm_response_success`** - Tests VLM response parsing for successful validation
- **`test_parse_vlm_response_failure`** - Tests VLM response parsing for failed validation
- **`test_parse_vlm_response_case_insensitive`** - Tests case-insensitive VLM response parsing
- **`test_parse_vlm_response_invalid_format`** - Tests handling of invalid VLM response formats
- **`test_list_files_pattern_matching`** - Tests file discovery with glob patterns
- **`test_list_files_no_matches`** - Tests behavior when no files match pattern
- **`test_list_files_subdirectory_pattern`** - Tests file discovery in subdirectories

### 2. `tests/integration/test_test_case_flow.py` - Integration Tests

**Purpose:** Test the complete end-to-end test case validation flow.

**Tests included:**

- **`test_full_test_case_validation_flow`** - Complete flow: create game → load test case → validate
- **`test_test_case_validation_with_mock_vlm`** - Tests VLM integration with mocked VLM client
- **`test_multiple_test_cases_discovery`** - Tests discovering multiple test case files
- **`test_test_case_movement_to_debug_folder`** - Tests moving test cases to `debug_tests/` after completion
- **`test_test_case_count_validation`** - Tests validation of test case count (1-5 required)
- **`test_test_case_with_pixi_game`** - Integration test with real PixiJS game

## Running the Tests

### Run All Tests
```bash
# From project root, with venv activated
pytest tests/
```

### Run Only Unit Tests
```bash
pytest tests/test_test_case_validation.py -v
```

### Run Only Integration Tests
```bash
pytest tests/integration/test_test_case_flow.py -v
```

### Run Specific Test
```bash
pytest tests/test_test_case_validation.py::test_save_debug_screenshot_with_prefix -v
```

### Run with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run with Verbose Output
```bash
pytest tests/ -v -s
```

## Test Coverage

The tests cover:

### Core Functionality
- ✅ Test case loading via `window.loadTestCase()`
- ✅ Test case JSON parsing
- ✅ Game state pause requirement
- ✅ Screenshot capture with test cases
- ✅ Console log capture during test case execution

### VLM Integration
- ✅ VLM response parsing (`<answer>` and `<reason>` tags)
- ✅ Case-insensitive parsing
- ✅ Invalid response handling
- ✅ Screenshot validation with expected output comparison

### File Management
- ✅ Test case file discovery with glob patterns
- ✅ Multiple test case handling (1-5 requirement)
- ✅ Test case movement to `debug_tests/` folder
- ✅ Debug screenshot saving with timestamps

### Error Handling
- ✅ Missing `window.loadTestCase` function
- ✅ Invalid JSON test cases
- ✅ No test cases found (validation error)
- ✅ Too many test cases (limit to 5)

### Game Integration
- ✅ Simple HTML games
- ✅ JavaScript games with state
- ✅ PixiJS games with graphics
- ✅ Game pause during test case loading

## Test Architecture

### Unit Tests
- Fast, isolated tests
- Mock external dependencies (VLM, file system where appropriate)
- Test individual functions and components
- No network calls

### Integration Tests
- Test complete workflows
- Use real Dagger/Playwright containers
- Test interactions between components
- Verify end-to-end functionality

### Fixtures (from `conftest.py`)
- `dagger_client` - Provides Dagger client for container operations
- `playwright_container` - Provides fresh Playwright container for each test

## Expected Test Results

All tests should pass. If any tests fail:

1. **Check Dagger installation** - Integration tests require Dagger
2. **Check network connectivity** - Some tests load PixiJS from CDN
3. **Check permissions** - Tests create temporary files/directories
4. **Check Python dependencies** - Ensure all requirements are installed

## Adding New Tests

When adding new test case validation features:

1. **Add unit tests** to `test_test_case_validation.py` for new functions
2. **Add integration tests** to `test_test_case_flow.py` for new workflows
3. **Update this documentation** with new test descriptions
4. **Ensure all tests pass** before committing

## Debugging Tests

### View Full Output
```bash
pytest tests/ -v -s --tb=short
```

### Run Single Test with Debugging
```bash
pytest tests/test_test_case_validation.py::test_name -v -s
```

### Check Test Coverage
```bash
pytest tests/ --cov=vlm_utils --cov=test_game --cov=agent_graph --cov-report=term-missing
```

## Notes

- Tests use temporary directories for file operations (auto-cleaned)
- Integration tests may take longer due to Playwright container operations
- Some tests require internet access (for CDN resources)
- VLM tests use mocks to avoid API costs
- Debug screenshots from tests are saved to `temp/debug_images/`

