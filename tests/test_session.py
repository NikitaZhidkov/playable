"""
Unit tests for src/session.py

Tests cover:
- Session class creation and serialization
- Session ID generation
- Message history conversion
- Graph state persistence
- Session file operations
- Path helper functions

Integration tests are in tests/integration/test_session_integration.py
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.session import (
    Session,
    generate_session_id,
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


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return Session(
        session_id="20251116_143022_ab12cd34",
        initial_prompt="Create a racing game",
        created_at="2025-11-16T14:30:22",
        last_modified="2025-11-16T15:45:10",
        iterations=[
            {"feedback": "Make it faster", "timestamp": "2025-11-16T15:00:00"}
        ],
        message_history=[
            {"type": "HumanMessage", "content": "Create game"},
            {"type": "AIMessage", "content": "Creating..."}
        ],
        selected_pack="Racing Pack",
        status="completed",
        git_branch="main",
        graph_state={"retry_count": 0, "is_completed": True},
        last_error=None,
        game_designer_output="# Racing Game GDD\n..."
    )


# ============================================================================
# Unit Tests - Session Class
# ============================================================================

def test_session_initialization():
    """Test Session class initialization with all parameters."""
    session = Session(
        session_id="test_123",
        initial_prompt="Test prompt",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    assert session.session_id == "test_123"
    assert session.initial_prompt == "Test prompt"
    assert session.iterations == []
    assert session.message_history == []
    assert session.selected_pack is None
    assert session.status == "in_progress"
    assert session.git_branch is None
    assert session.graph_state == {}
    assert session.last_error is None
    assert session.game_designer_output is None


def test_session_initialization_with_defaults():
    """Test Session with default values."""
    session = Session(
        session_id="test_123",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00",
        iterations=[{"test": "data"}],
        message_history=[{"type": "HumanMessage"}],
        selected_pack="Pack1",
        status="failed",
        git_branch="feature",
        graph_state={"key": "value"},
        last_error="Error message",
        game_designer_output="GDD content"
    )
    
    assert session.iterations == [{"test": "data"}]
    assert session.message_history == [{"type": "HumanMessage"}]
    assert session.selected_pack == "Pack1"
    assert session.status == "failed"
    assert session.git_branch == "feature"
    assert session.graph_state == {"key": "value"}
    assert session.last_error == "Error message"
    assert session.game_designer_output == "GDD content"


def test_session_to_dict(sample_session):
    """Test converting session to dictionary."""
    data = sample_session.to_dict()
    
    assert data["session_id"] == "20251116_143022_ab12cd34"
    assert data["initial_prompt"] == "Create a racing game"
    assert data["created_at"] == "2025-11-16T14:30:22"
    assert data["last_modified"] == "2025-11-16T15:45:10"
    assert len(data["iterations"]) == 1
    assert len(data["message_history"]) == 2
    assert data["selected_pack"] == "Racing Pack"
    assert data["status"] == "completed"
    assert data["git_branch"] == "main"
    assert data["graph_state"]["is_completed"] is True
    assert data["last_error"] is None
    assert "Racing Game GDD" in data["game_designer_output"]


def test_session_from_dict(sample_session):
    """Test creating session from dictionary."""
    data = sample_session.to_dict()
    restored = Session.from_dict(data)
    
    assert restored.session_id == sample_session.session_id
    assert restored.initial_prompt == sample_session.initial_prompt
    assert restored.created_at == sample_session.created_at
    assert restored.last_modified == sample_session.last_modified
    assert restored.iterations == sample_session.iterations
    assert restored.message_history == sample_session.message_history
    assert restored.selected_pack == sample_session.selected_pack
    assert restored.status == sample_session.status
    assert restored.git_branch == sample_session.git_branch
    assert restored.graph_state == sample_session.graph_state
    assert restored.last_error == sample_session.last_error
    assert restored.game_designer_output == sample_session.game_designer_output


def test_session_from_dict_with_missing_optional_fields():
    """Test creating session from dict with missing optional fields."""
    minimal_data = {
        "session_id": "test_123",
        "initial_prompt": "Test",
        "created_at": "2025-01-01T00:00:00",
        "last_modified": "2025-01-01T00:00:00"
    }
    
    session = Session.from_dict(minimal_data)
    
    assert session.session_id == "test_123"
    assert session.iterations == []
    assert session.message_history == []
    assert session.selected_pack is None
    assert session.status == "in_progress"
    assert session.git_branch is None
    assert session.graph_state == {}
    assert session.last_error is None
    assert session.game_designer_output is None


def test_session_serialization_roundtrip(sample_session):
    """Test that to_dict/from_dict is reversible."""
    data = sample_session.to_dict()
    restored = Session.from_dict(data)
    data2 = restored.to_dict()
    
    assert data == data2


# ============================================================================
# Unit Tests - Session Methods
# ============================================================================

def test_add_iteration():
    """Test adding feedback iteration to session."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    assert len(session.iterations) == 0
    
    session.add_iteration("Make it faster", "2025-01-01T01:00:00")
    
    assert len(session.iterations) == 1
    assert session.iterations[0]["feedback"] == "Make it faster"
    assert session.iterations[0]["timestamp"] == "2025-01-01T01:00:00"
    assert session.last_modified == "2025-01-01T01:00:00"


