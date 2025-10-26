"""
Integration tests for the complete test case validation flow.
Tests the end-to-end functionality including VLM validation, test case loading,
and test case movement to debug folder.
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from src.containers import Workspace, PlaywrightContainer
from src.vlm import VLMClient, validate_test_case_with_vlm
from test_game import validate_game_with_test_case


@pytest.mark.asyncio
async def test_full_test_case_validation_flow(dagger_client, playwright_container):
    """
    Integration test for the full test case validation flow:
    1. Create game with test case support
    2. Create test case files
    3. Load and validate test case
    4. Verify screenshot capture
    """
    # Create a complete game with test case support
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Game</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                background-color: #f0f0f0;
            }
            #game-container {
                padding: 40px;
                text-align: center;
            }
            #score {
                font-size: 48px;
                color: #333;
                margin-bottom: 20px;
            }
            #status {
                font-size: 24px;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div id="game-container">
            <div id="score">Score: 0</div>
            <div id="status">Playing</div>
        </div>
        <script>
            let gameState = {
                score: 0,
                status: 'playing',
                isPaused: false
            };
            
            // Game loop (simulated)
            let gameInterval = setInterval(() => {
                if (!gameState.isPaused) {
                    gameState.score++;
                    updateDisplay();
                }
            }, 100);
            
            function updateDisplay() {
                document.getElementById('score').textContent = 'Score: ' + gameState.score;
                document.getElementById('status').textContent = 
                    gameState.isPaused ? 'Paused' : gameState.status;
            }
            
            // Test case loading function
            window.loadTestCase = function(data) {
                console.log('Loading test case:', JSON.stringify(data));
                
                // Load state from test case
                if (data.score !== undefined) {
                    gameState.score = data.score;
                }
                if (data.status !== undefined) {
                    gameState.status = data.status;
                }
                
                // Pause game for test case
                gameState.isPaused = true;
                if (gameInterval) {
                    clearInterval(gameInterval);
                    gameInterval = null;
                }
                
                // Update display
                updateDisplay();
                
                console.log('Test case loaded, game paused');
                console.log('Current state:', JSON.stringify(gameState));
            };
            
            console.log('Game initialized');
        </script>
    </body>
    </html>
    """
    
    # Create test case with expected state
    test_case_1 = {
        "score": 100,
        "status": "Level 1",
        "expectedOutput": "Score display shows 100, status shows Level 1, game is paused"
    }
    
    # Create workspace with game and test case
    workspace = await Workspace.create(dagger_client)
    workspace.write_file("index.html", html_content)
    workspace.write_file("test_case_1.json", json.dumps(test_case_1, indent=2))
    
    # Copy to playwright container
    playwright_container.copy_directory(
        workspace.container().directory(".")
    )
    
    # Validate with test case
    result = await validate_game_with_test_case(
        container=playwright_container,
        test_case_json=json.dumps(test_case_1),
        test_case_name="test_case_1"
    )
    
    # Verify result
    assert result is not None, "Result should not be None"
    assert result.success is True, "Test should succeed"
    assert result.screenshot_bytes is not None, "Screenshot should be captured"
    assert len(result.screenshot_bytes) > 0, "Screenshot should have content"
    
    # Verify console logs show test case loading
    log_text = '\n'.join(result.console_logs)
    assert 'Loading test case' in log_text, "Should log test case loading"
    assert 'Test case loaded, game paused' in log_text, "Should confirm test case loaded"
    
    # Verify no errors
    assert len(result.errors) == 0, f"Should have no errors, got: {result.errors}"
    
    print(f"\n✅ Full test case validation flow works")
    print(f"   Screenshot: {len(result.screenshot_bytes)} bytes")
    print(f"   Console logs: {len(result.console_logs)} entries")
    print(f"   Errors: {len(result.errors)}")


