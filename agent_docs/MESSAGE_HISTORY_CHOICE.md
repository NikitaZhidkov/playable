# User Choice for Message History

## Overview

When providing feedback on an existing game, you now have the **choice** whether to:
1. **Continue with message history** - Agent remembers all previous conversations
2. **Start fresh** - Agent reads files from scratch, no memory of previous iterations

## The Logic

### 1. New Game Creation
- **Always starts fresh** (no previous history exists)
- First iteration of the conversation
- No choice needed

### 2. Providing Feedback in Same Session
- If you just created a game and immediately provide feedback
- System asks: Continue with history or start fresh?
- You choose based on your needs

### 3. Loading an Existing Session
- When you select an existing session to continue
- System checks if message history exists
- If history found: Asks whether to use it or start fresh
- If no history: Automatically starts fresh (fallback for old sessions)

## When to Choose Each Option

### ✅ Continue with Message History (Recommended Default)

**Use when:**
- The conversation is going well
- You want the agent to remember previous decisions
- You're making incremental improvements
- The agent's previous work was good
- You want consistent coding patterns

**Example:**
```
Iteration 1: Created a platformer game ✓
Iteration 2: Added enemies ✓
Iteration 3: Add power-ups
→ Choose: Continue (agent remembers game structure and enemy system)
```

### 🔄 Start Fresh

**Use when:**
- Conversation got off track or messy
- Message history is very long and causing issues
- You want a completely different approach
- Previous iterations made mistakes you want forgotten
- You're changing direction significantly

**Example:**
```
Iteration 1: Created a platformer game ✓
Iteration 2: Added complex physics system (got messy)
Iteration 3: Add enemies
→ Choose: Start fresh (agent forgets the messy physics attempt, reads clean code)
```

## User Interface Flow

### When You Continue/Load a Session:

```
📋 Session ID: 20251025_120000_abc123
📝 Original task: Create a space invaders game

📝 Found 45 messages from previous iterations.

Message history options:
  (c) Continue with message history (agent remembers previous conversation)
  (f) Start fresh (agent reads files from scratch, no memory of previous iterations)

Your choice [c/f] (default: c): 
```

**If you press Enter or type 'c':**
```
💬 Will continue with message history

What would you like to change or add?
Your feedback: Add a score multiplier
```
→ Agent sees all 45 previous messages + your new feedback

**If you type 'f':**
```
🔄 Will start fresh without message history

What would you like to change or add?
Your feedback: Add a score multiplier
```
→ Agent reads all game files but doesn't see previous message history

## What Happens Behind the Scenes

### Continue with History (c)
```python
# Loads previous messages
previous_messages = session.get_langchain_messages()
# Result: [message1, message2, ..., message45]

# Appends your new feedback
messages = previous_messages + [HumanMessage(feedback)]
# Result: [message1, message2, ..., message45, new_feedback]

# Agent sees full conversation history
```

### Start Fresh (f)
```python
# Builds context from scratch
project_context = build_feedback_context(session, game_path)
# Reads all files: game.js, index.html, style.css, etc.

# Creates new message with full context
messages = [HumanMessage(project_context + feedback)]
# Result: [single_message_with_all_files + feedback]

# Agent sees files but no conversation history
```

## Practical Examples

### Example 1: Successful Iteration

```
User: Creates "space invaders game"
Agent: ✓ Creates game

User: "Add power-ups" (Continues with history)
Agent: "I remember creating the game with enemies and player.
        I'll add power-ups to the existing system"
✓ Adds power-ups smoothly

User: "Make enemies faster" (Continues with history)
Agent: "I'll increase the enemy speed I implemented before"
✓ Updates enemy speed
```

### Example 2: Starting Fresh After Issues

```
User: Creates "platformer game"
Agent: ✓ Creates game

User: "Add double jump" (Continues with history)
Agent: Attempts double jump but creates buggy implementation
❌ Bugs introduced

User: Fixes manually, commits to git

User: "Add enemies" (Starts fresh)
Agent: Reads the clean, fixed code from files
       Doesn't remember the buggy double jump attempts
✓ Adds enemies to clean codebase
```

### Example 3: Long Session

```
After 10 iterations (100+ messages):

User: "Add new feature"
Options:
  (c) Continue - Agent sees all 100+ messages (might be slow/confusing)
  (f) Start fresh - Agent reads current clean files (faster, clearer)

Choose based on whether the long history is helpful or cluttering
```

## Benefits of User Choice

### 1. **Flexibility**
- You control when to use history and when to start fresh
- Adapt to different situations

### 2. **Recovery from Issues**
- If conversation went wrong, start fresh
- Don't get stuck with bad history

### 3. **Performance Control**
- Very long histories can be reset
- Keep context manageable

### 4. **Different Approaches**
- Continue: Incremental, consistent changes
- Fresh: Bold new directions, clean slate

## Technical Implementation

### Function Signature
```python
async def run_feedback_workflow(
    client: dagger.Client,
    session: Session,
    feedback: str,
    use_message_history: bool = True  # Default to continuing
) -> Session:
```

### Logic Flow
```python
if use_message_history:
    # Try to load history
    previous_messages = session.get_langchain_messages()
    
    if previous_messages:
        # Continue with history
        messages = previous_messages + [new_feedback]
    else:
        # No history available, fall back to fresh
        messages = [build_full_context() + new_feedback]
else:
    # User chose fresh
    messages = [build_full_context() + new_feedback]
```

### User Prompt
```python
if previous_messages:
    print(f"📝 Found {len(previous_messages)} messages from previous iterations.")
    print()
    print("Message history options:")
    print("  (c) Continue with message history")
    print("  (f) Start fresh")
    print()
    choice = input("Your choice [c/f] (default: c): ").strip().lower()
    
    use_history = (choice != 'f')  # Default to continue unless 'f'
```

## Default Behavior

- **Default choice**: Continue with history (press Enter or type 'c')
- **Rationale**: Most users want continuity by default
- **Easy override**: Type 'f' to start fresh when needed

## Backward Compatibility

- Old sessions without message history: Automatically start fresh
- No prompt shown if no history exists
- Graceful fallback ensures nothing breaks

## Best Practices

### ✅ Do:
- Use "continue" for normal incremental development
- Use "fresh" when conversation got messy
- Use "fresh" after manual fixes to forget bad attempts
- Use "fresh" for significantly different approaches

### ❌ Avoid:
- Starting fresh unnecessarily (loses valuable context)
- Continuing with extremely long histories that cause issues
- Continuing after the agent made repeated mistakes

## Summary

This feature gives you **full control** over conversation continuity:

- **New games**: Always fresh (no choice needed)
- **Feedback**: You choose - continue or fresh
- **Default**: Continue (most common case)
- **Override**: Easy to start fresh when needed

You decide when the agent's memory helps and when a clean slate is better! 🎯

