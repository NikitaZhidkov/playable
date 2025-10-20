"""
Browser testing module using Playwright to validate generated games.
Runs tests in a containerized Playwright environment using Dagger.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List
from workspace import Workspace
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
        
        // Capture screenshot
        const screenshotPath = '/app/screenshot.png';
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`Screenshot saved to ${screenshotPath}`);
        
    } catch (error) {
        const errorMsg = `Failed to load page: ${error.message}`;
        errors.push(errorMsg);
        consoleLogs.push(errorMsg);
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


def _parse_test_output(output: str) -> Dict:
    """Parse the test output and extract JSON result."""
    try:
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
    except Exception as e:
        logger.error(f"Failed to parse test output: {e}\nOutput:\n{output}")
        return {
            'success': False,
            'errors': [f"Failed to parse test output: {str(e)}"],
            'console_logs': []
        }


async def validate_game_in_workspace(workspace: Workspace) -> GameTestResult:
    """
    Test a game directly from a Workspace using containerized Playwright.
    
    This properly handles games with multiple files (JS, CSS, images, etc.)
    by running tests in a Playwright container with all workspace files.
    
    Args:
        workspace: Workspace containing the game files
    
    Returns:
        GameTestResult with success status, errors, console logs, and screenshot
    """
    try:
        logger.info("Setting up Playwright container for testing...")
        
        # Get the Dagger client from workspace
        client = workspace.client
        
        # Create Playwright container
        playwright_container = (
            client.container()
            .from_("mcr.microsoft.com/playwright:v1.49.0-jammy")
            # Copy workspace files to /app
            .with_directory("/app", workspace.container().directory("."))
            .with_workdir("/app")
            # Create package.json and install playwright locally (pin exact version to match image)
            .with_new_file("/app/package.json", '{"dependencies": {"playwright": "1.49.0"}}')
            .with_exec(["npm", "install"], expect=ReturnType.ANY)
            # Add the test script
            .with_new_file("/app/test-runner.js", TEST_SCRIPT)
        )
        
        logger.info("Running browser tests in container...")
        
        # Execute the test script
        # Use expect=ReturnType.ANY to not raise exception on non-zero exit codes
        executed_container = playwright_container.with_exec(
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
        screenshot_bytes = None
        try:
            # Dagger .contents() returns bytes directly for binary files
            screenshot_data = await executed_container.file("/app/screenshot.png").contents()
            # Ensure we have bytes, not string
            if isinstance(screenshot_data, str):
                screenshot_bytes = screenshot_data.encode('latin-1')  # Preserve binary data
            else:
                screenshot_bytes = screenshot_data
            logger.info(f"Screenshot extracted: {len(screenshot_bytes)} bytes")
        except Exception as e:
            logger.warning(f"Could not extract screenshot: {e}")
        
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
        
    except Exception as e:
        error_msg = f"Failed to run containerized tests: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return GameTestResult(success=False, errors=[error_msg])

