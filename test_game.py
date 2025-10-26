"""
Browser testing module using Playwright to validate generated games.
Runs tests in a containerized Playwright environment using Dagger.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List
from src.containers import PlaywrightContainer
import dagger
from dagger import ReturnType
import logging

logger = logging.getLogger(__name__)


class GameTestResult:
    """Result of browser testing a game."""
    
    def __init__(
        self, 
        success: bool, 
        errors: List[str],
        console_logs: List[str] | None = None,
        screenshot_bytes: bytes | None = None
    ):
        self.success = success
        self.errors = errors
        self.console_logs = console_logs or []
        self.screenshot_bytes = screenshot_bytes
    
    def __repr__(self):
        return f"GameTestResult(success={self.success}, errors={self.errors}, console_logs={len(self.console_logs)} items)"


# JavaScript test script that runs inside the Playwright container  
TEST_SCRIPT = """
const path = require('path');
const fs = require('fs');

async function testGame() {
    const errors = [];
    const warnings = [];
    const consoleLogs = [];
    
    // Import playwright (will be installed globally)
    const { chromium } = require('playwright');
    
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    // Capture all console messages (errors, warnings, logs)
    page.on('console', (msg) => {
        const msgType = msg.type().toUpperCase();
        const msgText = msg.text();
        const logEntry = `[${msgType}] ${msgText}`;
        
        consoleLogs.push(logEntry);
        
        if (msg.type() === 'error') {
            errors.push(logEntry);
        } else if (msg.type() === 'warning') {
            warnings.push(logEntry);
        }
    });
    
    // Capture page errors
    page.on('pageerror', (error) => {
        const errorMsg = `Uncaught exception: ${error.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
    });
    
    // Capture failed requests
    page.on('requestfailed', (request) => {
        const errorMsg = `Failed to load resource: ${request.url()}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
    });
    
    let screenshotCaptured = false;
    
    try {
        // Load the game
        const indexPath = path.resolve('/app/index.html');
        await page.goto(`file://${indexPath}`, { 
            waitUntil: 'networkidle',
            timeout: 10000 
        });
        
        // Wait for JavaScript initialization
        await page.waitForTimeout(2000);
        
        const title = await page.title();
        console.log(`Page loaded: ${title}`);
        
    } catch (error) {
        const errorMsg = `Failed to load page: ${error.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
    }
    
    // Always try to capture screenshot, even if page load failed
    try {
        const screenshotPath = '/app/screenshot.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        screenshotCaptured = true;
        console.log(`Screenshot saved to ${screenshotPath}`);
    } catch (screenshotError) {
        const errorMsg = `Failed to capture screenshot: ${screenshotError.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
        console.error(errorMsg);
    } finally {
        await browser.close();
    }
    
    // Output JSON result with all logs
    // Note: VLM will decide success, so we always return success: true here
    const result = {
        success: true,
        errors: errors,
        warnings: warnings,
        console_logs: consoleLogs
    };
    
    console.log('__TEST_RESULT__' + JSON.stringify(result) + '__END__');
    
    // Always exit with 0 since VLM will determine actual success
    process.exit(0);
}

testGame().catch((error) => {
    console.log('__TEST_RESULT__' + JSON.stringify({
        success: false,
        errors: [`Test execution failed: ${error.message}`],
        warnings: [],
        console_logs: [`Test execution failed: ${error.message}`]
    }) + '__END__');
    process.exit(1);
});
"""

# JavaScript test script for loading test cases
TEST_SCRIPT_WITH_TEST_CASE = """
const path = require('path');
const fs = require('fs');

async function testGameWithTestCase() {
    const errors = [];
    const warnings = [];
    const consoleLogs = [];
    
    // Get test case data from environment variable
    const testCaseJson = process.env.TEST_CASE_DATA;
    if (!testCaseJson) {
        console.log('__TEST_RESULT__' + JSON.stringify({
            success: false,
            errors: ['TEST_CASE_DATA environment variable not set'],
            warnings: [],
            console_logs: ['TEST_CASE_DATA environment variable not set']
        }) + '__END__');
        process.exit(1);
    }
    
    let testCaseData;
    try {
        testCaseData = JSON.parse(testCaseJson);
        console.log('Test case data parsed successfully');
    } catch (error) {
        console.log('__TEST_RESULT__' + JSON.stringify({
            success: false,
            errors: [`Failed to parse test case JSON: ${error.message}`],
            warnings: [],
            console_logs: [`Failed to parse test case JSON: ${error.message}`]
        }) + '__END__');
        process.exit(1);
    }
    
    // Import playwright (will be installed globally)
    const { chromium } = require('playwright');
    
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    // Capture all console messages (errors, warnings, logs)
    page.on('console', (msg) => {
        const msgType = msg.type().toUpperCase();
        const msgText = msg.text();
        const logEntry = `[${msgType}] ${msgText}`;
        
        consoleLogs.push(logEntry);
        
        if (msg.type() === 'error') {
            errors.push(logEntry);
        } else if (msg.type() === 'warning') {
            warnings.push(logEntry);
        }
    });
    
    // Capture page errors
    page.on('pageerror', (error) => {
        const errorMsg = `Uncaught exception: ${error.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
    });
    
    // Capture failed requests
    page.on('requestfailed', (request) => {
        const errorMsg = `Failed to load resource: ${request.url()}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
    });
    
    let screenshotCaptured = false;
    
    try {
        // Load the game
        const indexPath = path.resolve('/app/index.html');
        await page.goto(`file://${indexPath}`, { 
            waitUntil: 'networkidle',
            timeout: 10000 
        });
        
        // Wait for JavaScript initialization
        await page.waitForTimeout(2000);
        
        const title = await page.title();
        console.log(`Page loaded: ${title}`);
        
        // Check if window.loadTestCase exists
        const hasLoadTestCase = await page.evaluate(() => {
            return typeof window.loadTestCase === 'function';
        });
        
        if (!hasLoadTestCase) {
            const errorMsg = 'window.loadTestCase function not found in game code';
            errors.push(errorMsg);
            consoleLogs.push(errorMsg);
        } else {
            // Call window.loadTestCase with the test case data
            console.log('Calling window.loadTestCase...');
            await page.evaluate((data) => {
                window.loadTestCase(data);
            }, testCaseData);
            
            // Wait for game state to stabilize after loading test case
            await page.waitForTimeout(2000);
            console.log('Test case loaded and game state stabilized');
        }
        
    } catch (error) {
        const errorMsg = `Failed to load page or test case: ${error.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
    }
    
    // Always try to capture screenshot, even if page load failed
    try {
        const screenshotPath = '/app/screenshot.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        screenshotCaptured = true;
        console.log(`Screenshot saved to ${screenshotPath}`);
    } catch (screenshotError) {
        const errorMsg = `Failed to capture screenshot: ${screenshotError.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
        console.error(errorMsg);
    } finally {
        await browser.close();
    }
    
    // Output JSON result with all logs
    const result = {
        success: true,
        errors: errors,
        warnings: warnings,
        console_logs: consoleLogs
    };
    
    console.log('__TEST_RESULT__' + JSON.stringify(result) + '__END__');
    
    // Always exit with 0 since VLM will determine actual success
    process.exit(0);
}

testGameWithTestCase().catch((error) => {
    console.log('__TEST_RESULT__' + JSON.stringify({
        success: false,
        errors: [`Test execution failed: ${error.message}`],
        warnings: [],
        console_logs: [`Test execution failed: ${error.message}`]
    }) + '__END__');
    process.exit(1);
});
"""


def _parse_test_output(output: str) -> Dict:
    """Parse the test output and extract JSON result."""
    # Look for the JSON result marker
    start_marker = '__TEST_RESULT__'
    end_marker = '__END__'
    
    start_idx = output.find(start_marker)
    end_idx = output.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        logger.error(f"Could not find test result markers in output:\n{output}")
        return {
            'success': False,
            'errors': ["Failed to parse test output - no result markers found"],
            'console_logs': []
        }
    
    json_str = output[start_idx + len(start_marker):end_idx]
    result = json.loads(json_str)
    
    return result


async def validate_game_in_workspace(container: PlaywrightContainer) -> GameTestResult:
    """
    Test a game in a PlaywrightContainer using Playwright.
    
    The container should already have:
    - Game files copied via copy_directory()
    - Test script added via with_test_script()
    
    Args:
        container: PlaywrightContainer with game files and test script
    
    Returns:
        GameTestResult with success status, errors, console logs, and screenshot
    """
    logger.info("Running browser tests in PlaywrightContainer...")
    
    # Execute the test script in the container
    executed_container = container.container().with_exec(
        ["node", "test-runner.js"],
        expect=ReturnType.ANY
    )
    
    # Get the output (this will work even if exit code is non-zero)
    output = await executed_container.stdout()
    exit_code = await executed_container.exit_code()
    
    logger.info(f"Test completed with exit code {exit_code}")
    
    # Parse the output
    parsed_result = _parse_test_output(output)
    
    # Extract screenshot from container
    # We continue even if screenshot extraction fails since test results are still valuable
    screenshot_bytes = None

    import tempfile
    from pathlib import Path as PathLib
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_screenshot = PathLib(tmpdir) / "screenshot.png"
        
        # Export screenshot from container to temp file
        await executed_container.file("/app/screenshot.png").export(str(tmp_screenshot))
        
        # Read the exported file as bytes
        screenshot_bytes = tmp_screenshot.read_bytes()
        
    logger.info(f"Screenshot extracted successfully: {len(screenshot_bytes)} bytes")
    

    # Create GameTestResult with all data
    result = GameTestResult(
        success=parsed_result.get('success', False),
        errors=parsed_result.get('errors', []),
        console_logs=parsed_result.get('console_logs', []),
        screenshot_bytes=screenshot_bytes
    )
    
    if result.success:
        logger.info(f"✅ Browser tests completed - {len(result.console_logs)} console log(s) captured")
    else:
        logger.warning(f"❌ Browser tests failed - {len(result.errors)} error(s) found")
        for error in result.errors:
            logger.warning(f"  - {error}")
    
    return result


async def validate_game_with_test_case(
    container: PlaywrightContainer,
    test_case_json: str,
    test_case_name: str
) -> GameTestResult:
    """
    Test a game with a specific test case loaded.
    
    The container should already have:
    - Game files copied via copy_directory()
    
    Args:
        container: PlaywrightContainer with game files
        test_case_json: JSON string of the test case data
        test_case_name: Name of the test case for logging
    
    Returns:
        GameTestResult with success status, errors, console logs, and screenshot
    """
    logger.info(f"Running browser tests with test case: {test_case_name}")
    
    # Add test script with test case support
    container = container.with_test_script(TEST_SCRIPT_WITH_TEST_CASE)
    
    # Add test case data as environment variable
    container = container.container().with_env_variable("TEST_CASE_DATA", test_case_json)
    
    # Execute the test script
    executed_container = container.with_exec(
        ["node", "test-runner.js"],
        expect=ReturnType.ANY
    )
    
    # Get the output
    output = await executed_container.stdout()
    exit_code = await executed_container.exit_code()
    
    logger.info(f"Test case '{test_case_name}' completed with exit code {exit_code}")
    
    # Parse the output
    parsed_result = _parse_test_output(output)
    
    # Extract screenshot from container
    screenshot_bytes = None
    import tempfile
    from pathlib import Path as PathLib
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_screenshot = PathLib(tmpdir) / "screenshot.png"
        
        # Export screenshot from container to temp file
        await executed_container.file("/app/screenshot.png").export(str(tmp_screenshot))
        
        # Read the exported file as bytes
        screenshot_bytes = tmp_screenshot.read_bytes()
        
    logger.info(f"Screenshot extracted for test case '{test_case_name}': {len(screenshot_bytes)} bytes")

    # Create GameTestResult with all data
    result = GameTestResult(
        success=parsed_result.get('success', False),
        errors=parsed_result.get('errors', []),
        console_logs=parsed_result.get('console_logs', []),
        screenshot_bytes=screenshot_bytes
    )
    
    if result.success:
        logger.info(f"✅ Test case '{test_case_name}' browser tests completed")
    else:
        logger.warning(f"❌ Test case '{test_case_name}' browser tests failed")
        for error in result.errors:
            logger.warning(f"  - {error}")
    
    return result

