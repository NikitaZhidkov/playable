"""
Unit tests for src/llm_client.py

Tests cover:
- LLMClient initialization and configuration
- Message conversion (LangGraph → Anthropic format)
- Tool result buffering and grouping
- Response parsing (Anthropic → custom types)
- Prompt caching configuration

Integration tests are in tests/integration/test_anthropic_cache.py
"""
import pytest
import os
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.llm_client import LLMClient
from src.custom_types import TextRaw, ToolUse, ThinkingBlock


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client to avoid real API calls."""
    with patch('src.llm_client.Anthropic') as mock:
        yield mock


@pytest.fixture
def llm_client(mock_anthropic_client):
    """Create LLMClient with mocked Anthropic client."""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key-123'}):
        return LLMClient()


# ============================================================================
# Unit Tests - Initialization
# ============================================================================

def test_initialization_with_api_key(mock_anthropic_client):
    """Test LLMClient initialization with explicit API key."""
    client = LLMClient(api_key="explicit-key")
    
    assert client.api_key == "explicit-key"
    mock_anthropic_client.assert_called_once_with(api_key="explicit-key")


def test_initialization_with_env_api_key(mock_anthropic_client):
    """Test LLMClient initialization with env variable."""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'env-key-456'}):
        client = LLMClient()
        
        assert client.api_key == "env-key-456"
        mock_anthropic_client.assert_called_once_with(api_key="env-key-456")


def test_initialization_missing_api_key(mock_anthropic_client):
    """Test that missing API key raises ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            LLMClient()


def test_model_selection_priority(mock_anthropic_client):
    """Test model selection follows correct priority."""
    with patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'test-key',
        'LLM_BEST_CODING_MODEL': 'env-model'
    }):
        # Priority 1: Explicit parameter
        client1 = LLMClient(model="explicit-model")
        assert client1.model == "explicit-model"
        
        # Priority 2: LLM_BEST_CODING_MODEL env var
        client2 = LLMClient()
        assert client2.model == "env-model"


def test_model_selection_no_env(mock_anthropic_client):
    """Test model selection when no env vars set."""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}, clear=True):
        client = LLMClient()
        assert client.model is None  # Falls back to Anthropic default


# ============================================================================
# Unit Tests - Tool Formatting
# ============================================================================

def test_format_tools_for_anthropic(llm_client):
    """Test that tools are passed through as-is."""
    tools = [
        {
            "name": "write_file",
            "description": "Write a file",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }
    ]
    
    result = llm_client.format_tools_for_anthropic(tools)
    
    assert result == tools  # Should be pass-through


# ============================================================================
# Unit Tests - Response Parsing
# ============================================================================

def test_parse_response_with_text_block(llm_client):
    """Test parsing response with text content."""
    mock_response = Mock()
    mock_text_block = Mock()
    mock_text_block.type = "text"
    mock_text_block.text = "Here is my response"
    mock_response.content = [mock_text_block]
    
    result = llm_client.parse_anthropic_response(mock_response)
    
    assert len(result) == 1
    assert isinstance(result[0], TextRaw)
    assert result[0].text == "Here is my response"


def test_parse_response_with_tool_use_block(llm_client):
    """Test parsing response with tool use."""
    mock_response = Mock()
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "write_file"
    mock_tool_block.input = {"path": "game.js", "content": "console.log('hi');"}
    mock_tool_block.id = "call_123"
    mock_response.content = [mock_tool_block]
    
    result = llm_client.parse_anthropic_response(mock_response)
    
    assert len(result) == 1
    assert isinstance(result[0], ToolUse)
    assert result[0].name == "write_file"
    assert result[0].input == {"path": "game.js", "content": "console.log('hi');"}
    assert result[0].id == "call_123"


def test_parse_response_with_thinking_block(llm_client):
    """Test parsing response with thinking content."""
    mock_response = Mock()
    mock_thinking_block = Mock()
    mock_thinking_block.type = "thinking"
    mock_thinking_block.thinking = "I need to consider the edge cases..."
    mock_response.content = [mock_thinking_block]
    
    result = llm_client.parse_anthropic_response(mock_response)
    
    assert len(result) == 1
    assert isinstance(result[0], ThinkingBlock)
    assert result[0].thinking == "I need to consider the edge cases..."


