"""
PixiJS CDN configuration for game generation.
These CDN links should be used when generating HTML files for PixiJS games.
"""

# Official PixiJS v8.13.2 CDN links
PIXI_CDN_LINKS = {
    "core": "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js",
    "webworker": "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/webworker.min.js",
    "advanced_blend_modes": "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/advanced-blend-modes.min.js",
    "gif": "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/gif.min.js",
    "math_extras": "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/math-extras.min.js",
    "unsafe_eval": "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/unsafe-eval.min.js",
}

def get_pixi_script_tags() -> str:
    """
    Generate HTML script tags for PixiJS CDN links.
    Returns the core PixiJS library tag by default.
    Additional packages can be included as needed.
    """
    return f'<script src="{PIXI_CDN_LINKS["core"]}"></script>'

def get_all_pixi_script_tags() -> str:
    """
    Generate HTML script tags for all PixiJS CDN packages.
    Use this if you need all available PixiJS features.
    """
    tags = []
    tags.append(f'    <script src="{PIXI_CDN_LINKS["core"]}"></script>')
    tags.append(f'    <!-- Optional PixiJS packages (uncomment as needed): -->')
    tags.append(f'    <!-- <script src="{PIXI_CDN_LINKS["webworker"]}"></script> -->')
    tags.append(f'    <!-- <script src="{PIXI_CDN_LINKS["advanced_blend_modes"]}"></script> -->')
    tags.append(f'    <!-- <script src="{PIXI_CDN_LINKS["gif"]}"></script> -->')
    tags.append(f'    <!-- <script src="{PIXI_CDN_LINKS["math_extras"]}"></script> -->')
    tags.append(f'    <!-- <script src="{PIXI_CDN_LINKS["unsafe_eval"]}"></script> -->')
    return '\n'.join(tags)

def get_pixi_cdn_info() -> str:
    """
    Get formatted information about PixiJS CDN links for inclusion in prompts.
    """
    return f"""
IMPORTANT - PixiJS CDN Links (Version 8.13.2):
Use these official CDN links when generating HTML files:

Core PixiJS (REQUIRED):
  {PIXI_CDN_LINKS["core"]}

Optional Packages (include if needed):
  - Web Worker Support: {PIXI_CDN_LINKS["webworker"]}
  - Advanced Blend Modes: {PIXI_CDN_LINKS["advanced_blend_modes"]}
  - GIF Support: {PIXI_CDN_LINKS["gif"]}
  - Math Extras: {PIXI_CDN_LINKS["math_extras"]}
  - Unsafe Eval: {PIXI_CDN_LINKS["unsafe_eval"]}

IMPORTANT - File Naming Convention:
Your main HTML file MUST be named 'index.html'. This is the required entry point for the game.
Do not use custom names like 'game.html', 'tic-tac-toe.html', etc. Always use 'index.html'.

Example HTML structure:
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PixiJS Game</title>
    <script src="{PIXI_CDN_LINKS["core"]}"></script>
</head>
<body>
    <script>
        // Your PixiJS game code here
    </script>
</body>
</html>
"""

