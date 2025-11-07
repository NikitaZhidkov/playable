# Anthropic Cache Integration Test

This test verifies that Anthropic prompt caching is working correctly in our LLM client.

## What is being tested?

The test verifies that caching works for three key areas:

1. **System Prompts**: Large system instructions are cached and reused across API calls
2. **Tools**: Tool definitions are cached and reused across API calls  
3. **Message History**: Conversation history is cached for subsequent messages

## How to run

```bash
# Run with detailed output
python -m pytest tests/integration/test_anthropic_cache.py -v -s --log-cli-level=INFO

# Run as part of all integration tests
python -m pytest tests/integration/ -v -m integration
```

## Expected results

When the test passes, you should see output like:

```
📈 Conversational Cache Growth Analysis:
  Call 1 cache read: 1511 tokens
  Call 2 cache read: 1505 tokens
  Call 3 cache read: 1358 tokens

  Total cache created across calls: 153 tokens
  This shows message history is being added to cache!

Cache Performance Summary:
  First call:
    - Cache creation: 0 tokens
    - Cache read: 1511 tokens
    - Input tokens: 3
  Second call:
    - Cache creation: 0 tokens
    - Cache read: 1505 tokens
    - Input tokens: 3
  Third call:
    - Cache creation: 153 tokens
    - Cache read: 1358 tokens
    - Input tokens: 3

  📊 Cache Efficiency:
    - Total cache created: 153 tokens
    - Total cache reads: 4374 tokens
    - Total tokens saved: 4374 tokens

  ✅ Cache is functioning correctly for:
    ✓ System prompts (cached and reused)
    ✓ Tools (cached and reused)
    ✓ Message history (grows with conversation)
```

## What the numbers mean

- **Cache creation**: Tokens being written to cache (creates new cache entries)
- **Cache read**: Tokens being read from cache (saves API costs!)
- **Input tokens**: Non-cached input tokens (typically just the user message)

## Cost savings

Prompt caching significantly reduces API costs:
- Cached reads cost 90% less than regular input tokens
- System prompts (~1400 tokens) are cached and reused across all calls
- Tools (~150 tokens) are cached and reused across all calls
- **Message history grows with each conversation turn** (~150 tokens per message)
- Each new message is added to the cache for subsequent calls

### Real test results:
- **4374 tokens** read from cache across 3 API calls
- **153 tokens** of message history added to cache
- **Only 9 tokens** of non-cached input (3 tokens per user message)
- **~99% of input tokens** came from cache!

This means for a typical game development conversation with multiple iterations, we save thousands of tokens through caching, with the savings growing as the conversation continues!

## Requirements

- Valid `ANTHROPIC_API_KEY` in `.env`
- Model that supports caching (Claude 3.5 Sonnet or later)
- Network access to Anthropic API

