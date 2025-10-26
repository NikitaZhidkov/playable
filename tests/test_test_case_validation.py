"""
Unit tests for test case validation functionality.
Tests the new test case loading, validation, and VLM integration.
"""
import pytest
import json
from test_game import validate_game_with_test_case, TEST_SCRIPT_WITH_TEST_CASE
from src.containers import Workspace
from src.vlm.validation import _save_debug_screenshot, _parse_vlm_response
from pathlib import Path
import tempfile
import shutil


@pytest.mark.asyncio
async def test_validate_game_with_test_case_basic(dagger_client, playwright_container):
    """
    Test that we can load a test case and validate a game with it.
    """
    # Create a simple HTML file with loadTestCase function
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Case Game</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
            }
            #game-state {
                padding: 20px;
                font-size: 24px;
            }
        </style>
    </head>
    <body>
        <div id="game-state">Initial State</div>
        <script>
            let gameState = {
                message: "Initial State",
                score: 0
            };
            
            // Function to load test case
            window.loadTestCase = function(data) {
                console.log('Loading test case:', data);
                gameState.message = data.message || "Test State";
                gameState.score = data.score || 0;
                
                // Update display
                document.getElementById('game-state').textContent = 
                    gameState.message + ' - Score: ' + gameState.score;
                
                // Pause game (in this case, no game loop to pause)
                console.log('Game paused for test case');
            };
            
            console.log('Game initialized');
        </script>
    </body>
    </html>
    """
    
    # Create test case data
    test_case_data = {
        "message": "Test Case Loaded",
        "score": 42,
        "expectedOutput": "Test Case Loaded - Score: 42"
    }
    test_case_json = json.dumps(test_case_data)
    
    # Create workspace and add file
    workspace = await Workspace.create(dagger_client)
    workspace.write_file("index.html", html_content)
    
    # Copy to playwright container
    playwright_container.copy_directory(
        workspace.container().directory(".")
    )
    
    # Validate with test case
    result = await validate_game_with_test_case(
        container=playwright_container,
        test_case_json=test_case_json,
        test_case_name="test_case_1"
    )
    
    # Assertions
    assert result is not None, "Result should not be None"
    assert result.screenshot_bytes is not None, "Screenshot should be captured"
    assert len(result.screenshot_bytes) > 0, "Screenshot should have content"
    
    # Check console logs for test case loading
    log_text = '\n'.join(result.console_logs)
    assert 'Loading test case' in log_text, "Should log test case loading"
    assert 'Game paused for test case' in log_text, "Should log game pause"
    
    print(f"\n✅ Test case validation works: {len(result.screenshot_bytes)} bytes")
    print(f"   Console logs: {len(result.console_logs)} entries")


@pytest.mark.asyncio
async def test_validate_game_with_test_case_missing_function(dagger_client, playwright_container):
    """
    Test behavior when window.loadTestCase function is missing.
    """
    # Create HTML without loadTestCase function
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>No Test Case Support</title>
    </head>
    <body>
        <h1>Game without loadTestCase</h1>
    </body>
    </html>
    """
    
    test_case_data = {"message": "Test", "expectedOutput": "Something"}
    test_case_json = json.dumps(test_case_data)
    
    workspace = await Workspace.create(dagger_client)
    workspace.write_file("index.html", html_content)
    
    playwright_container.copy_directory(
        workspace.container().directory(".")
    )
    
    result = await validate_game_with_test_case(
        container=playwright_container,
        test_case_json=test_case_json,
        test_case_name="test_case_1"
    )
    
    # Should have error about missing function
    assert result is not None
    assert len(result.errors) > 0, "Should have errors"
    
    error_text = '\n'.join(result.errors)
    assert 'loadTestCase' in error_text, "Error should mention missing loadTestCase function"
    
    print(f"\n✅ Missing function detected correctly")
    print(f"   Errors: {result.errors}")


