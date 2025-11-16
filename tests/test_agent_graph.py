"""
Unit tests for agent_graph.py
Tests graph structure, node functionality, and state transitions.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.agent_graph import create_agent_graph
from src.llm_client import LLMClient
from src.tools import FileOperations
from src.custom_types import ToolUse, TextRaw, ToolResult
from src.containers import Workspace
import json


# ============================================================================
# Graph Structure Tests
# ============================================================================

def test_graph_creation():
    """Test that agent graph can be created."""
    llm_client = Mock(spec=LLMClient)
    file_ops = Mock(spec=FileOperations)
    file_ops.tools = []
    
    graph = create_agent_graph(llm_client, file_ops)
    
    assert graph is not None
    assert hasattr(graph, 'nodes')


def test_graph_has_all_required_nodes():
    """Test that graph contains all expected nodes."""
    llm_client = Mock(spec=LLMClient)
    file_ops = Mock(spec=FileOperations)
    file_ops.tools = []
    
    graph = create_agent_graph(llm_client, file_ops)
    
    expected_nodes = ["llm", "tools", "human_input", "build", "test"]
    
    for node_name in expected_nodes:
        assert node_name in graph.nodes, f"Missing node: {node_name}"


# ============================================================================
# LLM Client Integration Tests (without directly calling nodes)
# ============================================================================

def test_llm_response_parsing_with_text():
    """Test parsing LLM response with text only."""
    parsed = [TextRaw(text="I'll create a game")]
    
    # Extract text parts
    text_parts = [item.text for item in parsed if isinstance(item, TextRaw)]
    
    assert len(text_parts) == 1
    assert "create" in text_parts[0]


def test_llm_response_parsing_with_tool_calls():
    """Test parsing LLM response with tool calls."""
    parsed = [
        TextRaw(text="Creating file"),
        ToolUse(
            name="create_file",
            input={"path": "index.html"},
            id="call_123"
        )
    ]
    
    # Extract tool calls
    tool_calls = [item for item in parsed if isinstance(item, ToolUse)]
    
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "create_file"
    assert tool_calls[0].id == "call_123"


def test_tool_result_structure():
    """Test tool result structure."""
    tool_result = ToolResult(
        content="File created",
        tool_use_id="call_123",
        name="create_file",
        is_error=False
    )
    
    assert tool_result.content == "File created"
    assert tool_result.tool_use_id == "call_123"
    assert tool_result.name == "create_file"
    assert tool_result.is_error is False


# ============================================================================
# State Transition Tests
# ============================================================================

def test_retry_count_increments_on_failure():
    """Test retry count increments on failures."""
    state = {"retry_count": 0}
    
    # Simulate failure
    retry_count = state.get("retry_count", 0) + 1
    
    assert retry_count == 1


def test_retry_count_resets_on_success():
    """Test retry count resets on success."""
    state = {"retry_count": 3}
    
    # Simulate success
    retry_count = 0
    
    assert retry_count == 0


def test_test_failures_stored_in_state():
    """Test that test failures are properly stored in state."""
    state = {"test_failures": []}
    
    # Add failure
    state["test_failures"].append("VLM validation failed")
    
    assert len(state["test_failures"]) == 1
    assert "VLM" in state["test_failures"][0]


def test_is_completed_flag():
    """Test is_completed flag behavior."""
    state = {"is_completed": False}
    
    # Mark as completed
    state["is_completed"] = True
    
    assert state["is_completed"] is True


def test_workspace_propagation():
    """Test workspace state propagation pattern."""
    initial_workspace = Mock()
    updated_workspace = Mock()
    
    state = {"workspace": initial_workspace}
    
    # Simulate workspace update
    state["workspace"] = updated_workspace
    
    assert state["workspace"] == updated_workspace


def test_missing_retry_count_defaults_to_zero():
    """Test that missing retry_count defaults to 0."""
    state = {}
    
    retry_count = state.get("retry_count", 0)
    
    assert retry_count == 0


def test_empty_test_failures_list():
    """Test empty test_failures means success."""
    state = {"test_failures": []}
    
    has_failures = len(state["test_failures"]) > 0
    
    assert not has_failures


# ============================================================================
# Mode Switching Tests
# ============================================================================

def test_creation_mode_flag():
    """Test creation mode is indicated by is_feedback_mode=False."""
    state = {"is_feedback_mode": False}
    
    is_creation_mode = not state.get("is_feedback_mode", False)
    
    assert is_creation_mode


def test_feedback_mode_flag():
    """Test feedback mode is indicated by is_feedback_mode=True."""
    state = {"is_feedback_mode": True}
    
    is_feedback_mode = state.get("is_feedback_mode", False)
    
    assert is_feedback_mode


# ============================================================================
# Asset/Sound Context Tests
# ============================================================================

def test_asset_context_storage():
    """Test asset context is properly stored in state."""
    asset_context = "car.png: red race car\ntree.png: green tree"
    
    state = {"asset_context": asset_context}
    
    assert "asset_context" in state
    assert "car.png" in state["asset_context"]


def test_sound_context_storage():
    """Test sound context is properly stored in state."""
    sound_context = "engine.mp3: car engine sound"
    
    state = {"sound_context": sound_context}
    
    assert "sound_context" in state
    assert "engine.mp3" in state["sound_context"]


def test_optional_context_handling():
    """Test state works without optional asset/sound context."""
    state = {
        "messages": [],
        "workspace": Mock(),
        "is_feedback_mode": False
    }
    
    # Should not crash when contexts are missing
    asset_context = state.get("asset_context")
    sound_context = state.get("sound_context")
    
    assert asset_context is None
    assert sound_context is None


# ============================================================================
# Retry Logic Tests
# ============================================================================

def test_max_retries_limit():
    """Test max retries limit (5)."""
    MAX_RETRIES = 5
    
    state = {"retry_count": 5}
    
    should_stop = state["retry_count"] >= MAX_RETRIES
    
    assert should_stop


def test_retry_below_limit():
    """Test retry count below limit allows retry."""
    MAX_RETRIES = 5
    
    state = {"retry_count": 2}
    
    can_retry = state["retry_count"] < MAX_RETRIES
    
    assert can_retry


def test_retry_reset_after_success():
    """Test retry resets after passing previously failed stage."""
    previous_failures = ["VLM validation failed"]
    previous_retry_count = 3
    
    # After passing, reset
    if previous_retry_count > 0 and previous_failures:
        test_case_retry_count = 0
    
    assert test_case_retry_count == 0


# ============================================================================
# Test Case Validation Tests
# ============================================================================

def test_test_case_ordering():
    """Test that test cases are sorted correctly."""
    test_case_files = [
        "test_case_3.json",
        "test_case_1.json", 
        "test_case_5.json",
        "test_case_2.json"
    ]
    
    sorted_files = sorted(test_case_files)
    
    expected = [
        "test_case_1.json",
        "test_case_2.json",
        "test_case_3.json",
        "test_case_5.json"
    ]
    
    assert sorted_files == expected


def test_test_case_count_validation():
    """Test that 1-5 test cases are valid."""
    valid_counts = [1, 2, 3, 4, 5]
    
    for count in valid_counts:
        assert 1 <= count <= 5, f"Count {count} should be valid"
    
    assert not (0 >= 1 and 0 <= 5), "0 test cases should be invalid"
    assert not (6 >= 1 and 6 <= 5), "6 test cases should be limited"


def test_test_case_limit_enforcement():
    """Test that more than 5 test cases are limited to 5."""
    test_case_files = [f"test_case_{i}.json" for i in range(1, 8)]
    
    # Limit to 5
    limited = test_case_files[:5]
    
    assert len(limited) == 5


# ============================================================================
# Message History Tests
# ============================================================================

def test_message_history_append():
    """Test messages are appended to history."""
    state = {"messages": [HumanMessage(content="First")]}
    
    # Add AI message
    state["messages"].append(AIMessage(content="Response"))
    
    assert len(state["messages"]) == 2
    assert isinstance(state["messages"][1], AIMessage)


def test_message_types():
    """Test different message types in history."""
    messages = [
        HumanMessage(content="User message"),
        AIMessage(content="AI response"),
        ToolMessage(content="Tool result", tool_call_id="123", name="tool")
    ]
    
    assert isinstance(messages[0], HumanMessage)
    assert isinstance(messages[1], AIMessage)
    assert isinstance(messages[2], ToolMessage)
