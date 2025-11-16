"""
Unit tests for src/tools.py

Tests cover:
- Tool schema definitions
- Individual tool operations with mocked workspace
- Error handling for each tool
- Helper method functionality
- Edge cases

Integration tests are in tests/integration/test_tools_integration.py
"""
import pytest
from unittest.mock import Mock, AsyncMock
from src.tools import FileOperations
from src.custom_types import ToolUse, ToolUseResult, TextRaw, ThinkingBlock
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
# Unit Tests - Tool Definitions
# ============================================================================

def test_base_tools_structure(file_ops):
    """Test that all base tools are properly defined."""
    tools = file_ops.base_tools
    
    assert len(tools) == 5
    tool_names = [t["name"] for t in tools]
    assert tool_names == ["read_file", "write_file", "edit_file", "delete_file", "complete"]
    
    # Check each tool has required fields
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool


def test_read_file_tool_schema(file_ops):
    """Test read_file tool schema."""
    tool = file_ops.base_tools[0]
    
    assert tool["name"] == "read_file"
    assert tool["description"] == "Read file content"
    assert tool["input_schema"]["required"] == ["path"]
    assert "path" in tool["input_schema"]["properties"]


def test_write_file_tool_schema(file_ops):
    """Test write_file tool schema."""
    tool = file_ops.base_tools[1]
    
    assert tool["name"] == "write_file"
    assert tool["description"] == "Write content to a file"
    assert set(tool["input_schema"]["required"]) == {"path", "content"}


def test_edit_file_tool_schema(file_ops):
    """Test edit_file tool schema."""
    tool = file_ops.base_tools[2]
    
    assert tool["name"] == "edit_file"
    assert set(tool["input_schema"]["required"]) == {"path", "search", "replace"}
    assert "replace_all" in tool["input_schema"]["properties"]


def test_delete_file_tool_schema(file_ops):
    """Test delete_file tool schema."""
    tool = file_ops.base_tools[3]
    
    assert tool["name"] == "delete_file"
    assert tool["description"] == "Delete a file"
    assert tool["input_schema"]["required"] == ["path"]


def test_complete_tool_schema(file_ops):
    """Test complete tool schema."""
    tool = file_ops.base_tools[4]
    
    assert tool["name"] == "complete"
    assert "type checks" in tool["description"].lower()


# ============================================================================
# Unit Tests - read_file Tool
# ============================================================================

@pytest.mark.asyncio
async def test_read_file_success(file_ops, mock_workspace):
    """Test successful file reading."""
    mock_workspace.read_file.return_value = "file content"
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="read_file",
        input={"path": "test.txt"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].content == "file content"
    assert not results[0].is_error
    assert not is_completed
    mock_workspace.read_file.assert_called_once_with("test.txt")


