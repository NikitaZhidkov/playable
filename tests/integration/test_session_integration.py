"""
Integration tests for src/session.py

Tests cover:
- Full session lifecycle (create, save, load, modify, save again)
- Multiple session management
- Concurrent session operations
- Session persistence across saves/loads
- Integration with message history
- Graph state persistence and restoration
- Real filesystem operations

Unit tests are in tests/test_session.py
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.session import (
    Session,
    create_session,
    save_session,
    load_session,
    list_sessions,
    get_session_path,
    get_game_path,
    get_agent_path,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_base_path(tmp_path):
    """Create temporary base path for session storage."""
    return tmp_path / "games"


# ============================================================================
# Integration Tests - Full Session Lifecycle
# ============================================================================

def test_complete_session_lifecycle(temp_base_path):
    """Test creating, modifying, saving, and loading a session."""
    # 1. Create session
    session = create_session(
        "Create a racing game",
        base_path=temp_base_path,
        selected_pack="Racing Pack"
    )
    
    session_id = session.session_id
    assert session.initial_prompt == "Create a racing game"
    assert session.status == "in_progress"
    assert session.selected_pack == "Racing Pack"
    
    # 2. Add iterations and messages
    session.add_iteration("Make it faster", "2025-11-16T10:00:00")
    session.add_iteration("Add more cars", "2025-11-16T11:00:00")
    
    messages = [
        HumanMessage(content="Create a racing game"),
        AIMessage(content="Creating game...", tool_calls=[{"name": "write_file", "args": {}, "id": "call_1"}]),
        ToolMessage(content="Success", tool_call_id="call_1"),
    ]
    session.set_message_history(messages)
    
    # 3. Update graph state
    graph_state = {
        "retry_count": 2,
        "test_failures": ["test1 failed"],
        "is_completed": False,
        "is_feedback_mode": True,
        "original_prompt": "Create a racing game",
        "task_description": "Building racing game"
    }
    session.save_graph_state(graph_state)
    
    # 4. Update status and error
    session.status = "failed"
    session.last_error = "Build failed: missing asset"
    session.game_designer_output = "# Racing Game GDD\nA fast-paced racing game..."
    
    # 5. Save session
    save_session(session, base_path=temp_base_path)
    
    # 6. Load session back
    loaded = load_session(session_id, base_path=temp_base_path)
    
    # 7. Verify all data persisted
    assert loaded is not None
    assert loaded.session_id == session_id
    assert loaded.initial_prompt == "Create a racing game"
    assert loaded.selected_pack == "Racing Pack"
    assert loaded.status == "failed"
    assert loaded.last_error == "Build failed: missing asset"
    assert len(loaded.iterations) == 2
    assert loaded.iterations[0]["feedback"] == "Make it faster"
    assert loaded.iterations[1]["feedback"] == "Add more cars"
    assert len(loaded.message_history) == 3
    assert loaded.graph_state["retry_count"] == 2
    assert loaded.graph_state["test_failures"] == ["test1 failed"]
    assert loaded.graph_state["is_feedback_mode"] is True
    assert "Racing Game GDD" in loaded.game_designer_output


def test_session_modification_and_resave(temp_base_path):
    """Test modifying and resaving a session multiple times."""
    # Create initial session
    session = create_session("Original prompt", base_path=temp_base_path)
    session_id = session.session_id
    
    # First modification
    session.add_iteration("Iteration 1", "2025-11-16T10:00:00")
    session.status = "in_progress"
    save_session(session, base_path=temp_base_path)
    
    # Load and modify again
    session = load_session(session_id, base_path=temp_base_path)
    session.add_iteration("Iteration 2", "2025-11-16T11:00:00")
    session.status = "completed"
    save_session(session, base_path=temp_base_path)
    
    # Load and modify one more time
    session = load_session(session_id, base_path=temp_base_path)
    session.add_iteration("Iteration 3", "2025-11-16T12:00:00")
    save_session(session, base_path=temp_base_path)
    
    # Final verification
    final_session = load_session(session_id, base_path=temp_base_path)
    assert len(final_session.iterations) == 3
    assert final_session.status == "completed"
    assert final_session.iterations[0]["feedback"] == "Iteration 1"
    assert final_session.iterations[1]["feedback"] == "Iteration 2"
    assert final_session.iterations[2]["feedback"] == "Iteration 3"


def test_session_directories_structure(temp_base_path):
    """Test that session creation creates proper directory structure."""
    session = create_session("Test", base_path=temp_base_path)
    
    session_path = get_session_path(session.session_id, base_path=temp_base_path)
    game_path = get_game_path(session.session_id, base_path=temp_base_path)
    agent_path = get_agent_path(session.session_id, base_path=temp_base_path)
    
    # Verify all directories exist
    assert session_path.exists()
    assert session_path.is_dir()
    assert game_path.exists()
    assert game_path.is_dir()
    assert agent_path.exists()
    assert agent_path.is_dir()
    
    # Verify session.json exists
    session_file = session_path / "session.json"
    assert session_file.exists()
    assert session_file.is_file()


# ============================================================================
# Integration Tests - Multiple Sessions
# ============================================================================

def test_multiple_sessions_creation_and_listing(temp_base_path):
    """Test creating multiple sessions and listing them."""
    # Create multiple sessions
    prompts = [
        "Create a racing game",
        "Create a puzzle game",
        "Create a shooter game",
        "Create a platformer game",
        "Create an adventure game",
    ]
    
    created_ids = []
    for i, prompt in enumerate(prompts):
        session = create_session(
            prompt,
            base_path=temp_base_path,
            selected_pack=f"Pack {i}"
        )
        created_ids.append(session.session_id)
        # Add some variation to each session
        session.add_iteration(f"Iteration {i}", f"2025-11-16T{i:02d}:00:00")
        session.status = "completed" if i % 2 == 0 else "in_progress"
        save_session(session, base_path=temp_base_path)
    
    # List all sessions
    sessions = list_sessions(base_path=temp_base_path, limit=10)
    
    assert len(sessions) == 5
    # Verify all created sessions are in the list
    listed_ids = [s.session_id for s in sessions]
    for created_id in created_ids:
        assert created_id in listed_ids


def test_sessions_isolation(temp_base_path):
    """Test that sessions don't interfere with each other."""
    # Create two sessions
    session1 = create_session("Game 1", base_path=temp_base_path, selected_pack="Pack A")
    session2 = create_session("Game 2", base_path=temp_base_path, selected_pack="Pack B")
    
    # Modify session 1
    session1.add_iteration("Feedback 1", "2025-11-16T10:00:00")
    session1.status = "completed"
    session1.last_error = "Error in session 1"
    save_session(session1, base_path=temp_base_path)
    
    # Modify session 2
    session2.add_iteration("Feedback 2", "2025-11-16T11:00:00")
    session2.status = "failed"
    session2.last_error = "Error in session 2"
    save_session(session2, base_path=temp_base_path)
    
    # Load both back and verify they're independent
    loaded1 = load_session(session1.session_id, base_path=temp_base_path)
    loaded2 = load_session(session2.session_id, base_path=temp_base_path)
    
    assert loaded1.initial_prompt == "Game 1"
    assert loaded1.selected_pack == "Pack A"
    assert loaded1.status == "completed"
    assert loaded1.last_error == "Error in session 1"
    assert len(loaded1.iterations) == 1
    assert loaded1.iterations[0]["feedback"] == "Feedback 1"
    
    assert loaded2.initial_prompt == "Game 2"
    assert loaded2.selected_pack == "Pack B"
    assert loaded2.status == "failed"
    assert loaded2.last_error == "Error in session 2"
    assert len(loaded2.iterations) == 1
    assert loaded2.iterations[0]["feedback"] == "Feedback 2"


