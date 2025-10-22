"""
Unit tests for screenshot capture functionality.
Tests the Playwright container and screenshot extraction.
"""
import pytest
import asyncio
from test_game import validate_game_in_workspace
from workspace import Workspace
import dagger


@pytest.mark.asyncio
async def test_screenshot_capture_with_simple_html():
    """
    Test that we can capture a screenshot from a simple HTML file.
    This is a unit test that creates a minimal HTML file and verifies screenshot capture works.
    """
    # Create a simple HTML file
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Page</title>
        <style>
            body {
                background-color: #00ff00;
                margin: 0;
                padding: 0;
                width: 100vw;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: Arial, sans-serif;
            }
            h1 {
                color: white;
                font-size: 48px;
            }
        </style>
    </head>
    <body>
        <h1>Screenshot Test</h1>
    </body>
    </html>
    """
    
    # Create workspace and add file
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        
        # Write the HTML file
        workspace.write_file("index.html", html_content)
        
        # Validate the game (which captures screenshot)
        result = await validate_game_in_workspace(workspace)
        
        # Assertions
        assert result is not None, "Result should not be None"
        assert result.screenshot_bytes is not None, "Screenshot should be captured"
        assert len(result.screenshot_bytes) > 0, "Screenshot should have content"
        assert isinstance(result.screenshot_bytes, bytes), "Screenshot should be bytes"
        
        # Verify it's a valid PNG
        assert result.screenshot_bytes.startswith(b'\x89PNG'), "Screenshot should be a valid PNG file"
        
        print(f"\n✅ Screenshot captured: {len(result.screenshot_bytes)} bytes")
        print(f"   Console logs: {len(result.console_logs)} entries")
        print(f"   Errors: {len(result.errors)}")


@pytest.mark.asyncio
async def test_screenshot_capture_with_no_html():
    """
    Test behavior when index.html doesn't exist.
    Should still attempt to capture a screenshot (of error page).
    """
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        
        # Don't create any files - workspace is empty
        
        # Validate the game
        result = await validate_game_in_workspace(workspace)
        
        # Assertions
        assert result is not None, "Result should not be None"
        # Screenshot might still be captured (of error page)
        # But we should have errors
        assert len(result.errors) > 0, "Should have errors when index.html missing"
        
        print(f"\n✅ Error handling works:")
        print(f"   Errors: {result.errors}")
        print(f"   Screenshot captured: {result.screenshot_bytes is not None}")


@pytest.mark.asyncio
async def test_screenshot_capture_with_javascript_game():
    """
    Test screenshot capture with a real JavaScript game using PixiJS.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>PixiJS Test Game</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
        <style>
            body {
                margin: 0;
                padding: 0;
                overflow: hidden;
                background-color: #000000;
            }
        </style>
    </head>
    <body>
        <script>
            // Create Pixi application
            const app = new PIXI.Application();
            
            app.init({
                width: 800,
                height: 600,
                backgroundColor: 0x1099bb
            }).then(() => {
                document.body.appendChild(app.canvas);
                
                // Add a simple sprite
                const graphics = new PIXI.Graphics();
                graphics.rect(100, 100, 200, 200);
                graphics.fill(0xff0000);
                app.stage.addChild(graphics);
                
                // Add text
                const text = new PIXI.Text({
                    text: 'PixiJS Game Test',
                    style: {
                        fontFamily: 'Arial',
                        fontSize: 36,
                        fill: 0xffffff
                    }
                });
                text.x = 400;
                text.y = 300;
                text.anchor.set(0.5);
                app.stage.addChild(text);
                
                console.log('PixiJS game initialized successfully');
            }).catch(err => {
                console.error('Failed to initialize PixiJS:', err);
            });
        </script>
    </body>
    </html>
    """
    
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        workspace.write_file("index.html", html_content)
        
        # Validate the game
        result = await validate_game_in_workspace(workspace)
        
        # Assertions
        assert result is not None, "Result should not be None"
        assert result.screenshot_bytes is not None, "Screenshot should be captured"
        assert len(result.screenshot_bytes) > 0, "Screenshot should have content"
        
        # Check console logs for PixiJS initialization
        log_text = '\n'.join(result.console_logs)
        print(f"\n✅ PixiJS game screenshot captured: {len(result.screenshot_bytes)} bytes")
        print(f"   Console logs:\n{log_text[:500]}")
        
        # Verify it's a PNG
        assert result.screenshot_bytes.startswith(b'\x89PNG'), "Screenshot should be PNG"


@pytest.mark.asyncio
async def test_screenshot_bytes_type():
    """
    Test that screenshot is always returned as bytes, not string.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>Type Test</title></head>
    <body><h1 style="color: blue;">Type Test</h1></body>
    </html>
    """
    
    async with dagger.Connection() as client:
        workspace = await Workspace.create(client)
        workspace.write_file("index.html", html_content)
        
        result = await validate_game_in_workspace(workspace)
        
        # Critical assertion - must be bytes for PIL Image
        assert isinstance(result.screenshot_bytes, bytes) or result.screenshot_bytes is None, \
            f"Screenshot must be bytes or None, got {type(result.screenshot_bytes)}"
        
        if result.screenshot_bytes:
            # Should be able to use with PIL
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(result.screenshot_bytes))
            print(f"\n✅ Screenshot type correct: bytes")
            print(f"   Image size: {image.size}")
            print(f"   Image mode: {image.mode}")


if __name__ == "__main__":
    # Run tests
    print("Running screenshot capture tests...")
    asyncio.run(test_screenshot_capture_with_simple_html())
    asyncio.run(test_screenshot_capture_with_no_html())
    asyncio.run(test_screenshot_capture_with_javascript_game())
    asyncio.run(test_screenshot_bytes_type())