@pytest.mark.asyncio
async def test_read_file_not_found(file_ops, mock_workspace):
    """Test reading non-existent file."""
    mock_workspace.read_file.side_effect = FileNotFoundError("File not found: test.txt")
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="read_file",
        input={"path": "test.txt"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "File not found" in results[0].content


# ============================================================================
# Unit Tests - write_file Tool
# ============================================================================

@pytest.mark.asyncio
async def test_write_file_success(file_ops, mock_workspace):
    """Test successful file writing."""
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="write_file",
        input={"path": "test.txt", "content": "hello world"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].content == "success"
    assert not results[0].is_error
    assert not is_completed
    mock_workspace.write_file.assert_called_once_with("test.txt", "hello world")


@pytest.mark.asyncio
async def test_write_file_permission_error(file_ops, mock_workspace):
    """Test writing file with permission error."""
    mock_workspace.write_file.side_effect = PermissionError("Permission denied")
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="write_file",
        input={"path": "protected.txt", "content": "data"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "Permission denied" in results[0].content


@pytest.mark.asyncio
async def test_write_file_with_special_characters(file_ops, mock_workspace):
    """Test writing file with special characters."""
    special_content = "Hello\nWorld\t\r\n🎮"
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="write_file",
        input={"path": "special.txt", "content": special_content}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert results[0].content == "success"
    mock_workspace.write_file.assert_called_once_with("special.txt", special_content)


@pytest.mark.asyncio
async def test_write_file_empty_content(file_ops, mock_workspace):
    """Test writing empty file."""
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="write_file",
        input={"path": "empty.txt", "content": ""}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert results[0].content == "success"
    mock_workspace.write_file.assert_called_once_with("empty.txt", "")


@pytest.mark.asyncio
async def test_write_file_does_not_update_workspace_on_error(file_ops, mock_workspace):
    """Test that workspace is not updated when write fails."""
    original_workspace = mock_workspace
    mock_workspace.write_file.side_effect = PermissionError("Denied")
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="write_file",
        input={"path": "test.txt", "content": "data"}
    )
    
    await file_ops.run_tools([tool_use])
    
    # Workspace should remain unchanged on error
    assert file_ops.workspace is original_workspace


# ============================================================================
# Unit Tests - edit_file Tool
# ============================================================================

@pytest.mark.asyncio
async def test_edit_file_single_match(file_ops, mock_workspace):
    """Test editing file with single match."""
    original = "Hello World"
    mock_workspace.read_file.return_value = original
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "test.txt", "search": "World", "replace": "Universe"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].content == "success"
    assert not results[0].is_error
    mock_workspace.write_file.assert_called_once_with("test.txt", "Hello Universe")


@pytest.mark.asyncio
async def test_edit_file_not_found_search(file_ops, mock_workspace):
    """Test editing file when search text not found."""
    mock_workspace.read_file.return_value = "Hello World"
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "test.txt", "search": "NotFound", "replace": "Something"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "Search text not found" in results[0].content


@pytest.mark.asyncio
async def test_edit_file_multiple_matches_without_replace_all(file_ops, mock_workspace):
    """Test editing file with multiple matches without replace_all flag."""
    mock_workspace.read_file.return_value = "Hello Hello Hello"
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "test.txt", "search": "Hello", "replace": "Hi"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "found 3 times" in results[0].content
    assert "replace_all=true" in results[0].content


@pytest.mark.asyncio
async def test_edit_file_multiple_matches_with_replace_all(file_ops, mock_workspace):
    """Test editing file with multiple matches with replace_all flag."""
    mock_workspace.read_file.return_value = "Hello Hello Hello"
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "test.txt", "search": "Hello", "replace": "Hi", "replace_all": True}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].content == "success - replaced 3 occurrences"
    assert not results[0].is_error
    mock_workspace.write_file.assert_called_once_with("test.txt", "Hi Hi Hi")


@pytest.mark.asyncio
async def test_edit_file_multiline_search(file_ops, mock_workspace):
    """Test editing file with multiline search/replace."""
    original = "Line 1\nLine 2\nLine 3"
    mock_workspace.read_file.return_value = original
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "test.txt", "search": "Line 1\nLine 2", "replace": "Combined Line"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert results[0].content == "success"
    mock_workspace.write_file.assert_called_once_with("test.txt", "Combined Line\nLine 3")


@pytest.mark.asyncio
async def test_edit_file_file_not_found(file_ops, mock_workspace):
    """Test editing non-existent file."""
    mock_workspace.read_file.side_effect = FileNotFoundError("File not found")
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "missing.txt", "search": "old", "replace": "new"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "not found" in results[0].content.lower()


@pytest.mark.asyncio
async def test_edit_file_does_not_update_workspace_on_error(file_ops, mock_workspace):
    """Test that workspace is not updated when edit fails."""
    original_workspace = mock_workspace
    mock_workspace.read_file.side_effect = FileNotFoundError("Not found")
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="edit_file",
        input={"path": "test.txt", "search": "old", "replace": "new"}
    )
    
    await file_ops.run_tools([tool_use])
    
    # Workspace should remain unchanged on error
    assert file_ops.workspace is original_workspace


# ============================================================================
# Unit Tests - delete_file Tool
# ============================================================================

