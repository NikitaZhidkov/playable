# Browser Testing with Playwright

This project now includes automated browser testing for generated games using Playwright running in Docker containers.

## Features

- **Automatic Testing**: Games are tested in a real browser after the agent completes them
- **Containerized**: Tests run in isolated Playwright containers (no local installation needed)
- **Error Detection**: Captures JavaScript console errors and page load failures
- **Auto-Retry**: Agent automatically attempts to fix errors (up to 5 attempts)
- **Feedback Loop**: Test failures are sent back to the AI agent with detailed error messages

## Setup

No additional setup required! Just install Python dependencies:

```bash
# Install dependencies
pip install -r requirements.txt
```

Playwright runs in a Microsoft-provided Docker container (`mcr.microsoft.com/playwright:v1.49.0-jammy`), so you don't need to install browsers or Playwright locally.

## How It Works

### Workflow

1. Agent generates the game code (may include multiple files: HTML, JS, CSS, images, etc.)
2. Agent calls the `complete` tool
3. **Browser testing runs automatically**:
   - Spins up a Playwright container (`mcr.microsoft.com/playwright:v1.49.0-jammy`)
   - Copies all workspace files into the container
   - Runs a test script that loads the game in Chromium
   - All assets (external JS, CSS, images) load correctly via file:// protocol
   - Monitors for JavaScript console errors and warnings
   - Checks for page load failures and missing resources
   - Waits for JavaScript initialization (2 seconds)
   - Returns structured JSON results
   - Container is automatically cleaned up
4. **If tests pass**: Workflow ends, game is exported
5. **If tests fail**: 
   - Error details are sent back to the agent
   - Agent attempts to fix the errors
   - Process repeats (max 5 attempts)
6. **After 5 failed attempts**: Workflow ends with error report

### Test Detection

The browser tests check for:
- JavaScript console errors
- JavaScript console warnings
- Uncaught exceptions
- Failed resource requests
- Page load failures

### Output

When the game is complete, you'll see test results:

**Success:**
```
✅ Browser Test Status: PASSED
   No errors detected in browser
```

**Failure:**
```
⚠️  Browser Test Status: FAILED
   Retries: 3/5
   Errors found:
   - [ERROR] Uncaught ReferenceError: PIXI is not defined
   - Failed to load resource: https://cdn.jsdelivr.net/npm/pixi.js@7/dist/pixi.min.js
```

## Architecture

### New Files

- `test_game.py`: Playwright testing module with containerized browser automation
  - `validate_game_in_workspace()`: Tests games using Playwright in a Docker container
  - `TEST_SCRIPT`: JavaScript test runner executed inside the container
  - `_parse_test_output()`: Parses JSON test results from container output

### Modified Files

- `agent_state.py`: Added `test_failures` and `retry_count` fields
- `agent_graph.py`: Added `test_node` and retry routing logic
- `main.py`: Display test results in output
- `example.py`: Initialize new state fields
- `requirements.txt`: No Playwright dependency needed (runs in container)

### Containerized Architecture

The testing module uses containerized Playwright:
- **No local installation**: Playwright runs in Microsoft's official container
- **Isolated environment**: Each test runs in a fresh container
- **Multi-file support**: All workspace files copied into container
- **File protocol**: Games load via file:// with proper relative paths
- **Automatic cleanup**: Containers automatically removed after tests
- **Docker required**: Leverages existing Dagger/Docker infrastructure

### Flow Diagram

```
┌─────┐     ┌───────┐     ┌──────┐
│ LLM │────▶│ Tools │────▶│ Test │
└─────┘     └───────┘     └──────┘
   ▲                          │
   │                          ▼
   │                      Pass/Fail?
   │                          │
   └──────────────────────────┘
        (if fail & retry < 5)
```

## Disabling Tests

To disable browser testing, you can modify `agent_graph.py`:

```python
# In should_continue function, change:
if state.get("is_completed", False):
    return "test"  # This routes to testing

# To:
if state.get("is_completed", False):
    return END  # This skips testing
```

## Troubleshooting

### Docker/Dagger issues

Ensure Docker is running:
```bash
docker ps
```

### Tests failing on valid games

- Check internet connection (CDN resources like pixi.js need to load)
- Container has network access enabled by default
- Check logs for detailed error messages
- Test timeout is 10 seconds in container

### Container pulls slowly

First time may take a few minutes to download the Playwright image (~1GB):
```bash
# Pre-pull the image to speed up first test
docker pull mcr.microsoft.com/playwright:v1.49.0-jammy
```

### Infinite retry loop

- Max retries is 5, then stops
- Check logs to see what errors the agent is struggling with
- May need to adjust the game prompt or add more specific instructions

### Customizing the test script

Edit `TEST_SCRIPT` in `test_game.py` to:
- Change timeout values
- Add custom validation logic
- Modify error detection rules

