# Base64 Asset System - Updated Approach

## Overview

The asset system converts images to base64 and provides them in an `assets.js` file. The prompt references this file WITHOUT embedding the base64 data, keeping prompts efficient.

## Key Benefits

✅ **Efficient prompts** - No large base64 strings in prompts  
✅ **Single-file deployment** - All assets in `assets.js`  
✅ **No CORS issues** - No external file loading  
✅ **Smart caching** - Base64 cached in source pack  
✅ **Easy to use** - Just load `assets.js` in HTML  

## How It Works

### 1. Preparation Phase

When you select an asset pack:
```
1. System converts PNGs to base64 (cached)
2. Creates assets.js with all base64 data
3. Copies assets.js to workspace
4. Provides prompt with instructions (NO base64 in prompt!)
```

### 2. File Structure

**Source (assets/):**
```
assets/Racing Pack/
├── car_black_1.png         # Original images
├── rock1.png
├── description.xml         # Metadata
└── base64/                 # Auto-generated cache
    └── cache.json          # Cached base64 (gitignored)
```

**Workspace (games/session_xxx/):**
```
games/session_123/
├── index.html
├── game.js
└── assets/
    └── assets.js           # All base64 data here
```

### 3. Generated assets.js

```javascript
// Asset pack: Racing Pack
// Auto-generated base64 asset data

const ASSETS = {
    'car_black_1.png': 'data:image/png;base64,iVBORw0KGgo...',
    'rock1.png': 'data:image/png;base64,iVBORw0KGgo...',
    // ... all assets
};

// Export for use in game
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ASSETS;
}
```

### 4. Agent Instructions (in prompt)

The agent receives **instructions only**, NOT base64 data:

```markdown
## IMPORTANT: How to Use Assets with Base64

All assets are pre-converted to base64 and stored in 'assets/assets.js'.

### Step 1: Load the Assets File

<script src="assets/assets.js"></script>
<script src="game.js"></script>

### Step 2: Use the ASSETS Object

const car = PIXI.Sprite.from(ASSETS['car_black_1.png']);
```

## Comparison: Old vs New Approach

### ❌ Old (Embedded in Prompt)
```
Prompt size: ~34KB (with base64 data)
- Expensive tokens
- Slow to process
- Wasteful
```

### ✅ New (File Reference)
```
Prompt size: ~3KB (instructions only)
- Efficient tokens
- Fast to process
- Clean separation
```

## Usage Example

### Generated HTML (index.html):
```html
<!DOCTYPE html>
<html>
<head>
    <title>My Game</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
</head>
<body>
    <!-- Load assets first -->
    <script src="assets/assets.js"></script>
    <!-- Then load game -->
    <script src="game.js"></script>
</body>
</html>
```

### Generated Game (game.js):
```javascript
// ASSETS object already loaded from assets.js

const app = new PIXI.Application({
    width: 800,
    height: 600
});
document.body.appendChild(app.view);

// Use assets directly
const car = PIXI.Sprite.from(ASSETS['car_black_1.png']);
car.position.set(100, 200);
app.stage.addChild(car);

const rock = PIXI.Sprite.from(ASSETS['rock1.png']);
rock.position.set(300, 400);
app.stage.addChild(rock);
```

## Performance

### Prompt Size Reduction
```
Before: 34,610 characters (with embedded base64)
After:   2,920 characters (instructions only)
Savings: 91.6% reduction!
```

### File Sizes (Racing Pack - 17 assets)
```
cache.json:  32KB   (in source pack, gitignored)
assets.js:   31KB   (in workspace, used by game)
```

### Processing Speed
```
First run:     Generate base64 + create files
Subsequent:    Load from cache (instant)
```

## Cache Management

The cache is automatically managed:

```python
# First run with new/changed images
Processing base64 assets for pack: Racing Pack
Generating base64 for car_black_1.png
Generating base64 for car_blue_2.png
Base64 cache updated: 17 new/updated

# Subsequent runs
Processing base64 assets for pack: Racing Pack
All 17 assets loaded from cache
```

Cache invalidation:
- ✅ Detects file changes via MD5 hash
- ✅ Regenerates only changed files
- ✅ Removes deleted files from cache
- ✅ Automatic - no manual intervention

## API

### Main Function

```python
def prepare_pack_for_workspace(
    pack_name: str,
    workspace_assets_dir: Path,
    source_assets_dir: Path = Path("assets")
) -> Optional[str]:
    """
    Prepare asset pack for workspace.
    
    Returns:
        Prompt context (WITHOUT base64 data)
    
    Side effects:
        Creates workspace_assets_dir/assets.js with base64 data
    """
```

### Usage

```python
from pathlib import Path
from src.asset_manager import prepare_pack_for_workspace

# Prepare pack
asset_context = prepare_pack_for_workspace(
    pack_name="Racing Pack",
    workspace_assets_dir=Path("games/session_123/assets")
)

# asset_context contains instructions (NOT base64 data)
# assets.js file created with base64 data
```

## Testing

```bash
# Test the system
python test_base64_assets.py

# Run integration tests
pytest tests/integration/test_asset_loading_examples.py -v
```

Expected output:
```
✅ All tests passed!
- Prompt does NOT contain base64 data ✓
- assets.js file created ✓
- assets.js contains base64 data ✓
- Cache working correctly ✓
```

## Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| Prompt size | 34KB | 3KB |
| Token efficiency | ❌ Wasteful | ✅ Efficient |
| Processing speed | Slower | Faster |
| Prompt cost | Higher | Lower |
| Asset loading | Base64 embedded | Base64 in file |
| Deployment | Single file possible | Single file (can inline assets.js) |

## Migration Notes

### For Existing Code
No changes needed! The system automatically:
1. Generates base64 cache
2. Creates assets.js file
3. Provides updated instructions

### For New Games
The agent will automatically generate code that:
1. Loads `assets/assets.js`
2. Uses `ASSETS` object
3. Works with base64 data

## Troubleshooting

### Prompt still too large?
Check that base64 data is NOT in the prompt:
```python
asset_context = prepare_pack_for_workspace(...)
assert "data:image/png;base64," not in asset_context
```

### assets.js not created?
Verify the function was called with correct path:
```python
assets_js = workspace_assets_dir / "assets.js"
assert assets_js.exists()
```

### Cache not updating?
Force regeneration by deleting cache:
```bash
rm "assets/Racing Pack/base64/cache.json"
```

## Summary

The updated approach keeps **base64 data in files** (assets.js) and **instructions in prompts**, resulting in:

- **91% smaller prompts**
- **Faster processing**
- **Lower costs**
- **Better separation of concerns**
- **Same great deployment benefits**

The agent loads `assets.js` and uses the `ASSETS` object - simple and efficient!