def test_list_sessions_pagination(temp_base_path):
    """Test listing sessions with different limits."""
    # Create 10 sessions
    for i in range(10):
        session = create_session(f"Game {i}", base_path=temp_base_path)
        save_session(session, base_path=temp_base_path)
    
    # Test different limits
    all_sessions = list_sessions(base_path=temp_base_path, limit=100)
    assert len(all_sessions) == 10
    
    limited_sessions = list_sessions(base_path=temp_base_path, limit=5)
    assert len(limited_sessions) == 5
    
    single_session = list_sessions(base_path=temp_base_path, limit=1)
    assert len(single_session) == 1


# ============================================================================
# Integration Tests - Message History Persistence
# ============================================================================

def test_message_history_full_persistence(temp_base_path):
    """Test that complex message history persists correctly."""
    session = create_session("Test", base_path=temp_base_path)
    
    # Create complex message history
    messages = [
        HumanMessage(content="Create a game"),
        AIMessage(content="Creating...", tool_calls=[
            {"name": "write_file", "args": {"path": "game.js"}, "id": "call_1"},
            {"name": "read_file", "args": {"path": "config.json"}, "id": "call_2"},
        ]),
        ToolMessage(content="File written successfully", tool_call_id="call_1"),
        ToolMessage(content='{"width": 800}', tool_call_id="call_2"),
        AIMessage(content="Game created successfully"),
        HumanMessage(content="Make it faster"),
        AIMessage(content="Optimizing...", tool_calls=[
            {"name": "edit_file", "args": {"path": "game.js"}, "id": "call_3"},
        ]),
        ToolMessage(content="File edited", tool_call_id="call_3"),
        AIMessage(content="Optimization complete"),
    ]
    
    session.set_message_history(messages)
    save_session(session, base_path=temp_base_path)
    
    # Load and verify
    loaded = load_session(session.session_id, base_path=temp_base_path)
    restored_messages = loaded.get_langchain_messages()
    
    assert len(restored_messages) == 9
    
    # Verify message types and content
    assert isinstance(restored_messages[0], HumanMessage)
    assert restored_messages[0].content == "Create a game"
    
    assert isinstance(restored_messages[1], AIMessage)
    assert len(restored_messages[1].tool_calls) == 2
    
    assert isinstance(restored_messages[2], ToolMessage)
    assert restored_messages[2].tool_call_id == "call_1"
    
    assert isinstance(restored_messages[3], ToolMessage)
    assert restored_messages[3].tool_call_id == "call_2"
    
    assert isinstance(restored_messages[4], AIMessage)
    assert restored_messages[4].content == "Game created successfully"


