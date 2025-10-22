"""
Full integration test for screenshot capture flow.
Tests the complete workflow: workspace -> playwright -> screenshot -> VLM validation.
"""
import pytest
import asyncio
from test_game import validate_game_in_workspace
from workspace import Workspace
from llm_client import VLMClient
from vlm_utils import validate_playable_with_vlm
from playbook import VLM_PLAYABLE_VALIDATION_PROMPT
import dagger


@pytest.mark.asyncio
async def test_full_screenshot_to_vlm_flow():
    """
    Complete end-to-end test: create game -> capture screenshot -> validate with VLM.
    This mimics the exact flow that the agent uses.
    """
    # Create a simple test game
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Simple Test Game</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                font-family: 'Arial', sans-serif;
            }
            .game-container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                text-align: center;
            }
            h1 {
                color: #333;
                margin: 0 0 20px 0;
            }
            .status {
                color: #4ecdc4;
                font-size: 24px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="game-container">
            <h1>🎮 Test Game</h1>
            <div class="status">Game Running!</div>
        </div>
        <script>
            console.log('Game initialized successfully');
            console.warn('This is a test warning');
        </script>
    </body>
    </html>
    """
    
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        
        # Step 1: Create the game file
        print("\n📝 Step 1: Creating game HTML file...")
        workspace.write_file("index.html", html_content)
        print(f"   HTML file created in workspace")
        
        # Step 2: Run Playwright tests and capture screenshot
        print("\n🎭 Step 2: Running Playwright tests...")
        test_result = await validate_game_in_workspace(workspace)
        
        # Verify test results
        print(f"\n📊 Test Results:")
        print(f"   Success: {test_result.success}")
        print(f"   Errors: {len(test_result.errors)}")
        print(f"   Console logs: {len(test_result.console_logs)}")
        print(f"   Screenshot captured: {test_result.screenshot_bytes is not None}")
        
        # Critical assertions
        assert test_result is not None, "Test result should not be None"
        assert test_result.screenshot_bytes is not None, \
            f"Screenshot should be captured. Errors: {test_result.errors}"
        assert len(test_result.screenshot_bytes) > 0, "Screenshot should have content"
        assert isinstance(test_result.screenshot_bytes, bytes), "Screenshot must be bytes"
        
        # Verify PNG format
        assert test_result.screenshot_bytes.startswith(b'\x89PNG'), "Should be valid PNG"
        
        print(f"\n✅ Screenshot captured: {len(test_result.screenshot_bytes)} bytes")
        
        # Step 3: Validate with VLM (if API key available)
        print("\n🤖 Step 3: Validating with VLM...")
        try:
            vlm_client = VLMClient()
            
            is_valid, reason = validate_playable_with_vlm(
                vlm_client=vlm_client,
                screenshot_bytes=test_result.screenshot_bytes,
                console_logs=test_result.console_logs,
                user_prompt="Create a simple test game with a colorful gradient background",
                template_str=VLM_PLAYABLE_VALIDATION_PROMPT
            )
            
            print(f"\n📋 VLM Validation:")
            print(f"   Valid: {is_valid}")
            print(f"   Reason: {reason}")
            
            assert isinstance(is_valid, bool), "is_valid should be boolean"
            assert isinstance(reason, str), "reason should be string"
            assert len(reason) > 0, "reason should not be empty"
            
        except ValueError as e:
            print(f"\n⚠️  Skipping VLM validation: {e}")
            print("   Set GEMINI_API_KEY to test VLM validation")


@pytest.mark.asyncio  
async def test_screenshot_capture_failure_handling():
    """
    Test that we handle screenshot capture failures gracefully.
    """
    # Create HTML that will load but might have issues
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test</title>
    </head>
    <body>
        <script>
            // Cause an error
            throw new Error('Intentional error for testing');
        </script>
    </body>
    </html>
    """
    
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        workspace.write_file("index.html", html_content)
        
        result = await validate_game_in_workspace(workspace)
        
        # Even with errors, we should still capture a screenshot
        print(f"\n📊 Error handling test:")
        print(f"   Screenshot captured: {result.screenshot_bytes is not None}")
        print(f"   Errors: {result.errors}")
        print(f"   Console logs: {result.console_logs}")
        
        # Screenshot should still be captured (of error page)
        assert result.screenshot_bytes is not None, \
            "Screenshot should be captured even when page has errors"


@pytest.mark.asyncio
async def test_missing_index_html():
    """
    Test behavior when index.html is completely missing.
    """
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        # Don't create any files
        
        result = await validate_game_in_workspace(workspace)
        
        print(f"\n📊 Missing index.html test:")
        print(f"   Screenshot captured: {result.screenshot_bytes is not None}")
        print(f"   Errors: {result.errors[:3] if result.errors else []}")
        
        # Should have errors about missing file
        assert len(result.errors) > 0, "Should have errors when index.html missing"


if __name__ == "__main__":
    print("=" * 80)
    print("Running Full Screenshot Integration Tests")
    print("=" * 80)
    
    asyncio.run(test_full_screenshot_to_vlm_flow())
    asyncio.run(test_screenshot_capture_failure_handling())
    asyncio.run(test_missing_index_html())

