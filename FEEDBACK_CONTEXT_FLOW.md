# Feedback Context Flow Documentation

## Overview

When a user provides feedback on an existing game, the system builds a comprehensive context that includes the original prompt and all current game files, then combines it with the user's feedback to guide the agent's modifications.

## Architecture

### 1. Template Location (`playbook.py`)

The feedback prompt template is defined in `playbook.py`:

```python
FEEDBACK_CONTEXT_TEMPLATE = """{project_context}

Use the tools to create or modify files as needed.
Given original user request:
{user_prompt}
Implement solely the required changes according to the user feedback:
{feedback}"""
```

**Variables:**
- `{project_context}`: Current game files content (built by `build_feedback_context()`)
- `{user_prompt}`: Original user request that created the game
- `{feedback}`: User's feedback/request for changes

### 2. Context Building (`main.py`)

The `build_feedback_context()` function constructs the project context:

```python
async def build_feedback_context(session: Session, game_path: Path) -> str:
    """Build context string with all game files for feedback mode."""
    
    context_parts = [
        "Current game files:",
        ""
    ]
    
    # Read all files in game directory
    for file_path in sorted(game_path.rglob("*")):
        if file_path.is_file() and not file_path.name.startswith('.'):
            # Skip git files
            if '.git' in file_path.parts:
                continue
            
            rel_path = file_path.relative_to(game_path)
            content = file_path.read_text(encoding='utf-8')
            context_parts.append(f"=== {rel_path} ===")
            context_parts.append(content)
            context_parts.append("")
    
    return "\n".join(context_parts)
```

**Project Context Structure:**
```
Current game files:

=== index.html ===
<file content>

=== game.js ===
<file content>

=== style.css ===
<file content>
```

### 3. Usage in Feedback Workflow (`main.py`)

The feedback workflow combines context with user feedback:

```python
async def run_feedback_workflow(client: dagger.Client, session: Session, feedback: str) -> Session:
    # 1. Get game path
    game_path = get_game_path(session.session_id)
    
    # 2. Build context with existing game files
    project_context = await build_feedback_context(session, game_path)
    
    # 3. Initialize workspace with existing game files
    workspace = await initialize_workspace(client, game_path)
    
    # 4. Build feedback prompt using template
    feedback_prompt = FEEDBACK_CONTEXT_TEMPLATE.format(
        project_context=project_context,
        user_prompt=session.initial_prompt,
        feedback=feedback
    )
    
    # 5. Create initial state with feedback prompt
    initial_state = {
        "messages": [HumanMessage(content=feedback_prompt)],
        "workspace": workspace,
        "is_feedback_mode": True,
        ...
    }
    
    # 6. Run agent with feedback prompt
    final_state = await agent.ainvoke(initial_state)
```

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ User provides feedback: "Add score counter"            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ load_session(session_id)                               │
│ ├─ session.initial_prompt                              │
│ ├─ session.created_at                                  │
│ └─ session.iterations[]                                │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ build_feedback_context(session, game_path)            │
│                                                         │
│ Output (project_context):                              │
│ ┌─────────────────────────────────────────────────┐   │
│ │ Current game files:                            │   │
│ │                                                 │   │
│ │ === index.html ===                             │   │
│ │ <!DOCTYPE html>...                             │   │
│ │                                                 │   │
│ │ === game.js ===                                │   │
│ │ const app = new PIXI.Application...           │   │
│ │                                                 │   │
│ │ === style.css ===                              │   │
│ │ body { margin: 0; }...                         │   │
│ └─────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ FEEDBACK_CONTEXT_TEMPLATE.format()                     │
│                                                         │
│ Combines:                                               │
│ ├─ {project_context} = built context above            │
│ ├─ {user_prompt} = "Create a space shooter"           │
│ └─ {feedback} = "Add score counter"                   │
│                                                         │
│ Final prompt sent to agent:                            │
│ ┌─────────────────────────────────────────────────┐   │
│ │ Current game files:                            │   │
│ │ [all files content]                            │   │
│ │                                                 │   │
│ │ Use the tools to create or modify files as    │   │
│ │ needed.                                         │   │
│ │ Given original user request:                   │   │
│ │ Create a space shooter                         │   │
│ │ Implement solely the required changes         │   │
│ │ according to the user feedback:                │   │
│ │ Add score counter                              │   │
│ └─────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Agent receives prompt with full context                │
│ ├─ Understands original intent                         │
│ ├─ Sees current implementation                         │
│ ├─ Knows what user wants changed                       │
│ └─ Makes targeted modifications                        │
└─────────────────────────────────────────────────────────┘
```

## Key Benefits

### 1. **Complete Context**
- Agent has full visibility into original goal and current state
- No guessing about existing implementation
- Can make informed decisions about changes

### 2. **Targeted Changes**
- Agent can use `edit_file` for small changes
- Can use `write_file` for complete rewrites
- Preserves working functionality

### 3. **Consistency**
- Template ensures consistent format across all feedback iterations
- Easy to modify template in one place (`playbook.py`)
- Clear separation of concerns

### 4. **Traceability**
- Each iteration recorded in session.json
- Git commits track actual file changes
- Full history preserved

## Example: Complete Feedback Cycle

### Initial Creation
```python
# User: "Create a space shooter"
# Agent creates:
games/20251022_143052_a1b2c3d4/game/
  ├── index.html
  ├── game.js
  └── style.css
