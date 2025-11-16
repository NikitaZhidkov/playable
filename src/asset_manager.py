"""
Asset pack management for game development.
Handles asset discovery, file copying for build systems, and VLM-powered description management.
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PIL import Image

logger = logging.getLogger(__name__)


def list_available_packs(assets_dir: Path = Path("assets")) -> List[str]:
    """
    Scan assets directory for available asset packs.
    
    Args:
        assets_dir: Path to assets directory
    
    Returns:
        List of pack names (subdirectory names)
    """
    if not assets_dir.exists():
        logger.warning(f"Assets directory not found: {assets_dir}")
        return []
    
    packs = []
    for item in assets_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            packs.append(item.name)
    
    logger.info(f"Found {len(packs)} asset packs: {packs}")
    return sorted(packs)


def get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """
    Get width and height of an image file.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tuple of (width, height)
    """
    with Image.open(image_path) as img:
        return img.size


def parse_existing_descriptions(xml_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse existing description.xml file.
    Preserves ALL attributes including custom ones.
    
    Args:
        xml_path: Path to description.xml file
    
    Returns:
        Dictionary mapping filename to all attributes (width, height, description, and any custom attributes)
    """
    descriptions = {}
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    for asset in root.findall('asset'):
        name = asset.get('name', '')
        if name:
            # Extract ALL attributes, not just the standard ones
            descriptions[name] = dict(asset.attrib)
            # Remove 'name' from the dict since it's the key
            descriptions[name].pop('name', None)
            
            # Ensure required attributes have defaults if missing
            descriptions[name].setdefault('width', '0')
            descriptions[name].setdefault('height', '0')
            descriptions[name].setdefault('description', '')
    
    logger.info(f"Parsed {len(descriptions)} existing descriptions from {xml_path}")
    return descriptions




def describe_image_with_vlm(image_path: Path, pack_name: str) -> str:
    """
    Use VLM to generate a description for an asset image.
    
    Args:
        image_path: Path to the image file
        pack_name: Name of the asset pack (for context)
    
    Returns:
        Description string
    """

    from src.vlm import VLMClient
    
    vlm_client = VLMClient()
    
    # Create prompt for asset description
    prompt = f"""Describe this game asset from the "{pack_name}" pack. 
Be concise and focus on:
- Visual appearance and colors
- What it represents (character, object, terrain, etc.)
- Any notable features or details

Keep description under 100 characters. This will be used by a game developer to understand what assets are available.

Example good descriptions:
- "Black racing car viewed from above, compact sports car design"
- "Gray asphalt road tile texture with lane markings"
- "Small brown rock obstacle for terrain decoration"
"""
    
    # Load image
    image = Image.open(image_path)
    
    # Call VLM
    response = vlm_client.model.generate_content([prompt, image])
    description = response.text.strip()
    
    # Clean up description (remove quotes, newlines)
    description = description.replace('\n', ' ').replace('"', "'").strip()
    
    logger.info(f"Generated VLM description for {image_path.name}: {description[:60]}...")
    return description
    



def generate_description_xml(
    descriptions: Dict[str, Dict[str, str]], 
    pack_name: str
) -> str:
    """
    Generate XML string from descriptions dictionary.
    Preserves ALL attributes including custom ones.
    
    Args:
        descriptions: Dictionary mapping filename to all attributes (width, height, description, and any custom attributes)
        pack_name: Name of the asset pack
    
    Returns:
        Formatted XML string
    """
    # Create root element
    root = ET.Element('pack', attrib={'name': pack_name})
    
    # Add assets in sorted order
    for filename in sorted(descriptions.keys()):
        info = descriptions[filename]
        
        # Build attributes dict with 'name' first, then all others
        attribs = {'name': filename}
        
        # Add standard attributes in a consistent order
        for key in ['width', 'height', 'description']:
            if key in info:
                attribs[key] = str(info[key])
        
        # Add any custom attributes (sorted for consistency)
        for key in sorted(info.keys()):
            if key not in ['width', 'height', 'description']:
                attribs[key] = str(info[key])
        
        ET.SubElement(root, 'asset', attrib=attribs)
    
    # Pretty print XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Remove XML declaration and empty lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    if lines and lines[0].startswith('<?xml'):
        lines = lines[1:]
    
    return '\n'.join(lines)


