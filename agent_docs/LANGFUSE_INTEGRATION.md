# Langfuse Integration

This document describes the comprehensive Langfuse observability integration in the Playable Agent project.

**Using Langfuse 3.8.1** - Latest version with modern API

## Overview

Langfuse is integrated throughout the codebase to provide:
- **Token tracking** for both Claude (Anthropic) and Gemini models
- **Cost tracking** with accurate pricing calculations
- **Full trace hierarchy** from session workflows down to individual LLM calls
- **Metadata and tags** for filtering and analysis
- **Multi-modal support** tracking both text and image inputs

## Setup

### 1. Get Langfuse API Keys

Sign up at https://cloud.langfuse.com/ and get your API keys from the project settings.

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Langfuse for LLM observability and token tracking
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Start Using

Once configured, Langfuse will automatically track all LLM interactions!

## What We Track

### 1. Token Usage (Input/Output/Total)

#### Claude (Anthropic)
- **Model**: claude-3-5-sonnet-20241022
- **Tracked**: 
  - Input tokens
  - Output tokens
  - Total tokens
  - Cache creation tokens (when available)
  - Cache read tokens (when available)
- **Cost Tracking**: Disabled - Langfuse can calculate costs if you configure model pricing

#### Gemini (Google)
- **Model**: gemini-1.5-flash
- **Tracked**: 
  - Input tokens (prompt)
  - Output tokens (candidates)
  - Total tokens
  - Cached content tokens (when available)
- **Cost Tracking**: Disabled - Langfuse can calculate costs if you configure model pricing

> **Note**: We only track token counts, not costs. This ensures accuracy since cache pricing can vary. If you need cost tracking, configure model pricing in Langfuse dashboard.

### 2. Trace Hierarchy

```
Session Workflow (new_game_workflow or feedback_workflow)
├── llm_node (multiple calls)
│   └── llm_client.call (generation)
│       ├── Input tokens
│       ├── Output tokens
│       └── Cache tokens (if available)
├── tools_node
│   └── Tool executions
└── test_node
    └── VLM validation
        └── vlm_client.validate_with_screenshot (generation)
            ├── Input tokens
            ├── Output tokens
            └── Cached tokens (if available)
```

### 3. Session Metadata

#### New Game Workflow
- `session_id`: Unique identifier for the game session
- `task_description`: User's game creation prompt
- `has_asset_pack`: Whether assets are used
- `asset_pack`: Name of selected asset pack
- `final_status`: completed/failed/interrupted
- `message_count`: Total messages in conversation
- `retry_count`: Number of validation retries

#### Feedback Workflow
- `session_id`: Continuing session ID
- `original_prompt`: Original game creation prompt
- `feedback`: User's feedback for this iteration
- `use_message_history`: Whether continuing from previous messages
- `continue_from_state`: Whether restoring from crashed state
- `has_asset_pack`: Whether assets are used
- `previous_status`: Status before feedback
- `final_status`: Status after feedback
- `feedback_applied`: The feedback text

### 4. Tags

Tags help filter traces in Langfuse:

- **Workflow level**: `new_game`, `feedback`, `creation`, `iteration`
- **Node level**: `creation`, `feedback`, `retry_0`, `retry_1`, etc.

### 5. Metadata Per LLM Call

#### Claude Calls
```python
{
    "system_prompt_length": 1234,
    "num_tools": 5,
    "max_tokens": 8000,
    "provider": "anthropic",
    "conversation_length": 12,
    "stop_reason": "end_turn",
    "model": "claude-3-5-sonnet-20241022",
    "has_tool_calls": true
}
```

#### Gemini Calls
```python
{
    "has_image": true,
    "console_logs_length": 450,
    "user_prompt_length": 120,
    "provider": "google",
    "includes_image": true,
    "image_cost": 0.00001315625
}
```

#### LLM Node Metadata
```python
{
    "mode": "creation" | "feedback",
    "retry_count": 2,
    "has_asset_context": true,
    "message_count": 15,
    "session_id": "20251026_123456_abcd1234"
}
```

## Viewing Data in Langfuse

### 1. Dashboard
- View total costs across all sessions
- Track token usage trends
- Monitor success/failure rates

### 2. Traces
- See complete execution flow for each game session
- Drill down into individual LLM calls
- View input/output for debugging

### 3. Sessions
- All traces for a game session are grouped by `session_id`
- Track multiple feedback iterations
- Analyze retry patterns

### 4. Cost Analysis
- Filter by tags: `new_game`, `feedback`
- Compare costs between creation and iteration
- Track VLM validation costs separately

## Token Tracking (No Cost Calculation)

### What We Track

We follow Langfuse best practices by **explicitly ingesting token counts** from API responses without calculating costs in the application code.

