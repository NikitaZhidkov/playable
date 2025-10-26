"""
Integration tests for test_game module with real Workspace and Dagger containers.

These tests require:
- Docker daemon running
- Dagger SDK working
- Network access to pull container images

Run with: pytest tests/integration/ -v -m integration
Skip with: pytest tests/ -m "not integration"
"""
import pytest
import asyncio
import dagger
from test_game import validate_game_in_workspace, GameTestResult, TEST_SCRIPT
from src.containers import Workspace


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
async def simple_working_game_workspace(dagger_client):
    """Create a workspace with a simple working game."""
    # Create a minimal working HTML game
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Test Game</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            font-family: Arial, sans-serif;
        }
        #game {
            color: white;
            text-align: center;
        }
    </style>
</head>
<body>
    <div id="game">
        <h1>Test Game</h1>
        <p>Score: <span id="score">0</span></p>
        <button onclick="incrementScore()">Click Me!</button>
    </div>
    <script>
        let score = 0;
        function incrementScore() {
            score++;
            document.getElementById('score').textContent = score;
        }
        console.log('Game initialized successfully');
    </script>
</body>
</html>"""
    
    # Create workspace using the proper factory method
    workspace = await Workspace.create(
        client=dagger_client,
        base_image="alpine:latest",
        context=None
    )
    
    # Write the HTML file (workspace has /app as workdir)
    workspace = workspace.write_file("index.html", html_content, force=True)
    
    return workspace


@pytest.fixture
async def broken_game_workspace(dagger_client):
    """Create a workspace with a broken game (JavaScript error)."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Broken Test Game</title>
</head>
<body>
    <h1>Broken Game</h1>
    <script>
        // This will cause an error
        console.log('Starting game...');
        undefinedFunction(); // ReferenceError
        console.log('This should not appear');
    </script>
</body>
</html>"""
    
    workspace = await Workspace.create(
        client=dagger_client,
        base_image="alpine:latest",
        context=None
    )
    
    workspace = workspace.write_file("index.html", html_content, force=True)
    
    return workspace


class TestValidateGameInWorkspaceIntegration:
    """Integration tests for validate_game_in_workspace with real containers."""
    
    @pytest.mark.asyncio
    async def test_working_game_passes(self, simple_working_game_workspace, playwright_container):
        """Test that a working game passes validation."""
        # Copy workspace files to playwright container and add test script
        playwright_container.copy_directory(
            simple_working_game_workspace.container().directory(".")
        ).with_test_script(TEST_SCRIPT)
        
        result = await validate_game_in_workspace(playwright_container)
        
        assert isinstance(result, GameTestResult)
        assert result.success is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_broken_game_fails(self, broken_game_workspace, playwright_container):
        """Test that a broken game captures errors (VLM will decide if it failed)."""
        # Copy workspace files to playwright container and add test script
        playwright_container.copy_directory(
            broken_game_workspace.container().directory(".")
        ).with_test_script(TEST_SCRIPT)
        
        result = await validate_game_in_workspace(playwright_container)
        
        assert isinstance(result, GameTestResult)
        # Test script always returns success=True, VLM decides actual success
        assert result.success is True
        # But it should capture the error
        assert len(result.errors) > 0
        
        # Check that we caught the JavaScript error
        error_text = ' '.join(result.errors).lower()
        assert 'undefinedfunction' in error_text or 'error' in error_text
    
    @pytest.mark.asyncio
    async def test_game_with_external_resource_missing(self, dagger_client, playwright_container):
        """Test game that tries to load missing external resource."""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Game With Missing Resource</title>
    <script src="nonexistent.js"></script>
</head>
<body>
    <h1>Game With Missing Resource</h1>
    <script>
        console.log('Main script running');
    </script>
</body>
</html>"""
        
        workspace = await Workspace.create(
            client=dagger_client,
            base_image="alpine:latest",
            context=None
        )
        
        workspace = workspace.write_file("index.html", html_content, force=True)
        
        # Copy workspace files to playwright container and add test script
        playwright_container.copy_directory(
            workspace.container().directory(".")
        ).with_test_script(TEST_SCRIPT)
        
        result = await validate_game_in_workspace(playwright_container)
        
        assert isinstance(result, GameTestResult)
        # Test script always returns success=True, VLM decides actual success
        assert result.success is True
        # But it should capture the error about missing resource
        assert len(result.errors) > 0
        
        # Check that we detected the missing resource
        error_text = ' '.join(result.errors).lower()
        assert 'failed to load' in error_text or 'nonexistent.js' in error_text


class TestValidateGameWithComplexSetup:
    """Integration tests with more complex game setups."""
    
    @pytest.mark.asyncio
    async def test_game_with_separate_js_file(self, dagger_client, playwright_container):
        """Test game with external JavaScript file."""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Game With External JS</title>
</head>
<body>
    <h1>Game</h1>
    <div id="output"></div>
    <script src="game.js"></script>
</body>
</html>"""
        
        js_content = """
console.log('External JS loaded');
document.getElementById('output').textContent = 'Game initialized!';
"""
        
        workspace = await Workspace.create(
            client=dagger_client,
            base_image="alpine:latest",
            context=None
        )
        
        workspace = workspace.write_file("index.html", html_content, force=True)
        workspace = workspace.write_file("game.js", js_content, force=True)
        
        # Copy workspace files to playwright container and add test script
        playwright_container.copy_directory(
            workspace.container().directory(".")
        ).with_test_script(TEST_SCRIPT)
        
        result = await validate_game_in_workspace(playwright_container)
        
        assert isinstance(result, GameTestResult)
        assert result.success is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_game_with_css_and_js(self, dagger_client, playwright_container):
        """Test game with both CSS and JS files."""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Full Game</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="game">
        <h1>Full Featured Game</h1>
        <p id="status">Loading...</p>
    </div>
    <script src="app.js"></script>
</body>
</html>"""
        
        css_content = """
body {
    margin: 0;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
#game {
    background: white;
    padding: 20px;
    border-radius: 10px;
}
"""
        
        js_content = """
console.log('App starting...');
document.getElementById('status').textContent = 'Ready!';
console.log('App ready!');
"""
        
        workspace = await Workspace.create(
            client=dagger_client,
            base_image="alpine:latest",
            context=None
        )
        
        workspace = workspace.write_file("index.html", html_content, force=True)
        workspace = workspace.write_file("style.css", css_content, force=True)
        workspace = workspace.write_file("app.js", js_content, force=True)
        
        # Copy workspace files to playwright container and add test script
        playwright_container.copy_directory(
            workspace.container().directory(".")
        ).with_test_script(TEST_SCRIPT)
        
        result = await validate_game_in_workspace(playwright_container)
        
        assert isinstance(result, GameTestResult)
        assert result.success is True
        assert len(result.errors) == 0

