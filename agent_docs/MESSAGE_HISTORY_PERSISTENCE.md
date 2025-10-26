# Message History Persistence

## Problem

Previously, when providing feedback on a game, the system would **start a fresh conversation** each time. This caused several issues:

1. **Loss of Context**: The LLM didn't remember what it did in previous iterations
2. **Repeated Mistakes**: Without conversation history, the same errors could recur
3. **Inefficiency**: The LLM had to re-understand the entire codebase each time
4. **Inconsistency**: Changes could conflict with previous decisions

**Example Before:**
```
Session 1: Create game → [Messages saved nowhere]
Session 2: Add feature → [Started from scratch, no memory of Session 1]
Session 3: Fix bug → [Started from scratch, no memory of Sessions 1-2]
```

## Solution

Now the system **preserves the entire message history** across feedback iterations. When you provide feedback, the LLM sees:
- All previous user requests
- All previous LLM responses
- All tool calls and their results
- The complete conversation thread

**Example After:**
```
Session 1: Create game → [Messages saved]
Session 2: Add feature → [Continues from Session 1 messages] → [Messages updated]
Session 3: Fix bug → [Continues from Sessions 1-2 messages] → [Messages updated]
```

## How It Works

### 1. Message Storage (session.py)

```python
class Session:
    def __init__(self, ..., message_history: list[dict] = None):
        self.message_history = message_history or []
    
    def set_message_history(self, messages: list):
        """Save LangChain messages to JSON-serializable format"""
        # Converts HumanMessage, AIMessage, ToolMessage → dict
    
    def get_langchain_messages(self) -> list:
        """Load messages back as LangChain objects"""
        # Converts dict → HumanMessage, AIMessage, ToolMessage
```

### 2. Saving After Workflows (main.py)

After each workflow completion (create or feedback):

```python
# Save message history for future feedback iterations
session.set_message_history(final_state["messages"])
save_session(session)
logger.info(f"Saved {len(final_state['messages'])} messages to session history")
```

### 3. Loading in Feedback Mode (main.py)

When continuing a session with feedback:

```python
# Load previous message history to continue the conversation
previous_messages = session.get_langchain_messages()

if previous_messages:
    # Append new feedback message to existing conversation
    feedback_prompt = f"""User Feedback:
{feedback}

Please implement the requested changes."""
    
    messages = previous_messages + [HumanMessage(content=feedback_prompt)]
else:
    # Fallback for old sessions without message history
    messages = [HumanMessage(content=full_context_prompt)]
```

## Benefits

### 1. **Continuity**
The LLM maintains context across iterations:
```
User: "Create a space invaders game"
LLM: "I've created the game with enemies and a player ship"

User: "Make the enemies move faster"
LLM: "I'll increase the enemy speed in the existing game logic" 
      ↑ Remembers the game structure it created
```

### 2. **Consistency**
The LLM remembers its previous decisions:
```
Iteration 1: LLM uses specific variable names (playerSpeed, enemySpeed)
Iteration 2: LLM continues using the same naming convention
              ↑ Maintains consistency instead of switching to different names
```

### 3. **Efficiency**
No need to rebuild context from scratch:
```
Before: "Here are all the game files: [thousands of lines]..."
After:  "Please make the enemies faster"
         ↑ LLM already knows the codebase from previous messages
```

### 4. **Better Error Recovery**
The LLM can learn from mistakes:
```
Iteration 1: Tries approach A → Fails
Iteration 2: Sees the failure in history → Tries approach B
              ↑ Learns from the conversation history
```

## Message Structure

Messages are stored in JSON format in `games/<session_id>/session.json`:

