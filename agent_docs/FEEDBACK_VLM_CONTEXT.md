# Feedback-Aware VLM Validation

## Problem

During feedback iterations, the VLM (Vision Language Model) validation could incorrectly fail when:

1. **New features aren't immediately visible**: User requests "Add a score counter" but it might not be prominently displayed in the main game view
2. **Missing context**: VLM doesn't know this is a feedback iteration, so it validates as if it's a brand new game
3. **Overly strict validation**: VLM might reject the game because it doesn't see the new feature, even though it will be validated in test cases

**Example Problem:**
```
User creates: "Space invaders game"
VLM validates: ✅ Pass (sees enemies, player, gameplay)

User feedback: "Add a score counter in top-right"
VLM validates: ❌ Fail (doesn't see score counter prominently, rejects game)

BUT: Score counter exists and would pass test case validation
```

## Solution

The VLM validation prompt now **adapts based on whether it's initial creation or a feedback iteration**:

### Creation Mode (Original Behavior)
- Validates that the game matches the original prompt
- Expects to see all requested features
- Strict validation of what was asked for

### Feedback Mode (New Behavior)
- Shows the original game creation prompt
- Shows the current feedback being applied
- Explains that new features might not be fully visible yet
- Focuses on:
  1. Game still loads without critical errors
  2. No breaking changes were introduced
  3. Core game functionality remains intact
- Notes that specific features will be validated in test cases

## Implementation

### 1. Updated VLM Prompt Template (`playbook.py`)

```python
VLM_PLAYABLE_VALIDATION_PROMPT = """
{% if is_feedback_mode %}
**FEEDBACK ITERATION MODE**

This is a feedback iteration on an existing game.

Original prompt that created this game: {{ original_prompt }}

Current feedback being applied: {{ user_prompt }}

IMPORTANT: Since this is a feedback iteration adding/modifying specific features, 
the new feature might not be fully visible in the main game view yet. Focus on:
1. The game still loads without critical errors
2. No breaking changes were introduced
3. The core game functionality remains intact

The specific feature requested in the feedback will be validated separately through 
dedicated test cases.
{% else %}
Original prompt to generate this playable: {{ user_prompt }}.
{% endif %}

... (rest of validation prompt)
"""
```

### 2. Enhanced Function Signature (`vlm_utils.py`)

```python
def validate_playable_with_vlm(
    vlm_client,
    screenshot_bytes: bytes,
    console_logs: list[str],
    user_prompt: str,
    template_str: str,
    session_id: str = None,
    is_feedback_mode: bool = False,      # NEW
    original_prompt: str = None          # NEW
) -> Tuple[bool, str]:
```

### 3. Template Rendering with Context

```python
from jinja2 import Template

template = Template(template_str)
rendered_prompt = template.render(
    user_prompt=user_prompt,
    console_logs=formatted_logs,
    is_feedback_mode=is_feedback_mode,
    original_prompt=original_prompt or user_prompt
)
```

### 4. State Management (`agent_state.py`)

Added `original_prompt` field to track the initial game creation prompt:

```python
class AgentState(MessagesState):
    ...
    is_feedback_mode: bool
    original_prompt: str  # Original game creation prompt
```

### 5. Workflow Integration (`main.py`)

**Creation Mode:**
```python
initial_state = {
    "task_description": task_description,
    "is_feedback_mode": False,
    "original_prompt": task_description  # Same as current task
}
```

**Feedback Mode:**
```python
initial_state = {
    "task_description": feedback,
    "is_feedback_mode": True,
    "original_prompt": session.initial_prompt  # Keep original prompt
}
```

### 6. VLM Call with Context (`agent_graph.py`)

```python
is_feedback_mode = state.get("is_feedback_mode", False)
is_valid, reason = validate_playable_with_vlm(
    vlm_client=vlm_client,
    screenshot_bytes=test_result.screenshot_bytes,
    console_logs=test_result.console_logs,
    user_prompt=state.get("task_description", ""),
    template_str=VLM_PLAYABLE_VALIDATION_PROMPT,
    session_id=state.get("session_id"),
    is_feedback_mode=is_feedback_mode,
    original_prompt=state.get("original_prompt", "") if is_feedback_mode else None
)
```

## Benefits

### 1. **Smarter Validation in Feedback Mode**

