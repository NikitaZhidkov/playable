#!/usr/bin/env python3
"""
Test actual asset loading in Playwright to see the real errors.
"""
import asyncio
import dagger
from pathlib import Path


async def test_real_asset_loading():
    """Test asset loading with actual Playwright to see console errors."""
    
    # Create a simple test game with assets
    test_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Asset Loading Test</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
</head>
<body>
    <script>
        async function testAssets() {
            console.log('=== Starting asset loading test ===');
            
            const app = new PIXI.Application();
            await app.init({
                width: 400,
                height: 300,
                backgroundColor: 0x1099bb
            });
            document.body.appendChild(app.canvas);
            console.log('PIXI app initialized');
            
            try {
                // Method 1: Direct sprite creation
                console.log('Trying Method 1: PIXI.Sprite.from...');
                const sprite1 = PIXI.Sprite.from('assets/test.png');
                sprite1.x = 50;
                sprite1.y = 50;
                app.stage.addChild(sprite1);
                console.log('SUCCESS: Method 1 worked!');
            } catch (err) {
                console.error('ERROR Method 1:', err.message);
            }
            
            try {
                // Method 2: PIXI.Assets.load
                console.log('Trying Method 2: PIXI.Assets.load...');
                const texture = await PIXI.Assets.load('assets/test.png');
                const sprite2 = new PIXI.Sprite(texture);
                sprite2.x = 150;
                sprite2.y = 50;
                app.stage.addChild(sprite2);
                console.log('SUCCESS: Method 2 worked!');
            } catch (err) {
                console.error('ERROR Method 2:', err.message);
            }
            
            console.log('=== Test complete ===');
        }
        
        testAssets().catch(err => {
            console.error('FATAL ERROR:', err);
        });
    </script>
</body>
</html>"""
    
    # Create test script for Playwright
    test_script = """
const path = require('path');
const { chromium } = require('playwright');

async function testAssetLoading() {
    console.log('Starting Playwright test...');
    
    const consoleLogs = [];
    const errors = [];
    
    const browser = await chromium.launch({
        args: [
            '--allow-file-access-from-files',
            '--disable-web-security'
        ]
    });
    
    const page = await browser.newPage();
    
    // Capture all console messages
    page.on('console', (msg) => {
        const text = msg.text();
        consoleLogs.push(text);
        console.log('[BROWSER]', text);
    });
    
    // Capture errors
    page.on('pageerror', (error) => {
        const msg = `PageError: ${error.message}`;
        errors.push(msg);
        console.error('[ERROR]', msg);
    });
    
    // Capture failed requests
    page.on('requestfailed', (request) => {
        const msg = `RequestFailed: ${request.url()} - ${request.failure().errorText}`;
        errors.push(msg);
        console.error('[FAILED]', msg);
    });
    
    try {
        const indexPath = path.resolve('/app/index.html');
        console.log('Loading:', indexPath);
        
        await page.goto(`file://${indexPath}`, { 
            waitUntil: 'networkidle',
            timeout: 10000 
        });
        
        // Wait for test to complete
        await page.waitForTimeout(3000);
        
        // Take screenshot
        await page.screenshot({ path: '/app/test_screenshot.png' });
        console.log('Screenshot saved');
        
    } catch (error) {
        console.error('[EXCEPTION]', error.message);
    } finally {
        await browser.close();
    }
    
    console.log('\\n=== SUMMARY ===');
    console.log('Console logs:', consoleLogs.length);
    console.log('Errors:', errors.length);
    if (errors.length > 0) {
        console.log('\\nErrors found:');
        errors.forEach(err => console.log(' -', err));
    }
}

testAssetLoading().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
"""
    
    async with dagger.Connection() as client:
        print("\n" + "=" * 60)
        print("Testing Asset Loading in Playwright")
        print("=" * 60)
        
        # Create test image (1x1 red pixel PNG)
        red_pixel_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0x99, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x5C, 0xCD, 0xFF,
            0x1C, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        # Create container
        container = (
            client.container()
            .from_("mcr.microsoft.com/playwright:v1.49.0-jammy")
            .with_workdir("/app")
            .with_new_file("/app/package.json", '{"dependencies": {"playwright": "1.49.0"}}')
            .with_exec(["npm", "install"])
        )
        
        # Create assets directory in project
        test_assets_dir = Path("test_temp_assets")
        test_assets_dir.mkdir(exist_ok=True)
        (test_assets_dir / "test.png").write_bytes(red_pixel_png)
        
        try:
            # Add test files
            container = (
                container
                .with_new_file("/app/index.html", test_html)
                .with_new_file("/app/test-runner.js", test_script)
                .with_directory("/app/assets", client.host().directory(str(test_assets_dir)))
            )
            
            # Run test
            print("\nRunning test...")
            result = await container.with_exec(["node", "/app/test-runner.js"]).stdout()
        finally:
            # Cleanup
            import shutil
            if test_assets_dir.exists():
                shutil.rmtree(test_assets_dir)
        
        print("\n" + "=" * 60)
        print("Test Output:")
        print("=" * 60)
        print(result)
        
        # Try to get screenshot
        try:
            screenshot_bytes = await container.file("/app/test_screenshot.png").contents()
            screenshot_path = Path("test_asset_loading_screenshot.png")
            screenshot_path.write_bytes(screenshot_bytes)
            print(f"\n✓ Screenshot saved to: {screenshot_path}")
        except Exception as e:
            print(f"\n✗ Could not get screenshot: {e}")


if __name__ == "__main__":
    asyncio.run(test_real_asset_loading())

