"""
Integration tests for asset loading examples provided to the agent.

These tests verify that the code examples in the asset loading instructions
actually work correctly in the containerized Playwright environment.

These tests require:
- Docker daemon running
- Dagger SDK working
- Network access to pull container images
- Valid asset pack in assets/ directory

Run with: pytest tests/integration/test_asset_loading_examples.py -v -m integration
Skip with: pytest tests/ -m "not integration"
"""
import pytest
import asyncio
import dagger
from pathlib import Path
from src.containers import Workspace, PlaywrightContainer
from src.asset_manager import (
    format_asset_context_for_prompt,
    get_or_create_pack_descriptions,
    prepare_pack_for_workspace
)
from test_game import validate_game_in_workspace
import re


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def extract_code_examples(prompt_text: str) -> dict:
    """Extract JavaScript code examples from the prompt."""
    examples = {}
    
    # Extract Method 1 example (Direct Sprite Creation)
    method1_pattern = r'```javascript\s*\n// Load sprite directly.*?\nconst car = PIXI\.Sprite\.from\((.*?)\);'
    method1_match = re.search(method1_pattern, prompt_text, re.DOTALL)
    if method1_match:
        examples['method1_path'] = method1_match.group(1).strip()
    
    # Extract Method 2 example (Texture Loading)
    method2_pattern = r'```javascript\s*\nasync loadAssets\(\) \{(.*?)\}'
    method2_match = re.search(method2_pattern, prompt_text, re.DOTALL)
    if method2_match:
        examples['method2_code'] = method2_match.group(1).strip()
    
    # Extract path format rules
    correct_pattern = r'✓ CORRECT: [\'"]([^\'\"]+)[\'"]'
    correct_matches = re.findall(correct_pattern, prompt_text)
    examples['correct_paths'] = correct_matches
    
    wrong_pattern = r'✗ WRONG: [\'"]([^\'\"]+)[\'"]'
    wrong_matches = re.findall(wrong_pattern, prompt_text)
    examples['wrong_paths'] = wrong_matches
    
    return examples


@pytest.fixture
async def asset_workspace(dagger_client, tmp_path):
    """Create a workspace with test assets."""
    # Create temporary asset directory
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    
    # Create a simple test image (1x1 red pixel PNG)
    # This is a valid minimal PNG file
    red_pixel_png = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0x99, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
        0x00, 0x00, 0x03, 0x00, 0x01, 0x5C, 0xCD, 0xFF,
        0x1C, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    
    # Create test assets
    (assets_dir / "test_car.png").write_bytes(red_pixel_png)
    (assets_dir / "test_rock.png").write_bytes(red_pixel_png)
    (assets_dir / "test_road.png").write_bytes(red_pixel_png)
    
    # Create workspace with assets
    workspace = await Workspace.create(
        client=dagger_client,
        base_image="alpine:latest",
        context=dagger_client.host().directory(str(tmp_path))
    )
    
    return workspace


def create_test_game_html(loading_method: str, asset_path: str = "assets/test_car.png") -> str:
    """Create test HTML with specific asset loading method."""
    
    if loading_method == "method1_direct":
        loading_code = f"""
        async function initGame() {{
            const app = new PIXI.Application();
            await app.init({{
                width: 400,
                height: 300,
                backgroundColor: 0x1099bb
            }});
            document.body.appendChild(app.canvas);
            
            // Method 1: Direct sprite creation
            const car = PIXI.Sprite.from('{asset_path}');
            car.x = 100;
            car.y = 100;
            app.stage.addChild(car);
            
            console.log('SUCCESS: Method 1 - Direct sprite creation worked!');
            console.log('Car position:', car.x, car.y);
        }}
        """
    
    elif loading_method == "method2_texture":
        loading_code = f"""
        async function initGame() {{
            const app = new PIXI.Application();
            await app.init({{
                width: 400,
                height: 300,
                backgroundColor: 0x1099bb
            }});
            document.body.appendChild(app.canvas);
            
            // Method 2: Texture loading
            const textures = {{
                car: await PIXI.Assets.load('{asset_path}'),
                rock: await PIXI.Assets.load('assets/test_rock.png'),
                road: await PIXI.Assets.load('assets/test_road.png')
            }};
            
            const car = new PIXI.Sprite(textures.car);
            car.x = 100;
            car.y = 100;
            app.stage.addChild(car);
            
            console.log('SUCCESS: Method 2 - Texture loading worked!');
            console.log('Loaded textures:', Object.keys(textures).length);
        }}
        """
    
    elif loading_method == "wrong_path":
        # This should fail - testing wrong path format
        loading_code = f"""
        async function initGame() {{
            const app = new PIXI.Application();
            await app.init({{
                width: 400,
                height: 300,
                backgroundColor: 0x1099bb
            }});
            document.body.appendChild(app.canvas);
            
            // Wrong path format - should fail
            const car = PIXI.Sprite.from('{asset_path}');
            car.x = 100;
            car.y = 100;
            app.stage.addChild(car);
            
            console.log('This should not appear');
        }}
        """
    
    else:
        raise ValueError(f"Unknown loading method: {loading_method}")
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asset Loading Test</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            overflow: hidden;
            background: #333;
        }}
    </style>
