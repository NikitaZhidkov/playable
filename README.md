# Playable Ads Generator

An AI-powered coding agent that generates playable ads and pixi.js games from natural language descriptions.

## Features

- 🤖 **Autonomous Code Generation**: Uses Claude 3.5 Sonnet to write complete games
- 🎮 **Pixi.js Focused**: Specialized in creating interactive pixi.js games
- 🔄 **Interactive Loop**: Agent iteratively refines code until completion
- 🐳 **Containerized Workspace**: Uses Dagger for isolated, reproducible environments
- 🛠️ **Tool-Based Architecture**: Read, write, edit, and manage files programmatically

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy from ENV_TEMPLATE.txt)
export ANTHROPIC_API_KEY="your-api-key-here"
export GEMINI_API_KEY="your-gemini-key-here"
export LOGFIRE_TOKEN="your-logfire-token-here"

# Run the agent
python run.py
```

## Running Games Locally

Games are saved to `games/<session_id>/game/`. Due to browser CORS restrictions, you **cannot** simply open `index.html` directly. Use one of these methods:

### Method 1: Python HTTP Server (Recommended)

```bash
# Serve a specific game
python serve_game.py <session_id>

# List all available games
python serve_game.py
```

This will:
- Start a local HTTP server on port 8000
- Automatically open the game in your browser
- Avoid all CORS issues

### Method 2: Manual HTTP Server

```bash
cd games/<session_id>/game
python -m http.server 8000
# Then open http://localhost:8000 in your browser
```

### Why Not file:// Protocol?

Opening `index.html` directly (`file://`) triggers browser CORS restrictions that block loading assets (images, etc.). Always use an HTTP server for local development.

## Documentation

See [USAGE.md](USAGE.md) for detailed usage instructions, architecture overview, and customization options.

## Architecture

- **LangGraph**: Orchestrates the agent workflow
- **Anthropic Claude**: Generates code and makes decisions
- **Dagger**: Provides containerized workspace
- **Custom Tools**: File operations (read, write, edit, delete)

## Example

```bash
$ python main.py

🎮 Pixi.js Game Development Agent

What game would you like to create?
Your task: Create a simple space shooter game

[Agent generates complete game with HTML, CSS, and JavaScript]

✅ Task Completed!
Export files to directory: ./space-shooter
✅ Files exported to: ./space-shooter
To view your game, open ./space-shooter/index.html in a browser
```

## Project Structure

```
playable/
├── main.py              # Interactive CLI
├── agent_graph.py       # LangGraph workflow
├── agent_state.py       # State definition
├── llm_client.py        # Anthropic integration
├── workspace.py         # Dagger workspace
├── tools.py             # File operations
└── USAGE.md             # Detailed documentation
```

## Requirements

- Python 3.11+
- Docker (for Dagger)
- Anthropic API key

## License

See LICENSE file for details.