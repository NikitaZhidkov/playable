"""
Unit tests for asset_manager module.

Tests cover all core functionality:
- Asset pack discovery
- Image dimension detection
- XML description parsing and generation
- Asset context formatting for build systems
- Workspace preparation with file copying
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import xml.etree.ElementTree as ET
from src.asset_manager import (
    list_available_packs,
    get_image_dimensions,
    parse_existing_descriptions,
    generate_description_xml,
    format_asset_context_for_prompt,
    prepare_pack_for_workspace,
    list_available_sound_packs,
    parse_sound_descriptions,
    format_sound_context_for_prompt,
    prepare_sound_pack_for_workspace
)


class TestAssetPackDiscovery:
    """Test asset pack listing functionality."""
    
    def test_list_available_packs_empty_dir(self, tmp_path):
        """Test with empty assets directory."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        
        packs = list_available_packs(assets_dir)
        assert packs == []
    
    def test_list_available_packs_with_packs(self, tmp_path):
        """Test with multiple pack directories."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        
        # Create pack directories
        (assets_dir / "Pack1").mkdir()
        (assets_dir / "Pack2").mkdir()
        (assets_dir / "Pack3").mkdir()
        (assets_dir / ".hidden").mkdir()  # Should be ignored
        (assets_dir / "file.txt").write_text("not a directory")  # Should be ignored
        
        packs = list_available_packs(assets_dir)
        
        assert len(packs) == 3
        assert "Pack1" in packs
        assert "Pack2" in packs
        assert "Pack3" in packs
        assert ".hidden" not in packs
    
    def test_list_available_packs_nonexistent_dir(self, tmp_path):
        """Test with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        packs = list_available_packs(nonexistent)
        assert packs == []
    
    def test_list_available_packs_sorted(self, tmp_path):
        """Test that packs are returned in sorted order."""
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        
        (assets_dir / "Zebra").mkdir()
        (assets_dir / "Apple").mkdir()
        (assets_dir / "Mango").mkdir()
        
        packs = list_available_packs(assets_dir)
        assert packs == ["Apple", "Mango", "Zebra"]