@pytest.mark.asyncio
async def test_delete_file_success(file_ops, mock_workspace):
    """Test successful file deletion."""
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="delete_file",
        input={"path": "test.txt"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].content == "success"
    assert not results[0].is_error
    mock_workspace.rm.assert_called_once_with("test.txt")


@pytest.mark.asyncio
async def test_delete_file_permission_error(file_ops, mock_workspace):
    """Test deleting file with permission error."""
    mock_workspace.rm.side_effect = PermissionError("Cannot delete protected file")
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="delete_file",
        input={"path": "protected.txt"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "Cannot delete" in results[0].content or "Permission" in results[0].content


# ============================================================================
# Unit Tests - complete Tool
# ============================================================================

@pytest.mark.asyncio
async def test_complete_tool(file_ops, mock_workspace):
    """Test complete tool sets is_completed flag."""
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="complete",
        input={}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].content == "success"
    assert not results[0].is_error
    assert is_completed is True


# ============================================================================
# Unit Tests - Helper Methods
# ============================================================================

def test_short_dict_repr(file_ops):
    """Test short dictionary representation helper."""
    test_dict = {
        "short": "value",
        "long": "a" * 200,
        "number": 123,  # Non-string, should be skipped
    }
    
    result = file_ops._short_dict_repr(test_dict)
    
    assert "short: value" in result
    assert "long: " + "a" * 50 + "..." in result
    assert "number" not in result  # Non-strings are filtered


def test_unpack_exception_group_with_regular_exception(file_ops):
    """Test unpacking regular exception."""
    exc = ValueError("Test error")
    
    result = file_ops._unpack_exception_group(exc)
    
    assert len(result) == 1
    assert result[0] is exc


def test_unpack_exception_group_with_group(file_ops):
    """Test unpacking ExceptionGroup."""
    exc1 = ValueError("Error 1")
    exc2 = TypeError("Error 2")
    exc3 = RuntimeError("Error 3")
    
    # Create nested exception group
    group = BaseExceptionGroup("Test group", [exc1, exc2, exc3])
    
    result = file_ops._unpack_exception_group(group)
    
    assert len(result) == 3
    assert exc1 in result
    assert exc2 in result
    assert exc3 in result


@pytest.mark.asyncio
async def test_exception_group_handling(file_ops, mock_workspace):
    """Test handling of ExceptionGroup during tool execution."""
    # Create an exception group
    exc_group = BaseExceptionGroup(
        "Multiple errors",
        [ValueError("Error 1"), TypeError("Error 2")]
    )
    mock_workspace.read_file.side_effect = exc_group
    
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="read_file",
        input={"path": "test.txt"}
    )
    
    results, _ = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error
    assert "Multiple errors occurred" in results[0].content
    assert "ValueError: Error 1" in results[0].content
    assert "TypeError: Error 2" in results[0].content


# ============================================================================
# Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_empty_tool_list(file_ops):
    """Test running with empty tool list."""
    results, is_completed = await file_ops.run_tools([])
    
    assert len(results) == 0
    assert not is_completed


@pytest.mark.asyncio
async def test_invalid_tool_name(file_ops):
    """Test handling of invalid tool name."""
    tool_use = ToolUse(
        type="tool_use",
        id="test-1",
        name="invalid_tool",
        input={"some": "data"}
    )
    
    results, is_completed = await file_ops.run_tools([tool_use])
    
    assert len(results) == 1
    assert results[0].is_error


@pytest.mark.asyncio
async def test_mixed_content_blocks_filters_non_tools(file_ops, mock_workspace):
    """Test that TextRaw and ThinkingBlock are filtered out."""
    mock_workspace.read_file.return_value = "content"
    
    blocks = [
        TextRaw(type="text", text="Some text output"),
        ThinkingBlock(type="thinking", thinking="AI thinking..."),
        ToolUse(type="tool_use", id="1", name="read_file", input={"path": "test.txt"}),
    ]
    
    results, is_completed = await file_ops.run_tools(blocks)
    
    # Only tool use should produce result
    assert len(results) == 1
    assert results[0].content == "content"