</head>
<body>
    <script>
        {loading_code}
        
        initGame().catch((error) => {{
            console.error('ERROR: Game initialization failed:', error.message);
        }});
    </script>
</body>
</html>"""


def test_prompt_contains_required_sections():
    """Test that the asset prompt contains instructions but NOT base64 data."""
    # Create minimal XML content directly (skip VLM generation)
    xml_content = """<pack name="TestPack">
  <asset name="test_car.png" width="64" height="64" description="Test car sprite"/>
  <asset name="test_rock.png" width="32" height="32" description="Test rock obstacle"/>
</pack>"""
    
    # Format for prompt (no base64 parameter - it's in assets.js file)
    prompt_text = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check that prompt contains required sections
    assert "## IMPORTANT: How to Use Assets with Base64" in prompt_text, \
        "Prompt should contain base64 asset instructions section"
    
    assert "assets/assets.js" in prompt_text, \
        "Prompt should reference assets.js file"
    
    assert "<script src=\"assets/assets.js\"></script>" in prompt_text, \
        "Prompt should show how to load assets.js"
    
    # Verify async loading approach is documented
    assert "loadBase64Image" in prompt_text, \
        "Prompt should contain loadBase64Image helper function"
    
    assert "img.onload" in prompt_text, \
        "Prompt should mention img.onload event"
    
    assert "PIXI.Texture.from(img)" in prompt_text, \
        "Prompt should show PIXI.Texture.from(img) approach"
    
    assert "async function" in prompt_text, \
        "Prompt should show async function usage"
    
    # Verify warning about synchronous approach
    assert "doesn't work" in prompt_text.lower(), \
        "Prompt should warn that synchronous approach doesn't work"
    
    # Verify base64 data is NOT in prompt (it's in assets.js file instead)
    assert "data:image/png;base64," not in prompt_text, \
        "Prompt should NOT contain base64 data (it's in assets.js file)"
    
    # Verify instructions warn against wrong approaches
    assert "WRONG:" in prompt_text, \
        "Prompt should show wrong approaches"


@pytest.mark.asyncio
async def test_method1_direct_sprite_creation(dagger_client, asset_workspace, playwright_container):
    """Test that Method 1 (Direct Sprite Creation) works correctly."""
    # Create game HTML using Method 1
    html_content = create_test_game_html("method1_direct", "assets/test_car.png")
    
    # Write to workspace
    workspace = asset_workspace.write_file("index.html", html_content, force=True)
    
    # Copy to Playwright container
    playwright_container.reset()
    playwright_container.copy_directory(workspace.container().directory("."))
    
    # Create test script
    test_script = """
const path = require('path');
const { chromium } = require('playwright');

async function testAssetLoading() {
    const consoleLogs = [];
    const errors = [];
    
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    page.on('console', (msg) => {
        const text = msg.text();
        consoleLogs.push(text);
    });
    
    page.on('pageerror', (error) => {
        errors.push(error.message);
    });
    
    try {
        const indexPath = path.resolve('/app/index.html');
        await page.goto(`file://${indexPath}`, { 
            waitUntil: 'networkidle',
            timeout: 10000 
        });
        
        await page.waitForTimeout(3000);
    } catch (error) {
        errors.push(error.message);
    }
    
    await browser.close();
    
    console.log('__LOGS__' + JSON.stringify({logs: consoleLogs, errors: errors}) + '__END__');
}

