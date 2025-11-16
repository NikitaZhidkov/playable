# Asset Context Moved to User Prompt

## Overview

Asset and sound pack descriptions are now included in the **user prompt** instead of the **system prompt**. This is a better architectural design that separates system-level instructions from task-specific data.

## Changes Made

### 1. **Removed from System Prompt** (`agent_graph.py`)

**Before:**
```python
# System prompt with asset context injected
if asset_context:
    asset_instructions = ASSET_PACK_INSTRUCTIONS.format(asset_context=asset_context)
    system_prompt = system_prompt + "\n\n" + asset_instructions

if sound_context:
    sound_instructions = SOUND_PACK_INSTRUCTIONS.format(sound_context=sound_context)
    system_prompt = system_prompt + "\n\n" + sound_instructions
```

**After:**
```python
# Asset and sound pack context are now added to user messages, not system prompt
# This keeps system prompt focused on instructions, user prompt focused on task data
```

### 2. **Added to Initial User Message** (`main.py` - Creation Mode)

**Location:** Initial game creation prompt

```python
initial_prompt = f"""TASK:
Implement the following game design:

{game_designer_output}

Please create a complete, working pixi.js game..."""

# Add asset pack information to user prompt (not system prompt)
if asset_context:
    asset_instructions = ASSET_PACK_INSTRUCTIONS.format(asset_context=asset_context)
    initial_prompt += f"\n\n{asset_instructions}"

# Add sound pack information to user prompt (not system prompt)
if sound_context:
    sound_instructions = SOUND_PACK_INSTRUCTIONS.format(sound_context=sound_context)
    initial_prompt += f"\n\n{sound_instructions}"
```

### 3. **Added to Feedback Messages** (`main.py` - Feedback Mode)

Asset/sound pack context is now appended to feedback messages in **all three feedback scenarios**:

#### A. Continuing with message history:
```python
feedback_prompt = f"""User Feedback:
{feedback}

Please implement the requested changes..."""

# Add asset/sound pack info to feedback (in user prompt, not system prompt)
if asset_context:
    asset_instructions = ASSET_PACK_INSTRUCTIONS.format(asset_context=asset_context)
    feedback_prompt += f"\n\n{asset_instructions}"

if sound_context:
    sound_instructions = SOUND_PACK_INSTRUCTIONS.format(sound_context=sound_context)
    feedback_prompt += f"\n\n{sound_instructions}"
```

#### B. No message history (building context from scratch):
Same pattern - asset/sound context appended to `FEEDBACK_CONTEXT_TEMPLATE`

#### C. User chose to start fresh:
Same pattern - asset/sound context appended to feedback prompt

## Benefits

### 1. **Better Separation of Concerns**
- **System Prompt**: Defines agent behavior, capabilities, and rules
- **User Prompt**: Contains task-specific data and context

### 2. **More Flexible**
- Asset information can change per conversation
- System prompt remains constant and focused on core instructions

### 3. **Clearer Architecture**
- Easier to understand what's persistent (system) vs. task-specific (user)
- Follows LLM best practices for prompt engineering

### 4. **Better Token Usage**
- System prompt is cached by the LLM provider
- Task-specific data in user messages doesn't bloat the cached system prompt

## Technical Details

### Files Modified
1. `src/agent_graph.py`
   - Removed asset/sound context injection from system prompt
   - Removed `ASSET_PACK_INSTRUCTIONS` from imports
   - Updated logfire span to use `state.get("asset_context")`

2. `src/main.py`
   - Added `ASSET_PACK_INSTRUCTIONS` and `SOUND_PACK_INSTRUCTIONS` to imports
   - Appended asset/sound context to initial creation prompt
   - Appended asset/sound context to all feedback prompts (3 code paths)

### State Tracking
Asset and sound context remain in the agent state for tracking purposes:
```python
initial_state = {
    "messages": [...],
    "asset_context": asset_context,  # Keep in state for tracking
    "sound_context": sound_context   # Keep in state for tracking
    ...
}
```

## What the Agent Sees Now

### Before (System Prompt):
```
SYSTEM: You are a PixiJS game developer...
[CDN instructions]
[Asset pack instructions with all asset names and descriptions]  ← Fixed for all messages
[Sound pack instructions with all sound names and descriptions]  ← Fixed for all messages
```

### After (User Message):
```
SYSTEM: You are a PixiJS game developer...
[CDN instructions]  ← Clean, focused system prompt

USER: Implement this game design: [GDD]
[Asset pack instructions with all asset names and descriptions]  ← Task-specific data
[Sound pack instructions with all sound names and descriptions]  ← Task-specific data
```

## Verification

✅ No linter errors  
✅ All three feedback paths updated  
✅ Creation mode updated  
✅ Imports optimized  
✅ State tracking preserved

## Migration Notes

No breaking changes. The agent receives the same information, just in a different part of the message structure. This is transparent to the LLM and follows best practices for prompt engineering.

