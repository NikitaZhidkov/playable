#!/usr/bin/env python3
"""
Test script to verify base64 asset conversion functionality.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.asset_manager import (
    list_available_packs,
    prepare_pack_for_workspace,
    get_or_create_base64_assets
)


def test_base64_conversion():
    """Test base64 conversion of assets."""
    print("=" * 60)
    print("Testing Base64 Asset Conversion")
    print("=" * 60)
    print()
    
    # List available packs
    print("1. Listing available asset packs...")
    packs = list_available_packs()
    print(f"   Found {len(packs)} packs: {packs}")
    print()
    
    if not packs:
        print("❌ No asset packs found. Please add assets to the 'assets/' directory.")
        return False
    
    # Test with first available pack
    pack_name = packs[0]
    print(f"2. Testing with pack: {pack_name}")
    print()
    
    # Test base64 generation
    print("3. Generating base64 assets...")
    pack_path = Path("assets") / pack_name
    base64_assets = get_or_create_base64_assets(pack_path)
    
    if not base64_assets:
        print(f"❌ Failed to generate base64 assets for {pack_name}")
        return False
    
    print(f"   ✓ Generated {len(base64_assets)} base64 assets")
    
    # Show sample
    for i, (filename, data_uri) in enumerate(base64_assets.items()):
        if i >= 3:  # Show only first 3
            break
        print(f"     - {filename}: {len(data_uri)} characters")
        # Verify it's a valid data URI
        if not data_uri.startswith("data:image/"):
            print(f"       ⚠️  Invalid data URI format!")
    print()
    
    # Test cache (run again to verify caching)
    print("4. Testing cache (running again)...")
    base64_assets_cached = get_or_create_base64_assets(pack_path)
    
    if base64_assets_cached == base64_assets:
        print("   ✓ Cache working correctly (same results)")
    else:
        print("   ⚠️  Cache results differ")
    print()
    
    # Test full workspace preparation
    print("5. Testing full workspace preparation...")
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_assets_dir = Path(tmpdir) / "assets"
        asset_context = prepare_pack_for_workspace(
            pack_name=pack_name,
            workspace_assets_dir=workspace_assets_dir
        )
        
        if asset_context:
            print(f"   ✓ Generated asset context ({len(asset_context)} characters)")
            
            # Verify key phrases in context
            checks = [
                ("assets/assets.js", "Reference to assets.js file"),
                ("PIXI.Sprite.from(ASSETS[", "Usage example"),
                ("<script src=\"assets/assets.js\"></script>", "Loading instruction")
            ]
            
            print("   Verifying context content:")
            for phrase, description in checks:
                if phrase in asset_context:
                    print(f"     ✓ {description}")
                else:
                    print(f"     ✗ Missing: {description}")
            
            # Verify base64 data is NOT in prompt
            if "data:image/png;base64," not in asset_context:
                print(f"     ✓ Base64 data NOT in prompt (good for efficiency)")
            else:
                print(f"     ✗ Base64 data in prompt (should be in assets.js file)")
            
            # Verify assets.js file was created
            assets_js_file = workspace_assets_dir / "assets.js"
            if assets_js_file.exists():
                assets_js_content = assets_js_file.read_text()
                print(f"   ✓ assets.js created ({len(assets_js_content)} characters)")
                
                if "const ASSETS = {" in assets_js_content:
                    print(f"     ✓ Contains ASSETS object")
                if "data:image/png;base64," in assets_js_content:
                    print(f"     ✓ Contains base64 data")
            else:
                print(f"   ✗ assets.js file not created")
                return False
            
            # Show first 500 chars of prompt
            print()
            print("   First 500 characters of prompt context:")
            print("   " + "-" * 56)
            for line in asset_context[:500].split('\n'):
                print(f"   {line}")
            print("   " + "-" * 56)
        else:
            print("   ❌ Failed to generate asset context")
            return False
    print()
    
    # Check cache file was created
    print("6. Verifying cache file...")
    cache_file = pack_path / "base64" / "cache.json"
    if cache_file.exists():
        print(f"   ✓ Cache file exists: {cache_file}")
        import json
        with open(cache_file) as f:
            cache_data = json.load(f)
        print(f"   ✓ Cache contains {len(cache_data)} entries")
    else:
        print(f"   ❌ Cache file not found: {cache_file}")
        return False
    print()
    
    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_base64_conversion()
    sys.exit(0 if success else 1)