testAssetLoading().catch((error) => {
    console.log('__LOGS__' + JSON.stringify({logs: [], errors: [error.message]}) + '__END__');
    process.exit(1);
});
"""
    
    playwright_container.with_test_script(test_script)
    
    # Run test
    result = await playwright_container.container().with_exec(
        ["node", "/app/test-runner.js"],
        expect=dagger.ReturnType.ANY
    ).stdout()
    
    # Parse results
    assert "__LOGS__" in result, "Test should produce output"
    
    # Extract logs
    import json
    log_data = result.split("__LOGS__")[1].split("__END__")[0]
    data = json.loads(log_data)
    
    # Verify success
    success_logs = [log for log in data['logs'] if 'SUCCESS' in log and 'Method 1' in log]
    assert len(success_logs) > 0, f"Method 1 should succeed. Logs: {data['logs']}, Errors: {data['errors']}"
    
    # Should have no loading errors
    load_errors = [err for err in data['errors'] if 'Failed to load' in err or 'Failed to fetch' in err]
    assert len(load_errors) == 0, f"Should not have asset loading errors: {load_errors}"


@pytest.mark.asyncio
async def test_method2_texture_loading(dagger_client, asset_workspace, playwright_container):
    """Test that Method 2 (Texture Loading) works correctly."""
    # Create game HTML using Method 2
    html_content = create_test_game_html("method2_texture", "assets/test_car.png")
    
    # Write to workspace
    workspace = asset_workspace.write_file("index.html", html_content, force=True)
    
    # Copy to Playwright container
    playwright_container.reset()
    playwright_container.copy_directory(workspace.container().directory("."))
    
    # Create test script (same as Method 1)
    test_script = """
const path = require('path');
const { chromium } = require('playwright');

async function testAssetLoading() {
    const consoleLogs = [];
    const errors = [];
    
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    page.on('console', (msg) => {
        const text = msg.text();
        consoleLogs.push(text);
    });
    
    page.on('pageerror', (error) => {
        errors.push(error.message);
    });
    
    try {
        const indexPath = path.resolve('/app/index.html');
        await page.goto(`file://${indexPath}`, { 
            waitUntil: 'networkidle',
            timeout: 10000 
        });
        
        await page.waitForTimeout(3000);
    } catch (error) {
        errors.push(error.message);
    }
    
    await browser.close();
    
    console.log('__LOGS__' + JSON.stringify({logs: consoleLogs, errors: errors}) + '__END__');
}

testAssetLoading().catch((error) => {
    console.log('__LOGS__' + JSON.stringify({logs: [], errors: [error.message]}) + '__END__');
    process.exit(1);
});
"""
    
    playwright_container.with_test_script(test_script)
    
    # Run test
    result = await playwright_container.container().with_exec(
        ["node", "/app/test-runner.js"],
        expect=dagger.ReturnType.ANY
    ).stdout()
    
    # Parse results
    assert "__LOGS__" in result, "Test should produce output"
    
    import json
    log_data = result.split("__LOGS__")[1].split("__END__")[0]
    data = json.loads(log_data)
    
    # Verify success
    success_logs = [log for log in data['logs'] if 'SUCCESS' in log and 'Method 2' in log]
    assert len(success_logs) > 0, f"Method 2 should succeed. Logs: {data['logs']}, Errors: {data['errors']}"
    
    # Should load all 3 textures
    texture_logs = [log for log in data['logs'] if 'Loaded textures: 3' in log]
    assert len(texture_logs) > 0, f"Should load 3 textures. Logs: {data['logs']}"
    
    # Should have no loading errors
    load_errors = [err for err in data['errors'] if 'Failed to load' in err or 'Failed to fetch' in err]
    assert len(load_errors) == 0, f"Should not have asset loading errors: {load_errors}"


@pytest.mark.asyncio
async def test_wrong_path_format_fails(dagger_client, asset_workspace, playwright_container):
    """Test that wrong path formats (as documented) actually fail."""
    wrong_paths = [
        './assets/test_car.png',  # Wrong: relative with ./
        '/assets/test_car.png',   # Wrong: absolute path
        '/app/assets/test_car.png'  # Wrong: container path
    ]
    
    for wrong_path in wrong_paths:
        # Create game HTML with wrong path
        html_content = create_test_game_html("wrong_path", wrong_path)
        
        # Write to workspace
        workspace = asset_workspace.write_file("index.html", html_content, force=True)
        
        # Copy to Playwright container
        playwright_container.reset()
        playwright_container.copy_directory(workspace.container().directory("."))
        
        # Create test script
        test_script = """