def test_message_history_updates_across_saves(temp_base_path):
    """Test that message history accumulates across multiple saves."""
    session = create_session("Test", base_path=temp_base_path)
    session_id = session.session_id
    
    # First batch of messages
    messages1 = [
        HumanMessage(content="Message 1"),
        AIMessage(content="Response 1"),
    ]
    session.set_message_history(messages1)
    save_session(session, base_path=temp_base_path)
    
    # Load and add more messages
    session = load_session(session_id, base_path=temp_base_path)
    existing_messages = session.get_langchain_messages()
    new_messages = [
        HumanMessage(content="Message 2"),
        AIMessage(content="Response 2"),
    ]
    all_messages = existing_messages + new_messages
    session.set_message_history(all_messages)
    save_session(session, base_path=temp_base_path)
    
    # Load and add even more messages
    session = load_session(session_id, base_path=temp_base_path)
    existing_messages = session.get_langchain_messages()
    new_messages = [
        HumanMessage(content="Message 3"),
        AIMessage(content="Response 3"),
    ]
    all_messages = existing_messages + new_messages
    session.set_message_history(all_messages)
    save_session(session, base_path=temp_base_path)
    
    # Final verification
    final_session = load_session(session_id, base_path=temp_base_path)
    final_messages = final_session.get_langchain_messages()
    
    assert len(final_messages) == 6
    assert final_messages[0].content == "Message 1"
    assert final_messages[1].content == "Response 1"
    assert final_messages[2].content == "Message 2"
    assert final_messages[3].content == "Response 2"
    assert final_messages[4].content == "Message 3"
    assert final_messages[5].content == "Response 3"


# ============================================================================
# Integration Tests - Graph State Persistence
# ============================================================================

