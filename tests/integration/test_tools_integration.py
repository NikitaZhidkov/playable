"""
Integration tests for src/tools.py

Tests cover:
- Multiple tools working together
- Workspace state persistence
- Error isolation between tools
- Real workflow scenarios

Unit tests are in tests/test_tools.py
"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.tools import FileOperations
from src.custom_types import ToolUse, TextRaw, ThinkingBlock
from src.containers import Workspace


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_workspace():
    """Create a mock workspace for testing."""
    workspace = Mock(spec=Workspace)
    workspace.read_file = AsyncMock()
    workspace.write_file = Mock(return_value=workspace)
    workspace.rm = Mock(return_value=workspace)
    return workspace


@pytest.fixture
def file_ops(mock_workspace):
    """Create FileOperations instance with mock workspace."""
    return FileOperations(workspace=mock_workspace)


# ============================================================================
# Integration Tests - Multiple Tools
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_tools_in_sequence(file_ops, mock_workspace):
    """Test running multiple tools in sequence."""
    mock_workspace.read_file.return_value = "original content"
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file", input={"path": "a.txt", "content": "data"}),
        ToolUse(type="tool_use", id="2", name="read_file", input={"path": "b.txt"}),
        ToolUse(type="tool_use", id="3", name="delete_file", input={"path": "c.txt"}),
    ]
    
    results, is_completed = await file_ops.run_tools(tools)
    
    assert len(results) == 3
    assert all(not r.is_error for r in results)
    assert not is_completed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_does_not_stop_execution(file_ops, mock_workspace):
    """Test that error in one tool doesn't stop other tools."""
    mock_workspace.read_file.side_effect = [
        FileNotFoundError("Not found"),
        "success content"
    ]
    
    tools = [
        ToolUse(type="tool_use", id="1", name="read_file", input={"path": "missing.txt"}),
        ToolUse(type="tool_use", id="2", name="read_file", input={"path": "exists.txt"}),
    ]
    
    results, is_completed = await file_ops.run_tools([tools])
    
    assert len(results) == 2
    assert results[0].is_error
    assert not results[1].is_error
    assert results[1].content == "success content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_edit_read_workflow(file_ops, mock_workspace):
    """Test a realistic workflow: write, edit, read."""
    # Setup mock to return different content after edit
    mock_workspace.read_file.side_effect = [
        "Hello World",  # For edit_file
        "Hello Universe"  # Final read_file
    ]
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file", 
                input={"path": "test.txt", "content": "Hello World"}),
        ToolUse(type="tool_use", id="2", name="edit_file", 
                input={"path": "test.txt", "search": "World", "replace": "Universe"}),
        ToolUse(type="tool_use", id="3", name="read_file", 
                input={"path": "test.txt"}),
    ]
    
    results, _ = await file_ops.run_tools(tools)
    
    assert len(results) == 3
    assert results[0].content == "success"  # write
    assert results[1].content == "success"  # edit
    assert results[2].content == "Hello Universe"  # read


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_edit_delete_workflow(file_ops, mock_workspace):
    """Test create, edit, and delete workflow."""
    mock_workspace.read_file.return_value = "Version 1"
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file",
                input={"path": "temp.txt", "content": "Version 1"}),
        ToolUse(type="tool_use", id="2", name="edit_file",
                input={"path": "temp.txt", "search": "1", "replace": "2"}),
        ToolUse(type="tool_use", id="3", name="delete_file",
                input={"path": "temp.txt"}),
    ]
    
    results, _ = await file_ops.run_tools(tools)
    
    assert len(results) == 3
    assert all(not r.is_error for r in results)
    assert mock_workspace.rm.called


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mixed_content_blocks_integration(file_ops, mock_workspace):
    """Test handling mixed content blocks in realistic scenario."""
    mock_workspace.read_file.return_value = "file content"
    
    blocks = [
        TextRaw(type="text", text="Starting file operations..."),
        ToolUse(type="tool_use", id="1", name="write_file", 
                input={"path": "a.txt", "content": "data"}),
        ThinkingBlock(type="thinking", thinking="Deciding next action..."),
        TextRaw(type="text", text="Now reading the file..."),
        ToolUse(type="tool_use", id="2", name="read_file", 
                input={"path": "a.txt"}),
        TextRaw(type="text", text="Operations complete!"),
    ]
    
    results, is_completed = await file_ops.run_tools(blocks)
    
    # Only tool uses should produce results
    assert len(results) == 2
    assert results[0].content == "success"
    assert results[1].content == "file content"
    assert not is_completed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_at_end_of_workflow(file_ops, mock_workspace):
    """Test complete tool at end of multi-tool workflow."""
    mock_workspace.read_file.return_value = "content"
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file",
                input={"path": "game.ts", "content": "export class Game {}"}),
        ToolUse(type="tool_use", id="2", name="write_file",
                input={"path": "index.ts", "content": "import { Game } from './game'"}),
        ToolUse(type="tool_use", id="3", name="complete", input={}),
    ]
    
    results, is_completed = await file_ops.run_tools(tools)
    
    assert len(results) == 3
    assert all(not r.is_error for r in results)
    assert is_completed is True