def test_add_multiple_iterations():
    """Test adding multiple iterations."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    session.add_iteration("Feedback 1", "2025-01-01T01:00:00")
    session.add_iteration("Feedback 2", "2025-01-01T02:00:00")
    session.add_iteration("Feedback 3", "2025-01-01T03:00:00")
    
    assert len(session.iterations) == 3
    assert session.iterations[0]["feedback"] == "Feedback 1"
    assert session.iterations[1]["feedback"] == "Feedback 2"
    assert session.iterations[2]["feedback"] == "Feedback 3"
    assert session.last_modified == "2025-01-01T03:00:00"


def test_set_message_history_with_langchain_messages():
    """Test converting LangChain messages to storable format."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    messages = [
        HumanMessage(content="Create a game"),
        AIMessage(content="Creating game...", tool_calls=[{"name": "write_file", "args": {}, "id": "call_123"}]),
        ToolMessage(content="success", tool_call_id="call_123"),
    ]
    
    session.set_message_history(messages)
    
    assert len(session.message_history) == 3
    assert session.message_history[0]["type"] == "HumanMessage"
    assert session.message_history[0]["content"] == "Create a game"
    assert session.message_history[1]["type"] == "AIMessage"
    assert len(session.message_history[1]["tool_calls"]) == 1
    assert session.message_history[1]["tool_calls"][0]["name"] == "write_file"
    assert session.message_history[1]["tool_calls"][0]["id"] == "call_123"
    assert session.message_history[2]["type"] == "ToolMessage"
    assert session.message_history[2]["tool_call_id"] == "call_123"


def test_set_message_history_empty():
    """Test setting empty message history."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    session.set_message_history([])
    
    assert session.message_history == []


def test_get_langchain_messages():
    """Test converting stored messages back to LangChain format."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00",
        message_history=[
            {"type": "HumanMessage", "content": "Hello"},
            {"type": "AIMessage", "content": "Hi", "tool_calls": [{"name": "test", "args": {}, "id": "call_1"}]},
            {"type": "ToolMessage", "content": "success", "tool_call_id": "call_1"},
        ]
    )
    
    messages = session.get_langchain_messages()
    
    assert len(messages) == 3
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Hello"
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "Hi"
    assert len(messages[1].tool_calls) == 1
    assert messages[1].tool_calls[0]["name"] == "test"
    assert messages[1].tool_calls[0]["id"] == "call_1"
    assert isinstance(messages[2], ToolMessage)
    assert messages[2].content == "success"
    assert messages[2].tool_call_id == "call_1"