def test_graph_state_persistence_and_restoration(temp_base_path):
    """Test that graph state persists and can be restored correctly."""
    session = create_session("Test", base_path=temp_base_path)
    
    # Save complex graph state
    graph_state = {
        "retry_count": 5,
        "test_failures": [
            "Test 1 failed: assertion error",
            "Test 2 failed: timeout",
            "Test 3 failed: missing asset",
        ],
        "is_completed": False,
        "is_feedback_mode": True,
        "original_prompt": "Create an epic game",
        "task_description": "Building game with feedback loop",
    }
    session.save_graph_state(graph_state)
    save_session(session, base_path=temp_base_path)
    
    # Load and verify
    loaded = load_session(session.session_id, base_path=temp_base_path)
    restored_state = loaded.get_graph_state()
    
    assert restored_state["retry_count"] == 5
    assert len(restored_state["test_failures"]) == 3
    assert restored_state["test_failures"][0] == "Test 1 failed: assertion error"
    assert restored_state["is_completed"] is False
    assert restored_state["is_feedback_mode"] is True
    assert restored_state["original_prompt"] == "Create an epic game"
    assert restored_state["task_description"] == "Building game with feedback loop"


def test_graph_state_updates_across_iterations(temp_base_path):
    """Test that graph state can be updated across iterations."""
    session = create_session("Test", base_path=temp_base_path)
    session_id = session.session_id
    
    # Initial state
    state1 = {
        "retry_count": 1,
        "test_failures": ["Error 1"],
        "is_completed": False,
    }
    session.save_graph_state(state1)
    save_session(session, base_path=temp_base_path)
    
    # Update state - add more failures
    session = load_session(session_id, base_path=temp_base_path)
    state2 = {
        "retry_count": 2,
        "test_failures": ["Error 1", "Error 2"],
        "is_completed": False,
    }
    session.save_graph_state(state2)
    save_session(session, base_path=temp_base_path)
    
    # Final update - complete
    session = load_session(session_id, base_path=temp_base_path)
    state3 = {
        "retry_count": 3,
        "test_failures": [],
        "is_completed": True,
    }
    session.save_graph_state(state3)
    save_session(session, base_path=temp_base_path)
    
    # Verify final state
    final_session = load_session(session_id, base_path=temp_base_path)
    final_state = final_session.get_graph_state()
    
    assert final_state["retry_count"] == 3
    assert final_state["test_failures"] == []
    assert final_state["is_completed"] is True


# ============================================================================
# Integration Tests - Error Scenarios
# ============================================================================

def test_session_with_error_tracking(temp_base_path):
    """Test tracking errors across session lifecycle."""
    session = create_session("Test", base_path=temp_base_path)
    
    # First error
    session.status = "failed"
    session.last_error = "Build failed: syntax error in game.js line 42"
    session.add_iteration("Fix syntax error", "2025-11-16T10:00:00")
    save_session(session, base_path=temp_base_path)
    
    # Load, fix, second error
    session = load_session(session.session_id, base_path=temp_base_path)
    session.status = "failed"
    session.last_error = "Test failed: missing asset car.png"
    session.add_iteration("Add missing asset", "2025-11-16T11:00:00")
    save_session(session, base_path=temp_base_path)
    
    # Load, fix, success
    session = load_session(session.session_id, base_path=temp_base_path)
    session.status = "completed"
    session.last_error = None
    session.add_iteration("Fixed all issues", "2025-11-16T12:00:00")
    save_session(session, base_path=temp_base_path)
    
    # Verify final state
    final_session = load_session(session.session_id, base_path=temp_base_path)
    assert final_session.status == "completed"
    assert final_session.last_error is None
    assert len(final_session.iterations) == 3


def test_session_handles_empty_values(temp_base_path):
    """Test session handles empty/null values correctly."""
    session = create_session("Test", base_path=temp_base_path)
    
    # Set various empty values
    session.selected_pack = None
    session.git_branch = None
    session.last_error = None
    session.game_designer_output = None
    session.set_message_history([])
    session.save_graph_state({})
    
    save_session(session, base_path=temp_base_path)
    
    # Load and verify
    loaded = load_session(session.session_id, base_path=temp_base_path)
    
    assert loaded.selected_pack is None
    assert loaded.git_branch is None
    assert loaded.last_error is None
    assert loaded.game_designer_output is None
    assert loaded.message_history == []
    assert loaded.get_langchain_messages() == []
    # Empty graph state still has default values after save_graph_state({})
    graph_state = loaded.get_graph_state()
    assert graph_state["retry_count"] == 0
    assert graph_state["is_completed"] is False
    assert graph_state["is_feedback_mode"] is False


