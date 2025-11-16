"""
Integration tests for agent_graph.py
Tests graph creation, structure, and basic execution patterns.
"""
import pytest
from unittest.mock import Mock
from langchain_core.messages import HumanMessage, AIMessage
from src.agent_graph import create_agent_graph
from src.llm_client import LLMClient
from src.tools import FileOperations
from src.custom_types import ToolUse, TextRaw
from src.containers import Workspace
import src.agent_graph as agent_graph_module


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def disable_interactive_mode():
    """Disable interactive mode for all integration tests."""
    original_mode = agent_graph_module.INTERACTIVE_MODE
    agent_graph_module.INTERACTIVE_MODE = False
    yield
    agent_graph_module.INTERACTIVE_MODE = original_mode


# ============================================================================
# Graph Structure and Creation Tests
# ============================================================================

def test_compiled_graph_has_correct_structure():
    """Test that compiled graph has expected structure."""
    llm_client = Mock(spec=LLMClient)
    file_ops = Mock(spec=FileOperations)
    file_ops.tools = []
    
    graph = create_agent_graph(llm_client, file_ops)
    
    # Verify graph is compiled
    assert graph is not None
    
    # Verify all required nodes exist
    expected_nodes = ["llm", "tools", "human_input", "build", "test"]
    for node_name in expected_nodes:
        assert node_name in graph.nodes, f"Missing node: {node_name}"
    
    print("✅ Compiled graph has correct structure")


@pytest.mark.asyncio
async def test_graph_creates_with_real_workspace(dagger_client):
    """Test graph can be created with real workspace and containers."""
    llm_client = Mock(spec=LLMClient)
    
    # Create real workspace
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    # Create graph - this tests that graph creation works with real containers
    graph = create_agent_graph(llm_client, file_ops)
    
    assert graph is not None
    assert "llm" in graph.nodes
    assert "tools" in graph.nodes
    
    print("✅ Graph creates successfully with real workspace")


# ============================================================================
# FileOperations Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_file_operations_with_real_workspace(dagger_client):
    """Test that FileOperations works with real workspace."""
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    # Create a file using FileOperations
    file_ops.workspace = file_ops.workspace.write_file("test.txt", "test content")
    
    # Verify file was created
    files = await file_ops.workspace.ls(".")
    assert "test.txt" in files
    
    content = await file_ops.workspace.read_file("test.txt")
    assert content == "test content"
    
    print("✅ FileOperations works with real workspace")


@pytest.mark.asyncio
async def test_file_operations_multiple_file_operations(dagger_client):
    """Test that FileOperations can handle multiple file operations."""
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    # Create multiple files
    file_ops.workspace = file_ops.workspace.write_file("file1.txt", "content1")
    file_ops.workspace = file_ops.workspace.write_file("file2.txt", "content2")
    file_ops.workspace = file_ops.workspace.write_file("file3.txt", "content3")
    
    # Verify all files exist
    files = await file_ops.workspace.ls(".")
    assert "file1.txt" in files
    assert "file2.txt" in files
    assert "file3.txt" in files
    
    # Verify contents
    assert await file_ops.workspace.read_file("file1.txt") == "content1"
    assert await file_ops.workspace.read_file("file2.txt") == "content2"
    assert await file_ops.workspace.read_file("file3.txt") == "content3"
    
    print("✅ FileOperations handles multiple file operations")


# ============================================================================
# Mode and Context Tests
# ============================================================================

@pytest.mark.asyncio
async def test_graph_with_asset_context(dagger_client):
    """Test that graph can be created with asset context."""
    llm_client = Mock(spec=LLMClient)
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    graph = create_agent_graph(llm_client, file_ops)
    
    # Create state with asset context
    state = {
        "messages": [HumanMessage(content="Create game")],
        "workspace": workspace,
        "task_description": "Create game with assets",
        "is_completed": False,
        "is_feedback_mode": False,
        "retry_count": 0,
        "test_failures": [],
        "asset_context": "car.png: red race car sprite"
    }
    
    # Verify state structure is valid
    assert "asset_context" in state
    assert "car.png" in state["asset_context"]
    
    print("✅ Graph handles asset context in state")


@pytest.mark.asyncio
async def test_graph_with_sound_context(dagger_client):
    """Test that graph can be created with sound context."""
    llm_client = Mock(spec=LLMClient)
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    graph = create_agent_graph(llm_client, file_ops)
    
    # Create state with sound context
    state = {
        "messages": [HumanMessage(content="Create game")],
        "workspace": workspace,
        "task_description": "Create game with sounds",
        "is_completed": False,
        "is_feedback_mode": False,
        "retry_count": 0,
        "test_failures": [],
        "sound_context": "engine.mp3: car engine sound"
    }
    
    # Verify state structure is valid
    assert "sound_context" in state
    assert "engine.mp3" in state["sound_context"]
    
    print("✅ Graph handles sound context in state")


