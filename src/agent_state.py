from typing import TypedDict, Annotated, Any
from langgraph.graph import MessagesState
from src.containers import Workspace, PlaywrightContainer


class AgentState(MessagesState):
    """State for the coding agent.
    
    Extends MessagesState which provides:
    - messages: list of messages with automatic deduplication
    """
    workspace: Workspace
    playwright_container: PlaywrightContainer  # Reusable Playwright container for testing
    task_description: str
    is_completed: bool
    _parsed_content: list[Any]  # Temporary storage for parsed LLM response
    test_failures: list[str]  # Browser test error messages
    retry_count: int  # Number of test retry attempts
    session_id: str  # Unique session identifier
    is_feedback_mode: bool  # Whether we're in feedback mode or creation mode
    original_prompt: str  # Original game creation prompt (used in feedback mode for VLM context)
    asset_context: str  # Asset pack context for prompt injection (optional)
    sound_context: str  # Sound pack context for prompt injection (optional)

