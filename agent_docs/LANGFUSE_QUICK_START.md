# Langfuse Quick Start Guide

## Setup (2 minutes)

### 1. Get API Keys
Visit https://cloud.langfuse.com/ and create a project to get your keys.

### 2. Add to `.env`
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key-here
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 3. Run Your Agent
```bash
source venv/bin/activate
python src/main.py
```

That's it! 🎉

## What You'll See

### In Terminal

**With cache usage:**
```
Token usage - Input: 5000 (cache_write: 100, cache_read: 4000), 
Output: 567, Total: 5567
```

**Without cache:**
```
Token usage - Input: 1234, Output: 567, Total: 1801
```

> **Note**: We track token counts only (no cost calculation). If you want costs, configure model pricing in Langfuse dashboard!

### In Langfuse Dashboard

**Traces Tab:**
- All game creation sessions
- Complete execution flow
- Token usage per call
- Filter by session_id, tags, status

**Sessions Tab:**
- Grouped by `session_id`
- Track multiple feedback iterations
- See full conversation history
- Aggregate token usage

**Tokens:**
- Real-time token tracking
- Cache usage breakdown
- Filter by new_game vs feedback
- Compare Claude vs Gemini usage

## Key Metrics Tracked

| Metric | Description |
|--------|-------------|
| **Tokens** | Input, output, total for every call |
| **Cache Usage** | Cache read/write tokens tracked |
| **Traces** | Full execution hierarchy |
| **Sessions** | All iterations grouped together |
| **Metadata** | Mode, retries, assets, prompts |
| **Tags** | new_game, feedback, retry_N |
| **Errors** | Failed sessions with full context |

## Common Queries in Langfuse

### 1. Find Token-Heavy Sessions
- Sort traces by total tokens (descending)
- Check metadata for retry_count
- Identify opportunities for optimization

### 2. Track Success Rate
- Filter by tags: `new_game` or `feedback`
- Group by status: completed vs failed

### 3. Analyze Cache Effectiveness
- Check cache_read_tokens vs regular tokens
- See cache hit rates across sessions
- Optimize for better cache utilization

### 4. Compare Providers
- Claude calls: Check token usage patterns
- Gemini calls: Check image processing tokens
- Compare efficiency

### 5. Debug Failures
- Filter status: `failed`
- View full trace with error context
- Check token usage at failure point

## Features Available

✅ **Token Tracking**: Every LLM call tracked  
✅ **Cache Tracking**: Cache usage breakdown  
✅ **Trace Hierarchy**: Nested execution flow  
✅ **Session Grouping**: All iterations together  
✅ **Rich Metadata**: Context for every call  
✅ **Error Tracking**: Failed sessions preserved  
✅ **Multi-Modal**: Text + image tracking  
✅ **Tags**: Easy filtering and organization  

## Next Steps

1. **Explore Traces**: See execution flow in detail
2. **Track Tokens**: Monitor usage over time
3. **Optimize Prompts**: Use data to reduce tokens
4. **Leverage Cache**: Maximize cache hit rates
5. **Debug Issues**: Use traces for troubleshooting

## Advanced (Optional)

### Prompt Management
Store and version system prompts in Langfuse for A/B testing.

### Evaluation
Add LLM-as-judge to automatically score outputs.

### User Feedback
Integrate user ratings into traces for quality tracking.

### Datasets
Export successful sessions for model fine-tuning.

---

For complete documentation, see [LANGFUSE_INTEGRATION.md](LANGFUSE_INTEGRATION.md)