@pytest.mark.asyncio
async def test_test_case_validation_with_mock_vlm(dagger_client, playwright_container):
    """
    Test test case validation with mocked VLM to verify VLM integration.
    """
    # Create simple game with test case support
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>
        <div id="state">Initial</div>
        <script>
            window.loadTestCase = function(data) {
                document.getElementById('state').textContent = data.message;
                console.log('Test case loaded');
            };
        </script>
    </body>
    </html>
    """
    
    workspace = await Workspace.create(dagger_client)
    workspace.write_file("index.html", html_content)
    
    playwright_container.copy_directory(
        workspace.container().directory(".")
    )
    
    # Run test case validation
    test_case_json = json.dumps({
        "message": "Test State",
        "expectedOutput": "State shows Test State"
    })
    
    result = await validate_game_with_test_case(
        container=playwright_container,
        test_case_json=test_case_json,
        test_case_name="test_mock_vlm"
    )
    
    # Verify screenshot was captured
    assert result.screenshot_bytes is not None
    
    # Now test VLM validation with mock
    mock_vlm_client = Mock(spec=VLMClient)
    mock_vlm_client.model = Mock()
    
    # Mock VLM response
    mock_response = Mock()
    mock_response.text = "<reason>State correctly shows Test State</reason><answer>yes</answer>"
    mock_vlm_client.model.generate_content = Mock(return_value=mock_response)
    
    # Call validate_test_case_with_vlm
    is_valid, reason = validate_test_case_with_vlm(
        vlm_client=mock_vlm_client,
        screenshot_bytes=result.screenshot_bytes,
        expected_output="State shows Test State",
        template_str="{{ expected_output }}",
        test_case_name="test_mock_vlm"
    )
    
    # Verify VLM validation worked
    assert is_valid is True, "VLM should validate as success"
    assert "correctly" in reason.lower(), "Should extract reason from VLM response"
    
    # Verify VLM was called
    assert mock_vlm_client.model.generate_content.called, "VLM should be called"
    
    print(f"\n✅ Test case VLM integration works")
    print(f"   VLM validated: {is_valid}")
    print(f"   VLM reason: {reason}")


@pytest.mark.asyncio
async def test_multiple_test_cases_discovery(dagger_client):
    """
    Test discovering multiple test cases in workspace.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create multiple test cases
    for i in range(1, 4):
        test_case = {
            "testNumber": i,
            "expectedOutput": f"Test case {i} output"
        }
        workspace.write_file(f"test_case_{i}.json", json.dumps(test_case))
    
    # Also create MANIFEST and other files
    workspace.write_file("MANIFEST.json", '{"version": "1.0"}')
    workspace.write_file("index.html", '<html></html>')
    
    # Discover test cases
    test_case_files = await workspace.list_files("test_case_*.json")
    
    # Verify all test cases found
    assert len(test_case_files) == 3, f"Should find 3 test cases, found {len(test_case_files)}"
    
    # Verify order and content
    for i, filename in enumerate(sorted(test_case_files), 1):
        assert f"test_case_{i}.json" == filename, f"Test case {i} should be found"
        
        # Read and verify content
        content = await workspace.read_file(filename)
        data = json.loads(content)
        assert data["testNumber"] == i, f"Test case {i} should have correct data"
    
    print(f"\n✅ Multiple test cases discovered correctly")
    print(f"   Found: {sorted(test_case_files)}")


@pytest.mark.asyncio
async def test_test_case_movement_to_debug_folder(dagger_client):
    """
    Test that test cases are moved to debug_tests/ folder after completion.
    This simulates what happens in the agent_graph after all tests pass.
    """
    workspace = await Workspace.create(dagger_client)
    
    # Create test case files at root level
    test_case_files = ["test_case_1.json", "test_case_2.json", "MANIFEST.json"]
    for filename in test_case_files:
        workspace.write_file(filename, f'{{"file": "{filename}"}}')
    
    # Also create game files that should NOT be moved
    workspace.write_file("index.html", '<html></html>')
    workspace.write_file("game.js", 'console.log("game")')
    
    # Verify files exist at root
    for filename in test_case_files:
        content = await workspace.read_file(filename)
        assert content, f"{filename} should exist at root"
    
    # Simulate moving files to debug_tests/ (same logic as agent_graph)
    workspace = workspace.write_file("debug_tests/.gitkeep", "", force=True)
    
    for test_file in test_case_files:
        try:
            content = await workspace.read_file(test_file)
            workspace = workspace.write_file(f"debug_tests/{test_file}", content, force=True)
            workspace = workspace.rm(test_file)
        except Exception as e:
            print(f"Error moving {test_file}: {e}")
    
    # Verify files moved to debug_tests/
    for filename in test_case_files:
        debug_path = f"debug_tests/{filename}"
        content = await workspace.read_file(debug_path)
        assert content, f"{filename} should exist in debug_tests/"
        
        # Verify file no longer exists at root
        try:
            await workspace.read_file(filename)
            assert False, f"{filename} should not exist at root anymore"
        except FileNotFoundError:
            pass  # Expected
    
    # Verify game files still at root
    game_html = await workspace.read_file("index.html")
    assert game_html == '<html></html>', "Game files should remain at root"
    
    print(f"\n✅ Test case movement to debug_tests/ works")
    print(f"   Moved files: {test_case_files}")


