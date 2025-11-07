# Base64 Assets - Quick Start Guide

## What Changed?

Assets are now **embedded as base64** in your game code instead of being copied as separate files.

## Quick Test

```bash
# Test the base64 system
python test_base64_assets.py
```

## How It Works Now

### Before (File-based):
```
games/session_123/
├── index.html
└── assets/               ← Assets copied here
    ├── car.png
    └── rock.png
```

### After (Base64):
```
games/session_123/
└── index.html            ← Assets embedded in code
```

## Generated Code Example

The agent now generates code like this:

```javascript
// Assets embedded as base64
const ASSETS = {
    'car_black_1.png': 'data:image/png;base64,iVBORw0KGgo...',
    'rock1.png': 'data:image/png;base64,iVBORw0KGgo...',
    // ... all assets
};

// Use assets with PIXI.Sprite.from()
const car = PIXI.Sprite.from(ASSETS['car_black_1.png']);
app.stage.addChild(car);
```

## Benefits

✅ **Single-file deployment** - Everything in one HTML  
✅ **No CORS issues** - No external file loading  
✅ **Faster for users** - Assets load instantly  
✅ **Cleaner workspace** - No asset files to manage  
✅ **Smart caching** - Base64 cached between runs  

## Where is the Cache?

```
assets/
└── Racing Pack/
    ├── car_black_1.png      # Original files (keep these)
    └── base64/              # Auto-generated cache
        └── cache.json       # Base64 data (gitignored)
```

The cache:
- **Auto-generated** on first run
- **Auto-updated** when images change
- **Excluded from git** (see `.gitignore`)
- **About 32KB** for Racing Pack (17 assets)

## What to Do

### Nothing! 

The system works automatically:

1. Select an asset pack (same as before)
2. System converts to base64 (cached)
3. Agent gets base64 data in prompt
4. Agent generates code with embedded assets
5. Game works without asset files

### If You Want to Verify:

```bash
# Run tests
python test_base64_assets.py
pytest tests/integration/test_asset_loading_examples.py -v

# Check cache
ls -lh "assets/Racing Pack/base64/"
```

## Performance

### First Run:
```
Generating base64 for car_black_1.png
Generating base64 for car_blue_2.png
...
Base64 cache updated: 17 new/updated
```

### Subsequent Runs:
```
All 17 assets loaded from cache
```

**Result**: Instant on subsequent runs!

## Troubleshooting

### Cache not updating after changing an image?
```bash
# Delete cache to force regeneration
rm "assets/Racing Pack/base64/cache.json"
```

### Want to see what's in the cache?
```bash
# View cache contents
cat "assets/Racing Pack/base64/cache.json" | head -20
```

### Check if base64 is working:
```python
from pathlib import Path
from src.asset_manager import prepare_pack_for_workspace

context = prepare_pack_for_workspace(
    pack_name="Racing Pack",
    workspace_assets_dir=Path("dummy")
)

assert "data:image/png;base64," in context
print("✅ Base64 working!")
```

## More Info

- **Full docs**: See `BASE64_ASSETS.md`
- **Changes**: See `CHANGES_BASE64_ASSETS.md`
- **Tests**: Run `test_base64_assets.py`

## Questions?

**Q: Do I need to do anything different?**  
A: No! The agent handles everything automatically.

**Q: Can I still use the old approach?**  
A: The system now only supports base64. It's better for playable ads!

**Q: What about large assets?**  
A: Base64 adds ~33% size, but gzip compression helps. Optimize PNGs if needed.

**Q: Will old games still work?**  
A: Old games with file paths will need asset files. New games use base64.

## Summary

🎉 **Assets are now embedded as base64 for better playable ads!**

- No setup required
- Automatic caching
- Cleaner deployments
- Same workflow for you

Just select your asset pack and let the system handle the rest!

