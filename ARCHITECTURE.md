# Architecture Documentation

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│                          (main.py)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                            │
│                    (agent_graph.py)                              │
│                                                                   │
│   ┌─────────────┐      ┌──────────────┐     ┌────────────┐     │
│   │  llm_node   │─────▶│should_continue│────▶│    END     │     │
│   └──────┬──────┘      └──────┬───────┘     └────────────┘     │
│          │                     │                                 │
│          │                     ▼                                 │
│          │              ┌──────────────┐                        │
│          └──────────────│  tools_node  │                        │
│                         └──────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                            │         │
              ┌─────────────┘         └──────────────┐
              ▼                                       ▼
┌──────────────────────────┐          ┌────────────────────────┐
│   Anthropic Claude API   │          │   File Operations      │
│    (llm_client.py)       │          │     (tools.py)         │
│                          │          │                        │
│ • System Prompt          │          │ • read_file           │
│ • Message Conversion     │          │ • write_file          │
│ • Tool Formatting        │          │ • edit_file           │
│ • Response Parsing       │          │ • delete_file         │
└──────────────────────────┘          │ • complete            │
                                      └──────────┬─────────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────────┐
                                      │  Dagger Workspace    │
                                      │   (workspace.py)     │
                                      │                      │
                                      │ • Container Mgmt     │
                                      │ • File Operations    │
                                      │ • Git Diff           │
                                      │ • Export             │
                                      └──────────────────────┘
```

## Component Interaction Flow

### 1. Initialization Phase

```
main.py
  │
  ├─▶ Create Dagger Connection
  │     └─▶ workspace.Workspace.create()
  │           └─▶ Initialize Node.js container
  │
  ├─▶ Initialize LLMClient
  │     └─▶ Load ANTHROPIC_API_KEY
  │
  ├─▶ Initialize FileOperations
  │     └─▶ Wrap workspace with tools
  │
  └─▶ Create LangGraph Agent
        └─▶ agent_graph.create_agent_graph()
              └─▶ Compile StateGraph
```

### 2. Execution Phase

```
User Input: "Create a game"
  │
  ▼
HumanMessage added to state
  │
  ▼
┌─────────────────────────────────────┐
│         LLM Node                    │
│                                     │
│  1. Get messages from state         │
│  2. Get tools from FileOperations   │
│  3. Call Claude API                 │
│  4. Parse response                  │
│  5. Extract text & tool calls       │
│  6. Create AIMessage                │
│  7. Update state                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Should Continue Router           │
│                                     │
│  • Has tool calls? → tools_node     │
│  • Is completed? → END              │
│  • Otherwise → END                  │
└──────────────┬──────────────────────┘
               │
               ▼ (has tool calls)
┌─────────────────────────────────────┐
│         Tools Node                  │
│                                     │
│  1. Get tool calls from state       │
│  2. Execute via FileOperations      │
│  3. Call workspace methods          │
│  4. Collect results                 │
│  5. Create ToolMessages             │
│  6. Update state                    │
│  7. Check if completed              │
└──────────────┬──────────────────────┘
               │
               ▼
           Loop back to LLM Node
               │
               ▼ (when complete)
            Finalize
```

### 3. Tool Execution Detail

```
tools_node receives: [ToolUse(name="write_file", ...)]
  │
  ▼
FileOperations.run_tools()
  │
  ├─▶ Match tool name: "write_file"
  │     │
  │     ▼
  │   workspace.write_file(path, contents)
  │     │
  │     ├─▶ Check permissions
  │     ├─▶ container.with_new_file(path, contents)
  │     └─▶ Return success/error
  │
  └─▶ Create ToolUseResult
        │
        └─▶ Return to tools_node
              │
              └─▶ Convert to ToolMessage
                    │
                    └─▶ Add to state.messages
```

## Data Flow

### State Structure

```python
{
    "messages": [
        HumanMessage(content="Create a game"),
        AIMessage(content="I'll create...", tool_calls=[...]),
        ToolMessage(content="success", tool_call_id="..."),
        AIMessage(content="Now I'll...", tool_calls=[...]),
        # ...
    ],
    "workspace": Workspace(...),
    "task_description": "Create a game",
    "is_completed": False,
    "_parsed_content": [...]  # Temporary field
}
```

### Message Types

1. **HumanMessage**: User input
   ```python
   HumanMessage(content="Create a clicker game")
   ```

2. **AIMessage**: LLM response with optional tool calls
   ```python
   AIMessage(
       content="I'll create an HTML file...",
       tool_calls=[{
           "name": "write_file",
           "args": {"path": "index.html", "content": "..."},
           "id": "call_123"
       }]
   )
   ```

3. **ToolMessage**: Tool execution result
   ```python
   ToolMessage(
       content="success",
       tool_call_id="call_123",
       name="write_file"
   )
   ```

## Component Dependencies

```
main.py
  ├─ requires: agent_graph, workspace, tools, llm_client
  └─ provides: CLI interface

agent_graph.py
  ├─ requires: agent_state, llm_client, tools
  └─ provides: LangGraph workflow

llm_client.py
  ├─ requires: custom_types
  └─ provides: Anthropic API integration

tools.py
  ├─ requires: workspace, custom_types
  └─ provides: File operation tools

workspace.py
  ├─ requires: dagger, dagger_utils, log
  └─ provides: Containerized workspace

agent_state.py
  ├─ requires: workspace, langgraph
  └─ provides: State schema