def get_or_create_pack_descriptions(
    pack_path: Path,
    pack_name: str,
    force_regenerate: bool = False
) -> str:
    """
    Get or create description.xml for an asset pack.
    Validates existing descriptions and generates missing ones using VLM.
    
    Args:
        pack_path: Path to the pack directory
        pack_name: Name of the pack
        force_regenerate: If True, regenerate all descriptions
    
    Returns:
        XML content as string
    """
    logger.info(f"Processing asset pack: {pack_name} at {pack_path}")
    
    xml_path = pack_path / "description.xml"
    
    # Find all PNG files in pack
    png_files = sorted(pack_path.glob("*.png"))
    logger.info(f"Found {len(png_files)} PNG files in pack")
    
    if not png_files:
        logger.warning(f"No PNG files found in pack {pack_name}")
        return generate_description_xml({}, pack_name)
    
    # Parse existing descriptions if available
    existing_descriptions = {}
    if xml_path.exists() and not force_regenerate:
        existing_descriptions = parse_existing_descriptions(xml_path)
        logger.info(f"Loaded {len(existing_descriptions)} existing descriptions")
    
    # Build descriptions dictionary
    descriptions = {}
    missing_count = 0
    
    for png_file in png_files:
        filename = png_file.name
        width, height = get_image_dimensions(png_file)
        
        # Check if we have existing description
        if filename in existing_descriptions:
            # Preserve ALL existing attributes (including custom ones)
            descriptions[filename] = existing_descriptions[filename].copy()
            # Update dimensions if they changed
            descriptions[filename]['width'] = str(width)
            descriptions[filename]['height'] = str(height)
            logger.debug(f"Using existing description for {filename} (preserving custom attributes)")
        else:
            # Generate new description with VLM
            logger.info(f"Generating new description for {filename}")
            description = describe_image_with_vlm(png_file, pack_name)
            descriptions[filename] = {
                'width': str(width),
                'height': str(height),
                'description': description
            }
            missing_count += 1
    
    # Remove descriptions for files that no longer exist
    removed_count = len(existing_descriptions) - len([f for f in existing_descriptions if f in descriptions])
    if removed_count > 0:
        logger.info(f"Removed {removed_count} descriptions for deleted files")
    
    # Generate XML
    xml_content = generate_description_xml(descriptions, pack_name)
    
    # Save XML to pack directory
    xml_path.write_text(xml_content, encoding='utf-8')
    logger.info(f"Saved description.xml to {xml_path}")
    if missing_count > 0:
        logger.info(f"Generated {missing_count} new descriptions using VLM")
    
    return xml_content


def format_asset_context_for_prompt(
    xml_content: str, 
    pack_name: str
) -> str:
    """
    Format asset pack information for inclusion in agent prompt.
    Provides asset names and descriptions for use with build systems (Webpack/Vite).
    
    Args:
        xml_content: XML content with asset descriptions
        pack_name: Name of the pack
    
    Returns:
        Formatted text for prompt
    """
    # Parse XML to extract asset info
    root = ET.fromstring(xml_content)
    
    lines = [
        f"# Available Asset Pack: {pack_name}",
        "",
        "The following image assets are available in the 'assets/' directory:",
        ""
    ]
    
    # List assets with descriptions (including ALL custom attributes)
    for asset in root.findall('asset'):
        name = asset.get('name', '')
        width = asset.get('width', '0')
        height = asset.get('height', '0')
        description = asset.get('description', '')
        
        # Start with basic info
        line_parts = [f"- **{name}** ({width}x{height}px)"]
        
        # Add description if available
        if description:
            line_parts.append(f": {description}")
        
        # Add ALL other custom attributes from XML
        custom_attrs = []
        for attr_name, attr_value in sorted(asset.attrib.items()):
            if attr_name not in ['name', 'width', 'height', 'description']:
                custom_attrs.append(f"{attr_name}: {attr_value}")
        
        if custom_attrs:
            if description:
                line_parts.append(" | ")
            else:
                line_parts.append(": ")
            line_parts.append(", ".join(custom_attrs))
        
        lines.append("".join(line_parts))
    
    lines.extend([
        "",
        "## How to Use Assets",
        "",
        "All assets are located in the `assets/` directory and can be imported directly:",
        "",
        "### TypeScript/JavaScript with Build System:",
        "",
        "```typescript",
        "// Import assets directly - the build system will handle them",
        "import carImage from './assets/car_black_1.png';",
        "import rockImage from './assets/rock1.png';",
        "",
        "// Use with PixiJS",
        "const carSprite = PIXI.Sprite.from(carImage);",
        "const rockSprite = PIXI.Sprite.from(rockImage);",
        "```",
        "",
        "### File Paths in Code:",
        "",
        "```typescript",
        "// The build system will resolve these paths correctly",
        "PIXI.Assets.add('car', './assets/car_black_1.png');",
        "PIXI.Assets.add('rock', './assets/rock1.png');",
        "",
        "await PIXI.Assets.load(['car', 'rock']);",
        "",
        "const carSprite = PIXI.Sprite.from('car');",
        "```",
        "",
        "### Important Notes:",
        "- All asset files are physically present in the `assets/` directory",
        "- Use relative imports: `'./assets/filename.png'`",
        "- The build system (Webpack/Vite) will optimize and bundle assets automatically",
        "- No need for base64 encoding - use direct file references",
        ""
    ])
    
    return '\n'.join(lines)