```

### First Feedback
```python
# User: "Add score counter"

# Project context built:
project_context = """
Current game files:

=== index.html ===
<!DOCTYPE html>
<html>
  <head>
    <script src="https://cdn...pixi.js"></script>
    <link rel="stylesheet" href="style.css">
  </head>
  <body>
    <script src="game.js"></script>
  </body>
</html>

=== game.js ===
const app = new PIXI.Application({...});
// existing game code
...

=== style.css ===
body { margin: 0; padding: 0; }
...
"""

# Final prompt to agent:
feedback_prompt = FEEDBACK_CONTEXT_TEMPLATE.format(
    project_context=project_context,
    user_prompt="Create a space shooter",
    feedback="Add score counter"
)

# Result:
"""
Current game files:
[all files content]

Use the tools to create or modify files as needed.
Given original user request:
Create a space shooter
Implement solely the required changes according to the user feedback:
Add score counter
"""
```

### Agent Response
```python
# Agent reads game.js, understands the structure
# Agent uses edit_file to add score tracking
# Agent uses edit_file to add score display
# Calls complete() when done
```

### Result
```python
# Updated files saved to same location
# Git commit: "Feedback iteration: Add score counter"
# session.json updated with iteration
```

## Customization

### Modifying Context Format

Edit `build_feedback_context()` in `main.py`:

```python
# Add file statistics
context_parts.append(f"Total files: {file_count}")
context_parts.append(f"Total lines: {total_lines}")

# Add git information
git_log = subprocess.check_output(["git", "log", "--oneline", "-5"], cwd=game_path)
context_parts.append(f"Recent commits:\n{git_log.decode()}")

# Add custom metadata
context_parts.append(f"Last modified: {session.last_modified}")
```

### Modifying Template

Edit `FEEDBACK_CONTEXT_TEMPLATE` in `playbook.py`:

```python
FEEDBACK_CONTEXT_TEMPLATE = """{project_context}

═══════════════════════════════════
Use the tools to create or modify files as needed.
═══════════════════════════════════

Original user request:
{user_prompt}

User feedback for changes:
{feedback}

INSTRUCTIONS:
1. Read and understand the current implementation
2. Make minimal, targeted changes
3. Preserve all existing functionality
4. Test your changes
5. Call complete() when done
"""
```

## Summary

The feedback context system provides a robust way to give the agent full context when modifying existing games:

1. **Template** (`playbook.py`): Defines the prompt structure
2. **Context Builder** (`main.py`): Gathers all relevant information
3. **Workflow** (`main.py`): Orchestrates the feedback cycle
4. **Agent** (`agent_graph.py`): Processes with feedback mode system prompt

This architecture ensures the agent always has complete information to make intelligent modifications while preserving the original intent and working functionality of the game.