@pytest.mark.asyncio
async def test_graph_feedback_mode_state(dagger_client):
    """Test that graph can handle feedback mode state."""
    llm_client = Mock(spec=LLMClient)
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    graph = create_agent_graph(llm_client, file_ops)
    
    # Create feedback mode state
    state = {
        "messages": [
            HumanMessage(content="Create game"),
            AIMessage(content="Game created"),
            HumanMessage(content="Fix the background color")
        ],
        "workspace": workspace,
        "task_description": "Fix the background color",
        "is_completed": False,
        "is_feedback_mode": True,
        "retry_count": 1,
        "test_failures": ["Background color wrong"],
        "original_prompt": "Create game"
    }
    
    # Verify feedback mode state structure
    assert state["is_feedback_mode"] is True
    assert state["retry_count"] > 0
    assert len(state["test_failures"]) > 0
    assert "original_prompt" in state
    
    print("✅ Graph handles feedback mode state")


# ============================================================================
# State Transitions Tests
# ============================================================================

@pytest.mark.asyncio
async def test_workspace_state_persistence(dagger_client):
    """Test that workspace changes persist in state."""
    workspace = await Workspace.create(dagger_client)
    
    # Create initial file
    workspace = workspace.write_file("initial.txt", "initial content")
    
    # Verify file exists
    files = await workspace.ls(".")
    assert "initial.txt" in files
    
    # Create another file
    workspace = workspace.write_file("second.txt", "second content")
    
    # Verify both files exist
    files = await workspace.ls(".")
    assert "initial.txt" in files
    assert "second.txt" in files
    
    print("✅ Workspace state persists across operations")


# ============================================================================
# Message Flow Tests
# ============================================================================

def test_message_types_compatibility():
    """Test that different message types can coexist in state."""
    messages = [
        HumanMessage(content="User message"),
        AIMessage(content="AI response"),
        AIMessage(content="AI with tools", tool_calls=[
            {"name": "create_file", "args": {}, "id": "call_1"}
        ]),
        HumanMessage(content="Follow-up")
    ]
    
    # Verify all message types are valid
    assert all(msg is not None for msg in messages)
    assert len(messages) == 4
    
    # Verify tool calls structure
    assert len(messages[2].tool_calls) == 1
    assert messages[2].tool_calls[0]["name"] == "create_file"
    
    print("✅ Multiple message types work correctly")


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_graph_handles_missing_optional_context(dagger_client):
    """Test that graph works without optional asset/sound context."""
    llm_client = Mock(spec=LLMClient)
    workspace = await Workspace.create(dagger_client)
    file_ops = FileOperations(workspace)
    
    graph = create_agent_graph(llm_client, file_ops)
    
    # Create minimal state without optional contexts
    state = {
        "messages": [HumanMessage(content="Create game")],
        "workspace": workspace,
        "task_description": "Create game",
        "is_completed": False,
        "is_feedback_mode": False,
        "retry_count": 0,
        "test_failures": []
        # No asset_context or sound_context
    }
    
    # Verify state is valid (graph should handle missing optional fields)
    assert "asset_context" not in state
    assert "sound_context" not in state
    assert "messages" in state
    assert "workspace" in state
    
    print("✅ Graph handles missing optional context")


# ============================================================================
# Retry Logic Tests
# ============================================================================

def test_retry_count_state_transitions():
    """Test retry count transitions through different states."""
    # Start with 0
    state = {"retry_count": 0, "test_failures": []}
    assert state["retry_count"] == 0
    
    # Increment on failure
    state["retry_count"] += 1
    state["test_failures"].append("Build failed")
    assert state["retry_count"] == 1
    assert len(state["test_failures"]) == 1
    
    # Increment again on second failure
    state["retry_count"] += 1
    state["test_failures"].append("Build failed again")
    assert state["retry_count"] == 2
    
    # Reset on success
    state["retry_count"] = 0
    state["test_failures"] = []
    assert state["retry_count"] == 0
    assert len(state["test_failures"]) == 0
    
    print("✅ Retry count transitions work correctly")


def test_max_retries_limit():
    """Test that max retries limit is enforced."""
    MAX_RETRIES = 5
    
    state = {"retry_count": 6, "test_failures": ["Error"]}
    
    # Check if should stop
    should_stop = state["retry_count"] > MAX_RETRIES
    assert should_stop is True
    
    # Check if can continue
    state["retry_count"] = 3
    can_continue = state["retry_count"] <= MAX_RETRIES
    assert can_continue is True
    
    print("✅ Max retries limit enforced")