def test_get_langchain_messages_empty():
    """Test getting LangChain messages from empty history."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    messages = session.get_langchain_messages()
    
    assert messages == []


def test_message_history_roundtrip():
    """Test that message conversion is reversible."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    original_messages = [
        HumanMessage(content="Create game"),
        AIMessage(content="Creating...", tool_calls=[{"name": "write_file", "args": {}, "id": "1"}]),
        ToolMessage(content="done", tool_call_id="1"),
    ]
    
    session.set_message_history(original_messages)
    restored_messages = session.get_langchain_messages()
    
    assert len(restored_messages) == len(original_messages)
    assert all(isinstance(restored_messages[i], type(original_messages[i])) 
               for i in range(len(original_messages)))


def test_save_graph_state():
    """Test saving graph state."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    state = {
        "retry_count": 3,
        "test_failures": ["error1", "error2"],
        "is_completed": False,
        "is_feedback_mode": True,
        "original_prompt": "Original",
        "task_description": "Task",
        "extra_field": "should be ignored"  # Not in saved fields
    }
    
    session.save_graph_state(state)
    
    assert session.graph_state["retry_count"] == 3
    assert session.graph_state["test_failures"] == ["error1", "error2"]
    assert session.graph_state["is_completed"] is False
    assert session.graph_state["is_feedback_mode"] is True
    assert session.graph_state["original_prompt"] == "Original"
    assert session.graph_state["task_description"] == "Task"
    assert "extra_field" not in session.graph_state


def test_save_graph_state_with_defaults():
    """Test saving graph state with missing fields."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    state = {}  # Empty state
    
    session.save_graph_state(state)
    
    assert session.graph_state["retry_count"] == 0
    assert session.graph_state["test_failures"] == []
    assert session.graph_state["is_completed"] is False
    assert session.graph_state["is_feedback_mode"] is False
    assert session.graph_state["original_prompt"] == ""
    assert session.graph_state["task_description"] == ""