# ============================================================================
# Integration Tests - Real World Scenarios
# ============================================================================

def test_feedback_loop_simulation(temp_base_path):
    """Simulate a complete feedback loop with multiple iterations."""
    # Initial creation
    session = create_session(
        "Create a racing game with 3 cars",
        base_path=temp_base_path,
        selected_pack="Racing Pack"
    )
    session_id = session.session_id
    
    # First iteration: build game
    messages = [
        HumanMessage(content="Create a racing game with 3 cars"),
        AIMessage(content="Creating game...", tool_calls=[{"name": "write_file", "args": {}, "id": "call_1"}]),
        ToolMessage(content="Success", tool_call_id="call_1"),
        AIMessage(content="Game created"),
    ]
    session.set_message_history(messages)
    session.save_graph_state({"retry_count": 0, "is_completed": True})
    session.status = "completed"
    save_session(session, base_path=temp_base_path)
    
    # Feedback iteration 1: add more cars
    session = load_session(session_id, base_path=temp_base_path)
    session.add_iteration("Add 2 more cars (total 5)", "2025-11-16T10:00:00")
    existing_msgs = session.get_langchain_messages()
    new_msgs = [
        HumanMessage(content="Add 2 more cars (total 5)"),
        AIMessage(content="Adding cars...", tool_calls=[{"name": "edit_file", "args": {}, "id": "call_2"}]),
        ToolMessage(content="Success", tool_call_id="call_2"),
        AIMessage(content="Cars added"),
    ]
    session.set_message_history(existing_msgs + new_msgs)
    session.save_graph_state({"retry_count": 0, "is_completed": True, "is_feedback_mode": True})
    save_session(session, base_path=temp_base_path)
    
    # Feedback iteration 2: change colors
    session = load_session(session_id, base_path=temp_base_path)
    session.add_iteration("Make cars more colorful", "2025-11-16T11:00:00")
    existing_msgs = session.get_langchain_messages()
    new_msgs = [
        HumanMessage(content="Make cars more colorful"),
        AIMessage(content="Updating colors...", tool_calls=[{"name": "edit_file", "args": {}, "id": "call_3"}]),
        ToolMessage(content="Success", tool_call_id="call_3"),
        AIMessage(content="Colors updated"),
    ]
    session.set_message_history(existing_msgs + new_msgs)
    save_session(session, base_path=temp_base_path)
    
    # Final verification
    final_session = load_session(session_id, base_path=temp_base_path)
    
    assert final_session.initial_prompt == "Create a racing game with 3 cars"
    assert len(final_session.iterations) == 2
    assert final_session.iterations[0]["feedback"] == "Add 2 more cars (total 5)"
    assert final_session.iterations[1]["feedback"] == "Make cars more colorful"
    assert len(final_session.get_langchain_messages()) == 12  # 4 + 4 + 4
    assert final_session.status == "completed"


def test_failed_build_retry_simulation(temp_base_path):
    """Simulate a failed build with retries."""
    session = create_session("Create game", base_path=temp_base_path)
    session_id = session.session_id
    
    # First attempt - fail
    session.save_graph_state({
        "retry_count": 1,
        "test_failures": ["Syntax error"],
        "is_completed": False,
    })
    session.status = "failed"
    session.last_error = "Build failed: syntax error"
    save_session(session, base_path=temp_base_path)
    
    # Second attempt - fail again
    session = load_session(session_id, base_path=temp_base_path)
    session.save_graph_state({
        "retry_count": 2,
        "test_failures": ["Syntax error", "Missing asset"],
        "is_completed": False,
    })
    session.last_error = "Build failed: missing asset"
    save_session(session, base_path=temp_base_path)
    
    # Third attempt - success
    session = load_session(session_id, base_path=temp_base_path)
    session.save_graph_state({
        "retry_count": 3,
        "test_failures": [],
        "is_completed": True,
    })
    session.status = "completed"
    session.last_error = None
    save_session(session, base_path=temp_base_path)
    
    # Verify
    final = load_session(session_id, base_path=temp_base_path)
    assert final.graph_state["retry_count"] == 3
    assert final.graph_state["is_completed"] is True
    assert final.status == "completed"
    assert final.last_error is None

