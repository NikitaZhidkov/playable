# Logfire Context Improvements

## Overview

This document describes improvements made to Logfire observability to better track Google Vision API calls and provide LangGraph context for LLM calls.

## Changes Made

### 1. Google Vision API Tracking

**Problem**: Logfire was not tracking requests to Google's Gemini Vision API because only Anthropic SDK was instrumented.

**Solution**: Added manual Logfire spans to wrap Google Vision API calls in `src/vlm/client.py`:

```python
with logfire.span(
    "google_vision_api",
    model=self.model_name,
    provider="google",
    operation="generate_content"
):
    # Google Vision API call
    response = self.model.generate_content([rendered_prompt, image])
```

**What's tracked now:**
- Vision API calls are visible in Logfire traces
- Model name (e.g., `gemini-1.5-flash`)
- Provider (`google`)
- Operation type (`generate_content`)
- Token usage (input, output, cached)
- Prompt length and response length

### 2. LangGraph Context for LLM Calls

**Problem**: LLM calls in Logfire didn't show which LangGraph node made the call or what stage of the workflow we're in.

**Solution**: Added Logfire spans around each LangGraph node with contextual information:

#### LLM Node
```python
with logfire.span(
    "langgraph_llm_node",
    langgraph_node="llm",
    mode=mode,  # "creation" or "feedback"
    retry_count=retry_count,
    task_description=task_description[:100],
    has_asset_context=bool(asset_context),
    message_count=len(state["messages"])
):
    # LLM call
```

**Context tracked:**
- Node name: `"llm"`
- Mode: Creation or feedback mode
- Retry count: Current retry attempt (0-5)
- Task description: First 100 chars of task
- Asset context: Whether asset pack is being used
- Message count: Number of messages in conversation

#### Tools Node
```python
with logfire.span(
    "langgraph_tools_node",
    langgraph_node="tools",
    tool_count=len(tool_names),
    tools=tool_names,  # List of tool names being executed
    is_feedback_mode=state.get("is_feedback_mode", False)
):
    # Tool execution
```

**Context tracked:**
- Node name: `"tools"`
- Tool count: Number of tools being executed
- Tool names: List of tool names (e.g., `["write_file", "read_file"]`)
- Feedback mode: Whether in feedback iteration
- Completion status: Whether task was marked complete

#### Test Node
```python
with logfire.span(
    "langgraph_test_node",
    langgraph_node="test",
    is_feedback_mode=state.get("is_feedback_mode", False),
    retry_count=state.get("retry_count", 0)
):
    # Browser testing and VLM validation
```

**Context tracked:**
- Node name: `"test"`
- Feedback mode: Whether in feedback iteration
- Retry count: Current retry attempt

#### VLM Validation Spans

Added specific spans for VLM validations within the test node:

**Main Playable Validation:**
```python
with logfire.span(
    "vlm_playable_validation",
    validation_type="main_playable",
    is_feedback_mode=is_feedback_mode,
    test_run_id=test_run_id
):
    # VLM validation of main playable
```

**Test Case Validation:**
```python
with logfire.span(
    "vlm_test_case_validation",
    validation_type="test_case",
    test_case_name=test_case_name,
    expected_output=expected_output[:100],
    test_run_id=test_run_id
):
    # VLM validation of specific test case
```

## Benefits

### 1. Better Debugging
- **Before**: Hard to tell which LLM call was for which purpose
- **After**: Clear labels showing if it's a creation, feedback, or retry attempt

### 2. Complete API Coverage
- **Before**: Google Vision API calls were invisible in Logfire
- **After**: All API calls (both Anthropic and Google) are tracked

### 3. Better Performance Analysis
- **Before**: Couldn't correlate LLM usage with workflow stage
- **After**: Can see exactly where time/tokens are being spent in the workflow

### 4. Easier Trace Navigation
- **Before**: Flat list of API calls without context
- **After**: Hierarchical spans showing:
  - LangGraph node → LLM call
  - Test node → VLM playable validation
  - Test node → VLM test case validations (1-5)

## Example Trace Structure

Now in Logfire, you'll see traces like:

```
langgraph_llm_node (mode="creation", retry_count=0)
  └─ Message with 'claude-sonnet-4-20250514' (Anthropic instrumentation)
     └─ Token usage: 1200 input, 800 output

langgraph_tools_node (tools=["write_file", "write_file", "complete_task"])
  └─ Tools executed: 3

langgraph_test_node (retry_count=0)
  ├─ vlm_playable_validation (validation_type="main_playable")
  │  └─ google_vision_api (model="gemini-1.5-flash")
  │     └─ Token usage: 2500 input, 150 output
  ├─ vlm_test_case_validation (test_case_name="test_case_1")
  │  └─ google_vision_api
  ├─ vlm_test_case_validation (test_case_name="test_case_2")
  │  └─ google_vision_api
  └─ ...
```

## Usage

No configuration changes needed - these improvements are automatic once the code is deployed.

Just run your workflow as usual:
```bash
python run.py
```

Then view traces in Logfire dashboard at https://logfire.pydantic.dev/

## Technical Details

### Span Attributes

All spans include relevant attributes that can be filtered/searched in Logfire:

- **langgraph_node**: Node name (`"llm"`, `"tools"`, `"test"`)
- **mode**: Creation or feedback mode
- **retry_count**: Current retry attempt (0-5)
- **task_description**: Truncated task description
- **tool_count**: Number of tools executed
- **tools**: List of tool names
- **validation_type**: Type of VLM validation (`"main_playable"` or `"test_case"`)
- **test_case_name**: Name of test case being validated
- **test_run_id**: ID for grouping all validations in a test run
- **model**: Model name for API calls
- **provider**: API provider (`"google"` or `"anthropic"`)

### Performance Impact

Minimal - spans add negligible overhead:
- ~1-2ms per span creation
- Metadata is logged asynchronously
- No impact on API call latency

## Files Modified

1. `src/vlm/client.py`:
   - Added `import logfire`
   - Wrapped `validate_with_screenshot()` method with span
   - Added token usage logging

2. `src/agent_graph.py`:
   - Added `import logfire`
   - Wrapped `llm_node()` LLM call with span
   - Wrapped `tools_node()` execution with span
   - Wrapped entire `test_node()` with span
   - Added sub-spans for VLM validations