def test_get_graph_state():
    """Test retrieving graph state."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00",
        graph_state={"retry_count": 5, "is_completed": True}
    )
    
    state = session.get_graph_state()
    
    assert state["retry_count"] == 5
    assert state["is_completed"] is True
    # Verify it's a copy, not the original
    state["retry_count"] = 10
    assert session.graph_state["retry_count"] == 5


def test_get_graph_state_empty():
    """Test retrieving empty graph state."""
    session = Session(
        session_id="test",
        initial_prompt="Test",
        created_at="2025-01-01T00:00:00",
        last_modified="2025-01-01T00:00:00"
    )
    
    state = session.get_graph_state()
    
    assert state == {}


# ============================================================================
# Unit Tests - Session ID Generation
# ============================================================================

def test_generate_session_id_format():
    """Test that generated session ID has correct format."""
    session_id = generate_session_id()
    
    # Format: YYYYMMDD_HHMMSS_<8-char-uuid>
    parts = session_id.split("_")
    
    assert len(parts) == 3
    assert len(parts[0]) == 8  # YYYYMMDD
    assert len(parts[1]) == 6  # HHMMSS
    assert len(parts[2]) == 8  # Short UUID


def test_generate_session_id_uniqueness():
    """Test that generated IDs are unique."""
    ids = [generate_session_id() for _ in range(100)]
    
    assert len(set(ids)) == 100  # All unique


@patch('src.session.datetime')
def test_generate_session_id_timestamp(mock_datetime):
    """Test that session ID contains correct timestamp."""
    mock_datetime.now.return_value.strftime.return_value = "20251116_143022"
    
    session_id = generate_session_id()
    
    assert session_id.startswith("20251116_143022_")


# ============================================================================
# Unit Tests - Path Helper Functions
# ============================================================================

def test_get_session_path():
    """Test getting session path."""
    path = get_session_path("test_session_123")
    
    assert path == Path("games/test_session_123")


def test_get_session_path_with_custom_base():
    """Test getting session path with custom base."""
    path = get_session_path("test_123", base_path=Path("/tmp/sessions"))
    
    assert path == Path("/tmp/sessions/test_123")


def test_get_game_path():
    """Test getting game path."""
    path = get_game_path("test_session_123")
    
    assert path == Path("games/test_session_123/game")


def test_get_game_path_with_custom_base():
    """Test getting game path with custom base."""
    path = get_game_path("test_123", base_path=Path("/tmp/sessions"))
    
    assert path == Path("/tmp/sessions/test_123/game")


def test_get_agent_path():
    """Test getting agent path."""
    path = get_agent_path("test_session_123")
    
    assert path == Path("games/test_session_123/agent")


def test_get_agent_path_with_custom_base():
    """Test getting agent path with custom base."""
    path = get_agent_path("test_123", base_path=Path("/tmp/sessions"))
    
    assert path == Path("/tmp/sessions/test_123/agent")


# ============================================================================
# Unit Tests - Session File Operations
# ============================================================================

def test_save_session_creates_file(temp_base_path, sample_session):
    """Test that save_session creates session.json file."""
    # Create session directory
    session_dir = temp_base_path / sample_session.session_id
    session_dir.mkdir(parents=True)
    
    save_session(sample_session, base_path=temp_base_path)
    
    session_file = session_dir / "session.json"
    assert session_file.exists()


def test_save_session_content(temp_base_path, sample_session):
    """Test that saved session has correct JSON content."""
    session_dir = temp_base_path / sample_session.session_id
    session_dir.mkdir(parents=True)
    
    save_session(sample_session, base_path=temp_base_path)
    
    session_file = session_dir / "session.json"
    with open(session_file) as f:
        data = json.load(f)
    
    assert data["session_id"] == sample_session.session_id
    assert data["initial_prompt"] == sample_session.initial_prompt
    assert data["status"] == "completed"


def test_load_session_success(temp_base_path, sample_session):
    """Test loading session from file."""
    session_dir = temp_base_path / sample_session.session_id
    session_dir.mkdir(parents=True)
    save_session(sample_session, base_path=temp_base_path)
    
    loaded = load_session(sample_session.session_id, base_path=temp_base_path)
    
    assert loaded is not None
    assert loaded.session_id == sample_session.session_id
    assert loaded.initial_prompt == sample_session.initial_prompt
    assert loaded.status == sample_session.status


def test_load_session_not_found(temp_base_path):
    """Test loading non-existent session."""
    loaded = load_session("nonexistent_session", base_path=temp_base_path)
    
    assert loaded is None


def test_load_session_corrupted_json(temp_base_path):
    """Test loading session with corrupted JSON."""
    session_id = "corrupted_session"
    session_dir = temp_base_path / session_id
    session_dir.mkdir(parents=True)
    
    # Write invalid JSON
    session_file = session_dir / "session.json"
    session_file.write_text("{ invalid json }", encoding="utf-8")
    
    loaded = load_session(session_id, base_path=temp_base_path)
    
    assert loaded is None


# ============================================================================
# Unit Tests - List Sessions
# ============================================================================

def test_list_sessions_empty_directory(temp_base_path):
    """Test listing sessions with no sessions."""
    temp_base_path.mkdir(parents=True)
    
    sessions = list_sessions(base_path=temp_base_path)
    
    assert sessions == []


def test_list_sessions_nonexistent_directory():
    """Test listing sessions when base path doesn't exist."""
    sessions = list_sessions(base_path=Path("/nonexistent/path"))
    
    assert sessions == []