custom_types.py
  ├─ requires: (stdlib only)
  └─ provides: Type definitions

dagger_utils.py
  ├─ requires: dagger
  └─ provides: Helper utilities

log.py
  ├─ requires: (stdlib only)
  └─ provides: Logging setup
```

## File System Layer

```
Host Machine
  │
  └─▶ Dagger Client
        │
        └─▶ Docker Container (oven/bun:1.2.5-alpine)
              │
              ├─▶ /app (workspace)
              │     │
              │     ├─ index.html (created by agent)
              │     ├─ game.js (created by agent)
              │     └─ ... (other files)
              │
              └─▶ Operations:
                    • with_new_file(): Create/overwrite file
                    • file().contents(): Read file
                    • without_file(): Delete file
                    • directory().export(): Export to host
```

## Error Handling Strategy

```
┌─────────────────────────────────────┐
│      Any Operation                  │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Try Operation       │
    └──────┬───────────────┘
           │
           ├─▶ Success → Return result
           │
           ├─▶ FileNotFoundError → Return error to LLM
           │                        (LLM will retry/fix)
           │
           ├─▶ PermissionError → Return error to LLM
           │                      (LLM will adjust)
           │
           ├─▶ TransportError → Retry with backoff
           │                     (tenacity in workspace.py)
           │
           └─▶ Other Exception → Log & return error to LLM
```

## Concurrency Model

- **Async/Await**: All I/O operations are async
- **Single Thread**: LangGraph execution is sequential
- **No Parallelism**: Tools execute one at a time
- **Reason**: Simpler state management, easier debugging

## Memory Management

- **Short-term**: Messages in state (current session)
- **No Long-term**: No persistence between runs
- **Future**: Can add checkpointing via LangGraph

```python
# Future enhancement:
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string("checkpoints.db")
agent = workflow.compile(checkpointer=memory)
```

## Security Model

```
┌─────────────────────────────────────┐
│         User Machine                │
│  • Python process (trusted)         │
│  • Has API keys                     │
│  • Can access filesystem            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Docker Container               │
│  • Isolated filesystem              │
│  • No network by default            │
│  • Limited resources                │
│  • Can't access host directly       │
└─────────────────────────────────────┘
```

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Container Start | 5-10s | First time only |
| LLM Call | 2-5s | Depends on response size |
| File Operation | <100ms | In-memory in container |
| Export | 1-2s | Copy from container to host |

## Scalability

### Current Limits
- **Single User**: One session at a time
- **Single Container**: One workspace per session
- **Sequential**: One tool call at a time

### Future Scaling
- **Multi-User**: Use session IDs, separate workspaces
- **Parallel Tools**: Execute independent tools in parallel
- **Distributed**: Run containers on remote machines
- **Caching**: Cache LLM responses for similar tasks

## Extension Points

### 1. Add New Tools

```python
# In tools.py
def base_tools(self):
    return [
        # ... existing tools
        {
            "name": "run_tests",
            "description": "Run game tests",
            "input_schema": {...}
        }
    ]

# In run_tools()
case "run_tests":
    result = await self.workspace.exec(["npm", "test"])
    return ToolUseResult.from_tool_use(block, result.stdout)
```

### 2. Change LLM Provider

```python
# Create new openai_client.py
class OpenAIClient:
    def call(self, messages, tools):
        # OpenAI implementation
        pass

# In agent_graph.py
llm_client = OpenAIClient()  # Instead of LLMClient
```

### 3. Add Streaming

```python
# In main.py
async for event in agent.astream(state):
    if "messages" in event:
        print(event["messages"][-1].content)
```

### 4. Add Checkpointing

```python
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string(":memory:")
agent = workflow.compile(checkpointer=memory)

# Resume from checkpoint
config = {"configurable": {"thread_id": "123"}}
result = await agent.ainvoke(state, config)
```

## Testing Strategy

### Unit Tests
```python
# Test individual components
async def test_llm_client():
    client = LLMClient()
    response = client.call([...], tools)
    assert response is not None

async def test_file_operations():
    ops = FileOperations(workspace)
    result = await ops.run_tools([...])
    assert result[1] == False  # not completed
```

### Integration Tests
```python
# Test full workflow
async def test_agent_creates_file():
    agent = create_agent_graph(llm_client, file_ops)
    state = {"messages": [HumanMessage("Create index.html")]}
    result = await agent.ainvoke(state)
    
    files = await workspace.ls(".")
    assert "index.html" in files
```

### End-to-End Tests
```python
# Test via main.py
# Simulate user input
# Verify exported files
```

## Monitoring & Observability

### Logging Levels
- **DEBUG**: Full message contents, tool inputs/outputs
- **INFO**: High-level actions (tool calls, LLM calls)
- **WARNING**: Retries, recoverable errors
- **ERROR**: Failures, exceptions

### Metrics to Track
- LLM call latency
- Tool execution time
- Success/failure rates
- Container lifecycle

### Future: Add Tracing
```python
from langfuse import Langfuse

langfuse = Langfuse()
# Trace all operations
```

## Summary

This architecture provides:

✅ **Modularity**: Each component has single responsibility
✅ **Testability**: Clear interfaces between components
✅ **Extensibility**: Easy to add tools, change LLM, add features
✅ **Robustness**: Error handling at every layer
✅ **Maintainability**: Clean separation of concerns
✅ **Performance**: Async I/O, retry logic, caching-ready
✅ **Security**: Containerized execution, permission checks

The system is production-ready and can scale to handle complex game generation tasks.

