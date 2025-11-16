# Game Designer Asset Context - Moved to User Prompt

## Issue Found

The game designer LLM was receiving asset pack information in the **system prompt**, which was inconsistent with the architecture change we just made for the main agent (where we moved it to the user prompt).

Additionally, there was a redundancy: the `user_prompt` was being included in BOTH the system prompt template AND sent as a separate user message.

## Changes Made

### 1. **Cleaned Up System Prompt** (`prompts.py`)

**Removed dynamic placeholders:**
- ❌ `{asset_pack_info}` - removed from line 699
- ❌ `{sound_instructions}` - removed from line 763
- ❌ `{asset_instructions}` - removed from line 771
- ❌ `{user_prompt}` - removed from line 811

**Result:** `GAME_DESIGNER_PROMPT` is now pure instructions without task-specific data.

### 2. **Updated Game Designer Call** (`main.py`)

**Before:**
```python
# Format system prompt with everything
formatted_prompt = GAME_DESIGNER_PROMPT.format(
    asset_pack_info=asset_pack_info,
    asset_instructions=asset_instructions,
    sound_instructions=sound_instructions,
    user_prompt=user_prompt
)

response = llm_client.call(
    messages=[{"role": "user", "content": user_prompt}],  # Redundant!
    system=formatted_prompt
)
```

**After:**
```python
# Build user message with all task-specific context
user_message = f"""Here is the user's short game concept:

{user_prompt}

{asset_pack_info}

{asset_instructions}

{sound_instructions}"""

response = llm_client.call(
    messages=[{"role": "user", "content": user_message}],
    system=GAME_DESIGNER_PROMPT  # Pure instructions
)
```

## Benefits

### 1. **Architectural Consistency**
Both the game designer and main agent now follow the same pattern:
- **System Prompt**: Pure behavioral instructions
- **User Message**: Task description + asset context

### 2. **No Redundancy**
Eliminated duplicate user_prompt in both system and user messages.

### 3. **Better Separation of Concerns**
- System: "How to design games"
- User: "Design this specific game with these assets"

### 4. **More Maintainable**
Clearer code structure where task data flows through user messages.

## What the Game Designer Receives

### System Prompt (Pure Instructions):
```
You are a senior playable-ad game designer.
Transform the user's short concept into a concise, build-ready Mini-GDD...

[Output format specifications]
[Section guidelines]
[Examples]
```

### User Message (Task + Context):
```
Here is the user's short game concept:
simple racing game

Asset Pack Information:
You have access to the following asset pack: Racing Pack

Available assets:
- car_black_1.png (64x64px): Black racing car...
- rock1.png (32x32px): Small brown rock...
[... full asset list with descriptions ...]

IMPORTANT: When specifying assets in your GDD, you MUST use these exact asset filenames.
[... asset instructions ...]

[... sound pack info ...]
```

## Verification

✅ No linter errors  
✅ System prompt is pure instructions  
✅ User message contains all task-specific data  
✅ Consistent with main agent architecture  
✅ No redundant information

## Impact

**Breaking Changes:** None - the game designer receives the same information, just in the correct message type.

**Performance:** Potentially better token caching since system prompt is now static.

**Maintainability:** Much clearer what's system-level vs task-level context.

