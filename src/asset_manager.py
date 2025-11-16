"""
Asset pack management for game development.
Handles asset discovery, file-based assets for TypeScript imports, and description management.
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom
from PIL import Image
import base64
import hashlib
import json

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


def get_file_hash(file_path: Path) -> str:
    """
    Calculate MD5 hash of a file for change detection.
    
    Args:
        file_path: Path to the file
    
    Returns:
        MD5 hash string
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def image_to_base64(image_path: Path) -> str:
    """
    Convert an image file to base64 data URI.
    
    Args:
        image_path: Path to the image file
    
    Returns:
        Base64 data URI string (e.g., "data:image/png;base64,...")
    """

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        # Determine MIME type from extension
        ext = image_path.suffix.lower()
        mime_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }.get(ext, 'image/png')
        
        data_uri = f"data:{mime_type};base64,{base64_data}"
        logger.debug(f"Converted {image_path.name} to base64 ({len(data_uri)} chars)")
        return data_uri


def load_base64_cache(cache_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load base64 cache metadata.
    
    Args:
        cache_path: Path to cache.json file
    
    Returns:
        Dictionary mapping filename to {hash, base64_data}
    """
    if not cache_path.exists():
        return {}
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_base64_cache(cache_path: Path, cache_data: Dict[str, Dict[str, str]]):
    """
    Save base64 cache metadata.
    
    Args:
        cache_path: Path to cache.json file
        cache_data: Dictionary mapping filename to {hash, base64_data}
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)
    logger.debug(f"Saved base64 cache to {cache_path}")


def get_or_create_base64_assets(pack_path: Path) -> Dict[str, str]:
    """
    Get or create base64-encoded versions of all PNG assets in a pack.
    Uses caching to avoid re-encoding unchanged files.
    
    Args:
        pack_path: Path to the asset pack directory
    
    Returns:
        Dictionary mapping filename to base64 data URI
    """
    logger.info(f"Processing base64 assets for pack: {pack_path.name}")
    
    # Set up base64 cache directory
    base64_dir = pack_path / "base64"
    base64_dir.mkdir(exist_ok=True)
    cache_file = base64_dir / "cache.json"
    
    # Load existing cache
    cache = load_base64_cache(cache_file)
    
    # Find all PNG files
    png_files = sorted(pack_path.glob("*.png"))
    current_files = {f.name for f in png_files}
    cached_files = set(cache.keys())
    
    # Remove cache entries for deleted files
    removed_files = cached_files - current_files
    for filename in removed_files:
        logger.info(f"Removing cached base64 for deleted file: {filename}")
        cache.pop(filename, None)
    
    # Process each PNG file
    base64_assets = {}
    updated_count = 0
    cached_count = 0
    
    for png_file in png_files:
        filename = png_file.name
        file_hash = get_file_hash(png_file)
        
        # Check if we have a valid cached version
        if filename in cache and cache[filename].get('hash') == file_hash:
            # Use cached version
            base64_assets[filename] = cache[filename]['base64_data']
            cached_count += 1
            logger.debug(f"Using cached base64 for {filename}")
        else:
            # Generate new base64
            logger.info(f"Generating base64 for {filename}")
            base64_data = image_to_base64(png_file)
            base64_assets[filename] = base64_data
            
            # Update cache
            cache[filename] = {
                'hash': file_hash,
                'base64_data': base64_data
            }
            updated_count += 1
    
    # Save updated cache
    if updated_count > 0 or removed_files:
        save_base64_cache(cache_file, cache)
        logger.info(f"Base64 cache updated: {updated_count} new/updated, {len(removed_files)} removed, {cached_count} cached")
    else:
        logger.info(f"All {cached_count} assets loaded from cache")
    
    return base64_assets


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


def create_assets_js_file(base64_assets: Dict[str, str], pack_name: str) -> str:
    """
    Create a JavaScript file with all base64 assets.
    
    Args:
        base64_assets: Dictionary mapping filename to base64 data URI
        pack_name: Name of the asset pack
    
    Returns:
        JavaScript file content
    """
    lines = [
        f"// Asset pack: {pack_name}",
        "// Auto-generated base64 asset data",
        "",
        "const ASSETS = {",
    ]
    
    for i, (filename, base64_data) in enumerate(sorted(base64_assets.items())):
        comma = "," if i < len(base64_assets) - 1 else ""
        lines.append(f"    '{filename}': '{base64_data}'{comma}")
    
    lines.extend([
        "};",
        "",
        "// Export for use in game",
        "if (typeof module !== 'undefined' && module.exports) {",
        "    module.exports = ASSETS;",
        "}",
        ""
    ])
    
    return '\n'.join(lines)


