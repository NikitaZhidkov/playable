"""
Unit tests for asset loading instructions provided to the agent.

These tests verify that the build system instructions:
1. Are clear and complete
2. Include valid TypeScript/JavaScript examples
3. Focus on import-based asset loading (not base64)

No Docker/Dagger required - these are pure unit tests.
"""
import pytest
import re
from src.asset_manager import format_asset_context_for_prompt


def test_prompt_format_basic():
    """Test that the formatting function works with minimal XML."""
    xml_content = """<pack name="TestPack">
  <asset name="test.png" width="64" height="64" description="Test asset"/>
</pack>"""
    
    result = format_asset_context_for_prompt(xml_content, "TestPack")
    
    assert isinstance(result, str)
    assert len(result) > 0
    assert "TestPack" in result


def test_prompt_contains_required_sections():
    """Test that all required instructional sections are present."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for build system instructions
    assert "## How to Use Assets" in prompt, \
        "Must have usage instructions heading"
    
    assert "import" in prompt.lower(), \
        "Must show import-based approach"
    
    assert "Build System" in prompt or "build system" in prompt, \
        "Must mention build system"


def test_import_examples_present():
    """Test that import examples are present."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for import example
    assert "import" in prompt.lower(), \
        "Must show import-based approach"
    
    # Verify it's in a code block
    assert "```typescript" in prompt or "```javascript" in prompt, \
        "Examples must be in code blocks"
    
    # Check that PIXI.Sprite.from is mentioned
    assert "PIXI.Sprite.from" in prompt, \
        "Must show PIXI.Sprite.from usage"


def test_no_base64_references():
    """Test that instructions don't mention base64 (outdated approach)."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Should NOT mention base64
    assert "base64" not in prompt.lower(), \
        "Should not mention base64 (outdated approach)"
    
    assert "data:image" not in prompt, \
        "Should not include data URIs (outdated approach)"


def test_relative_import_path_format():
    """Test that import paths use relative format."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Should show relative import paths
    assert "'./assets/" in prompt or '"./assets/' in prompt, \
        "Must show relative import paths with './assets/'"


def test_example_code_syntax_valid():
    """Test that example code uses valid TypeScript/JavaScript syntax patterns."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for modern syntax
    assert "import" in prompt.lower(), \
        "Examples should show import statements"
    
    # Check for proper method calls
    assert "PIXI.Sprite.from(" in prompt, \
        "Examples should show PIXI.Sprite.from() method calls"


def test_pixi_api_correct():
    """Test that PixiJS API usage is correct."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for correct PixiJS API calls
    assert "PIXI.Sprite.from(" in prompt, \
        "Must use PIXI.Sprite.from() for sprite creation"


def test_multiple_assets_listed():
    """Test that multiple assets are listed properly."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
  <asset name="rock.png" width="32" height="32" description="Rock obstacle"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check that both assets are listed
    assert "car.png" in prompt
    assert "rock.png" in prompt


def test_comments_in_examples():
    """Test that code examples include helpful comments."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for comment markers in code blocks
    assert "//" in prompt, \
        "Code examples should include explanatory comments"


def test_assets_available_mentioned():
    """Test that instructions mention assets directory."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check that it mentions assets directory
    assert "assets/" in prompt.lower(), \
        "Instructions should mention assets directory"


def test_asset_list_included():
    """Test that the actual assets in the pack are listed."""
    xml_content = """<pack name="TestPack">
  <asset name="car_black_1.png" width="64" height="64" description="Black racing car"/>
  <asset name="rock1.png" width="32" height="32" description="Stone obstacle"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check that asset names are included
    assert "car_black_1.png" in prompt, \
        "Asset list should include car_black_1.png"
    
    assert "rock1.png" in prompt, \
        "Asset list should include rock1.png"
    
    # Check that descriptions are included
    assert "Black racing car" in prompt or "racing car" in prompt.lower(), \
        "Asset descriptions should be included"


def test_build_system_mentioned():
    """Test that build system is mentioned."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Should mention build system
    assert "build system" in prompt.lower() or "webpack" in prompt.lower() or "vite" in prompt.lower(), \
        "Should mention build system (Webpack/Vite)"


def test_no_broken_formatting():
    """Test that there are no obvious formatting issues."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for proper markdown formatting
    assert "**" in prompt, \
        "Should use bold formatting for emphasis"
    
    # Check that code blocks are present
    assert "```" in prompt, \
        "Should have code block examples"

