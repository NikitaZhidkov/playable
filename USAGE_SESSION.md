# Session-Based Workflow - User Guide

## Quick Start

### Starting the Agent
```bash
python main.py
```

## Main Menu Options

When you run the agent, you'll see:
```
🎮 Pixi.js Game Development Agent
═══════════════════════════════════════

What would you like to do?
  (n) Create a new game
  (c) Continue working on an existing game
  (e) Exit
```

## Creating a New Game

1. Choose option `n`
2. Enter your game description:
   ```
   What game would you like to create?
   Example: 'Create a simple platformer game with a character that can jump'
   
   Your task: Create a space shooter with enemies
   ```

3. The agent will:
   - Generate a unique session ID (e.g., `20251022_143052_a1b2c3d4`)
   - Create the game files
   - Run browser tests to validate
   - Save everything to `games/<session_id>/game/`
   - Initialize a git repository

4. After completion, you'll be asked:
   ```
   Continue working on this game? (y/n):
   ```
   - `y` - Stay on this session for more changes
   - `n` - Return to main menu

## Continuing an Existing Game

1. Choose option `c`
2. You'll see a list of your recent sessions:
   ```
   📚 Recent Sessions
   ═══════════════════════════════════════
   
   1. [20251022_143052_a1b2c3d4]
      Created: 2025-10-22 14:30
      Prompt: Create a space shooter with enemies
      Iterations: 2
   
   2. [20251022_120030_x9y8z7w6]
      Created: 2025-10-22 12:00
      Prompt: Make a puzzle game like Tetris
      Iterations: 0
   
   Enter session number (1-5) or session ID:
   Selection:
   ```

3. Select by:
   - **Number**: Enter `1`, `2`, etc.
   - **Full ID**: Paste `20251022_143052_a1b2c3d4`

4. Provide your feedback:
   ```
   Current game: Create a space shooter with enemies...
   
   What would you like to change or add?
   Example: 'Add a score counter in the top right corner'
   
   Your feedback: Add power-ups that make the ship faster
   ```

5. The agent will:
   - Load all existing game files
   - Understand the current implementation
   - Apply your requested changes
   - Run browser tests
   - Update the files in place
   - Create a git commit with your feedback

6. After completion, you'll be asked:
   ```
   Continue working on this game? (y/n):
   ```

## Session Folder Structure

Each session creates this structure:
```
games/20251022_143052_a1b2c3d4/
├── session.json          # Metadata
└── game/                 # Your game files
    ├── index.html
    ├── game.js
    ├── style.css
    └── .git/             # Full change history
```

## Tips

### For Better Results

**When creating a new game:**
- Be specific about what you want
- Mention game mechanics, visual style, controls
- Example: "Create a side-scrolling platformer with jumping, collectible coins, and simple physics"

**When providing feedback:**
- Be clear about what to change
- Reference specific elements if needed
- Example: "Make the player character move faster and add a double jump ability"

### Session IDs

Session IDs have a timestamp prefix for easy sorting:
- Format: `YYYYMMDD_HHMMSS_<uuid>`
- Example: `20251022_143052_a1b2c3d4`
  - Created on: Oct 22, 2025 at 2:30:52 PM

### Git History

Each session maintains a complete git history:
- Initial creation: "Initial game creation"
- Each feedback: "Feedback iteration: <your feedback>"

To view history:
```bash
cd games/20251022_143052_a1b2c3d4/game
git log
```

### Viewing Your Game

After creation or updates:
```bash
# Open in browser
open games/20251022_143052_a1b2c3d4/game/index.html

# Or use a local server
cd games/20251022_143052_a1b2c3d4/game
python -m http.server 8000
# Then open http://localhost:8000
```

## Workflow Examples

### Example 1: Create and Iterate
```
1. Start agent
2. Choose (n) - New game
3. Enter: "Create a simple snake game"
4. Wait for completion
5. Choose (y) - Continue working
6. Enter: "Add score display and game over screen"
7. Wait for changes
8. Choose (y) - Continue working
9. Enter: "Make the snake move faster as score increases"
10. Wait for changes
11. Choose (n) - Done
```

### Example 2: Return to Old Project
```
1. Start agent
2. Choose (c) - Continue
3. Select session from list: 1
4. Enter: "Add sound effects when eating food"
5. Wait for changes
6. Choose (n) - Done
7. Choose (e) - Exit
```

## Troubleshooting

### Session not found
- Make sure you're in the project directory
- Check that `games/` folder exists
- Verify session ID is correct

### Agent makes wrong changes
- Try again with more specific feedback
- Reference exact file names or elements
- Break complex changes into smaller steps

### Want to start over on a session
- The old versions are in git history
- Navigate to the game folder and use git commands:
  ```bash
  cd games/<session_id>/game
  git log              # See history
  git reset --hard HEAD~1  # Undo last change
  ```

## Environment Setup

Required environment variables (in `.env`):
```
ANTHROPIC_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
LLM_BEST_CODING_MODEL=claude-sonnet-4-20250514
LLM_VISION_MODEL=gemini-2.0-flash-exp
```

## Keyboard Shortcuts

- `Ctrl+C` - Interrupt current operation (returns to menu)
- Type `e` at menu - Exit the agent

## Have Fun! 🎮

Your games are saved permanently. You can always come back to any session and continue improving your game!