def format_asset_context_for_prompt(
    xml_content: str, 
    pack_name: str
) -> str:
    """
    Format asset pack information for inclusion in agent prompt.
    References assets.js file instead of embedding base64 data.
    
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
        "The following assets are available in the 'assets/assets.js' file:",
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
        
        # Add ALL other custom attributes from XML (e.g., human_description, or any other custom tags)
        custom_attrs = []
        for attr_name, attr_value in sorted(asset.attrib.items()):
            # Skip standard attributes we already handled
            if attr_name not in ['name', 'width', 'height', 'description']:
                custom_attrs.append(f"{attr_name}: {attr_value}")
        
        # Append custom attributes
        if custom_attrs:
            if description:
                line_parts.append(" | ")
            else:
                line_parts.append(": ")
            line_parts.append(", ".join(custom_attrs))
        
        lines.append("".join(line_parts))
    
    lines.extend([
        "",
        "## IMPORTANT: How to Use Assets with Base64",
        "",
        "**All assets are pre-converted to base64 and stored in 'assets/assets.js'.**",
        "**This file is already in your workspace - just load it!**",
        "",
        "### Step 1: Load the Assets File",
        "",
        "In your HTML file, load the assets before your game script:",
        "",
        "```html",
        "<script src=\"assets/assets.js\"></script>",
        "<script src=\"game.js\"></script>",
        "```",
        "",
        "### Step 2: Load Base64 Images Correctly",
        "",
        "**CRITICAL: The synchronous `PIXI.Sprite.from(base64String)` doesn't work!**",
        "**You MUST use the async Image loading approach:**",
        "",
        "```javascript",
        "// Helper function to load base64 image asynchronously",
        "function loadBase64Image(base64Data) {",
        "    return new Promise((resolve, reject) => {",
        "        const img = new Image();",
        "        img.onload = () => resolve(img);",
        "        img.onerror = reject;",
        "        img.src = base64Data;",
        "    });",
        "}",
        "",
        "// Load and create sprite from base64",
        "async function createSprite(assetName) {",
        "    const img = await loadBase64Image(ASSETS[assetName]);",
        "    const texture = PIXI.Texture.from(img);",
        "    return new PIXI.Sprite(texture);",
        "}",
        "",
        "// Usage in your game",
        "async function setupGame() {",
        "    const car = await createSprite('car_black_1.png');",
        "    car.x = 100;",
        "    car.y = 200;",
        "    app.stage.addChild(car);",
        "}",
        "",
        "setupGame();",
        "```",
        "",
        "### Complete Example with Multiple Assets:",
        "",
        "```javascript",
        "// ASSETS object is already loaded from assets.js",
        "",
        "// Helper function",
        "function loadBase64Image(base64Data) {",
        "    return new Promise((resolve, reject) => {",
        "        const img = new Image();",
        "        img.onload = () => resolve(img);",
        "        img.onerror = reject;",
        "        img.src = base64Data;",
        "    });",
        "}",
        "",
        "async function createSprite(assetName) {",
        "    const img = await loadBase64Image(ASSETS[assetName]);",
        "    const texture = PIXI.Texture.from(img);",
        "    return new PIXI.Sprite(texture);",
        "}",
        "",
        "// Load all assets and set up game",
        "async function initGame() {",
        "    // Load multiple assets",
        "    const car = await createSprite('car_black_1.png');",
        "    const rock = await createSprite('rock1.png');",
        "    const road = await createSprite('road_asphalt03.png');",
        "    ",
        "    // Position sprites",
        "    car.position.set(100, 200);",
        "    rock.position.set(300, 400);",
        "    road.position.set(0, 0);",
        "    ",
        "    // Add to stage",
        "    app.stage.addChild(road, rock, car);",
        "    ",
        "    // Start game loop",
        "    app.ticker.add(gameLoop);",
        "}",
        "",
        "// Initialize when ready",
        "initGame();",
        "```",
        "",
        "### CRITICAL RULES:",
        "- ✓ CORRECT: Load base64 into Image element, wait for onload, then PIXI.Texture.from(img)",
        "- ✓ CORRECT: Use async/await with the helper functions above",
        "- ✗ WRONG: `PIXI.Sprite.from(ASSETS['car.png'])` - synchronous approach doesn't work!",
        "- ✗ WRONG: `PIXI.Sprite.from('assets/car.png')` - PNG files don't exist!",
        "",
        "### Why This Approach?",
        "- Base64 images need async loading via Image element",
        "- Synchronous PIXI.Sprite.from() doesn't work with base64 data URIs",
        "- The img.onload event ensures texture is ready before use",
        "- PIXI.Texture.from(img) creates texture from loaded Image element",
        "",
        "### Complete Working Example",
        "",
        "**index.html:**",
        "```html",
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <meta charset=\"UTF-8\">",
        "    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        "    <title>My PixiJS Game</title>",
        "    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js\"></script>",
        "    <style>",
        "        body { margin: 0; padding: 0; overflow: hidden; }",
        "        #game { width: 100vw; height: 100vh; }",
        "    </style>",
        "</head>",
        "<body>",
        "    <div id=\"game\"></div>",
        "    <!-- Load assets first -->",
        "    <script src=\"assets/assets.js\"></script>",
        "    <!-- Then load game -->",
        "    <script src=\"game.js\"></script>",
        "</body>",
        "</html>",
        "```",
        "",
        "**game.js:**",
        "```javascript",
        "// ASSETS object is already loaded from assets/assets.js",
        "",
        "// Helper to load Base64 as texture",
        "async function loadTexture(base64) {",
        "    return new Promise(resolve => {",
        "        const img = new Image();",
        "        img.onload = () => resolve(PIXI.Texture.from(img));",
        "        img.src = base64;",
        "    });",
        "}",
        "",
        "// Initialize game",
        "(async () => {",
        "    // Create PixiJS app",
        "    const app = new PIXI.Application();",
        "    await app.init({ width: 800, height: 600, backgroundColor: 0x1099bb });",
        "    ",
        "    // Add canvas to page (CRITICAL: use app.view in PixiJS v8)",
        "    document.getElementById('game').appendChild(app.view);",
        "    ",
        "    // Load texture from Base64",
        "    const carTexture = await loadTexture(ASSETS['car_black_1.png']);",
        "    ",
        "    // Create sprite",
        "    const car = new PIXI.Sprite(carTexture);",
        "    car.x = 400;",
        "    car.y = 300;",
        "    app.stage.addChild(car);",
        "    ",
        "    // Game loop (optional)",
        "    app.ticker.add((delta) => {",
        "        // Game logic here",
        "        car.rotation += 0.01 * delta;",
        "    });",
        "})();",
        "```",
        "",
        "### File Structure:",
        "```",
        "your-game/",
        "├── index.html          (loads assets.js and game.js)",
        "├── game.js             (your game code with async loading)",
        "└── assets/",
        "    └── assets.js       (pre-generated base64 data)",
        "```",
        "",
        "Remember: Always use the async Image loading approach with base64 data!",
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
    Copy asset pack files to workspace for TypeScript imports.
    Handles both visual assets (from assets/) and audio (from Sounds/).
    
    Args:
        pack_name: Name of the pack to prepare
        workspace_assets_dir: Path to workspace assets directory
        source_assets_dir: Path to source assets directory (for sprites)
        source_sounds_dir: Path to source sounds directory (for audio)
    
    Returns:
        Formatted asset info string with descriptions, or None if no assets found
    """
    # Create workspace assets directory
    workspace_assets_dir.mkdir(parents=True, exist_ok=True)
    
    sprites = []
    sounds = []
    
    # Copy sprite assets from assets/PackName/
    sprite_pack_path = source_assets_dir / pack_name
    if sprite_pack_path.exists():
        for file in sprite_pack_path.iterdir():
            if file.is_file() and file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                shutil.copy2(file, workspace_assets_dir / file.name)
                sprites.append(file.name)
                logger.info(f"Copied sprite: {file.name}")
    
    # Copy sound assets from Sounds/PackName/
    sound_pack_path = source_sounds_dir / pack_name
    if sound_pack_path.exists():
        for file in sound_pack_path.iterdir():
            if file.is_file() and file.suffix.lower() in ['.mp3', '.wav', '.ogg']:
                shutil.copy2(file, workspace_assets_dir / file.name)
                sounds.append(file.name)
                logger.info(f"Copied sound: {file.name}")
    
    if not sprites and not sounds:
        logger.warning(f"No assets found for pack: {pack_name}")
        return None
    
    # Read sprite descriptions
    sprite_desc_xml_path = sprite_pack_path / "description.xml" if sprite_pack_path.exists() else None
    sprite_xml_content = ""
    if sprite_desc_xml_path and sprite_desc_xml_path.exists():
        sprite_xml_content = sprite_desc_xml_path.read_text()
        logger.info(f"Loaded sprite descriptions from {sprite_desc_xml_path}")
    
    # Read sound descriptions
    sound_desc_xml_path = sound_pack_path / "description.xml" if sound_pack_path.exists() else None
    sound_xml_content = ""
    if sound_desc_xml_path and sound_desc_xml_path.exists():
        sound_xml_content = sound_desc_xml_path.read_text()
        logger.info(f"Loaded sound descriptions from {sound_desc_xml_path}")
    
    # Format asset info for prompt
    asset_info = f"Pack: {pack_name}\n"
    asset_info += f"Sprites ({len(sprites)}): {', '.join(sprites)}\n"
    if sprite_xml_content:
        asset_info += f"\nSprite Descriptions:\n{sprite_xml_content}\n"
    
    asset_info += f"\nSounds ({len(sounds)}): {', '.join(sounds)}\n"
    if sound_xml_content:
        asset_info += f"\nSound Descriptions:\n{sound_xml_content}\n"
    
    logger.info(f"Prepared {len(sprites)} sprites and {len(sounds)} sounds for TypeScript imports")
    return asset_info


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
    
    import shutil
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



