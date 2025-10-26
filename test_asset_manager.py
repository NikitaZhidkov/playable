#!/usr/bin/env python3
"""
Simple test script for asset_manager module.
"""
from pathlib import Path
from src.asset_manager import (
    list_available_packs,
    get_or_create_pack_descriptions,
    format_asset_context_for_prompt
)

def test_asset_manager():
    """Test basic asset manager functionality."""
    print("=" * 60)
    print("Testing Asset Manager")
    print("=" * 60)
    print()
    
    # Test 1: List available packs
    print("Test 1: List available packs")
    packs = list_available_packs()
    print(f"Found {len(packs)} packs: {packs}")
    print()
    
    if not packs:
        print("⚠️  No packs found. Please ensure assets/ directory exists with pack subdirectories.")
        return
    
    # Test 2: Get/create descriptions for first pack
    pack_name = packs[0]
    print(f"Test 2: Get/create descriptions for '{pack_name}'")
    pack_path = Path("assets") / pack_name
    
    xml_content = get_or_create_pack_descriptions(pack_path, pack_name)
    print(f"Generated XML ({len(xml_content)} characters)")
    print()
    print("XML Content:")
    print("-" * 60)
    print(xml_content)
    print("-" * 60)
    print()
    
    # Test 3: Format for prompt
    print("Test 3: Format asset context for prompt")
    asset_context = format_asset_context_for_prompt(xml_content, pack_name)
    print("Asset Context:")
    print("-" * 60)
    print(asset_context)
    print("-" * 60)
    print()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    test_asset_manager()