def test_list_sessions_sorts_by_newest(temp_base_path):
    """Test that sessions are sorted by session ID (newest first)."""
    temp_base_path.mkdir(parents=True)
    
    # Create sessions with different timestamps
    sessions_data = [
        ("20251116_100000_aaaaaaaa", "First"),
        ("20251116_120000_bbbbbbbb", "Second"),
        ("20251116_110000_cccccccc", "Third"),
    ]
    
    for session_id, prompt in sessions_data:
        session = Session(
            session_id=session_id,
            initial_prompt=prompt,
            created_at="2025-11-16T00:00:00",
            last_modified="2025-11-16T00:00:00"
        )
        session_dir = temp_base_path / session_id
        session_dir.mkdir(parents=True)
        save_session(session, base_path=temp_base_path)
    
    sessions = list_sessions(base_path=temp_base_path, limit=10)
    
    assert len(sessions) == 3
    assert sessions[0].initial_prompt == "Second"  # 12:00 - newest
    assert sessions[1].initial_prompt == "Third"   # 11:00
    assert sessions[2].initial_prompt == "First"   # 10:00 - oldest


def test_list_sessions_respects_limit(temp_base_path):
    """Test that list_sessions respects the limit parameter."""
    temp_base_path.mkdir(parents=True)
    
    # Create 10 sessions
    for i in range(10):
        session_id = f"2025111{i}_000000_test{i:04d}"
        session = Session(
            session_id=session_id,
            initial_prompt=f"Prompt {i}",
            created_at="2025-11-16T00:00:00",
            last_modified="2025-11-16T00:00:00"
        )
        session_dir = temp_base_path / session_id
        session_dir.mkdir(parents=True)
        save_session(session, base_path=temp_base_path)
    
    sessions = list_sessions(base_path=temp_base_path, limit=3)
    
    assert len(sessions) == 3


def test_list_sessions_skips_invalid_directories(temp_base_path):
    """Test that list_sessions skips directories without session.json."""
    temp_base_path.mkdir(parents=True)
    
    # Create valid session
    valid_session = Session(
        session_id="20251116_100000_valid123",
        initial_prompt="Valid",
        created_at="2025-11-16T00:00:00",
        last_modified="2025-11-16T00:00:00"
    )
    valid_dir = temp_base_path / valid_session.session_id
    valid_dir.mkdir(parents=True)
    save_session(valid_session, base_path=temp_base_path)
    
    # Create directory without session.json
    invalid_dir = temp_base_path / "invalid_session"
    invalid_dir.mkdir(parents=True)
    
    # Create regular file (not directory)
    (temp_base_path / "regular_file.txt").write_text("not a session")
    
    sessions = list_sessions(base_path=temp_base_path)
    
    assert len(sessions) == 1
    assert sessions[0].session_id == valid_session.session_id


# ============================================================================
# Unit Tests - Create Session
# ============================================================================

def test_create_session_basic(temp_base_path):
    """Test creating a new session."""
    session = create_session("Create a racing game", base_path=temp_base_path)
    
    assert session.session_id is not None
    assert session.initial_prompt == "Create a racing game"
    assert session.created_at is not None
    assert session.last_modified is not None
    assert session.status == "in_progress"
    assert session.iterations == []
    assert session.message_history == []


def test_create_session_with_asset_pack(temp_base_path):
    """Test creating session with asset pack."""
    session = create_session(
        "Create game",
        base_path=temp_base_path,
        selected_pack="Racing Pack"
    )
    
    assert session.selected_pack == "Racing Pack"


def test_create_session_creates_directories(temp_base_path):
    """Test that create_session creates required directories."""
    session = create_session("Test", base_path=temp_base_path)
    
    session_dir = temp_base_path / session.session_id
    game_dir = session_dir / "game"
    agent_dir = session_dir / "agent"
    
    assert session_dir.exists()
    assert game_dir.exists()
    assert agent_dir.exists()


def test_create_session_saves_metadata(temp_base_path):
    """Test that create_session saves session.json."""
    session = create_session("Test", base_path=temp_base_path)
    
    session_file = temp_base_path / session.session_id / "session.json"
    assert session_file.exists()
    
    # Verify can be loaded back
    loaded = load_session(session.session_id, base_path=temp_base_path)
    assert loaded.initial_prompt == "Test"

