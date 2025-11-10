# Feedback Mode File Loading Investigation & Fix

## Problem Statement

In feedback mode, the agent reports that files are not accessible in the workspace, even though the files appear in the agent's history/prompt. This suggests:

1. **Prompt initialization works**: Files are read from disk and included in the feedback context
2. **Workspace file access fails**: When the agent tries to read/write files through workspace operations, they're not found

## Root Cause Analysis

### Potential Issues Identified

1. **Dagger Directory Loading**
   - `client.host().directory()` loads files from the host filesystem
   - By default, it respects `.gitignore` files when a `.git` directory is present
   - Game directories have their own `.git` folder and `.gitignore` (which only excludes `debug/`)

2. **File Export/Import Flow**
   - **New game mode**: Files created in workspace → exported to disk → committed to git
   - **Feedback mode**: Files loaded from disk → copied to workspace → agent works → exported back to disk
   
3. **Potential Race Condition in `save_game_files`**
   - In feedback mode, the function:
     1. Deletes all files except `.git` and `debug`
     2. Exports workspace files to the now-mostly-empty directory
   - If the export fails or is incomplete, files could be lost

## Changes Made

### 1. Enhanced Logging in `initialize_workspace` (src/main.py:63-115)

Added detailed logging to track:
- Files on disk before loading into Dagger
- Files that Dagger successfully loads
- Files in the workspace after creation

```python
# List files that exist on disk before loading
disk_files = list(context_dir.rglob("*"))
disk_file_count = len([f for f in disk_files if f.is_file()])
logger.info(f"Files on disk in {context_dir}: {disk_file_count} files")

# Verify what Dagger sees in the directory
entries = await context.entries()
logger.info(f"Files loaded by Dagger: {len(entries)} entries")

# Verify files in workspace after creation
workspace_files = await workspace.ls(".")
logger.info(f"Files in workspace after creation: {len(workspace_files)} entries")
```

### 2. Enhanced Logging in `save_game_files` (src/main.py:670-721)

Added comprehensive logging to track the entire save process:
- Files in workspace before export
- Files on disk before cleanup (feedback mode)
- What gets removed during cleanup
- Files on disk after cleanup
- Files on disk after export
- Total file count after export

```python
# Log what's in workspace before export
workspace_files = await workspace.ls(".")
logger.info(f"Files in workspace before export: {len(workspace_files)} entries")

# Log cleanup process in feedback mode
if not is_new:
    files_before_cleanup = list(game_path.iterdir())
    logger.info(f"Files before cleanup: {[f.name for f in files_before_cleanup]}")
    # ... cleanup ...
    files_after_cleanup = list(game_path.iterdir())
    logger.info(f"Files after cleanup: {[f.name for f in files_after_cleanup]}")

# Verify files after export
files_after_export = list(game_path.iterdir())
logger.info(f"Files after export: {[f.name for f in files_after_export]}")
```

### 3. Created Integration Tests

Created comprehensive integration tests in `tests/integration/test_feedback_workflow_files.py`:

- `test_files_accessible_after_save_and_reload`: Verifies basic file persistence
- `test_nested_directory_structure_preserved`: Tests nested directories
- `test_feedback_context_includes_all_files`: Verifies prompt building
- `test_feedback_mode_after_multiple_iterations`: Tests multiple feedback cycles
- `test_git_files_excluded_from_workspace`: Verifies .git handling

### 4. Created Unit Tests

Created unit tests in `tests/test_feedback_file_logic.py` to verify file management logic without Docker:

- `test_game_path_structure`: Verifies session directory structure
- `test_files_persist_to_disk`: Tests file persistence
- `test_save_game_files_logic_cleanup`: Tests cleanup logic
- `test_context_dir_availability_for_feedback`: Tests file availability for feedback
- `test_directory_listing_includes_nested_files`: Tests recursive file discovery

## Testing Results

### Unit Tests (✅ All Passed)
```bash
pytest tests/test_feedback_file_logic.py -v
# 5 passed in 0.02s
```

The unit tests confirm that the file management logic works correctly at the Python/filesystem level.

### Integration Tests (⚠️ Requires Docker)
```bash
pytest tests/integration/test_feedback_workflow_files.py -v -m integration
# ERROR: Docker not running (Dagger engine not available)
```

Integration tests require Docker to be running. Need to run these with user's environment to test the actual Dagger integration.

## Next Steps for User

1. **Run the application in feedback mode with logging enabled**
   ```bash
   python run.py --feedback <session_id>
   ```

2. **Check the logs for the following patterns**:
   - "Files on disk in games/XXX/game: N files" - Should show files exist on disk
   - "Files loaded by Dagger: N entries" - Should match disk file count
   - "Files in workspace after creation: N entries" - Should match Dagger count
   - "Files in workspace before export: N entries" - Should show files agent created/modified
   - "Files after export: [...]" - Should show files were exported successfully

3. **If files are missing at any stage**:
   - **Files on disk but not loaded by Dagger**: Issue with `.gitignore` or Dagger configuration
   - **Files loaded by Dagger but not in workspace**: Issue with Workspace.create
   - **Files in workspace but not in agent**: Issue with agent file operations
   - **Files not exported**: Issue with export process

## Potential Solutions (if issues are confirmed)

### If Dagger is excluding git-ignored files:
```python
# Option 1: Explicitly include all files (if Dagger supports)
context = client.host().directory(str(context_dir), include=["**/*"])

# Option 2: Exclude .gitignore from being respected
context = client.host().directory(str(context_dir), exclude=[])

# Option 3: Use a different loading method
# Copy files manually instead of using host().directory()
```

### If export is failing silently:
```python
# Add error handling around export
try:
    await workspace.container().directory(".").export(str(game_path))
    logger.info("Export completed successfully")
except Exception as e:
    logger.error(f"Export failed: {e}")
    raise
```

### If .git directory is causing issues:
```python
# Temporarily move .git during reload, restore after
if (game_path / ".git").exists():
    shutil.move(game_path / ".git", game_path.parent / ".git_backup")
context = client.host().directory(str(context_dir))
shutil.move(game_path.parent / ".git_backup", game_path / ".git")
```

## Summary

- **Root cause**: Likely related to how Dagger loads directories from the host filesystem
- **Fix approach**: Added comprehensive logging to diagnose the exact point of failure
- **Tests created**: Both unit tests (passing) and integration tests (need Docker)
- **Action required**: User needs to run the application and review logs to confirm the exact failure point

The logging will definitively show where files are being lost in the pipeline, allowing for a targeted fix.


