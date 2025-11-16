"""Tests for agent_state module."""

import pytest
from unittest.mock import Mock
from src.agent_state import AgentState
from src.containers import Workspace, PlaywrightContainer


class TestAgentState:
    """Test AgentState structure and functionality."""
    
    def test_agent_state_instantiation(self):
        """Test that AgentState can be instantiated with all required fields."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Test task",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="test_session_123",
            is_feedback_mode=False,
            original_prompt="Create a game",
            asset_context="",
            sound_context=""
        )
        
        assert state["workspace"] == workspace
        assert state["playwright_container"] == playwright_container
        assert state["task_description"] == "Test task"
        assert state["is_completed"] is False
        assert state["_parsed_content"] == []
        assert state["test_failures"] == []
        assert state["retry_count"] == 0
        assert state["session_id"] == "test_session_123"
        assert state["is_feedback_mode"] is False
        assert state["original_prompt"] == "Create a game"
        assert state["asset_context"] == ""
        assert state["sound_context"] == ""
    
    def test_agent_state_has_messages_field(self):
        """Test that AgentState inherits messages field from MessagesState."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        state = AgentState(
            messages=[{"role": "user", "content": "Hello"}],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Test",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="test",
            is_feedback_mode=False,
            original_prompt="",
            asset_context="",
            sound_context=""
        )
        
        assert "messages" in state
        assert len(state["messages"]) == 1
        assert state["messages"][0]["content"] == "Hello"
    
    def test_agent_state_field_modification(self):
        """Test that AgentState fields can be modified."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Initial task",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="test",
            is_feedback_mode=False,
            original_prompt="",
            asset_context="",
            sound_context=""
        )
        
        # Modify fields
        state["task_description"] = "Updated task"
        state["is_completed"] = True
        state["retry_count"] = 3
        state["test_failures"] = ["Error 1", "Error 2"]
        
        assert state["task_description"] == "Updated task"
        assert state["is_completed"] is True
        assert state["retry_count"] == 3
        assert len(state["test_failures"]) == 2
    
    def test_agent_state_with_test_failures(self):
        """Test AgentState properly stores test failure information."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        test_errors = [
            "Browser error: Element not found",
            "Timeout waiting for selector",
            "JavaScript error in game code"
        ]
        
        state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Test",
            is_completed=False,
            _parsed_content=[],
            test_failures=test_errors,
            retry_count=2,
            session_id="test",
            is_feedback_mode=False,
            original_prompt="",
            asset_context="",
            sound_context=""
        )
        
        assert state["test_failures"] == test_errors
        assert len(state["test_failures"]) == 3
        assert state["retry_count"] == 2
    
    def test_agent_state_feedback_mode_vs_creation_mode(self):
        """Test AgentState properly distinguishes between feedback and creation modes."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        # Creation mode
        creation_state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Create a new game",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="creation_123",
            is_feedback_mode=False,
            original_prompt="Create a racing game",
            asset_context="Racing assets available",
            sound_context="Racing sounds available"
        )
        
        # Feedback mode
        feedback_state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Make the car faster",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="feedback_456",
            is_feedback_mode=True,
            original_prompt="Create a racing game",  # Preserved from creation
            asset_context="",
            sound_context=""
        )
        
        assert creation_state["is_feedback_mode"] is False
        assert feedback_state["is_feedback_mode"] is True
        assert feedback_state["original_prompt"] == creation_state["original_prompt"]
    
    def test_agent_state_with_parsed_content(self):
        """Test AgentState stores parsed LLM response content."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        parsed_content = [
            {"type": "code", "content": "const x = 5;"},
            {"type": "text", "content": "This is an explanation"},
        ]
        
        state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Test",
            is_completed=False,
            _parsed_content=parsed_content,
            test_failures=[],
            retry_count=0,
            session_id="test",
            is_feedback_mode=False,
            original_prompt="",
            asset_context="",
            sound_context=""
        )
        
        assert state["_parsed_content"] == parsed_content
        assert len(state["_parsed_content"]) == 2
        assert state["_parsed_content"][0]["type"] == "code"
    
    def test_agent_state_with_context_enrichment(self):
        """Test AgentState properly stores asset and sound context for prompt injection."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        asset_context = "Available assets: car.png, track.png, wheel.png"
        sound_context = "Available sounds: engine.mp3, crash.mp3"
        
        state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Create racing game",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="test",
            is_feedback_mode=False,
            original_prompt="Create a racing game",
            asset_context=asset_context,
            sound_context=sound_context
        )
        
        assert state["asset_context"] == asset_context
        assert state["sound_context"] == sound_context
        assert "car.png" in state["asset_context"]
        assert "engine.mp3" in state["sound_context"]
    
    def test_agent_state_session_id_uniqueness(self):
        """Test that different AgentState instances can have different session IDs."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        state1 = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Task 1",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="session_aaa",
            is_feedback_mode=False,
            original_prompt="",
            asset_context="",
            sound_context=""
        )
        
        state2 = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Task 2",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="session_bbb",
            is_feedback_mode=False,
            original_prompt="",
            asset_context="",
            sound_context=""
        )
        
        assert state1["session_id"] != state2["session_id"]
        assert state1["session_id"] == "session_aaa"
        assert state2["session_id"] == "session_bbb"
    
    def test_agent_state_completion_workflow(self):
        """Test typical workflow of completing a task through state changes."""
        workspace = Mock(spec=Workspace)
        playwright_container = Mock(spec=PlaywrightContainer)
        
        # Initial state
        state = AgentState(
            messages=[],
            workspace=workspace,
            playwright_container=playwright_container,
            task_description="Create a game",
            is_completed=False,
            _parsed_content=[],
            test_failures=[],
            retry_count=0,
            session_id="workflow_test",
            is_feedback_mode=False,
            original_prompt="Create a game",
            asset_context="",
            sound_context=""
        )
        
        assert state["is_completed"] is False
        assert state["retry_count"] == 0
        assert state["test_failures"] == []
        
        # Simulate failure
        state["test_failures"] = ["Error in game.ts"]
        state["retry_count"] = 1
        
        assert state["test_failures"] == ["Error in game.ts"]
        assert state["retry_count"] == 1
        assert state["is_completed"] is False
        
        # Simulate success
        state["test_failures"] = []
        state["is_completed"] = True
        
        assert state["test_failures"] == []
        assert state["is_completed"] is True

