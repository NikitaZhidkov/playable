"""
Asset pack management for game development.
Handles asset discovery, VLM-based description generation, and XML creation.
"""
import logging
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
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.warning(f"Could not get dimensions for {image_path}: {e}")
        return (0, 0)


def parse_existing_descriptions(xml_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse existing description.xml file.
    
    Args:
        xml_path: Path to description.xml file
    
    Returns:
        Dictionary mapping filename to {width, height, description}
    """
    descriptions = {}
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        for asset in root.findall('asset'):
            name = asset.get('name', '')
            if name:
                descriptions[name] = {
                    'width': asset.get('width', '0'),
                    'height': asset.get('height', '0'),
                    'description': asset.get('description', '')
                }
        
        logger.info(f"Parsed {len(descriptions)} existing descriptions from {xml_path}")
        return descriptions
        
    except Exception as e:
        logger.warning(f"Error parsing existing XML {xml_path}: {e}")
        return {}


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
    
    Args:
        descriptions: Dictionary mapping filename to {width, height, description}
        pack_name: Name of the asset pack
    
    Returns:
        Formatted XML string
    """
    # Create root element
    root = ET.Element('pack', attrib={'name': pack_name})
    
    # Add assets in sorted order
    for filename in sorted(descriptions.keys()):
        info = descriptions[filename]
        ET.SubElement(
            root,
            'asset',
            attrib={
                'name': filename,
                'width': str(info['width']),
                'height': str(info['height']),
                'description': info['description']
            }
        )
    
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
            descriptions[filename] = existing_descriptions[filename]
            # Update dimensions if they changed
            descriptions[filename]['width'] = str(width)
            descriptions[filename]['height'] = str(height)
            logger.debug(f"Using existing description for {filename}")
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
    try:
        xml_path.write_text(xml_content, encoding='utf-8')
        logger.info(f"Saved description.xml to {xml_path}")
        if missing_count > 0:
            logger.info(f"Generated {missing_count} new descriptions using VLM")
    except Exception as e:
        logger.error(f"Error saving description.xml: {e}")
    
    return xml_content


def format_asset_context_for_prompt(xml_content: str, pack_name: str) -> str:
    """
    Format asset pack information for inclusion in agent prompt.
    
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
        "The following assets are available in the 'assets/' folder:",
        ""
    ]
    
    for asset in root.findall('asset'):
        name = asset.get('name', '')
        width = asset.get('width', '0')
        height = asset.get('height', '0')
        description = asset.get('description', '')
        
        lines.append(f"- **{name}** ({width}x{height}px): {description}")
    
    lines.extend([
        "",
        "To use these assets in your game:",
        "- Load images using: `PIXI.Sprite.from('assets/{filename}')`",
        "- Assets are located in the 'assets/' folder",
        "- Use these assets to create visually appealing games",
        ""
    ])
    
    return '\n'.join(lines)


def prepare_pack_for_workspace(
    pack_name: str,
    workspace_assets_dir: Path,
    source_assets_dir: Path = Path("assets")
) -> Optional[str]:
    """
    Prepare an asset pack for use in workspace.
    Generates/validates descriptions and copies assets.
    
    Args:
        pack_name: Name of the pack to prepare
        workspace_assets_dir: Path to workspace assets directory
        source_assets_dir: Path to source assets directory
    
    Returns:
        Formatted asset context for prompt, or None if failed
    """
    pack_path = source_assets_dir / pack_name
    
    if not pack_path.exists():
        logger.error(f"Pack directory not found: {pack_path}")
        return None
    
    logger.info(f"Preparing pack '{pack_name}' for workspace")
    
    # Get or create descriptions
    xml_content = get_or_create_pack_descriptions(pack_path, pack_name)
    
    # Create workspace assets directory
    workspace_assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all PNG files to workspace
    png_files = list(pack_path.glob("*.png"))
    for png_file in png_files:
        dest = workspace_assets_dir / png_file.name
        import shutil
        shutil.copy2(png_file, dest)
        logger.debug(f"Copied {png_file.name} to workspace")
    
    logger.info(f"Copied {len(png_files)} assets to workspace")
    
    # Copy description.xml to workspace
    xml_dest = workspace_assets_dir / "description.xml"
    xml_dest.write_text(xml_content, encoding='utf-8')
    logger.info(f"Copied description.xml to workspace")
    
    # Format context for prompt
    asset_context = format_asset_context_for_prompt(xml_content, pack_name)
    
    return asset_context
    


