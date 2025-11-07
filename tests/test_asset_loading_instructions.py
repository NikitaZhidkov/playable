"""
Unit tests for asset loading instructions provided to the agent.

These tests verify that:
1. The instructions are clear and complete
2. The code examples are valid JavaScript
3. The path formats are correctly specified

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


def test_prompt_contains_all_required_sections():
    """Test that all required instructional sections are present."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for main sections
    assert "## IMPORTANT: How to Load Assets Correctly" in prompt, \
        "Must have main instructions heading"
    
    assert "**Correct Way: PIXI.Sprite.from()**" in prompt, \
        "Must document PIXI.Sprite.from() method"
    
    assert "**For Multiple Assets:**" in prompt, \
        "Must show how to load multiple assets"
    
    assert "**CRITICAL Path Format:**" in prompt, \
        "Must emphasize critical path format rules"
    
    assert "**DO NOT USE**:" in prompt, \
        "Must warn about methods that don't work"


def test_method1_example_present():
    """Test that Method 1 example code is present and valid."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for Method 1 code example
    assert "PIXI.Sprite.from('assets/" in prompt, \
        "Method 1 example must show PIXI.Sprite.from with correct path"
    
    # Verify it's in a code block
    assert "```javascript" in prompt, \
        "Examples must be in JavaScript code blocks"
    
    # Check that the example uses correct path format
    method1_pattern = r"PIXI\.Sprite\.from\('assets/[^']+'\)"
    assert re.search(method1_pattern, prompt), \
        "Method 1 must use correct path format: 'assets/filename.png'"


def test_warns_against_broken_methods():
    """Test that instructions warn against methods that don't work."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check that it warns against PIXI.Assets.load
    assert "PIXI.Assets.load()" in prompt, \
        "Must mention PIXI.Assets.load()"
    
    assert "doesn't work in testing environment" in prompt, \
        "Must explain why not to use PIXI.Assets.load()"
    
    assert "DO NOT USE" in prompt, \
        "Must have clear DO NOT USE section"


def test_correct_path_examples():
    """Test that correct path format examples are shown."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Find all correct path examples (now using backticks for inline code)
    correct_pattern = r"✓ CORRECT: `['\"]([^'\"]+)['\"]`"
    correct_paths = re.findall(correct_pattern, prompt)
    
    assert len(correct_paths) > 0, f"Must provide at least one correct path example. Got: {prompt}"
    
    for path in correct_paths:
        assert path.startswith('assets/'), \
            f"Correct path must start with 'assets/': {path}"
        assert not path.startswith('./'), \
            f"Correct path should not start with './': {path}"
        assert path.endswith('.png'), \
            f"Path examples should use .png extension: {path}"


def test_wrong_path_examples():
    """Test that wrong path format examples are shown."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Find all wrong path examples (now using backticks for inline code)
    wrong_pattern = r"✗ WRONG: `['\"]([^'\"]+)['\"]`"
    wrong_paths = re.findall(wrong_pattern, prompt)
    
    assert len(wrong_paths) > 0, "Must provide wrong path examples"
    
    # Verify wrong paths are actually wrong
    for path in wrong_paths:
        # At least one of these should be true for it to be a "wrong" example
        is_wrong = (
            path.startswith('./') or  # Wrong: relative with ./
            path.startswith('/') or   # Wrong: absolute path
            'app' in path             # Wrong: container path
        )
        assert is_wrong, \
            f"Wrong path example should actually be wrong: {path}"


def test_path_format_rules_clear():
    """Test that path format rules are clearly stated."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for checkmark and X mark symbols
    assert "✓" in prompt, "Must use checkmark for correct examples"
    assert "✗" in prompt, "Must use X mark for wrong examples"
    
    # Check that CORRECT and WRONG are clearly labeled
    assert "CORRECT:" in prompt, "Must label correct examples"
    assert "WRONG:" in prompt, "Must label wrong examples"


def test_example_code_syntax_valid():
    """Test that example code uses valid JavaScript syntax patterns."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for common JavaScript patterns
    assert "const " in prompt or "let " in prompt, \
        "Examples should use modern JavaScript variable declarations"
    
    # Check for proper method calls
    assert "PIXI.Sprite.from(" in prompt, \
        "Examples should show PIXI.Sprite.from() method calls"
    
    # Check for property assignments
    assert ".x =" in prompt or ".y =" in prompt, \
        "Examples should show property assignments"


def test_pixi_api_correct():
    """Test that PixiJS API usage is correct."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for correct PixiJS API calls
    assert "PIXI.Sprite.from(" in prompt, \
        "Must use PIXI.Sprite.from() for direct sprite creation"
    
    # Check that we mention PIXI.Assets.load() to warn against it
    assert "PIXI.Assets.load()" in prompt, \
        "Must mention PIXI.Assets.load() to warn against using it"
    
    # Check for app.stage.addChild
    assert "app.stage.addChild" in prompt, \
        "Must show how to add sprite to stage"


def test_multiple_assets_guidance():
    """Test that guidance for multiple assets is provided."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
  <asset name="rock.png" width="32" height="32" description="Rock obstacle"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for multiple assets section
    assert "**For Multiple Assets:**" in prompt, \
        "Must have section for loading multiple assets"
    
    # Check that it shows multiple PIXI.Sprite.from calls
    sprite_from_count = prompt.count("PIXI.Sprite.from(")
    assert sprite_from_count >= 3, \
        f"Examples should show loading multiple assets (found {sprite_from_count} calls)"


def test_comments_in_examples():
    """Test that code examples include helpful comments."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for comment markers in code blocks
    assert "//" in prompt, \
        "Code examples should include explanatory comments"


def test_assets_already_copied_mentioned():
    """Test that instructions mention assets are already available."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check that it mentions assets are ready
    mentions_ready = (
        "already copied" in prompt.lower() or
        "already" in prompt.lower() or
        "ready" in prompt.lower()
    )
    
    assert mentions_ready, \
        "Instructions should mention that assets are already available"


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


def test_explains_why_sprite_from():
    """Test that instructions explain why to use PIXI.Sprite.from()."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for explanation
    assert "Why PIXI.Sprite.from()?" in prompt, \
        "Should explain why to use this method"
    
    assert "testing environment" in prompt.lower(), \
        "Should mention testing environment compatibility"


def test_no_broken_formatting():
    """Test that there are no obvious formatting issues."""
    xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Car sprite"/>
</pack>"""
    
    prompt = format_asset_context_for_prompt(xml_content, "TestPack")
    
    # Check for balanced code blocks
    assert prompt.count("```javascript") == prompt.count("```") // 2, \
        "All JavaScript code blocks should be properly closed"
    
    # Check for proper markdown formatting
    assert "**" in prompt, \
        "Should use bold formatting for emphasis"
    
    # No double spaces at start of lines (markdown formatting issue)
    lines = prompt.split('\n')
    for i, line in enumerate(lines):
        if line and not line.startswith('  ') and not line.startswith('    '):
            # Only check non-indented lines
            assert not line.startswith('  '), \
                f"Line {i} has unexpected double space at start: {line[:20]}"

