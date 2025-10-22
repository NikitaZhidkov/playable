from typing import TypedDict, Annotated, Any
from langgraph.graph import MessagesState
from workspace import Workspace


class AgentState(MessagesState):
    """State for the coding agent.
    
    Extends MessagesState which provides:
    - messages: list of messages with automatic deduplication
    """
    workspace: Workspace
    task_description: str
    is_completed: bool
    _parsed_content: list[Any]  # Temporary storage for parsed LLM response
    test_failures: list[str]  # Browser test error messages
    retry_count: int  # Number of test retry attempts
    session_id: str  # Unique session identifier
    is_feedback_mode: bool  # Whether we're in feedback mode or creation mode

