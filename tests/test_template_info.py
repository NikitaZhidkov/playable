"""Tests for template structure information generation."""

import pytest
from pathlib import Path
from src.main import get_template_structure_info


class TestTemplateStructureInfo:
    """Test template structure info generation."""
    
    def test_get_template_structure_info_returns_string(self):
        """Test that function returns a string."""
        result = get_template_structure_info()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_template_info_contains_file_structure(self):
        """Test that output contains file structure section."""
        result = get_template_structure_info()
        assert "## File Structure" in result
        assert "src/" in result
        assert "assets/" in result
        assert "package.json" in result
    
    def test_template_info_contains_all_file_contents(self):
        """Test that output includes all template file contents."""
        result = get_template_structure_info()
        
        # Should contain all file sections
        assert "### src/index.html" in result
        assert "### src/index.ts" in result
        assert "### src/index.css" in result
        assert "### src/Game.ts" in result
        assert "### package.json" in result
    
    def test_template_info_contains_actual_file_content(self):
        """Test that actual file content is included."""
        result = get_template_structure_info()
        
        # Should contain actual TypeScript/HTML content from files
        assert "import" in result
        assert "PIXI" in result or "pixi" in result
        assert "class Game" in result
        assert "<!DOCTYPE html>" in result
    
    def test_template_info_has_working_example_emphasis(self):
        """Test that output emphasizes this is a working example."""
        result = get_template_structure_info()
        
        assert "WORKING EXAMPLE" in result
        assert "working example" in result.lower()
        assert "modify" in result.lower() or "replace" in result.lower()
    
    def test_template_info_has_instructions(self):
        """Test that output contains clear instructions."""
        result = get_template_structure_info()
        
        assert "## What You Should Do:" in result
        assert "MODIFY src/Game.ts" in result
        assert "DON'T MODIFY" in result
    
    def test_template_info_has_important_notes(self):
        """Test that output contains important technical notes."""
        result = get_template_structure_info()
        
        assert "## Important Notes:" in result
        assert "PixiJS" in result
        assert "SDK" in result
        assert "Asset imports" in result.lower() or "import" in result
    
    def test_template_info_has_pixi_v8_reference(self):
        """Test that output mentions PixiJS v8."""
        result = get_template_structure_info()
        
        assert "PixiJS v8" in result or "PIXI v8" in result
    
    def test_template_info_warns_against_cdn(self):
        """Test that output warns against using CDN links."""
        result = get_template_structure_info()
        
        assert "CDN" in result
        assert "package.json" in result
    
    def test_template_files_actually_exist(self):
        """Test that all referenced template files actually exist."""
        template_path = Path("templates/playable-template-pixi")
        
        # These files must exist for the function to work
        assert (template_path / "src/Game.ts").exists()
        assert (template_path / "src/index.html").exists()
        assert (template_path / "src/index.ts").exists()
        assert (template_path / "src/index.css").exists()
        assert (template_path / "package.json").exists()
    
    def test_template_files_have_content(self):
        """Test that template files are not empty."""
        template_path = Path("templates/playable-template-pixi")
        
        game_ts = (template_path / "src/Game.ts").read_text(encoding='utf-8')
        assert len(game_ts) > 100
        assert "class Game" in game_ts
        
        index_html = (template_path / "src/index.html").read_text(encoding='utf-8')
        assert len(index_html) > 10
        assert "<!DOCTYPE" in index_html
        
        index_ts = (template_path / "src/index.ts").read_text(encoding='utf-8')
        assert len(index_ts) > 50
        assert "import" in index_ts
        
        package_json = (template_path / "package.json").read_text(encoding='utf-8')
        assert len(package_json) > 50
        assert "pixi.js" in package_json
    
    def test_output_is_well_formatted_markdown(self):
        """Test that output is properly formatted markdown."""
        result = get_template_structure_info()
        
        # Should have markdown headers
        assert result.count("##") >= 3  # Multiple sections
        
        # Should have code blocks
        assert "```typescript" in result
        assert "```html" in result
        assert "```json" in result
        assert "```css" in result
        
        # Code blocks should be properly closed
        typescript_blocks = result.count("```typescript")
        html_blocks = result.count("```html")
        json_blocks = result.count("```json")
        css_blocks = result.count("```css")
        
        total_opening_blocks = typescript_blocks + html_blocks + json_blocks + css_blocks
        # Each opening should have content and then be closed
        # We can check total ``` count should be at least 2x the specific ones
        assert result.count("```") >= total_opening_blocks * 2
    
    def test_game_ts_example_code_patterns(self):
        """Test that Game.ts content shows key patterns."""
        result = get_template_structure_info()
        
        # Should show key PixiJS patterns from the template
        assert "PIXI.Application" in result
        assert "PIXI.Assets.load" in result or "Assets.load" in result
        assert "resize" in result
        assert "pause" in result
        assert "resume" in result
    
    def test_function_runs_without_errors(self):
        """Test that function executes without raising exceptions."""
        # This should not raise any exception
        result = get_template_structure_info()
        
        # Basic sanity checks
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 1000  # Should be substantial content