# ============================================================================
# Integration Tests - Workspace State Persistence
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_state_persists_across_writes(file_ops, mock_workspace):
    """Test that workspace state updates persist across multiple writes."""
    workspace_v1 = Mock(spec=Workspace)
    workspace_v1.write_file = Mock(return_value=workspace_v1)
    
    workspace_v2 = Mock(spec=Workspace)
    workspace_v2.write_file = Mock(return_value=workspace_v2)
    
    mock_workspace.write_file.side_effect = [workspace_v1, workspace_v2]
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file",
                input={"path": "file1.txt", "content": "data1"}),
        ToolUse(type="tool_use", id="2", name="write_file",
                input={"path": "file2.txt", "content": "data2"}),
    ]
    
    await file_ops.run_tools(tools)
    
    # Workspace should be updated to latest version
    assert file_ops.workspace is workspace_v2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_state_persists_across_edits(file_ops, mock_workspace):
    """Test that workspace state updates persist across multiple edits."""
    mock_workspace.read_file.return_value = "original"
    
    new_workspace = Mock(spec=Workspace)
    new_workspace.write_file = Mock(return_value=new_workspace)
    new_workspace.read_file = AsyncMock(return_value="modified")
    
    mock_workspace.write_file.return_value = new_workspace
    
    tools = [
        ToolUse(type="tool_use", id="1", name="edit_file",
                input={"path": "test.txt", "search": "original", "replace": "modified"}),
    ]
    
    await file_ops.run_tools(tools)
    
    assert file_ops.workspace is new_workspace


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_state_persists_across_deletes(file_ops, mock_workspace):
    """Test that workspace state updates persist across deletions."""
    new_workspace = Mock(spec=Workspace)
    new_workspace.rm = Mock(return_value=new_workspace)
    mock_workspace.rm.return_value = new_workspace
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="delete_file",
        input={"path": "test.txt"}
    )
    
    await file_ops.run_tools([tool_use])
    
    assert file_ops.workspace is new_workspace


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_state_chain_through_mixed_operations(file_ops, mock_workspace):
    """Test workspace state updates chain through write/edit/delete."""
    ws1 = Mock(spec=Workspace)
    ws1.write_file = Mock(return_value=ws1)
    ws1.read_file = AsyncMock(return_value="content")
    
    ws2 = Mock(spec=Workspace)
    ws2.write_file = Mock(return_value=ws2)
    
    ws3 = Mock(spec=Workspace)
    ws3.rm = Mock(return_value=ws3)
    
    mock_workspace.write_file.return_value = ws1
    ws1.write_file.return_value = ws2
    ws2.rm.return_value = ws3
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file",
                input={"path": "a.txt", "content": "data"}),
        ToolUse(type="tool_use", id="2", name="edit_file",
                input={"path": "a.txt", "search": "data", "replace": "DATA"}),
        ToolUse(type="tool_use", id="3", name="delete_file",
                input={"path": "a.txt"}),
    ]
    
    await file_ops.run_tools(tools)
    
    # Should end up with final workspace
    assert file_ops.workspace is ws3


