# Local CORS Issue and Solution

## The Problem

When you open a game by double-clicking `index.html`, the browser opens it with the `file://` protocol:
```
file:///Users/nikita/Programming/playable/games/20251026_224428_fd0d469e/game/index.html
```

This causes CORS (Cross-Origin Resource Sharing) errors:
```
Access to fetch at 'file:///Users/.../assets/rock1.png' from origin 'null' has been blocked by CORS policy
```

**Why does this happen?**
- Browser security prevents `file://` pages from loading other local files
- Each `file://` resource is treated as a different origin
- This is a fundamental browser security feature

**Why do images work in a new tab?**
- Opening an image directly has no CORS check (it's just an image)
- But loading an image FROM a page triggers CORS validation

## The Solution: Use HTTP Server

Games MUST be served via HTTP protocol (`http://localhost`) to avoid CORS restrictions.

### ✅ Solution 1: Python Script (Easiest)

We provide `serve_game.py` that handles everything:

```bash
# List available games
python serve_game.py

# Serve a specific game
python serve_game.py 20251026_224428_fd0d469e
```

The script will:
1. ✅ Start HTTP server on port 8000
2. ✅ Automatically open game in browser
3. ✅ No CORS errors!

### ✅ Solution 2: Python Built-in Server

```bash
cd games/20251026_224428_fd0d469e/game
python -m http.server 8000
# Open http://localhost:8000 in browser
```

### ✅ Solution 3: Node.js Server

```bash
cd games/20251026_224428_fd0d469e/game
npx http-server -p 8000
# Open http://localhost:8000 in browser
```

### ✅ Solution 4: VS Code Live Server

1. Install "Live Server" extension
2. Right-click `index.html`
3. Select "Open with Live Server"

## Why We Can't Fix This in the Code

The CORS restriction is a **browser security feature**, not a code bug. Solutions:

❌ **Can't fix**: Modify HTML/JavaScript (browsers ignore this)
❌ **Can't fix**: Add CORS headers to files (only works for HTTP servers)
❌ **Can't fix**: Disable CORS in browser (not practical for users)

✅ **Can fix**: Serve files via HTTP (proper web development practice)

## What We Fixed for Testing

The automated **Playwright testing environment** has CORS disabled:

```javascript
// test_game.py - Playwright configuration
const browser = await chromium.launch({
    args: [
        '--allow-file-access-from-files',
        '--disable-web-security'
    ]
});
```

This only applies to **automated tests**, not to manual browser usage.

## Agent Instructions Updated

The agent now includes instructions in every generated game:

```html
<!--
To run this game locally:
1. Start a local HTTP server:
   python -m http.server 8000
2. Open http://localhost:8000 in your browser

(Opening index.html directly will cause CORS errors)
-->
```

These instructions appear at the top of every `index.html` file.

## Quick Reference

| Method | Command | Auto-opens? | Easy? |
|--------|---------|-------------|-------|
| serve_game.py | `python serve_game.py <id>` | ✅ Yes | ⭐⭐⭐ |
| Python server | `python -m http.server 8000` | ❌ No | ⭐⭐ |
| Node server | `npx http-server -p 8000` | ❌ No | ⭐⭐ |
| VS Code | Right-click → Live Server | ✅ Yes | ⭐⭐⭐ |

## Testing Your Setup

Run the game server and verify:

```bash
# Start server
python serve_game.py 20251026_224428_fd0d469e

# Should see:
# ✓ Server running at http://localhost:8000/
# ✓ Opening game in browser...
```

Open browser console (F12):
- ✅ **Good**: No CORS errors, assets load correctly
- ❌ **Bad**: CORS errors → You're still using file:// protocol

## Summary

- **Problem**: Browser CORS blocks file:// asset loading
- **Solution**: Always use HTTP server for local development
- **Testing**: Playwright tests have CORS disabled automatically
- **Agent**: Now includes instructions in every game
- **Tool**: Use `serve_game.py` for easiest workflow

**Bottom line**: Never open `index.html` directly. Always use an HTTP server! 🚀

