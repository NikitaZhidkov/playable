"""
Playable validation prompt templates.
"""

PLAYABLE_VALIDATION_PROMPT = """Given the attached screenshot, decide where the playable code is correct and relevant to the original prompt. Keep in mind that the backend is currently not implemented, so you can only validate the frontend code and ignore the backend part.
Original prompt to generate this playable: {{ user_prompt }}.

Console logs from the browsers:
{{ console_logs }}

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
"""