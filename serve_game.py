#!/usr/bin/env python3
"""
Simple HTTP server to run games locally without CORS issues.

Usage:
    python serve_game.py [session_id]
    
If no session_id provided, will list available games.
"""
import sys
import http.server
import socketserver
from pathlib import Path
import webbrowser
import time
from threading import Timer


def list_games():
    """List all available game sessions."""
    games_dir = Path("games")
    if not games_dir.exists():
        print("No games directory found.")
        return []
    
    sessions = []
    for session_dir in sorted(games_dir.iterdir(), reverse=True):
        if session_dir.is_dir() and not session_dir.name.startswith('.'):
            session_json = session_dir / "session.json"
            if session_json.exists():
                sessions.append(session_dir.name)
    
    return sessions


def serve_game(session_id=None, port=8000):
    """Serve a game via HTTP to avoid CORS issues."""
    games_dir = Path("games")
    
    if session_id is None:
        # List available games
        sessions = list_games()
        if not sessions:
            print("No games found.")
            return
        
        print("\n" + "=" * 60)
        print("Available Games:")
        print("=" * 60)
        for i, session in enumerate(sessions, 1):
            print(f"  {i}. {session}")
        print("=" * 60)
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <session_id>")
        print("\nExample:")
        print(f"  python {sys.argv[0]} {sessions[0]}")
        return
    
    # Validate session
    game_dir = games_dir / session_id / "game"
    if not game_dir.exists():
        print(f"Error: Game not found: {game_dir}")
        print("\nAvailable games:")
        for session in list_games():
            print(f"  - {session}")
        return
    
    # Check for index.html
    index_file = game_dir / "index.html"
    if not index_file.exists():
        print(f"Error: index.html not found in {game_dir}")
        return
    
    print("\n" + "=" * 60)
    print(f"🎮 Starting Game Server")
    print("=" * 60)
    print(f"Session: {session_id}")
    print(f"Game Directory: {game_dir}")
    print(f"URL: http://localhost:{port}/")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server")
    print()
    
    # Change to game directory
    import os
    os.chdir(game_dir)
    
    # Create server
    Handler = http.server.SimpleHTTPRequestHandler
    Handler.extensions_map.update({
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.css': 'text/css',
        '.html': 'text/html',
    })
    
    # Open browser after a short delay
    def open_browser():
        webbrowser.open(f'http://localhost:{port}/')
    
    Timer(1.0, open_browser).start()
    
    # Start server
    with socketserver.TCPServer(("", port), Handler) as httpd:
        try:
            print(f"✓ Server running at http://localhost:{port}/")
            print(f"✓ Opening game in browser...")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        serve_game(session_id, port)
    else:
        serve_game()