@pytest.mark.asyncio
async def test_validate_game_with_test_case_invalid_json(dagger_client, playwright_container):
    """
    Test behavior with invalid JSON in test case.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <script>
            window.loadTestCase = function(data) {
                console.log('Loaded:', data);
            };
        </script>
    </body>
    </html>
    """
    
    # Invalid JSON
    test_case_json = "{ invalid json }"
    
    workspace = await Workspace.create(dagger_client)
    workspace.write_file("index.html", html_content)
    
    playwright_container.copy_directory(
        workspace.container().directory(".")
    )
    
    # The test script will exit with error before creating screenshot when JSON is invalid
    # We should catch this exception
    try:
        result = await validate_game_with_test_case(
            container=playwright_container,
            test_case_json=test_case_json,
            test_case_name="test_case_invalid"
        )
        
        # If we get a result, it should have errors
        assert result is not None
        assert len(result.errors) > 0, "Should have errors for invalid JSON"
        
        error_text = '\n'.join(result.errors)
        assert 'JSON' in error_text or 'parse' in error_text.lower(), "Error should mention JSON parsing"
        
        print(f"\n✅ Invalid JSON detected correctly")
        print(f"   Errors: {result.errors}")
        
    except Exception as e:
        # It's also acceptable to get an exception when screenshot doesn't exist
        # This happens when the test script exits before creating the screenshot
        error_msg = str(e).lower()
        assert 'screenshot' in error_msg or 'no such file' in error_msg, \
            f"Exception should be about missing screenshot, got: {e}"
        
        print(f"\n✅ Invalid JSON caused early exit (expected)")
        print(f"   Exception: {type(e).__name__}: {str(e)[:100]}")


def test_test_script_with_test_case_defined():
    """
    Test that TEST_SCRIPT_WITH_TEST_CASE is properly defined.
    """
    assert TEST_SCRIPT_WITH_TEST_CASE is not None
    assert len(TEST_SCRIPT_WITH_TEST_CASE) > 0
    assert 'TEST_CASE_DATA' in TEST_SCRIPT_WITH_TEST_CASE
    assert 'window.loadTestCase' in TEST_SCRIPT_WITH_TEST_CASE
    assert 'testGameWithTestCase' in TEST_SCRIPT_WITH_TEST_CASE
    
    print(f"\n✅ TEST_SCRIPT_WITH_TEST_CASE is properly defined")
    print(f"   Length: {len(TEST_SCRIPT_WITH_TEST_CASE)} characters")


def test_save_debug_screenshot_with_prefix():
    """
    Test that debug screenshots are saved with correct naming.
    """
    # Create temporary test screenshot
    test_screenshot = b'\x89PNG\r\n\x1a\n' + b'fake_png_data'
    
    # Save with custom prefix
    screenshot_path = _save_debug_screenshot(test_screenshot, "test_case_1")
    
    try:
        # Verify file exists
        assert screenshot_path.exists(), "Screenshot file should exist"
        
        # Verify filename format
        filename = screenshot_path.name
        assert filename.startswith("test_case_1_"), f"Filename should start with prefix: {filename}"
        assert filename.endswith(".png"), f"Filename should end with .png: {filename}"
        
        # Verify content
        saved_content = screenshot_path.read_bytes()
        assert saved_content == test_screenshot, "Saved content should match original"
        
        print(f"\n✅ Debug screenshot saved correctly")
        print(f"   Path: {screenshot_path}")
        print(f"   Filename format correct: {filename}")
        
    finally:
        # Cleanup - remove the test file and directory
        if screenshot_path.exists():
            screenshot_path.unlink()
            # Try to remove the parent directory if empty
            try:
                screenshot_path.parent.rmdir()
            except:
                pass


def test_parse_vlm_response_success():
    """
    Test parsing VLM response for successful validation.
    """
    response_text = """
    <reason>The screenshot shows the game in the expected state with all elements visible</reason>
    <answer>yes</answer>
    """
    
    is_valid, reason = _parse_vlm_response(response_text)
    
    assert is_valid is True, "Should parse as valid"
    assert "expected state" in reason.lower(), "Should extract reason"
    
    print(f"\n✅ VLM response parsed correctly (success)")
    print(f"   Valid: {is_valid}")
    print(f"   Reason: {reason}")