Before:
```
Feedback: "Add score counter"
VLM: ❌ "I don't see a score counter, failing validation"
Result: False negative, wasted retry
```

After:
```
Feedback: "Add score counter"
VLM: ✅ "This is feedback adding a score counter. Game loads fine, no errors.
         The score feature will be validated in test cases. Passing main validation."
Result: Correct validation, continues to test cases
```

### 2. **Clearer Context for VLM**

The VLM now understands:
- What the game was originally created for
- What specific change is being made
- That it should focus on stability, not feature completeness

### 3. **Separation of Concerns**

- **Main validation**: Game loads, no critical errors, core functionality intact
- **Test case validation**: Specific features work as expected

### 4. **Fewer False Failures**

Reduces retry loops caused by VLM being overly strict during feedback iterations.

## Example Scenarios

### Scenario 1: Adding UI Element

```
Original: "Create a platformer game with jumping"
Feedback: "Add a pause button in top-left corner"

VLM in Creation Mode (if this were initial):
- Expects to see platformer gameplay
- Expects jumping mechanics visible
- Expects pause button
- ❌ Might fail if pause button not prominent

VLM in Feedback Mode (actual):
- Sees this is adding a pause button to existing game
- Validates: game loads ✅, no errors ✅, core gameplay intact ✅
- Passes main validation
- Pause button tested specifically in test cases
```

### Scenario 2: Modifying Game Logic

```
Original: "Create a memory card matching game"
Feedback: "Make cards flip faster"

VLM in Feedback Mode:
- Original game: memory card matching
- Feedback: faster flip animation
- Validates: game loads ✅, cards visible ✅, no errors ✅
- Passes (speed change validated in test cases)
```

### Scenario 3: Adding Game Feature

```
Original: "Create snake game"
Feedback: "Add power-ups that make snake move faster"

VLM in Feedback Mode:
- Original game: snake game
- Feedback: adding power-ups
- Validates: snake game still works ✅, no errors ✅
- Passes (power-up functionality tested in test cases)
- Note: Power-up might not even be visible in main screenshot if not spawned yet
```

## Prompt Examples

### Creation Mode Prompt

```
Given the attached screenshot, decide where the playable code is correct and 
relevant to the original prompt.

Original prompt to generate this playable: Create a space invaders game.

Console logs from the browsers:
[INFO] Game initialized
...
```

### Feedback Mode Prompt

```
Given the attached screenshot, decide where the playable code is correct and 
relevant to the original prompt.

**FEEDBACK ITERATION MODE**

This is a feedback iteration on an existing game.

Original prompt that created this game: Create a space invaders game

Current feedback being applied: Add a score counter in the top-right corner

IMPORTANT: Since this is a feedback iteration adding/modifying specific features,
the new feature might not be fully visible in the main game view yet. Focus on:
1. The game still loads without critical errors
2. No breaking changes were introduced  
3. The core game functionality remains intact

The specific feature requested in the feedback will be validated separately through
dedicated test cases. Therefore, if the main game looks functional and has no 
critical errors, you can approve it even if the specific feedback feature isn't 
prominently visible yet.

Console logs from the browsers:
[INFO] Game initialized
[INFO] Score system added
...
```

## Testing

To verify this works:

1. Create a game: "Create a simple platformer"
2. VLM validates in creation mode
3. Provide feedback: "Add collectible coins"
4. VLM validates in feedback mode with context
5. Observe that VLM is more lenient about coin visibility but still validates game stability

## Technical Details

### Jinja2 Template Conditionals

The prompt uses Jinja2 `{% if %}` blocks to conditionally render different content:

```jinja2
{% if is_feedback_mode %}
  ... feedback-specific instructions ...
{% else %}
  ... creation-specific instructions ...
{% endif %}
```

### Backward Compatibility

- `is_feedback_mode` defaults to `False`
- `original_prompt` defaults to `None` (falls back to `user_prompt`)
- Old tests continue to work without changes

## Summary

This enhancement makes VLM validation **context-aware**, reducing false failures during feedback iterations while maintaining strict validation for initial game creation. The VLM now understands the difference between:

- ✅ **Creation**: "Build this from scratch" → Strict validation of all features
- ✅ **Feedback**: "Add this feature" → Focus on stability, delegate feature testing to test cases

Result: Fewer wasted retries, better validation flow, clearer VLM reasoning! 🎉

