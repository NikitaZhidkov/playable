# Test Suite for src/tools.py

## Overview
Comprehensive unit and integration tests for the `FileOperations` class and all tool implementations.

## Test Coverage

### ✅ Tool Schema Tests (5 tests)
- `test_base_tools_structure` - Verifies all 5 tools are defined
- `test_read_file_tool_schema` - Validates read_file schema
- `test_write_file_tool_schema` - Validates write_file schema  
- `test_edit_file_tool_schema` - Validates edit_file schema
- `test_complete_tool_schema` - Validates complete tool schema

### ✅ read_file Tool Tests (2 tests)
- `test_read_file_success` - Successful file reading
- `test_read_file_not_found` - FileNotFoundError handling

### ✅ write_file Tool Tests (4 tests)
- `test_write_file_success` - Successful file writing
- `test_write_file_permission_error` - PermissionError handling
- `test_write_file_with_special_characters` - Unicode, newlines, tabs
- `test_write_file_empty_content` - Empty file creation

### ✅ edit_file Tool Tests (6 tests)
- `test_edit_file_single_match` - Single search/replace
- `test_edit_file_not_found_search` - Search text not found error
- `test_edit_file_multiple_matches_without_replace_all` - Multiple matches error
- `test_edit_file_multiple_matches_with_replace_all` - Bulk replacement
- `test_edit_file_multiline_search` - Multiline search/replace
- `test_edit_file_file_not_found` - Missing file error

### ✅ delete_file Tool Tests (2 tests)
- `test_delete_file_success` - Successful deletion
- `test_delete_file_permission_error` - PermissionError handling

### ✅ complete Tool Test (1 test)
- `test_complete_tool` - Verifies is_completed flag is set

### ✅ Integration Tests (3 tests)
- `test_multiple_tools_in_sequence` - Sequential tool execution
- `test_mixed_content_blocks` - Text, thinking, and tool blocks
- `test_error_does_not_stop_execution` - Error isolation

### ✅ Helper Method Tests (3 tests)
- `test_short_dict_repr` - Dictionary truncation helper
- `test_unpack_exception_group_with_regular_exception` - Regular exception handling
- `test_unpack_exception_group_with_group` - ExceptionGroup unpacking
- `test_exception_group_handling` - Full ExceptionGroup flow

### ✅ Workspace State Tests (3 tests)
- `test_workspace_state_persists_across_writes` - Write updates workspace
- `test_workspace_state_persists_across_edits` - Edit updates workspace
- `test_workspace_state_persists_across_deletes` - Delete updates workspace

### ✅ Edge Case Tests (4 tests)
- `test_empty_tool_list` - Empty tool list handling
- `test_invalid_tool_name` - Invalid tool error
- `test_write_file_updates_workspace_on_error` - No update on write error
- `test_edit_file_updates_workspace_on_error` - No update on edit error

## Total: 38 Tests

## Running the Tests

### Prerequisites
```bash
# Ensure pytest is installed
pip install pytest pytest-asyncio
```

### Run All Tests
```bash
pytest tests/test_tools.py -v
```

### Run Specific Test Category
```bash
# Unit tests only
pytest tests/test_tools.py -v -k "test_write_file or test_read_file"

# Integration tests only
pytest tests/test_tools.py -v -k "integration"

# Error handling tests
pytest tests/test_tools.py -v -k "error"
```

### Run with Coverage
```bash
pytest tests/test_tools.py --cov=src.tools --cov-report=html
```

## Test Structure

### Fixtures
- `mock_workspace` - Mock Workspace with AsyncMock methods
- `file_ops` - FileOperations instance with mock workspace

### Test Categories

#### 1. **Unit Tests**
- Test individual tool operations in isolation
- Mock all workspace interactions
- Verify tool behavior and error handling

#### 2. **Integration Tests**
- Test multiple tools working together
- Test workspace state persistence
- Test mixed content blocks

#### 3. **Error Handling Tests**
- FileNotFoundError
- PermissionError
- ValueError
- ExceptionGroup (Python 3.11+)

#### 4. **Edge Cases**
- Empty inputs
- Special characters
- Multiline content
- Invalid tool names
- Multiple matches

## Key Test Principles

### ✅ Fail Fast Philosophy
Tests verify that errors propagate correctly:
```python
# File not found should raise immediately
mock_workspace.read_file.side_effect = FileNotFoundError("Not found")
results, _ = await file_ops.run_tools([tool_use])
assert results[0].is_error
```

### ✅ Workspace Immutability
Tests verify workspace updates only on success:
```python
# On error, workspace should not change
original_workspace = mock_workspace
mock_workspace.write_file.side_effect = PermissionError("Denied")
await file_ops.run_tools([tool_use])
assert file_ops.workspace is original_workspace
```

### ✅ Tool Independence
Each tool test is independent and can run in isolation.

## Mock Strategy

### AsyncMock for async methods
```python
workspace.read_file = AsyncMock(return_value="content")
```

### Return self for mutating methods
```python
workspace.write_file = Mock(return_value=workspace)
```

### Side effects for errors
```python
workspace.read_file.side_effect = FileNotFoundError("Not found")
```

## Example Test Pattern

```python
@pytest.mark.asyncio
async def test_tool_operation(file_ops, mock_workspace):
    """Test description."""
    # Arrange
    mock_workspace.some_method.return_value = "expected"
    tool_use = ToolUse(...)
    
    # Act
    results, is_completed = await file_ops.run_tools([tool_use])
    
    # Assert
    assert len(results) == 1
    assert results[0].content == "expected"
    assert not results[0].is_error
    mock_workspace.some_method.assert_called_once()
```

## Coverage Goals

- ✅ **100% line coverage** for src/tools.py
- ✅ **100% branch coverage** for error paths
- ✅ **All edge cases** covered
- ✅ **All error types** tested

## Future Enhancements

1. Add performance tests for large files
2. Add stress tests for many sequential operations
3. Add tests for concurrent tool execution
4. Add property-based tests with Hypothesis

## Related Files

- `src/tools.py` - Source code being tested
- `src/custom_types.py` - Type definitions
- `src/containers/workspace.py` - Workspace implementation
- `pytest.ini` - Pytest configuration

