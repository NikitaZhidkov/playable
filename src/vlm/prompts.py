"""
VLM validation prompt templates.
"""

# ============================================================================
# VLM Validation Prompts
# ============================================================================

VLM_PLAYABLE_VALIDATION_PROMPT = """Given the attached screenshot, decide where the playable code is correct and relevant to the original prompt. Keep in mind that the backend is currently not implemented, so you can only validate the frontend code and ignore the backend part.

{% if is_feedback_mode %}
**FEEDBACK ITERATION MODE**

This is a feedback iteration on an existing game.

Original prompt that created this game: {{ original_prompt }}

Current feedback being applied: {{ user_prompt }}

IMPORTANT: Since this is a feedback iteration adding/modifying specific features, the new feature might not be fully visible in the main game view yet. Focus on validating that:
1. The game still loads without critical errors
2. No breaking changes were introduced
3. The core game functionality remains intact

The specific feature requested in the feedback will be validated separately through dedicated test cases. Therefore, if the main game looks functional and has no errors, you can approve it even if the specific feedback feature isn't prominently visible yet.
{% else %}
Original prompt to generate this playable: {{ user_prompt }}.
{% endif %}

Console logs from the browsers:
{{ console_logs }}

{IGNORE_WARNINGS}

Answer "yes" or "no" wrapped in <answer> tag. Explain error in logs if it exists. Follow the example below.

Example 1:
<reason>the playable looks valid</reason>
<answer>yes</answer>

Example 2:
<reason>there is nothing on the screenshot, rendering issue caused by unhandled empty collection in the react component</reason>
<answer>no</answer>

Example 3:
<reason>the playable looks okay, but displays database connection error. Given it is not playable-related, I should answer yes</reason>
<answer>yes</answer>

Example 4:
<reason>the playable looks good and works correctly. The WebGL performance warnings in the logs are normal browser behavior and can be ignored</reason>
<answer>yes</answer>

{% if is_feedback_mode %}
Example 5 (Feedback Mode):
<reason>This is a feedback iteration adding a score counter. The game loads correctly without errors and the core gameplay is intact. The score counter feature will be validated in dedicated test cases, so the main validation passes.</reason>
<answer>yes</answer>
{% endif %}
"""

VLM_TEST_CASE_VALIDATION_PROMPT = """You are validating a specific game state loaded from a test case.

The game has loaded a test case with the following expected output:
{{ expected_output }}

Your task is to compare the screenshot with the expected output description and determine if they match.

IMPORTANT:
- Focus ONLY on visual correctness - does what you see match the expected output?
- The game has already passed basic validation (no JavaScript errors)
- Ignore console logs - they were validated in the main test
- Be strict but reasonable - minor visual differences are OK if the core state matches

Answer "yes" if the screenshot matches the expected output, "no" if it doesn't.

Example 1:
<reason>The screenshot shows the player at the expected position with score 0 and no enemies, exactly as described</reason>
<answer>yes</answer>

Example 2:
<reason>Expected to see score 100 but screenshot shows score 0, the game state wasn't loaded correctly</reason>
<answer>no</answer>

Example 3:
<reason>Expected player at position (100, 200) but player appears to be at a different location on screen</reason>
<answer>no</answer>
"""

