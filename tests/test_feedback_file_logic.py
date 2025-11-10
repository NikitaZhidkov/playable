"""
Unit tests for feedback workflow file logic (no Docker required).

These tests verify the file management logic without needing containers.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from src.session import create_session, save_session, load_session, get_game_path


class TestFeedbackFileManagement:
    """Test file management logic for feedback workflow."""
    
    def test_game_path_structure(self):
        """Test that game path structure is created correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            session = create_session(
                "Test game",
                base_path=temp_path,
                selected_pack=None
            )
            
            # Verify session directory structure
            session_path = temp_path / session.session_id
            assert session_path.exists()
            assert (session_path / "game").exists()
            assert (session_path / "agent").exists()
            assert (session_path / "session.json").exists()
    
    def test_files_persist_to_disk(self):
        """Test that files written to game path persist correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            session = create_session(
                "Test game",
                base_path=temp_path,
                selected_pack=None
            )
            
            game_path = get_game_path(session.session_id, base_path=temp_path)
            
            # Write test files
            (game_path / "index.html").write_text("<html></html>")
            (game_path / "game.js").write_text("console.log('test');")
            
            # Create nested structure
            (game_path / "assets").mkdir()
            (game_path / "assets" / "sprite.png").write_text("fake_image_data")
            
            # Verify files exist
            assert (game_path / "index.html").exists()
            assert (game_path / "game.js").exists()
            assert (game_path / "assets" / "sprite.png").exists()
            
            # Verify content
            assert (game_path / "index.html").read_text() == "<html></html>"
            assert (game_path / "game.js").read_text() == "console.log('test');"
    
    def test_save_game_files_logic_cleanup(self):
        """Test the cleanup logic in save_game_files for feedback mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            session = create_session(
                "Test game",
                base_path=temp_path,
                selected_pack=None
            )
            
            game_path = get_game_path(session.session_id, base_path=temp_path)
            
            # Create initial files
            (game_path / "old_file.html").write_text("old")
            (game_path / "old_dir").mkdir()
            (game_path / "old_dir" / "nested.js").write_text("old nested")
            
            # Create .git and debug directories that should be preserved
            (game_path / ".git").mkdir()
            (game_path / ".git" / "config").write_text("git config")
            (game_path / "debug").mkdir()
            (game_path / "debug" / "log.txt").write_text("debug log")
            
            # Simulate feedback mode cleanup (from save_game_files)
            is_new = False
            if not is_new:
                for item in game_path.iterdir():
                    if item.name not in ['.git', 'debug']:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
            
            # Verify cleanup worked correctly
            assert not (game_path / "old_file.html").exists()
            assert not (game_path / "old_dir").exists()
            
            # Verify .git and debug were preserved
            assert (game_path / ".git").exists()
            assert (game_path / ".git" / "config").exists()
            assert (game_path / "debug").exists()
            assert (game_path / "debug" / "log.txt").exists()
            
            # Now write new files (simulating workspace export)
            (game_path / "new_file.html").write_text("new")
            (game_path / "new_dir").mkdir()
            (game_path / "new_dir" / "nested.js").write_text("new nested")
            
            # Verify new files exist alongside preserved ones
            assert (game_path / "new_file.html").exists()
            assert (game_path / "new_dir" / "nested.js").exists()
            assert (game_path / ".git" / "config").exists()
            assert (game_path / "debug" / "log.txt").exists()
    
    def test_context_dir_availability_for_feedback(self):
        """Test that game_path exists and has files when feedback mode initializes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Simulate: Create a game in new mode
            session = create_session(
                "Original game",
                base_path=temp_path,
                selected_pack=None
            )
            
            game_path = get_game_path(session.session_id, base_path=temp_path)
            
            # Write game files (simulating agent creating files)
            (game_path / "index.html").write_text("<html>Game</html>")
            (game_path / "game.js").write_text("const game = {};")
            (game_path / "assets").mkdir()
            (game_path / "assets" / "player.png").write_text("player_sprite")
            
            # Save session
            save_session(session, base_path=temp_path)
            
            # Simulate: Load session for feedback mode
            loaded_session = load_session(session.session_id, base_path=temp_path)
            assert loaded_session is not None
            
            feedback_game_path = get_game_path(loaded_session.session_id, base_path=temp_path)
            
            # This is what initialize_workspace checks
            assert feedback_game_path.exists(), "Game path should exist for feedback mode"
            
            # Verify all files are available
            assert (feedback_game_path / "index.html").exists()
            assert (feedback_game_path / "game.js").exists()
            assert (feedback_game_path / "assets" / "player.png").exists()
            
            # Verify we can list all files (what Dagger should see)
            all_files = list(feedback_game_path.rglob("*"))
            file_names = [f.name for f in all_files if f.is_file()]
            
            assert "index.html" in file_names
            assert "game.js" in file_names
            assert "player.png" in file_names
    
    def test_directory_listing_includes_nested_files(self):
        """Test that recursive file listing works (what Dagger directory loading does)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create complex structure
            (temp_path / "index.html").write_text("html")
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.js").write_text("js")
            (temp_path / "src" / "utils").mkdir()
            (temp_path / "src" / "utils" / "helper.js").write_text("helper")
            (temp_path / "assets").mkdir()
            (temp_path / "assets" / "images").mkdir()
            (temp_path / "assets" / "images" / "sprite.png").write_text("sprite")
            
            # Simulate what Dagger sees when loading a directory
            all_items = list(temp_path.rglob("*"))
            all_files = [item for item in all_items if item.is_file()]
            
            # Get relative paths
            rel_paths = [str(f.relative_to(temp_path)) for f in all_files]
            
            # Verify all files are discovered
            assert "index.html" in rel_paths
            assert "src/main.js" in rel_paths
            assert "src/utils/helper.js" in rel_paths
            assert "assets/images/sprite.png" in rel_paths
            
            print(f"\nDiscovered {len(rel_paths)} files:")
            for path in sorted(rel_paths):
                print(f"  - {path}")


