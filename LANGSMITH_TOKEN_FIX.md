# LangSmith Token Usage Fix

## Problem
LangSmith UI was showing 0 for token usage even though tokens were being consumed and logged to the console.

## Root Cause
When using custom API clients (Anthropic and Gemini) directly instead of through LangChain wrappers, the `@traceable` decorator cannot automatically extract token usage from API responses. LangSmith needs explicit token usage information to display it in the UI.

## Solution
Updated both `LLMClient` (Anthropic) and `VLMClient` (Gemini) to explicitly report token usage to LangSmith by:

1. Importing `get_current_run_tree()` from `langsmith.run_helpers`
2. Getting the current run tree within the `@traceable` decorated function
3. Updating the run tree's metadata with token usage in the format LangSmith UI expects

### Changes Made

#### `/Users/nikita/Programming/playable/src/llm_client.py`
- Added import: `from langsmith.run_helpers import get_current_run_tree`
- Added code after the API call to extract token usage from Anthropic's response
- Uses `run_tree.update_metadata()` with standard token usage fields (prompt_tokens, completion_tokens, total_tokens)
- Includes cache token information in total (cache_creation_input_tokens, cache_read_input_tokens)

#### `/Users/nikita/Programming/playable/src/vlm/client.py`
- Added import: `from langsmith.run_helpers import get_current_run_tree`
- Added code after the API call to extract token usage from Gemini's response
- Uses `run_tree.update_metadata()` with standard token usage fields (prompt_tokens, completion_tokens, total_tokens)

## Token Usage Format
The fix uses the standard OpenAI-compatible token format that LangSmith UI recognizes:
```python
{
    "prompt_tokens": <input tokens>,
    "completion_tokens": <output tokens>,
    "total_tokens": <total>
}
```

This is stored in the run tree's metadata using `run_tree.update_metadata()` which LangSmith UI reads to display token counts.

### Code Implementation
```python
# For Anthropic Claude
run_tree = get_current_run_tree()
if run_tree:
    run_tree.update_metadata({
        "prompt_tokens": total_input,
        "completion_tokens": usage.output_tokens,
        "total_tokens": total_input + usage.output_tokens
    })

# For Gemini
run_tree = get_current_run_tree()
if run_tree:
    run_tree.update_metadata({
        "prompt_tokens": usage_metadata.prompt_token_count,
        "completion_tokens": usage_metadata.candidates_token_count,
        "total_tokens": usage_metadata.total_token_count
    })
```

## Verification
To verify the fix is working:

1. Run your agent with LangSmith tracking enabled
2. Check the LangSmith UI dashboard
3. You should now see token usage displayed for both:
   - Claude API calls (under `claude_call` traces)
   - Gemini VLM calls (under `gemini_vlm_validation` traces)

## Technical Details

### Why This Approach?
- Using `get_current_run_tree()` allows us to access the current trace context
- We use `run_tree.update_metadata()` as recommended by LangSmith documentation
- We DON'T call `run_tree.end()` manually - the `@traceable` decorator handles that
- The approach is non-invasive and doesn't change the function's return value or behavior
- Follows the official LangSmith pattern for custom API client instrumentation

### Clean Implementation
The code is straightforward without error handling wrappers - it either works or fails clearly, making debugging easier.

## References
- LangSmith Documentation: https://docs.smith.langchain.com/
- LangSmith Run Helpers: https://api.python.langchain.com/en/latest/run_helpers/langsmith.run_helpers.html

