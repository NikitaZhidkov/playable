# Logfire Integration

## Overview

This project uses [Logfire](https://logfire.pydantic.dev/) version **4.14.2** for LLM observability and tracing. Logfire is Pydantic's observability platform that provides automatic instrumentation for Anthropic Claude and other LLM providers.

## Migration from LangSmith

We've migrated from LangSmith to Logfire for better integration with modern Python tools and simpler setup.

### Changes Made

1. **Dependencies**: Removed `langsmith==0.4.34`, added `logfire==2.7.0`
2. **Imports**: Removed all `from langsmith import traceable` imports
3. **Decorators**: Removed all `@traceable()` decorators from functions
4. **Token Tracking**: Removed manual token tracking code (Logfire handles this automatically)
5. **Configuration**: Replaced LangSmith env vars with Logfire configuration

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs `logfire==4.14.2` along with all other dependencies.

### 2. Authenticate with Logfire

```bash
logfire auth
```

This will open your browser and guide you through the authentication process. It will automatically configure your local environment and create the necessary configuration files.

### 3. Configure Environment Variables (Optional)

If you need to set a token manually, add to your `.env` file:

```bash
LOGFIRE_TOKEN=your-logfire-token-here
```

## Features

### Automatic Instrumentation

Logfire automatically instruments:
- **Anthropic Claude API calls**: All LLM calls are automatically logged with token usage, latency, and cost
- **Request/Response data**: Full context of prompts and completions
- **Error tracking**: Automatic error logging and stack traces

### What's Logged

The integration automatically tracks:
- LLM model used
- Token usage (input, output, total)
- Request latency
- Cost per request
- Full prompt and completion content
- Tool calls and responses
- Error details

## Viewing Traces

1. Visit [https://logfire.pydantic.dev/](https://logfire.pydantic.dev/)
2. Log in with your account
3. Navigate to your project
4. View traces, metrics, and logs in the dashboard

## Code Changes

### Before (LangSmith)

```python
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

@traceable(name="claude_call", run_type="llm")
def call(self, messages, tools):
    response = self.client.messages.create(...)
    
    # Manual token tracking
    run_tree = get_current_run_tree()
    if run_tree:
        run_tree.add_metadata({...})
    
    return response
```

### After (Logfire)

```python
import logfire

# In main.py initialization
logfire.configure()
logfire.instrument_anthropic()

# In llm_client.py - no decorator needed!
def call(self, messages, tools):
    response = self.client.messages.create(...)
    # Automatically tracked by Logfire!
    return response
```

## Benefits

1. **Simpler Code**: No decorators or manual token tracking needed
2. **Automatic Instrumentation**: Works out of the box with Anthropic SDK
3. **Modern Stack**: Built on OpenTelemetry standards
4. **Better Performance**: Lower overhead than manual tracking
5. **Rich UI**: Beautiful dashboard for exploring traces

## Troubleshooting

### No traces appearing

1. Check that you've authenticated: `logfire auth`
2. Verify your token is set (if using manual configuration)
3. Check that `logfire.configure()` is called before any LLM calls
4. Ensure `logfire.instrument_anthropic()` is called

### Authentication issues

Run `logfire auth` again to re-authenticate:

```bash
logfire auth
```

## Resources

- [Logfire Documentation](https://docs.pydantic.dev/logfire/)
- [Anthropic Integration](https://docs.pydantic.dev/logfire/integrations/anthropic/)
- [Logfire Dashboard](https://logfire.pydantic.dev/)


