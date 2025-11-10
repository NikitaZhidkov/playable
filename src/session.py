"""
Session management for game development projects.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Session:
    """Represents a game development session."""
    
    def __init__(
        self,
        session_id: str,
        initial_prompt: str,
        created_at: str,
        last_modified: str,
        iterations: list[dict] = None,
        message_history: list[dict] = None,
        selected_pack: Optional[str] = None,
        status: str = "in_progress",
        git_branch: Optional[str] = None,
        graph_state: Optional[dict] = None,
        last_error: Optional[str] = None,
        game_designer_output: Optional[str] = None
    ):
        self.session_id = session_id
        self.initial_prompt = initial_prompt
        self.created_at = created_at
        self.last_modified = last_modified
        self.iterations = iterations or []
        self.message_history = message_history or []
        self.selected_pack = selected_pack
        self.status = status
        self.git_branch = git_branch
        self.graph_state = graph_state or {}
        self.last_error = last_error
        self.game_designer_output = game_designer_output
    
    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "initial_prompt": self.initial_prompt,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "iterations": self.iterations,
            "message_history": self.message_history,
            "selected_pack": self.selected_pack,
            "status": self.status,
            "git_branch": self.git_branch,
            "graph_state": self.graph_state,
            "last_error": self.last_error,
            "game_designer_output": self.game_designer_output
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create session from dictionary."""
        return cls(
            session_id=data["session_id"],
            initial_prompt=data["initial_prompt"],
            created_at=data["created_at"],
            last_modified=data["last_modified"],
            iterations=data.get("iterations", []),
            message_history=data.get("message_history", []),
            selected_pack=data.get("selected_pack"),
            status=data.get("status", "in_progress"),
            git_branch=data.get("git_branch"),
            graph_state=data.get("graph_state", {}),
            last_error=data.get("last_error"),
            game_designer_output=data.get("game_designer_output")
        )
    
    def add_iteration(self, feedback: str, timestamp: str):
        """Add a feedback iteration to the session."""
        self.iterations.append({
            "feedback": feedback,
            "timestamp": timestamp
        })
        self.last_modified = timestamp
    
    def set_message_history(self, messages: list):
        """Save message history for this session."""
        # Convert LangChain messages to serializable format
        self.message_history = []
        for msg in messages:
            msg_dict = {
                "type": msg.__class__.__name__,
                "content": msg.content
            }
            # Include tool calls if present
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            # Include tool_call_id for tool messages
            if hasattr(msg, 'tool_call_id'):
                msg_dict["tool_call_id"] = msg.tool_call_id
            self.message_history.append(msg_dict)
    
    def get_langchain_messages(self) -> list:
        """Convert stored message history back to LangChain messages."""
        from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
        
        messages = []
        for msg_dict in self.message_history:
            msg_type = msg_dict.get("type", "HumanMessage")
            content = msg_dict.get("content", "")
            
            if msg_type == "HumanMessage":
                messages.append(HumanMessage(content=content))
            elif msg_type == "AIMessage":
                tool_calls = msg_dict.get("tool_calls", [])
                messages.append(AIMessage(content=content, tool_calls=tool_calls))
            elif msg_type == "ToolMessage":
                tool_call_id = msg_dict.get("tool_call_id", "")
                messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
        
        return messages
    
    def save_graph_state(self, state: dict):
        """Save essential graph state for recovery."""
        self.graph_state = {
            "retry_count": state.get("retry_count", 0),
            "test_failures": state.get("test_failures", []),
            "is_completed": state.get("is_completed", False),
            "is_feedback_mode": state.get("is_feedback_mode", False),
            "original_prompt": state.get("original_prompt", ""),
            "task_description": state.get("task_description", "")
        }
    
    def get_graph_state(self) -> dict:
        """Retrieve saved graph state."""
        return self.graph_state.copy() if self.graph_state else {}


def generate_session_id() -> str:
    """
    Generate a unique session ID with timestamp prefix.
    Format: YYYYMMDD_HHMMSS_<short_uuid>
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{timestamp}_{short_uuid}"


def create_session(initial_prompt: str, base_path: Path = Path("games"), selected_pack: Optional[str] = None) -> Session:
    """Create a new session."""
    session_id = generate_session_id()
    timestamp = datetime.now().isoformat()
    
    session = Session(
        session_id=session_id,
        initial_prompt=initial_prompt,
        created_at=timestamp,
        last_modified=timestamp,
        selected_pack=selected_pack
    )
    
    # Create session directory structure
    session_path = base_path / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    (session_path / "game").mkdir(exist_ok=True)
    (session_path / "agent").mkdir(exist_ok=True)
    
    # Save session metadata
    save_session(session, base_path)
    
    logger.info(f"Created new session: {session_id}")
    return session


def save_session(session: Session, base_path: Path = Path("games")):
    """Save session metadata to JSON file."""
    session_path = base_path / session.session_id / "session.json"
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session.to_dict(), f, indent=2)
    logger.info(f"Saved session metadata: {session.session_id}")


def load_session(session_id: str, base_path: Path = Path("games")) -> Optional[Session]:
    """Load session metadata from JSON file."""
    session_path = base_path / session_id / "session.json"
    
    if not session_path.exists():
        logger.warning(f"Session file not found: {session_path}")
        return None
    
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session = Session.from_dict(data)
        logger.info(f"Loaded session: {session_id}")
        return session
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
        return None


def list_sessions(base_path: Path = Path("games"), limit: int = 5) -> list[Session]:
    """
    List recent sessions sorted by creation date (newest first).
    Returns up to 'limit' sessions.
    """
    if not base_path.exists():
        return []
    
    sessions = []
    
    # Iterate through all directories in base_path
    for session_dir in base_path.iterdir():
        if not session_dir.is_dir():
            continue
        
        session_file = session_dir / "session.json"
        if not session_file.exists():
            # Try to migrate old format (user_prompt.txt)
            old_prompt_file = session_dir / "user_prompt.txt"
            if old_prompt_file.exists():
                logger.info(f"Found old format session: {session_dir.name}")
                # Could migrate here, but for now just skip
                continue
        
        session = load_session(session_dir.name, base_path)
        if session:
            sessions.append(session)
    
    # Sort by session_id (which has timestamp prefix) in descending order
    sessions.sort(key=lambda s: s.session_id, reverse=True)
    
    return sessions[:limit]


def get_session_path(session_id: str, base_path: Path = Path("games")) -> Path:
    """Get the path to a session directory."""
    return base_path / session_id


def get_game_path(session_id: str, base_path: Path = Path("games")) -> Path:
    """Get the path to the game files within a session."""
    return base_path / session_id / "game"


def get_agent_path(session_id: str, base_path: Path = Path("games")) -> Path:
    """Get the path to the agent workspace within a session."""
    return base_path / session_id / "agent"

