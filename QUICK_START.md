# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API Key

**Option A: Using .env file (recommended)**

Create a `.env` file in the project root:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_BEST_CODING_MODEL=claude-3-5-sonnet-20241022
```

**Option B: Using environment variables**

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
export LLM_BEST_CODING_MODEL="claude-3-5-sonnet-20241022"
```

Get your key from: https://console.anthropic.com/

### 3. Verify Docker is Running

```bash
docker ps
```

If not running, start Docker Desktop.

### 4. Run the Agent

```bash
python main.py
```

### 5. Enter Your Game Idea

```
What game would you like to create?
Your task: Create a simple clicker game
```

### 6. Wait for Completion

The agent will:
- Plan the game structure
- Create HTML file
- Write JavaScript code
- Test and refine
- Mark as complete

### 7. Export and Play

```
Export files to directory: ./my-game
```

Then open `./my-game/index.html` in your browser!

## Example Tasks

### Beginner
- "Create a button that counts clicks"
- "Make a simple color picker"
- "Build a to-do list"

### Intermediate
- "Create a flappy bird clone"
- "Make a snake game"
- "Build a memory matching game"

### Advanced
- "Create a platformer with physics"
- "Build a space shooter with enemies"
- "Make a tower defense game"

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
```bash
export ANTHROPIC_API_KEY="your-key"
```

### "Cannot connect to Docker daemon"
Start Docker:
- macOS: Open Docker Desktop
- Linux: `sudo systemctl start docker`
- Windows: Start Docker Desktop

### Agent gets stuck
Press `Ctrl+C` to interrupt and try again with a simpler task.

### Files not created
Check the logs for errors. The agent will retry failed operations automatically.

## What's Next?

1. Read [USAGE.md](USAGE.md) for advanced features
2. Check [IMPLEMENTATION.md](IMPLEMENTATION.md) for architecture details
3. Look at [example.py](example.py) for programmatic usage
4. Customize system prompt in `llm_client.py`
5. Add your own tools in `tools.py`

## Support

Issues? Check:
1. Docker is running
2. API key is set correctly
3. Requirements are installed
4. You have internet connection

Still stuck? Review the logs for detailed error messages.

## Architecture (Simplified)

```
You: "Create a game"
  ↓
Claude: Analyzes and plans
  ↓
Agent: Creates files
  ↓
Claude: Reviews and refines
  ↓
Agent: Done! ✅
```

That's it! Start creating games! 🎮