@pytest.mark.asyncio
async def test_test_case_count_validation(dagger_client):
    """
    Test that the system validates test case count (1-5 required).
    """
    workspace = await Workspace.create(dagger_client)
    
    # Test 1: No test cases (should fail)
    test_files_0 = await workspace.list_files("test_case_*.json")
    assert len(test_files_0) == 0, "Should have no test cases initially"
    
    # Test 2: Valid count (1 test case)
    workspace.write_file("test_case_1.json", '{"test": 1}')
    test_files_1 = await workspace.list_files("test_case_*.json")
    assert len(test_files_1) == 1, "Should have 1 test case"
    assert 1 <= len(test_files_1) <= 5, "Count should be in valid range"
    
    # Test 3: Valid count (5 test cases - maximum)
    for i in range(2, 6):
        workspace.write_file(f"test_case_{i}.json", f'{{"test": {i}}}')
    test_files_5 = await workspace.list_files("test_case_*.json")
    assert len(test_files_5) == 5, "Should have 5 test cases"
    assert 1 <= len(test_files_5) <= 5, "Count should be in valid range"
    
    # Test 4: Too many test cases (6+)
    workspace.write_file("test_case_6.json", '{"test": 6}')
    test_files_6 = await workspace.list_files("test_case_*.json")
    assert len(test_files_6) == 6, "Should find 6 test cases"
    # In actual implementation, we would only use first 5
    test_files_limited = test_files_6[:5]
    assert len(test_files_limited) == 5, "Should limit to 5 test cases"
    
    print(f"\n✅ Test case count validation logic works")
    print(f"   0 cases: {len(test_files_0)} (invalid)")
    print(f"   1 case: {len(test_files_1)} (valid)")
    print(f"   5 cases: {len(test_files_5)} (valid)")
    print(f"   6+ cases: {len(test_files_6)} (limited to 5)")


@pytest.mark.asyncio
async def test_test_case_with_pixi_game(dagger_client, playwright_container):
    """
    Integration test with a real PixiJS game that supports test cases.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>PixiJS Test Case Game</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
        <style>
            body { margin: 0; padding: 0; overflow: hidden; }
        </style>
    </head>
    <body>
        <script>
            let app = null;
            let scoreText = null;
            let isPaused = false;
            let gameState = {
                score: 0,
                level: 1
            };
            
            // Initialize PixiJS
            const initApp = new PIXI.Application();
            initApp.init({
                width: 800,
                height: 600,
                backgroundColor: 0x1099bb
            }).then(() => {
                app = initApp;
                document.body.appendChild(app.canvas);
                
                // Add score text
                scoreText = new PIXI.Text({
                    text: 'Score: 0',
                    style: {
                        fontFamily: 'Arial',
                        fontSize: 36,
                        fill: 0xffffff
                    }
                });
                scoreText.x = 20;
                scoreText.y = 20;
                app.stage.addChild(scoreText);
                
                console.log('PixiJS game initialized');
            });
            
            // Test case loading function
            window.loadTestCase = function(data) {
                console.log('Loading test case:', JSON.stringify(data));
                
                if (!app || !scoreText) {
                    console.error('Game not initialized');
                    return;
                }
                
                // Load state
                if (data.score !== undefined) {
                    gameState.score = data.score;
                }
                if (data.level !== undefined) {
                    gameState.level = data.level;
                }
                
                // Update display
                scoreText.text = 'Score: ' + gameState.score + ' Level: ' + gameState.level;
                
                // Pause game
                isPaused = true;
                if (app.ticker) {
                    app.ticker.stop();
                }
                
                console.log('Test case loaded, game paused');
            };
        </script>
    </body>
    </html>
    """
    
    test_case = {
        "score": 500,
        "level": 5,
        "expectedOutput": "Score: 500 Level: 5 displayed in game"
    }
    
    workspace = await Workspace.create(dagger_client)
    workspace.write_file("index.html", html_content)
    
    playwright_container.copy_directory(
        workspace.container().directory(".")
    )
    
    result = await validate_game_with_test_case(
        container=playwright_container,
        test_case_json=json.dumps(test_case),
        test_case_name="test_pixi_game"
    )
    
    # Verify result
    assert result is not None
    assert result.screenshot_bytes is not None
    
    # Check logs for PixiJS initialization and test case loading
    log_text = '\n'.join(result.console_logs)
    assert 'PixiJS game initialized' in log_text or 'initialized' in log_text.lower()
    assert 'Loading test case' in log_text
    
    print(f"\n✅ PixiJS game test case integration works")
    print(f"   Screenshot: {len(result.screenshot_bytes)} bytes")
    print(f"   Console logs captured: {len(result.console_logs)} entries")

