# Base64 Asset System

## Overview

The asset system now uses base64-encoded data URIs instead of copying physical files to the workspace. This approach provides several benefits for playable ads development:

- **Single-file deployment**: All assets embedded directly in the code
- **No CORS issues**: No external file loading required
- **Faster loading**: Assets are part of the HTML/JS bundle
- **Cleaner workspace**: No asset files copied to game directories
- **Better caching**: Base64 data cached in source pack directory

## How It Works

### 1. Asset Preparation

When you select an asset pack, the system:
1. Scans the pack directory for PNG files
2. Converts each image to a base64 data URI
3. Caches the base64 data in `assets/<pack_name>/base64/cache.json`
4. Includes the base64 data in the agent's prompt

### 2. Cache Management

The base64 cache automatically:
- **Detects changes**: Uses MD5 hashing to detect modified images
- **Updates on change**: Regenerates base64 only for changed files
- **Removes old entries**: Cleans up cache for deleted files
- **Persists across runs**: Avoids re-encoding unchanged images

### 3. Usage in Game Code

The agent receives instructions to use assets like this:

```javascript
// Assets object with base64 data URIs
const ASSETS = {
    'car_black_1.png': 'data:image/png;base64,iVBORw0KGgoAAAANS...',
    'rock1.png': 'data:image/png;base64,iVBORw0KGgoAAAANS...',
    // ... more assets
};

// Use with PIXI.Sprite.from()
const car = PIXI.Sprite.from(ASSETS['car_black_1.png']);
car.position.set(100, 200);
app.stage.addChild(car);
```

## File Structure

```
assets/
├── Racing Pack/
│   ├── car_black_1.png          # Original PNG files
│   ├── car_blue_2.png
│   ├── ...
│   ├── description.xml          # Asset metadata
│   └── base64/                  # Base64 cache (auto-generated)
│       └── cache.json           # Cached base64 data
```

**Note**: The `base64/` directories are automatically generated and excluded from git via `.gitignore`.

## Cache File Format

```json
{
  "car_black_1.png": {
    "hash": "a1b2c3d4e5f6...",
    "base64_data": "data:image/png;base64,iVBORw0KGgoAAAANS..."
  },
  "rock1.png": {
    "hash": "f6e5d4c3b2a1...",
    "base64_data": "data:image/png;base64,iVBORw0KGgoAAAANS..."
  }
}
```

## API Reference

### `get_or_create_base64_assets(pack_path: Path) -> Dict[str, str]`

Generates or retrieves cached base64-encoded versions of all PNG assets in a pack.

**Parameters:**
- `pack_path`: Path to the asset pack directory

**Returns:**
- Dictionary mapping filename to base64 data URI

**Example:**
```python
from pathlib import Path
from src.asset_manager import get_or_create_base64_assets

pack_path = Path("assets/Racing Pack")
base64_assets = get_or_create_base64_assets(pack_path)

print(f"Loaded {len(base64_assets)} assets")
for filename, data_uri in base64_assets.items():
    print(f"  {filename}: {len(data_uri)} characters")
```

### `prepare_pack_for_workspace(pack_name: str, workspace_assets_dir: Path) -> Optional[str]`

Prepares an asset pack for use by generating base64 data and formatting instructions for the agent.

**Parameters:**
- `pack_name`: Name of the asset pack
- `workspace_assets_dir`: Path to workspace assets directory (kept for API compatibility, not used)

**Returns:**
- Formatted asset context string for agent prompt, or None if failed

**Example:**
```python
from pathlib import Path
from src.asset_manager import prepare_pack_for_workspace

asset_context = prepare_pack_for_workspace(
    pack_name="Racing Pack",
    workspace_assets_dir=Path("games/session_123/assets")
)

if asset_context:
    print("Asset pack prepared successfully")
    # Use asset_context in agent prompt
```

## Benefits for Playable Ads

### 1. Single-File Distribution
All assets are embedded in the HTML file, making distribution simpler:
```html
<!DOCTYPE html>
<html>
<head>...</head>
<body>
    <script>
        const ASSETS = { /* base64 data */ };
        // Game code using ASSETS
    </script>
</body>
</html>
```

### 2. No Loading Delays
Assets are available immediately - no async loading required:
```javascript
// Works instantly - no await needed!
const sprite = PIXI.Sprite.from(ASSETS['car.png']);
app.stage.addChild(sprite);
```

### 3. No CORS Issues
Since everything is embedded, no cross-origin restrictions apply.

### 4. Smaller Total Size
When gzipped, base64-encoded assets are often similar in size to separate files, and you save HTTP overhead.

## Performance Considerations

### Base64 Size Impact
- Base64 encoding increases data size by ~33%
- Example: 10KB PNG → ~13KB base64
- However, gzip compression reduces this overhead significantly

### Cache Performance
First run (no cache):
```
Processing base64 assets for pack: Racing Pack
Generating base64 for car_black_1.png
Generating base64 for car_blue_2.png
...
Base64 cache updated: 17 new/updated, 0 removed, 0 cached
```

Subsequent runs (with cache):
```
Processing base64 assets for pack: Racing Pack
All 17 assets loaded from cache
```

## Testing

Run the base64 asset test:
```bash
python test_base64_assets.py
```

Run the integration test:
```bash
pytest tests/integration/test_asset_loading_examples.py::test_racing_pack_asset_loading -v
```

## Migration Notes

### Before (File-based)
```javascript
// Old approach - files copied to workspace
const car = PIXI.Sprite.from('assets/car_black_1.png');
```

### After (Base64)
```javascript
// New approach - base64 data URIs
const ASSETS = {
    'car_black_1.png': 'data:image/png;base64,...'
};
const car = PIXI.Sprite.from(ASSETS['car_black_1.png']);
```

## Troubleshooting

### Cache Not Updating
If you modify an image and the cache doesn't update:
1. Check file permissions on `assets/<pack>/base64/`
2. Delete `cache.json` to force regeneration
3. Verify the image file was actually modified (check timestamp)

### Base64 Too Large
If base64 data makes prompts too large:
1. Optimize PNG files before encoding (use tools like `pngcrush` or `optipng`)
2. Consider reducing image dimensions if appropriate
3. Use fewer assets per pack

### Missing Assets in Prompt
If assets don't appear in the agent's prompt:
1. Verify PNG files exist in `assets/<pack>/`
2. Check logs for conversion errors
3. Ensure `prepare_pack_for_workspace()` returns non-None

## Future Enhancements

Possible improvements:
- Support for other image formats (JPEG, WebP)
- Compression options for base64 data
- Asset spritesheet generation
- Progressive loading for large asset packs