class TestImageDimensions:
    """Test image dimension detection."""
    
    def test_get_image_dimensions(self, tmp_path):
        """Test getting dimensions of a real PNG image."""
        # Create a minimal 1x1 red pixel PNG
        png_data = bytes([
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
        
        image_path = tmp_path / "test.png"
        image_path.write_bytes(png_data)
        
        width, height = get_image_dimensions(image_path)
        assert width == 1
        assert height == 1


class TestDescriptionParsing:
    """Test XML description parsing."""
    
    def test_parse_existing_descriptions(self, tmp_path):
        """Test parsing valid description.xml file."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
  <asset name="rock.png" width="32" height="32" description="Test rock"/>
</pack>"""
        
        xml_path = tmp_path / "description.xml"
        xml_path.write_text(xml_content)
        
        descriptions = parse_existing_descriptions(xml_path)
        
        assert len(descriptions) == 2
        assert "car.png" in descriptions
        assert descriptions["car.png"]["width"] == "64"
        assert descriptions["car.png"]["height"] == "64"
        assert descriptions["car.png"]["description"] == "Test car"
        assert "rock.png" in descriptions
    
    def test_parse_descriptions_with_custom_attributes(self, tmp_path):
        """Test that custom attributes are preserved."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car" human_description="A nice car" category="vehicle"/>
</pack>"""
        
        xml_path = tmp_path / "description.xml"
        xml_path.write_text(xml_content)
        
        descriptions = parse_existing_descriptions(xml_path)
        
        assert descriptions["car.png"]["human_description"] == "A nice car"
        assert descriptions["car.png"]["category"] == "vehicle"
    
    def test_parse_descriptions_missing_fields(self, tmp_path):
        """Test parsing XML with missing optional fields."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png"/>
</pack>"""
        
        xml_path = tmp_path / "description.xml"
        xml_path.write_text(xml_content)
        
        descriptions = parse_existing_descriptions(xml_path)
        
        assert descriptions["car.png"]["width"] == "0"
        assert descriptions["car.png"]["height"] == "0"
        assert descriptions["car.png"]["description"] == ""


class TestDescriptionGeneration:
    """Test XML description generation."""
    
    def test_generate_description_xml(self):
        """Test generating XML from descriptions dictionary."""
        descriptions = {
            "car.png": {"width": "64", "height": "64", "description": "Test car"},
            "rock.png": {"width": "32", "height": "32", "description": "Test rock"}
        }
        
        xml_content = generate_description_xml(descriptions, "TestPack")
        
        assert "<pack name=\"TestPack\">" in xml_content
        assert "car.png" in xml_content
        assert "rock.png" in xml_content
        assert "Test car" in xml_content
        
        # Verify it's valid XML
        root = ET.fromstring(xml_content)
        assert root.tag == "pack"
        assert root.get("name") == "TestPack"
        assert len(root.findall("asset")) == 2
    
    def test_generate_xml_with_custom_attributes(self):
        """Test that custom attributes are included in generated XML."""
        descriptions = {
            "car.png": {
                "width": "64", 
                "height": "64", 
                "description": "Test car",
                "custom_field": "custom_value"
            }
        }
        
        xml_content = generate_description_xml(descriptions, "TestPack")
        
        assert "custom_field=\"custom_value\"" in xml_content
    
    def test_generate_xml_sorted_assets(self):
        """Test that assets are generated in sorted order."""
        descriptions = {
            "zebra.png": {"width": "10", "height": "10", "description": "Z"},
            "apple.png": {"width": "10", "height": "10", "description": "A"},
            "mango.png": {"width": "10", "height": "10", "description": "M"}
        }
        
        xml_content = generate_description_xml(descriptions, "TestPack")
        
        # Check order in XML
        apple_pos = xml_content.index("apple.png")
        mango_pos = xml_content.index("mango.png")
        zebra_pos = xml_content.index("zebra.png")
        
        assert apple_pos < mango_pos < zebra_pos


class TestAssetContextFormatting:
    """Test formatting asset context for LLM prompts."""
    
    def test_format_asset_context_basic(self):
        """Test basic context formatting."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
</pack>"""
        
        context = format_asset_context_for_prompt(xml_content, "TestPack")
        
        assert "TestPack" in context
        assert "car.png" in context
        assert "64x64" in context
        assert "Test car" in context
    
    def test_format_includes_build_system_instructions(self):
        """Test that context includes build system usage instructions."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
</pack>"""
        
        context = format_asset_context_for_prompt(xml_content, "TestPack")
        
        # Should mention build system approach
        assert "import" in context.lower()
        assert "assets/" in context
        assert "PIXI.Sprite.from" in context
        
        # Should NOT mention base64
        assert "base64" not in context.lower()
        assert "data:image" not in context
    
    def test_format_includes_typescript_examples(self):
        """Test that TypeScript/JavaScript examples are included."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
</pack>"""
        
        context = format_asset_context_for_prompt(xml_content, "TestPack")
        
        assert "```typescript" in context or "```javascript" in context
        assert "import" in context
        assert "./assets/" in context
    
    def test_format_preserves_custom_attributes(self):
        """Test that custom attributes are shown in context."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car" category="vehicle"/>
</pack>"""
        
        context = format_asset_context_for_prompt(xml_content, "TestPack")
        
        assert "category: vehicle" in context
    
    def test_format_multiple_assets(self):
        """Test formatting with multiple assets."""
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
  <asset name="rock.png" width="32" height="32" description="Test rock"/>
  <asset name="road.png" width="128" height="128" description="Test road"/>
</pack>"""
        
        context = format_asset_context_for_prompt(xml_content, "TestPack")
        
        assert "car.png" in context
        assert "rock.png" in context
        assert "road.png" in context


class TestWorkspacePreparation:
    """Test workspace preparation with file copying."""
    
    def test_prepare_pack_copies_image_files(self, tmp_path):
        """Test that image files are copied to workspace."""
        # Create source pack
        source_assets = tmp_path / "source_assets"
        pack_dir = source_assets / "TestPack"
        pack_dir.mkdir(parents=True)
        
        # Create test images
        (pack_dir / "car.png").write_text("fake png")
        (pack_dir / "rock.png").write_text("fake png")
        
        # Create description.xml
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
  <asset name="rock.png" width="32" height="32" description="Test rock"/>
</pack>"""
        (pack_dir / "description.xml").write_text(xml_content)
        
        # Prepare workspace
        workspace_dir = tmp_path / "workspace_assets"
        context = prepare_pack_for_workspace(
            pack_name="TestPack",
            workspace_assets_dir=workspace_dir,
            source_assets_dir=source_assets
        )
        
        # Verify files were copied
        assert (workspace_dir / "car.png").exists()
        assert (workspace_dir / "rock.png").exists()
        
        # Verify context was returned
        assert context is not None
        assert "car.png" in context
        assert "rock.png" in context
    
    def test_prepare_pack_returns_formatted_context(self, tmp_path):
        """Test that prepare_pack returns properly formatted context."""
        # Create source pack
        source_assets = tmp_path / "source_assets"
        pack_dir = source_assets / "TestPack"
        pack_dir.mkdir(parents=True)
        
        (pack_dir / "car.png").write_text("fake png")
        
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
</pack>"""
        (pack_dir / "description.xml").write_text(xml_content)
        
        workspace_dir = tmp_path / "workspace_assets"
        context = prepare_pack_for_workspace(
            pack_name="TestPack",
            workspace_assets_dir=workspace_dir,
            source_assets_dir=source_assets
        )
        
        # Context should be build-system focused
        assert "import" in context.lower()
        assert "TestPack" in context
        assert "car.png" in context
    
    def test_prepare_pack_no_assets(self, tmp_path):
        """Test handling when pack has no assets."""
        source_assets = tmp_path / "source_assets"
        pack_dir = source_assets / "TestPack"
        pack_dir.mkdir(parents=True)
        
        workspace_dir = tmp_path / "workspace_assets"
        context = prepare_pack_for_workspace(
            pack_name="TestPack",
            workspace_assets_dir=workspace_dir,
            source_assets_dir=source_assets
        )
        
        assert context is None
    
    def test_prepare_pack_nonexistent_pack(self, tmp_path):
        """Test handling when pack doesn't exist."""
        source_assets = tmp_path / "source_assets"
        source_assets.mkdir()
        
        workspace_dir = tmp_path / "workspace_assets"
        context = prepare_pack_for_workspace(
            pack_name="NonexistentPack",
            workspace_assets_dir=workspace_dir,
            source_assets_dir=source_assets
        )
        
        assert context is None
    
    def test_prepare_pack_creates_workspace_dir(self, tmp_path):
        """Test that workspace directory is created if it doesn't exist."""
        source_assets = tmp_path / "source_assets"
        pack_dir = source_assets / "TestPack"
        pack_dir.mkdir(parents=True)
        
        (pack_dir / "car.png").write_text("fake png")
        xml_content = """<pack name="TestPack">
  <asset name="car.png" width="64" height="64" description="Test car"/>
</pack>"""
        (pack_dir / "description.xml").write_text(xml_content)
        
        workspace_dir = tmp_path / "workspace_assets"  # Doesn't exist yet
        
        prepare_pack_for_workspace(
            pack_name="TestPack",
            workspace_assets_dir=workspace_dir,
            source_assets_dir=source_assets
        )
        
        assert workspace_dir.exists()
        assert workspace_dir.is_dir()


class TestSoundPacks:
    """Test sound pack functionality."""
    
    def test_list_available_sound_packs(self, tmp_path):
        """Test listing sound packs."""
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir()
        
        (sounds_dir / "Pack1").mkdir()
        (sounds_dir / "Pack2").mkdir()
        
        packs = list_available_sound_packs(sounds_dir)
        
        assert len(packs) == 2
        assert "Pack1" in packs
        assert "Pack2" in packs
    
    def test_parse_sound_descriptions(self, tmp_path):
        """Test parsing sound description XML."""
        xml_content = """<pack name="SoundPack">
  <sound name="music.mp3" type="music" description="Background music"/>
  <sound name="jump.wav" type="sfx" description="Jump sound effect"/>
</pack>"""
        
        xml_path = tmp_path / "description.xml"
        xml_path.write_text(xml_content)
        
        descriptions = parse_sound_descriptions(xml_path)
        
        assert len(descriptions) == 2
        assert "music.mp3" in descriptions
        assert descriptions["music.mp3"]["type"] == "music"
        assert descriptions["music.mp3"]["description"] == "Background music"
    
    def test_format_sound_context(self):
        """Test formatting sound context for prompt."""
        xml_content = """<pack name="SoundPack">
  <sound name="music.mp3" type="music" description="Background music"/>
</pack>"""
        
        context = format_sound_context_for_prompt(xml_content, "SoundPack")
        
        assert "SoundPack" in context
        assert "music.mp3" in context
        assert "Background music" in context
        assert "Audio" in context or "sound" in context.lower()
    
    def test_prepare_sound_pack_copies_files(self, tmp_path):
        """Test that sound files are copied to workspace."""
        # Create source sound pack
        source_sounds = tmp_path / "source_sounds"
        pack_dir = source_sounds / "TestSoundPack"
        pack_dir.mkdir(parents=True)
        
        # Create test sound files
        (pack_dir / "music.mp3").write_text("fake mp3")
        (pack_dir / "jump.wav").write_text("fake wav")
        
        # Create description.xml
        xml_content = """<pack name="TestSoundPack">
  <sound name="music.mp3" type="music" description="Background music"/>
  <sound name="jump.wav" type="sfx" description="Jump sound"/>
</pack>"""
        (pack_dir / "description.xml").write_text(xml_content)
        
        # Prepare workspace
        workspace_dir = tmp_path / "workspace_sounds"
        context = prepare_sound_pack_for_workspace(
            pack_name="TestSoundPack",
            workspace_sounds_dir=workspace_dir,
            source_sounds_dir=source_sounds
        )
        
        # Verify files were copied
        assert (workspace_dir / "music.mp3").exists()
        assert (workspace_dir / "jump.wav").exists()
        
        # Verify context was returned
        assert context is not None
        assert "music.mp3" in context
        assert "jump.wav" in context


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_xml_content(self):
        """Test handling empty XML."""
        xml_content = """<pack name="EmptyPack">
</pack>"""
        
        context = format_asset_context_for_prompt(xml_content, "EmptyPack")
        
        assert "EmptyPack" in context
        # Should still provide instructions even with no assets
        assert len(context) > 0
    
    def test_special_characters_in_descriptions(self):
        """Test handling special characters in descriptions."""
        descriptions = {
            "test.png": {
                "width": "64",
                "height": "64",
                "description": "Test with 'quotes' and \"double quotes\""
            }
        }
        
        xml_content = generate_description_xml(descriptions, "TestPack")
        
        # Should be valid XML
        root = ET.fromstring(xml_content)
        assert root.tag == "pack"