const path = require('path');
const { chromium } = require('playwright');

async function testAssetLoading() {
    const errors = [];
    
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    page.on('pageerror', (error) => {
        errors.push(error.message);
    });
    
    page.on('requestfailed', (request) => {
        errors.push(`Failed to load: ${request.url()}`);
    });
    
    try {
        const indexPath = path.resolve('/app/index.html');
        await page.goto(`file://${indexPath}`, { 
            waitUntil: 'networkidle',
            timeout: 10000 
        });
        
        await page.waitForTimeout(2000);
    } catch (error) {
        errors.push(error.message);
    }
    
    await browser.close();
    
    console.log('__ERRORS__' + JSON.stringify({errors: errors}) + '__END__');
}

testAssetLoading().catch((error) => {
    console.log('__ERRORS__' + JSON.stringify({errors: [error.message]}) + '__END__');
    process.exit(1);
});
"""
        
        playwright_container.with_test_script(test_script)
        
        # Run test
        result = await playwright_container.container().with_exec(
            ["node", "/app/test-runner.js"],
            expect=dagger.ReturnType.ANY
        ).stdout()
        
        # Parse results
        assert "__ERRORS__" in result, f"Test should produce output for path: {wrong_path}"
        
        import json
        error_data = result.split("__ERRORS__")[1].split("__END__")[0]
        data = json.loads(error_data)
        
        # Verify that wrong path causes errors
        # Note: We expect loading errors or failures here
        assert len(data['errors']) > 0, \
            f"Wrong path format '{wrong_path}' should cause errors, but none were found"


@pytest.mark.asyncio 
async def test_racing_pack_asset_loading(tmp_path):
    """Test asset loading with real Racing Pack if it exists."""
    racing_pack_path = Path("assets") / "Racing Pack"
    
    if not racing_pack_path.exists():
        pytest.skip("Racing Pack not found - skipping real pack test")
    
    # Prepare pack for workspace (this is what the agent will use)
    workspace_assets_dir = tmp_path / "game_assets"
    
    from src.asset_manager import prepare_pack_for_workspace
    asset_context = prepare_pack_for_workspace(
        pack_name="Racing Pack",
        workspace_assets_dir=workspace_assets_dir
    )
    
    assert asset_context is not None, "Should successfully prepare Racing Pack"
    
    # Verify instructions are present but NOT base64 data
    assert "## IMPORTANT: How to Use Assets with Base64" in asset_context, \
        "Should include base64 usage instructions"
    assert "assets/assets.js" in asset_context, \
        "Should reference assets.js file"
    assert "PIXI.Sprite.from(ASSETS[" in asset_context, \
        "Should include usage example with ASSETS object"
    
    # Verify base64 data is NOT in prompt (efficiency)
    assert "data:image/png;base64," not in asset_context, \
        "Should NOT include base64 data in prompt (it's in assets.js file)"
    
    # Verify assets.js was created in workspace
    assets_js_file = workspace_assets_dir / "assets.js"
    assert assets_js_file.exists(), \
        "assets.js should be created in workspace"
    
    # Verify assets.js contains base64 data
    assets_js_content = assets_js_file.read_text()
    assert "data:image/png;base64," in assets_js_content, \
        "assets.js should contain base64 data"
    assert "'car_black_1.png':" in assets_js_content, \
        "assets.js should include car_black_1.png"
    assert "'rock1.png':" in assets_js_content, \
        "assets.js should include rock1.png"
    assert "const ASSETS = {" in assets_js_content, \
        "assets.js should define ASSETS object"
    
    # Verify PNG files are NOT copied to workspace
    assert not (workspace_assets_dir / "car_black_1.png").exists(), \
        "PNG files should NOT be copied to workspace (using assets.js instead)"
    
    # Verify cache was created in source pack
    cache_file = racing_pack_path / "base64" / "cache.json"
    assert cache_file.exists(), \
        "Base64 cache should be created in source pack directory"

