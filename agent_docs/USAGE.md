# Pixi.js Game Development Agent - Usage Guide

## Overview

This is an interactive AI coding agent that creates pixi.js games from natural language descriptions. The agent uses LangGraph for orchestration and Anthropic's Claude for code generation.

## Architecture

### Core Components

1. **`workspace.py`**: Dagger-based containerized workspace for code execution
2. **`tools.py`**: File operation tools (read, write, edit, delete)
3. **`agent_state.py`**: LangGraph state definition
4. **`llm_client.py`**: Anthropic Claude integration
5. **`agent_graph.py`**: LangGraph workflow definition
6. **`main.py`**: Interactive CLI interface

### Workflow

```
User Input → LLM Node → Tools Node → LLM Node → ... → Complete
```

1. **LLM Node**: Claude decides what actions to take based on the task
2. **Tools Node**: Executes file operations (create/edit files)
3. Loop continues until the agent calls the `complete` tool

## Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Set Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Install Docker (required for Dagger)
# https://docs.docker.com/get-docker/
```

## Running the Agent

### Basic Usage

```bash
python main.py
```

The agent will prompt you for a task description. Examples:

- "Create a simple flappy bird clone"
- "Make a platformer game with jumping physics"
- "Build a space shooter with asteroids"
- "Create a puzzle game like 2048"

### Example Session

```
🎮 Pixi.js Game Development Agent
================================================================

What game would you like to create?
Your task: Create a simple brick breaker game

Task: Create a simple brick breaker game
================================================================

🤖 Agent is working on your task...

[Agent creates files, writes code, tests...]

================================================================
✅ Task Completed!
================================================================

📝 Changes made:
+++ index.html
[Shows the diff of created files]

Export files to directory: ./my-game
✅ Files exported to: /path/to/my-game
To view your game, open /path/to/my-game/index.html in a browser
```

## How It Works

### 1. Workspace Initialization

The agent creates a containerized Node.js environment using Dagger:

```python
workspace = await Workspace.create(
    client=client,
    base_image="oven/bun:1.2.5-alpine",
    setup_cmd=[
        ["npm", "install", "-g", "npm@latest"],
        ["apk", "add", "--no-cache", "git"]
    ]
)
```

### 2. Agent Loop

The LangGraph agent follows this loop:

1. **Understand**: Claude analyzes the task
2. **Plan**: Decides what files to create
3. **Execute**: Uses tools to create/edit files
4. **Verify**: Reviews the changes
5. **Complete**: Calls the complete tool when done

### 3. Tool Execution

The agent has access to these tools:

- `read_file(path)`: Read file contents
- `write_file(path, content)`: Create/overwrite a file
- `edit_file(path, search, replace)`: Edit existing files
- `delete_file(path)`: Delete a file
- `complete()`: Mark task as finished

### 4. Output

The agent provides:

- Real-time logging of actions
- A git diff showing all changes
- Option to export files to local directory

## Customization

### Modify the System Prompt

Edit `llm_client.py` to change the agent's behavior:

```python
SYSTEM_PROMPT = """You are an expert pixi.js game developer..."""
```

### Add More Tools

Extend `FileOperations` in `tools.py`:

```python
{
    "name": "your_tool",
    "description": "Tool description",
    "input_schema": {...}
}
```

### Change Base Image

Modify `main.py` to use a different container:

```python
workspace = await Workspace.create(
    client=client,
    base_image="python:3.11-alpine",  # Different base
    ...
)
```

## Troubleshooting

### "ANTHROPIC_API_KEY not found"

Set your API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Docker daemon is not running"

Start Docker Desktop or the Docker daemon.

### Agent Gets Stuck

The agent has built-in retry logic with exponential backoff. If it gets truly stuck, press Ctrl+C to interrupt.

### Files Not Exported

Check that:
1. The export directory path is valid
2. You have write permissions
3. The agent completed successfully

## Advanced Usage

### Programmatic Usage

You can use the agent programmatically:

```python
import asyncio
import dagger
from workspace import Workspace
from tools import FileOperations
from llm_client import LLMClient
from agent_graph import create_agent_graph
from langchain_core.messages import HumanMessage

async def create_game(task: str):
    async with dagger.Connection() as client:
        workspace = await Workspace.create(
            client=client,
            base_image="node:20-alpine"
        )
        
        llm_client = LLMClient()
        file_ops = FileOperations(workspace=workspace)
        agent = create_agent_graph(llm_client, file_ops)
        
        state = {
            "messages": [HumanMessage(content=task)],
            "workspace": workspace,
            "task_description": task,
            "is_completed": False
        }
        
        final_state = await agent.ainvoke(state)
        return final_state

asyncio.run(create_game("Create a pong game"))
```

## Project Structure

```
playable/
├── workspace.py          # Containerized workspace
├── tools.py              # File operation tools
├── dagger_utils.py       # Dagger utilities
├── custom_types.py       # Type definitions
├── log.py                # Logging utilities
├── agent_state.py        # LangGraph state
├── llm_client.py         # Anthropic integration
├── agent_graph.py        # LangGraph workflow
├── main.py               # CLI interface
├── requirements.txt      # Python dependencies
└── USAGE.md              # This file
```

## Next Steps

1. Try creating different types of games
2. Customize the system prompt for different use cases
3. Add more tools for advanced functionality
4. Integrate with CI/CD for automated testing
5. Add memory/checkpointing for longer sessions

## Support

For issues or questions:
- Check the logs for detailed error messages
- Review the system prompt in `llm_client.py`
- Ensure all dependencies are installed
- Verify Docker is running properly