# ============================================================================
# Integration Tests - Error Handling in Workflows
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_partial_workflow_failure(file_ops, mock_workspace):
    """Test workflow where some operations succeed and some fail."""
    mock_workspace.read_file.side_effect = [
        "content1",
        FileNotFoundError("Missing"),
        "content3"
    ]
    
    tools = [
        ToolUse(type="tool_use", id="1", name="read_file", input={"path": "a.txt"}),
        ToolUse(type="tool_use", id="2", name="read_file", input={"path": "missing.txt"}),
        ToolUse(type="tool_use", id="3", name="read_file", input={"path": "c.txt"}),
    ]
    
    results, _ = await file_ops.run_tools(tools)
    
    assert len(results) == 3
    assert not results[0].is_error
    assert results[0].content == "content1"
    assert results[1].is_error
    assert not results[2].is_error
    assert results[2].content == "content3"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workspace_rollback_on_error(file_ops, mock_workspace):
    """Test that workspace doesn't update when operation fails."""
    original_workspace = mock_workspace
    mock_workspace.write_file.side_effect = [
        Mock(spec=Workspace),  # First write succeeds
        PermissionError("Access denied")  # Second write fails
    ]
    
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file",
                input={"path": "allowed.txt", "content": "ok"}),
        ToolUse(type="tool_use", id="2", name="write_file",
                input={"path": "denied.txt", "content": "fail"}),
    ]
    
    results, _ = await file_ops.run_tools(tools)
    
    # First succeeded
    assert not results[0].is_error
    # Second failed, workspace should stay at first update
    assert results[1].is_error
    # Workspace should be first updated version, not original
    assert file_ops.workspace is not original_workspace


# ============================================================================
# Integration Tests - Realistic Game Development Scenarios
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_typescript_game_creation_workflow(file_ops, mock_workspace):
    """Test realistic TypeScript game file creation."""
    tools = [
        ToolUse(type="tool_use", id="1", name="write_file",
                input={"path": "src/Game.ts", "content": "export class Game { }"}),
        ToolUse(type="tool_use", id="2", name="write_file",
                input={"path": "src/index.ts", "content": "import { Game } from './Game'"}),
        ToolUse(type="tool_use", id="3", name="write_file",
                input={"path": "config.json", "content": '{"speed": 5}'}),
        ToolUse(type="tool_use", id="4", name="write_file",
                input={"path": "test_case_1.json", "content": '{"score": 0}'}),
        ToolUse(type="tool_use", id="5", name="complete", input={}),
    ]
    
    results, is_completed = await file_ops.run_tools(tools)
    
    assert len(results) == 5
    assert all(not r.is_error for r in results)
    assert is_completed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_game_modification_with_feedback(file_ops, mock_workspace):
    """Test modifying existing game based on feedback."""
    mock_workspace.read_file.side_effect = [
        "export class Game { speed = 3; }",  # For first edit
        '{"speed": 3}',  # For config edit
    ]
    
    tools = [
        ToolUse(type="tool_use", id="1", name="edit_file",
                input={"path": "src/Game.ts", "search": "speed = 3", "replace": "speed = 5"}),
        ToolUse(type="tool_use", id="2", name="edit_file",
                input={"path": "config.json", "search": '"speed": 3', "replace": '"speed": 5'}),
        ToolUse(type="tool_use", id="3", name="complete", input={}),
    ]
    
    results, is_completed = await file_ops.run_tools(tools)
    
    assert len(results) == 3
    assert all(not r.is_error for r in results)
    assert is_completed

