# Asset Loading Fix

## Problem

The agent was trying to use assets from the Racing Pack but failing with this error:

```
Uncaught exception: [Loader.load] Failed to load file:///app/assets/car_black_1.png.
TypeError: Failed to fetch
```

The agent was using code like this:

```javascript
async loadAssets() {
    const assets = [
        'assets/car_black_1.png',
        'assets/rock1.png',
        'assets/road_asphalt03.png'
    ];
    
    for (const asset of assets) {
        await PIXI.Assets.load(asset);  // ❌ This was failing
    }
}
```

## Root Cause

The assets **were being copied correctly** to the workspace and Playwright container. The issue was with **how the agent was loading them**:

1. Assets are correctly copied from `assets/Racing Pack/` to workspace at `/app/assets/`
2. Game runs in Playwright via `file:///app/index.html` protocol
3. The sequential preloading approach had compatibility issues in the containerized environment

## Solution

Updated `src/asset_manager.py` to provide **detailed, specific instructions** on how to load assets correctly in the prompt. The new instructions include:

### Method 1: Direct Sprite Creation (RECOMMENDED)
```javascript
// Load sprite directly - works immediately
const car = PIXI.Sprite.from('assets/car_black_1.png');
```

This method is more robust and doesn't require async preloading.

### Method 2: Texture Loading with Proper Async/Await
```javascript
async loadAssets() {
    // Load and store textures
    this.textures = {
        car: await PIXI.Assets.load('assets/car_black_1.png'),
        rock: await PIXI.Assets.load('assets/rock1.png'),
        road: await PIXI.Assets.load('assets/road_asphalt03.png')
    };
}

// Then create sprites from stored textures
const car = new PIXI.Sprite(this.textures.car);
```

This approach stores texture references for reuse.

### Critical Path Format Rules

The instructions now explicitly state:
- ✓ **CORRECT**: `'assets/car_black_1.png'`
- ✗ **WRONG**: `'./assets/car_black_1.png'`
- ✗ **WRONG**: `'/assets/car_black_1.png'`
- ✗ **WRONG**: `'/app/assets/car_black_1.png'`

## File Changed

- `src/asset_manager.py` - Updated `format_asset_context_for_prompt()` function

## Testing

The fix ensures that when an asset pack is selected:
1. Assets are copied to `game_path/assets/` (already working)
2. Workspace loads assets into container at `/app/assets/` (already working)
3. **NEW**: Agent receives clear instructions on the correct loading methods
4. Agent can now successfully use assets without falling back to programmatic graphics

## CORS Fix (Additional Issue)

After implementing the initial fix, a CORS (Cross-Origin Resource Sharing) error was discovered:
```
CORS policy errors when loading assets from file:// protocol
```

**Solution**: Updated Playwright browser launch in `test_game.py` to include flags that allow local file access:

```javascript
const browser = await chromium.launch({
    args: [
        '--allow-file-access-from-files',
        '--disable-web-security'
    ]
});
```

This allows the browser to load local assets when the game is served via `file://` protocol in the testing environment.

## Key Benefits

1. **Better Instructions**: Agent now has explicit examples of working code
2. **Multiple Methods**: Agent can choose the best approach for its use case
3. **Error Prevention**: Clear anti-patterns help avoid common mistakes
4. **CORS Resolution**: Browser configured to allow local file access
5. **No Breaking Changes**: Asset copying mechanism remains unchanged