def test_parse_vlm_response_failure():
    """
    Test parsing VLM response for failed validation.
    """
    response_text = """
    <reason>The score displays 0 but expected 100</reason>
    <answer>no</answer>
    """
    
    is_valid, reason = _parse_vlm_response(response_text)
    
    assert is_valid is False, "Should parse as invalid"
    assert "score" in reason.lower(), "Should extract reason"
    
    print(f"\n✅ VLM response parsed correctly (failure)")
    print(f"   Valid: {is_valid}")
    print(f"   Reason: {reason}")


def test_parse_vlm_response_case_insensitive():
    """
    Test that VLM response parsing is case-insensitive.
    """
    response_text = """
    <REASON>Test passed</REASON>
    <ANSWER>YES</ANSWER>
    """
    
    is_valid, reason = _parse_vlm_response(response_text)
    
    assert is_valid is True, "Should parse uppercase YES as valid"
    assert "Test passed" in reason, "Should extract reason"
    
    print(f"\n✅ VLM response case-insensitive parsing works")


def test_parse_vlm_response_invalid_format():
    """
    Test handling of invalid VLM response format.
    """
    response_text = "This is not a valid response format"
    
    is_valid, reason = _parse_vlm_response(response_text)
    
    assert is_valid is False, "Should return False for invalid format"
    assert "Invalid VLM response" in reason or response_text in reason, \
        "Should indicate invalid format in reason"
    
    print(f"\n✅ Invalid VLM response handled correctly")
    print(f"   Reason: {reason[:100]}")


@pytest.mark.asyncio
async def test_list_files_pattern_matching(dagger_client):
    """
    Test that workspace.list_files() correctly finds files by pattern.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create test case files
    workspace.write_file("test_case_1.json", '{"test": 1}')
    workspace.write_file("test_case_2.json", '{"test": 2}')
    workspace.write_file("test_case_3.json", '{"test": 3}')
    workspace.write_file("MANIFEST.json", '{"version": "1.0"}')
    workspace.write_file("index.html", '<html></html>')
    
    # Find test case files
    test_case_files = await workspace.list_files("test_case_*.json")
    
    # Assertions
    assert len(test_case_files) == 3, f"Should find 3 test case files, found {len(test_case_files)}"
    assert "test_case_1.json" in test_case_files, "Should find test_case_1.json"
    assert "test_case_2.json" in test_case_files, "Should find test_case_2.json"
    assert "test_case_3.json" in test_case_files, "Should find test_case_3.json"
    assert "MANIFEST.json" not in test_case_files, "Should not include MANIFEST.json"
    assert "index.html" not in test_case_files, "Should not include index.html"
    
    print(f"\n✅ list_files() pattern matching works")
    print(f"   Found files: {test_case_files}")


@pytest.mark.asyncio
async def test_list_files_no_matches(dagger_client):
    """
    Test that workspace.list_files() returns empty list when no files match.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create files that don't match pattern
    workspace.write_file("index.html", '<html></html>')
    workspace.write_file("game.js", 'console.log("test")')
    
    # Search for non-existent pattern
    test_case_files = await workspace.list_files("test_case_*.json")
    
    # Should return empty list, not error
    assert isinstance(test_case_files, list), "Should return a list"
    assert len(test_case_files) == 0, "Should return empty list when no matches"
    
    print(f"\n✅ list_files() handles no matches correctly")
    print(f"   Returned: {test_case_files}")


@pytest.mark.asyncio
async def test_list_files_subdirectory_pattern(dagger_client):
    """
    Test that workspace.list_files() can search in subdirectories.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create files in subdirectory
    workspace.write_file("debug_tests/test_case_1.json", '{"test": 1}')
    workspace.write_file("debug_tests/test_case_2.json", '{"test": 2}')
    workspace.write_file("test_case_3.json", '{"test": 3}')
    
    # Search for files in subdirectory
    debug_files = await workspace.list_files("debug_tests/test_case_*.json")
    
    # Assertions
    assert len(debug_files) == 2, f"Should find 2 files in debug_tests/, found {len(debug_files)}"
    
    print(f"\n✅ list_files() subdirectory pattern works")
    print(f"   Found files: {debug_files}")