def prepare_pack_for_workspace(
    pack_name: str,
    workspace_assets_dir: Path,
    source_assets_dir: Path = Path("assets"),
    source_sounds_dir: Path = Path("Sounds")
) -> Optional[str]:
    """
    Copy asset pack files to workspace for build system usage.
    Handles both visual assets (from assets/) and audio (from Sounds/).
    
    Args:
        pack_name: Name of the pack to prepare
        workspace_assets_dir: Path to workspace assets directory
        source_assets_dir: Path to source assets directory (for sprites)
        source_sounds_dir: Path to source sounds directory (for audio)
    
    Returns:
        Formatted asset context with descriptions for LLM prompt, or None if no assets found
    """
    logger.info(f"Preparing asset pack '{pack_name}' for workspace")
    
    # Create workspace assets directory
    workspace_assets_dir.mkdir(parents=True, exist_ok=True)
    
    asset_context_parts = []
    
    # Handle sprite assets from assets/PackName/
    sprite_pack_path = source_assets_dir / pack_name
    if sprite_pack_path.exists():
        sprite_files = []
        for file in sprite_pack_path.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                shutil.copy2(file, workspace_assets_dir / file.name)
                sprite_files.append(file.name)
                logger.info(f"Copied image asset: {file.name}")
        
        # Get sprite descriptions and format for prompt
        sprite_desc_xml_path = sprite_pack_path / "description.xml"
        if sprite_desc_xml_path.exists() and sprite_files:
            sprite_xml_content = sprite_desc_xml_path.read_text(encoding='utf-8')
            sprite_context = format_asset_context_for_prompt(sprite_xml_content, pack_name)
            asset_context_parts.append(sprite_context)
            logger.info(f"Prepared {len(sprite_files)} image assets with descriptions")
    
    # Handle sound assets from Sounds/PackName/
    sound_pack_path = source_sounds_dir / pack_name
    if sound_pack_path.exists():
        sound_files = []
        for file in sound_pack_path.iterdir():
            if file.is_file() and file.suffix.lower() in ['.mp3', '.wav', '.ogg']:
                shutil.copy2(file, workspace_assets_dir / file.name)
                sound_files.append(file.name)
                logger.info(f"Copied audio asset: {file.name}")
        
        # Get sound descriptions and format for prompt
        sound_desc_xml_path = sound_pack_path / "description.xml"
        if sound_desc_xml_path.exists() and sound_files:
            sound_xml_content = sound_desc_xml_path.read_text(encoding='utf-8')
            sound_context = format_sound_context_for_prompt(sound_xml_content, pack_name)
            asset_context_parts.append(sound_context)
            logger.info(f"Prepared {len(sound_files)} audio assets with descriptions")
    
    if not asset_context_parts:
        logger.warning(f"No assets found for pack: {pack_name}")
        return None
    
    # Combine all asset contexts
    return "\n\n".join(asset_context_parts)


def list_available_sound_packs(sounds_dir: Path = Path("Sounds")) -> List[str]:
    """
    Scan sounds directory for available sound packs.
    
    Args:
        sounds_dir: Path to sounds directory
    
    Returns:
        List of pack names (subdirectory names)
    """
    if not sounds_dir.exists():
        logger.warning(f"Sounds directory not found: {sounds_dir}")
        return []
    
    packs = []
    for item in sounds_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            packs.append(item.name)
    
    logger.info(f"Found {len(packs)} sound packs: {packs}")
    return sorted(packs)