**Claude (Anthropic):**
```python
usage_data = {
    "input": usage.input_tokens,
    "output": usage.output_tokens,
    "total": usage.input_tokens + usage.output_tokens,
    "unit": "TOKENS"
}

# Include cache info if available
if usage.cache_creation_input_tokens:
    usage_data["cache_creation_input_tokens"] = usage.cache_creation_input_tokens
if usage.cache_read_input_tokens:
    usage_data["cache_read_input_tokens"] = usage.cache_read_input_tokens
```

**Gemini (Google):**
```python
usage_data = {
    "input": usage_metadata.prompt_token_count,
    "output": usage_metadata.candidates_token_count,
    "total": usage_metadata.total_token_count,
    "unit": "TOKENS"
}

# Include cache info if available
if usage_metadata.cached_content_token_count:
    usage_data["cached_content_token_count"] = usage_metadata.cached_content_token_count
```

### Console Output

**With cache usage (Claude):**
```
Token usage - Input: 5000 (cache_write: 100, cache_read: 4000), 
Output: 567, Total: 5567
```

**With cache usage (Gemini):**
```
Token usage - Input: 3000 (cached: 2500), 
Output: 450, Total: 3450
```

**Without cache usage:**
```
Token usage - Input: 1234, Output: 567, Total: 1801
```

### Cost Tracking in Langfuse (Optional)

If you want cost tracking:

1. **Configure Model Pricing** in Langfuse dashboard
2. **Define cache pricing** for accurate calculations
3. **Langfuse will automatically calculate costs** based on token usage we send

This approach ensures:
- ✅ Accurate token counts always tracked
- ✅ Cache information preserved for Langfuse
- ✅ Costs calculated by Langfuse with your pricing config
- ✅ No risk of incorrect cost estimates in code

## Advanced Features

### 1. Trace Context Propagation

The `@observe` decorator automatically creates nested traces:
- Workflow functions create top-level traces
- Node functions create spans within the workflow
- LLM calls create generation spans within nodes

### 2. Error Tracking

Failed workflows are automatically tagged with:
- `status`: "failed"
- `error`: Error message
- Full trace preserved for debugging

### 3. Multi-Modal Tracking

VLM calls with images are tracked with:
- Image presence flag
- Separate image cost
- Screenshot metadata

## Debugging with Langfuse

### Common Use Cases

1. **High Token Usage**
   - Filter traces by cost
   - Check `conversation_length` metadata
   - Review `system_prompt_length`

2. **Validation Failures**
   - Find traces with high `retry_count`
   - Check VLM validation outputs
   - Review console logs in metadata

3. **Performance Analysis**
   - Compare latencies between creation and feedback
   - Analyze tool execution time
   - Track retry patterns

4. **Cost Optimization**
   - Identify expensive sessions
   - Compare costs with/without assets
   - Track VLM vs LLM costs

## Best Practices

1. **Session IDs**: Always unique, automatically managed
2. **Metadata**: Rich context for every trace
3. **Tags**: Use for filtering in Langfuse UI
4. **Error Handling**: All errors captured with context
5. **Cost Tracking**: Automatic and accurate

## Future Enhancements

Potential additions:
1. **User Feedback**: Integrate user ratings into traces
2. **Prompt Management**: Version and test prompts in Langfuse
3. **Evaluation**: Add LLM-as-judge for output quality
4. **A/B Testing**: Compare different system prompts
5. **Datasets**: Export successful sessions for fine-tuning

## Troubleshooting

### No Data in Langfuse?

1. Check environment variables are set:
   ```bash
   echo $LANGFUSE_PUBLIC_KEY
   echo $LANGFUSE_SECRET_KEY
   ```

2. Check Langfuse client initialization:
   ```python
   from langfuse import Langfuse
   langfuse = Langfuse()
   print("✅ Langfuse initialized")
   ```

3. Check network connectivity to Langfuse host

### Token Counts are Zero?

1. Verify API responses include usage metadata
2. Check model compatibility (some models don't report usage)
3. Review logs for API errors

### Traces are Disconnected?

1. Ensure all async functions are properly decorated
2. Check that `langfuse_context` is imported where used
3. Verify decorator order (should be before async def)

## Summary

Our Langfuse integration provides:

✅ **Complete Observability**: Every LLM call tracked  
✅ **Cost Transparency**: Accurate cost calculations  
✅ **Rich Metadata**: Session, retry, and context tracking  
✅ **Multi-Modal Support**: Text and image inputs  
✅ **Error Tracking**: Failed sessions preserved  
✅ **Performance Insights**: Latency and token analysis  
✅ **Production Ready**: Battle-tested decorators and error handling  

This enables data-driven optimization of prompts, costs, and performance!