def test_parse_response_with_mixed_blocks(llm_client):
    """Test parsing response with multiple block types."""
    mock_response = Mock()
    
    mock_text = Mock()
    mock_text.type = "text"
    mock_text.text = "I'll create a file"
    
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.name = "write_file"
    mock_tool.input = {"path": "test.js"}
    mock_tool.id = "call_456"
    
    mock_thinking = Mock()
    mock_thinking.type = "thinking"
    mock_thinking.thinking = "First I should..."
    
    mock_response.content = [mock_thinking, mock_text, mock_tool]
    
    result = llm_client.parse_anthropic_response(mock_response)
    
    assert len(result) == 3
    assert isinstance(result[0], ThinkingBlock)
    assert isinstance(result[1], TextRaw)
    assert isinstance(result[2], ToolUse)


# ============================================================================
# Unit Tests - Message Conversion (Simple Cases)
# ============================================================================

def test_convert_human_message(llm_client):
    """Test converting a simple human message."""
    messages = [
        HumanMessage(content="Create a game")
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Create a game"


def test_convert_ai_message_without_tools(llm_client):
    """Test converting AI message without tool calls."""
    messages = [
        AIMessage(content="I'll create the game for you")
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert result[0]["content"] == "I'll create the game for you"


def test_convert_ai_message_with_tool_calls(llm_client):
    """Test converting AI message with tool calls."""
    messages = [
        AIMessage(
            content="I'll write the file",
            tool_calls=[
                {
                    "name": "write_file",
                    "args": {"path": "game.js", "content": "code"},
                    "id": "call_789"
                }
            ]
        )
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    assert isinstance(result[0]["content"], list)
    assert len(result[0]["content"]) == 2
    
    # First element should be text
    assert result[0]["content"][0]["type"] == "text"
    assert result[0]["content"][0]["text"] == "I'll write the file"
    
    # Second element should be tool_use
    assert result[0]["content"][1]["type"] == "tool_use"
    assert result[0]["content"][1]["id"] == "call_789"
    assert result[0]["content"][1]["name"] == "write_file"
    assert result[0]["content"][1]["input"] == {"path": "game.js", "content": "code"}


def test_convert_ai_message_with_multiple_tool_calls(llm_client):
    """Test converting AI message with multiple tool calls."""
    messages = [
        AIMessage(
            content="Creating files",
            tool_calls=[
                {"name": "write_file", "args": {"path": "a.js"}, "id": "call_1"},
                {"name": "write_file", "args": {"path": "b.js"}, "id": "call_2"},
            ]
        )
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert len(result[0]["content"]) == 3  # text + 2 tool_use
    assert result[0]["content"][0]["type"] == "text"
    assert result[0]["content"][1]["type"] == "tool_use"
    assert result[0]["content"][2]["type"] == "tool_use"


def test_convert_dict_message(llm_client):
    """Test converting dict message (backwards compatibility)."""
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert result[0] == {"role": "user", "content": "Hello"}


# ============================================================================
# Unit Tests - Tool Result Buffering (Critical!)
# ============================================================================

def test_convert_single_tool_message(llm_client):
    """Test converting a single tool result."""
    messages = [
        ToolMessage(content="File written successfully", tool_call_id="call_1")
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert isinstance(result[0]["content"], list)
    assert len(result[0]["content"]) == 1
    assert result[0]["content"][0]["type"] == "tool_result"
    assert result[0]["content"][0]["tool_use_id"] == "call_1"
    assert result[0]["content"][0]["content"] == "File written successfully"


def test_convert_consecutive_tool_messages_are_grouped(llm_client):
    """Test that consecutive tool results are grouped in single user message."""
    messages = [
        ToolMessage(content="File 1 written", tool_call_id="call_1"),
        ToolMessage(content="File 2 written", tool_call_id="call_2"),
        ToolMessage(content="File 3 written", tool_call_id="call_3"),
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    # CRITICAL: All tool results should be in ONE user message
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert len(result[0]["content"]) == 3
    
    for i, tool_result in enumerate(result[0]["content"]):
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == f"call_{i+1}"
        assert tool_result["content"] == f"File {i+1} written"


def test_tool_results_flushed_before_human_message(llm_client):
    """Test that buffered tool results are flushed before human message."""
    messages = [
        ToolMessage(content="Result 1", tool_call_id="call_1"),
        ToolMessage(content="Result 2", tool_call_id="call_2"),
        HumanMessage(content="What's next?"),
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 2
    
    # First message: grouped tool results
    assert result[0]["role"] == "user"
    assert len(result[0]["content"]) == 2
    assert result[0]["content"][0]["type"] == "tool_result"
    assert result[0]["content"][1]["type"] == "tool_result"
    
    # Second message: human message
    assert result[1]["role"] == "user"
    assert result[1]["content"] == "What's next?"


def test_tool_results_flushed_before_ai_message(llm_client):
    """Test that buffered tool results are flushed before AI message."""
    messages = [
        ToolMessage(content="Done", tool_call_id="call_1"),
        AIMessage(content="Great!"),
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[0]["content"][0]["type"] == "tool_result"
    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "Great!"


def test_tool_results_flushed_at_end(llm_client):
    """Test that buffered tool results are flushed at end of message list."""
    messages = [
        AIMessage(content="Creating files", tool_calls=[
            {"name": "write_file", "args": {}, "id": "call_1"}
        ]),
        ToolMessage(content="Success", tool_call_id="call_1"),
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 2
    assert result[0]["role"] == "assistant"
    assert result[1]["role"] == "user"
    assert result[1]["content"][0]["type"] == "tool_result"


# ============================================================================
# Unit Tests - Complex Message Conversion Scenarios
# ============================================================================

def test_convert_full_conversation_with_tools(llm_client):
    """Test converting a complete conversation with tool usage."""
    messages = [
        HumanMessage(content="Create a game"),
        AIMessage(content="I'll create it", tool_calls=[
            {"name": "write_file", "args": {"path": "game.js"}, "id": "call_1"}
        ]),
        ToolMessage(content="File created", tool_call_id="call_1"),
        AIMessage(content="Done!"),
        HumanMessage(content="Make it better"),
        AIMessage(content="Improving...", tool_calls=[
            {"name": "edit_file", "args": {"path": "game.js"}, "id": "call_2"}
        ]),
        ToolMessage(content="File edited", tool_call_id="call_2"),
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    # Should be: user, assistant, user(tool), assistant, user, assistant, user(tool)
    assert len(result) == 7
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
    assert result[2]["role"] == "user"  # Tool result
    assert result[3]["role"] == "assistant"
    assert result[4]["role"] == "user"
    assert result[5]["role"] == "assistant"
    assert result[6]["role"] == "user"  # Tool result


def test_convert_multiple_tools_then_multiple_results(llm_client):
    """Test AI calling multiple tools, then receiving multiple results."""
    messages = [
        HumanMessage(content="Read and write files"),
        AIMessage(content="Processing", tool_calls=[
            {"name": "read_file", "args": {"path": "a.js"}, "id": "call_1"},
            {"name": "write_file", "args": {"path": "b.js"}, "id": "call_2"},
        ]),
        ToolMessage(content="Read content", tool_call_id="call_1"),
        ToolMessage(content="Written", tool_call_id="call_2"),
        AIMessage(content="All done!"),
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 4
    
    # Message 1: User
    assert result[0]["role"] == "user"
    
    # Message 2: Assistant with 2 tool calls
    assert result[1]["role"] == "assistant"
    assert len(result[1]["content"]) == 3  # text + 2 tool_use
    
    # Message 3: User with 2 tool results (grouped!)
    assert result[2]["role"] == "user"
    assert len(result[2]["content"]) == 2
    assert result[2]["content"][0]["type"] == "tool_result"
    assert result[2]["content"][1]["type"] == "tool_result"
    
    # Message 4: Assistant
    assert result[3]["role"] == "assistant"


def test_convert_mixed_dict_and_langgraph_messages(llm_client):
    """Test handling mixed message formats."""
    messages = [
        {"role": "user", "content": "Hello"},
        AIMessage(content="Hi there"),
        {"role": "user", "content": "Create game"},
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 3
    assert all(msg["role"] in ["user", "assistant"] for msg in result)


def test_convert_tool_results_flush_before_dict_message(llm_client):
    """Test tool results are flushed before dict message."""
    messages = [
        ToolMessage(content="Done", tool_call_id="call_1"),
        {"role": "user", "content": "What now?"},
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[0]["content"][0]["type"] == "tool_result"
    assert result[1] == {"role": "user", "content": "What now?"}


# ============================================================================
# Unit Tests - Edge Cases
# ============================================================================

def test_convert_empty_message_list(llm_client):
    """Test converting empty message list."""
    result = llm_client.convert_messages_for_anthropic([])
    
    assert result == []


def test_convert_ai_message_with_empty_content(llm_client):
    """Test AI message with empty content but tool calls."""
    messages = [
        AIMessage(content="", tool_calls=[
            {"name": "test", "args": {}, "id": "call_1"}
        ])
    ]
    
    result = llm_client.convert_messages_for_anthropic(messages)
    
    assert len(result) == 1
    assert result[0]["role"] == "assistant"
    # Should still have content list with empty text + tool_use
    assert isinstance(result[0]["content"], list)


# ============================================================================
# Unit Tests - Cache Control Configuration
# ============================================================================

def test_call_adds_cache_control_to_system(llm_client):
    """Test that cache_control is added to system prompt."""
    mock_response = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = []
    
    llm_client.client.messages.create = Mock(return_value=mock_response)
    
    llm_client.call(
        messages=[HumanMessage(content="Test")],
        tools=[],
        system="System prompt",
        max_tokens=1000
    )
    
    call_args = llm_client.client.messages.create.call_args
    system_arg = call_args.kwargs['system']
    
    assert isinstance(system_arg, list)
    assert len(system_arg) == 1
    assert system_arg[0]["type"] == "text"
    assert system_arg[0]["text"] == "System prompt"
    assert system_arg[0]["cache_control"] == {"type": "ephemeral"}


def test_call_adds_cache_control_to_tools(llm_client):
    """Test that cache_control is added to last tool."""
    mock_response = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = []
    
    llm_client.client.messages.create = Mock(return_value=mock_response)
    
    tools = [
        {"name": "tool1", "description": "First tool"},
        {"name": "tool2", "description": "Second tool"},
    ]
    
    llm_client.call(
        messages=[HumanMessage(content="Test")],
        tools=tools,
        system="System",
        max_tokens=1000
    )
    
    call_args = llm_client.client.messages.create.call_args
    tools_arg = call_args.kwargs['tools']
    
    # Last tool should have cache_control
    assert tools_arg[-1]["cache_control"] == {"type": "ephemeral"}
    # First tool should not (we only add to last one)
    assert "cache_control" not in tools_arg[0]


def test_call_adds_cache_control_to_last_message_string_content(llm_client):
    """Test cache_control added to last message with string content."""
    mock_response = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = []
    
    llm_client.client.messages.create = Mock(return_value=mock_response)
    
    llm_client.call(
        messages=[
            HumanMessage(content="First message"),
            HumanMessage(content="Last message")
        ],
        tools=[],
        system="System",
        max_tokens=1000
    )
    
    call_args = llm_client.client.messages.create.call_args
    messages_arg = call_args.kwargs['messages']
    
    # Last message should have content converted to list with cache_control
    last_msg = messages_arg[-1]
    assert isinstance(last_msg["content"], list)
    assert last_msg["content"][0]["type"] == "text"
    assert last_msg["content"][0]["text"] == "Last message"
    assert last_msg["content"][0]["cache_control"] == {"type": "ephemeral"}


def test_call_adds_cache_control_to_last_message_list_content(llm_client):
    """Test cache_control added to last message with list content."""
    mock_response = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = []
    
    llm_client.client.messages.create = Mock(return_value=mock_response)
    
    llm_client.call(
        messages=[
            AIMessage(content="Text", tool_calls=[
                {"name": "test", "args": {}, "id": "call_1"}
            ])
        ],
        tools=[],
        system="System",
        max_tokens=1000
    )
    
    call_args = llm_client.client.messages.create.call_args
    messages_arg = call_args.kwargs['messages']
    
    # Last content block should have cache_control
    last_msg = messages_arg[-1]
    assert isinstance(last_msg["content"], list)
    assert len(last_msg["content"]) == 2  # text + tool_use
    assert last_msg["content"][-1]["cache_control"] == {"type": "ephemeral"}


def test_call_requires_system_prompt(llm_client):
    """Test that call raises error if system prompt is None."""
    with pytest.raises(ValueError, match="System prompt must be provided"):
        llm_client.call(
            messages=[HumanMessage(content="Test")],
            tools=[],
            system=None,
            max_tokens=1000
        )


def test_call_passes_correct_parameters(llm_client):
    """Test that call passes all parameters correctly to Anthropic API."""
    mock_response = Mock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_response.content = []
    
    llm_client.client.messages.create = Mock(return_value=mock_response)
    llm_client.model = "claude-3-5-sonnet-20241022"
    
    llm_client.call(
        messages=[HumanMessage(content="Test")],
        tools=[{"name": "test_tool"}],
        system="Test system",
        max_tokens=4000,
        temperature=0.5
    )
    
    call_args = llm_client.client.messages.create.call_args
    
    assert call_args.kwargs['model'] == "claude-3-5-sonnet-20241022"
    assert call_args.kwargs['max_tokens'] == 4000
    assert call_args.kwargs['temperature'] == 0.5
    assert isinstance(call_args.kwargs['system'], list)
    assert len(call_args.kwargs['messages']) >= 1
    assert len(call_args.kwargs['tools']) >= 1