def parse_sound_descriptions(xml_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse sound description.xml file.
    
    Args:
        xml_path: Path to description.xml file
    
    Returns:
        Dictionary mapping filename to all attributes (name, description, type, duration, etc.)
    """
    descriptions = {}
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    for sound in root.findall('sound'):
        name = sound.get('name', '')
        if name:
            descriptions[name] = dict(sound.attrib)
            descriptions[name].pop('name', None)
            
            descriptions[name].setdefault('description', '')
            descriptions[name].setdefault('type', 'unknown')
    
    logger.info(f"Parsed {len(descriptions)} sound descriptions from {xml_path}")
    return descriptions


def format_sound_context_for_prompt(xml_content: str, pack_name: str) -> str:
    """
    Format sound pack information for inclusion in agent prompt.
    
    Args:
        xml_content: XML content with sound descriptions
        pack_name: Name of the pack
    
    Returns:
        Formatted text for prompt
    """
    root = ET.fromstring(xml_content)
    
    lines = [
        f"# Available Sound Pack: {pack_name}",
        "",
        "The following sounds/music are available in the 'sounds/' directory:",
        ""
    ]
    
    for sound in root.findall('sound'):
        name = sound.get('name', '')
        description = sound.get('description', '')
        sound_type = sound.get('type', 'unknown')
        
        line_parts = [f"- **{name}** (Type: {sound_type})"]
        
        if description:
            line_parts.append(f": {description}")
        
        custom_attrs = []
        for attr_name, attr_value in sorted(sound.attrib.items()):
            if attr_name not in ['name', 'description', 'type']:
                custom_attrs.append(f"{attr_name}: {attr_value}")
        
        if custom_attrs:
            if description:
                line_parts.append(" | ")
            else:
                line_parts.append(": ")
            line_parts.append(", ".join(custom_attrs))
        
        lines.append("".join(line_parts))
    
    lines.extend([
        "",
        "## How to Use Sounds",
        "",
        "Load sound files from the 'sounds/' directory:",
        "",
        "```javascript",
        "// Background music",
        "const backgroundMusic = new Audio('sounds/background.mp3');",
        "backgroundMusic.loop = true;",
        "backgroundMusic.volume = 0.5;",
        "",
        "// Start music after first user interaction",
        "let musicStarted = false;",
        "app.view.addEventListener('pointerdown', () => {",
        "    if (!musicStarted) {",
        "        backgroundMusic.play();",
        "        musicStarted = true;",
        "    }",
        "}, { once: true });",
        "```",
        "",
        "Remember: Browser autoplay policies require user interaction before playing audio!",
        ""
    ])
    
    return '\n'.join(lines)


def prepare_sound_pack_for_workspace(
    pack_name: str,
    workspace_sounds_dir: Path,
    source_sounds_dir: Path = Path("Sounds")
) -> Optional[str]:
    """
    Prepare a sound pack for use in workspace.
    Copies sound files and returns formatted context for prompt.
    
    Args:
        pack_name: Name of the sound pack to prepare
        workspace_sounds_dir: Path to workspace sounds directory
        source_sounds_dir: Path to source sounds directory
    
    Returns:
        Formatted sound context for prompt, or None if failed
    """
    pack_path = source_sounds_dir / pack_name
    
    if not pack_path.exists():
        logger.warning(f"Sound pack directory not found: {pack_path}")
        return None
    
    logger.info(f"Preparing sound pack '{pack_name}'")
    
    xml_path = pack_path / "description.xml"
    if not xml_path.exists():
        logger.warning(f"No description.xml found for sound pack {pack_name}")
        return None
    
    xml_content = xml_path.read_text(encoding='utf-8')
    
    workspace_sounds_dir.mkdir(parents=True, exist_ok=True)
    
    sound_files = list(pack_path.glob("*.mp3")) + list(pack_path.glob("*.wav")) + list(pack_path.glob("*.ogg"))
    
    if not sound_files:
        logger.warning(f"No sound files found in pack {pack_name}")
        return None
    
    for sound_file in sound_files:
        dest_path = workspace_sounds_dir / sound_file.name
        shutil.copy2(sound_file, dest_path)
        logger.info(f"Copied sound file: {sound_file.name}")
    
    logger.info(f"Prepared {len(sound_files)} sound files")
    
    sound_context = format_sound_context_for_prompt(xml_content, pack_name)
    
    return sound_context