```json
{
  "session_id": "20251025_120000_abc123",
  "initial_prompt": "Create a platformer game",
  "message_history": [
    {
      "type": "HumanMessage",
      "content": "Create a platformer game with jumping"
    },
    {
      "type": "AIMessage",
      "content": "I'll create the game with PIXI.js...",
      "tool_calls": [
        {
          "name": "write_file",
          "args": {"path": "game.js", "content": "..."},
          "id": "call_123"
        }
      ]
    },
    {
      "type": "ToolMessage",
      "content": "success",
      "tool_call_id": "call_123"
    },
    ...
  ]
}
```

## Backward Compatibility

The system handles old sessions without message history gracefully:

```python
if previous_messages:
    # New behavior: Continue from previous messages
    messages = previous_messages + [new_feedback]
else:
    # Old behavior: Build full context (for old sessions)
    messages = [full_context_with_all_files]
```

This ensures old sessions still work while new sessions benefit from message persistence.

## Technical Details

### Message Serialization

LangChain messages are converted to JSON-serializable dictionaries:

```python
# Original LangChain Message
AIMessage(
    content="I'll create the game",
    tool_calls=[{"name": "write_file", "args": {...}, "id": "call_1"}]
)

# Serialized to:
{
    "type": "AIMessage",
    "content": "I'll create the game",
    "tool_calls": [{"name": "write_file", "args": {...}, "id": "call_1"}]
}
```

### Message Deserialization

Dictionaries are converted back to LangChain messages:

```python
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

if msg_type == "HumanMessage":
    return HumanMessage(content=content)
elif msg_type == "AIMessage":
    return AIMessage(content=content, tool_calls=tool_calls)
elif msg_type == "ToolMessage":
    return ToolMessage(content=content, tool_call_id=tool_call_id)
```

## Example Flow

### Initial Game Creation

```
User: "Create a space invaders game"

Messages after completion:
[
  HumanMessage("Create a space invaders game"),
  AIMessage("I'll create the game...", tool_calls=[write_file(...)]),
  ToolMessage("success"),
  AIMessage("I've created the game..."),
  ... (validation messages, test case creation, etc.)
]

→ Saved to session.json
```

### First Feedback Iteration

```
User: "Make the enemies faster"

Loaded messages: [all messages from creation]
New message: HumanMessage("Make the enemies faster")

Combined messages:
[
  ... (all previous messages),
  HumanMessage("Make the enemies faster")
]

→ LLM sees full context and knows what to modify

Messages after completion:
[
  ... (all previous messages),
  HumanMessage("Make the enemies faster"),
  AIMessage("I'll increase the enemy speed...", tool_calls=[...]),
  ToolMessage("success"),
  ... (new validation messages)
]

→ Updated in session.json
```

### Second Feedback Iteration

```
User: "Add a score display"

Loaded messages: [all messages from creation + first feedback]
New message: HumanMessage("Add a score display")

Combined messages:
[
  ... (all previous messages from creation and first feedback),
  HumanMessage("Add a score display")
]

→ LLM has complete history of all changes made

→ Updated in session.json after completion
```

## Storage Impact

Message history is stored in `session.json` which grows with each iteration:

- **Initial creation**: ~5-20 messages (~10-50 KB)
- **After 3 feedback iterations**: ~20-80 messages (~50-200 KB)
- **After 10 feedback iterations**: ~50-200 messages (~100-500 KB)

This is negligible compared to game files and is essential for maintaining conversation continuity.

## Testing

To verify message history works:

```bash
# Run the application
python main.py

# 1. Create a new game
# 2. Note what the LLM creates
# 3. Provide feedback that references previous work
# 4. Observe that the LLM understands context without re-reading all files
```

**Expected behavior:**
- First feedback: LLM remembers what it created
- Second feedback: LLM remembers both creation and first feedback
- Nth feedback: LLM has complete conversation history

## Summary

This change transforms the system from having **no memory** between iterations to having **complete conversation memory**, enabling:

- ✅ Continuous conversation flow
- ✅ Consistent code changes
- ✅ Learning from previous iterations
- ✅ Better understanding of user intent
- ✅ More efficient feedback loops

The LLM now truly continues the conversation instead of starting over each time!

