# PixiJS CDN Links Reference

This document contains the official CDN links for PixiJS v8.13.2 used in this project.

## Core Library (Required)

The main PixiJS library that must be included in every game:

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
```

## Optional Packages

Include these packages only if you need their specific functionality:

### Web Worker Support
For running PixiJS in web workers:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/webworker.min.js"></script>
```

### Advanced Blend Modes
For advanced blending effects:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/advanced-blend-modes.min.js"></script>
```

### GIF Support
For animated GIF support:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/gif.min.js"></script>
```

### Math Extras
For additional math utilities:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/math-extras.min.js"></script>
```

### Unsafe Eval
For features requiring eval (use with caution):
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/packages/unsafe-eval.min.js"></script>
```

## Example HTML Template

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PixiJS Game</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #000;
        }
    </style>
    <!-- Core PixiJS library -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pixi.js/8.13.2/pixi.min.js"></script>
    <!-- Add optional packages here if needed -->
</head>
<body>
    <script>
        // Your PixiJS game code here
        const app = new PIXI.Application();
        await app.init({ width: 800, height: 600 });
        document.body.appendChild(app.canvas);
        
        // Your game logic...
    </script>
</body>
</html>
```

## Integration with Agent

The agent automatically includes these CDN links when generating games. The links are configured in `pixi_cdn.py` and injected into the agent's prompt via `main.py`.

## Updating CDN Links

If you need to update to a different version of PixiJS:

1. Edit the `PIXI_CDN_LINKS` dictionary in `pixi_cdn.py`
2. Update the version number in this document
3. Test the generated games to ensure compatibility

## More Information

- [PixiJS Official Documentation](https://pixijs.com/)
- [PixiJS GitHub Repository](https://github.com/pixijs/pixijs)
- [CDNJS PixiJS Page](https://cdnjs.com/libraries/pixi.js)

