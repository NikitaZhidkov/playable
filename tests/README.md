# Test Suite for Playable Game Generator

This directory contains comprehensive tests for the playable game generator project, separated into **unit tests** (fast, mocked) and **integration tests** (slower, real containers).

## Running Tests

### Run only unit tests (fast, recommended for development)
```bash
. .venv/bin/activate
pytest tests/ -v -m unit
```

### Run only integration tests (requires Docker/Dagger)
```bash
. .venv/bin/activate
pytest tests/integration/ -v -m integration
```

### Run all tests
```bash
. .venv/bin/activate
pytest tests/ -v
```

### Skip integration tests (default for CI)
```bash
. .venv/bin/activate
pytest tests/ -v -m "not integration"
```

### Run specific test file
```bash
. .venv/bin/activate
pytest tests/test_test_game.py -v
```

## Test Organization

### Unit Tests (`tests/test_test_game.py`)
- **Fast** - Run in < 3 seconds
- **No external dependencies** - Use mocks for Dagger/containers
- **Marked with** `@pytest.mark.unit`

### Integration Tests (`tests/integration/test_game_integration.py`)
- **Slower** - Pull Docker images, run real containers
- **Require Docker/Dagger** - Must have Docker daemon running
- **Marked with** `@pytest.mark.integration`
- **Real end-to-end testing** - Uses actual Workspace and Playwright containers

## Test Coverage

### test_test_game.py - Unit Tests (22 tests)

Tests for the `test_game.py` module which handles browser-based testing using Playwright.

#### GameTestResult Class (3 tests)
- ✅ Initialization with success
- ✅ Initialization with failures
- ✅ String representation

#### _parse_test_output Function (9 tests)
- ✅ Parse successful test output
- ✅ Parse failed test output with errors
- ✅ Parse output with console errors/warnings
- ✅ Handle missing result markers
- ✅ Handle missing start marker
- ✅ Handle missing end marker
- ✅ Handle invalid JSON
- ✅ Parse complex output with logs
- ✅ Parse test execution errors

#### TEST_SCRIPT Validation (3 tests)
- ✅ Contains required Playwright elements
- ✅ Has proper error handling (try/catch/finally)
- ✅ Outputs JSON results correctly

#### Integration Tests (2 tests)
- ✅ Complete workflow for successful games
- ✅ Complete workflow for failed games

#### validate_game_in_workspace Function - Mocked (5 tests)
- ✅ Successful game test with Playwright container
- ✅ Failed game test with error reporting
- ✅ Container execution exceptions
- ✅ Malformed test output handling
- ✅ Correct with_exec parameters (ReturnType.ANY)

### test_game_integration.py - Integration Tests (5 tests)

Tests real Workspace and Dagger container execution with actual Playwright.

#### validate_game_in_workspace - Real Containers (5 tests)
- ✅ Working game passes validation (simple HTML/JS game)
- ✅ Broken game fails with JavaScript errors detected
- ✅ Missing external resource detected
- ✅ Game with separate JS file works
- ✅ Game with CSS and JS files works

## Test Dependencies

- `pytest==8.4.2` - Testing framework
- `pytest-asyncio==1.2.0` - Async test support  
- `pytest-mock==3.15.1` - Mocking support
- `dagger-io` - For integration tests with real containers

All dependencies are managed via `uv` and listed in `requirements.txt`.

## Integration Test Requirements

Integration tests require:
1. **Docker daemon running** - Tests use containerized Playwright
2. **Network access** - To pull `mcr.microsoft.com/playwright:v1.49.0-jammy` image
3. **Dagger SDK** - Already in requirements.txt

First run will be slower as it pulls the Playwright image (~1GB).

## Test Structure

Tests use:
- **Mocking**: Extensive mocking of Dagger containers and Workspace objects
- **Async testing**: Full async/await support for containerized operations
- **Unit tests**: Isolated testing of individual functions
- **Integration tests**: End-to-end workflow testing

## Adding New Tests

When adding new test files:
1. Name them `test_*.py`
2. Place them in the `tests/` directory
3. Use `pytest.mark.asyncio` for async tests
4. Follow the existing test class structure
5. Run tests to verify they work

## Configuration

Test configuration is in `pytest.ini` at the project root:
- Test path: `tests/`
- Async mode: Auto
- Python files pattern: `test_*.py`
- Custom markers:
  - `unit` - Fast tests with mocks
  - `integration` - Slow tests with real containers

## CI/CD Recommendations

For continuous integration:
```bash
# Fast feedback loop - run unit tests only
pytest tests/ -v -m unit

# Full validation (if Docker available)
pytest tests/ -v

# Skip integration tests (no Docker)
pytest tests/ -v -m "not integration"
```

