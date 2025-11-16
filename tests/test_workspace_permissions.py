"""Tests for workspace file permission restrictions."""

import pytest
import dagger
from src.containers import Workspace


@pytest.mark.asyncio
class TestWorkspacePermissions:
    """Test that workspace correctly restricts file operations to allowed paths."""
    
    async def test_workspace_allows_src_files(self):
        """Test that agent can write files in src/ folder."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should succeed - src/ is allowed
            workspace = workspace.write_file("src/test.ts", "console.log('test');")
            content = await workspace.read_file("src/test.ts")
            assert content == "console.log('test');"
    
    async def test_workspace_blocks_assets_files(self):
        """Test that agent cannot write files in assets/ folder (read-only)."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should fail - assets/ is read-only, not in allowed paths
            with pytest.raises(PermissionError, match="not in allowed paths"):
                workspace.write_file("assets/sprite.png", "fake-png-data")
    
    async def test_workspace_can_read_assets(self):
        """Test that agent can read assets (but not write)."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Create an asset with force=True (simulating system-prepared assets)
            workspace = workspace.write_file("assets/car.png", "fake-png-data", force=True)
            
            # Should be able to read it
            content = await workspace.read_file("assets/car.png")
            assert content == "fake-png-data"
            
            # But should NOT be able to modify it
            with pytest.raises(PermissionError):
                workspace.write_file("assets/car.png", "hacked-data")
    
    async def test_workspace_blocks_package_json(self):
        """Test that agent cannot modify package.json."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should fail - package.json is not in allowed paths
            with pytest.raises(PermissionError, match="not in allowed paths"):
                workspace.write_file("package.json", '{"name": "hacked"}')
    
    async def test_workspace_blocks_tsconfig(self):
        """Test that agent cannot modify tsconfig.json."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should fail - tsconfig.json is not in allowed paths
            with pytest.raises(PermissionError, match="not in allowed paths"):
                workspace.write_file("tsconfig.json", '{}')
    
    async def test_workspace_blocks_root_files(self):
        """Test that agent cannot create files in root directory."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should fail - root files are not allowed
            with pytest.raises(PermissionError, match="not in allowed paths"):
                workspace.write_file("README.md", "# Hacked")
    
    async def test_workspace_blocks_test_cases(self):
        """Test that agent cannot create test case files in root."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should fail - test_case files in root are not allowed
            with pytest.raises(PermissionError, match="not in allowed paths"):
                workspace.write_file("test_case_1.json", '{"test": "data"}')
    
    async def test_workspace_allows_nested_src_files(self):
        """Test that agent can write deeply nested files in src/."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Should succeed - nested in src/ is allowed
            workspace = workspace.write_file("src/components/Button.ts", "export class Button {}")
            content = await workspace.read_file("src/components/Button.ts")
            assert content == "export class Button {}"
    
    async def test_workspace_can_read_protected_files(self):
        """Test that agent can read (but not write) files outside allowed paths."""
        async with dagger.Connection() as client:
            # Create workspace with a file outside allowed paths
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Write a file with force=True to bypass restrictions (simulating system-created file)
            workspace = workspace.write_file("package.json", '{"name": "test"}', force=True)
            
            # Should be able to read it
            content = await workspace.read_file("package.json")
            assert content == '{"name": "test"}'
            
            # But should not be able to modify it
            with pytest.raises(PermissionError):
                workspace.write_file("package.json", '{"name": "hacked"}')
    
    async def test_workspace_delete_respects_allowed(self):
        """Test that delete operations also respect allowed paths."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            # Create files
            workspace = workspace.write_file("src/test.ts", "test")
            
            # Should be able to delete allowed files
            workspace = workspace.rm("src/test.ts")
            
            # Verify it's deleted
            with pytest.raises(FileNotFoundError):
                await workspace.read_file("src/test.ts")
            
            # Cannot delete assets (read-only)
            workspace = workspace.write_file("assets/test.png", "test", force=True)  # Created by system
            with pytest.raises(PermissionError):
                workspace.rm("assets/test.png")
    
    async def test_initialize_workspace_has_restrictions(self):
        """Test that the actual initialize_workspace function sets up restrictions."""
        async with dagger.Connection() as client:
            from src.main import initialize_workspace
            
            workspace = await initialize_workspace(client, context_dir=None)
            
            # Should be able to write to src/
            workspace = workspace.write_file("src/MyGame.ts", "export class MyGame {}")
            
            # Should NOT be able to write to root
            with pytest.raises(PermissionError, match="not in allowed paths"):
                workspace.write_file("package.json", "hacked")
    
    async def test_permission_error_message_is_clear(self):
        """Test that permission errors have clear, helpful messages."""
        async with dagger.Connection() as client:
            workspace = await Workspace.create(
                client=client,
                base_image="alpine",
                allowed=["src/"]
            )
            
            try:
                workspace.write_file("build.json", "hacked")
                pytest.fail("Should have raised PermissionError")
            except PermissionError as e:
                error_msg = str(e)
                # Should mention what was attempted
                assert "build.json" in error_msg
                # Should mention allowed paths
                assert "allowed paths" in error_msg
                # Should list the actual allowed paths
                assert "src/" in error_msg
            
            # Test assets are also protected
            try:
                workspace.write_file("assets/hacked.png", "hacked")
                pytest.fail("Should have raised PermissionError for assets")
            except PermissionError as e:
                error_msg = str(e)
                assert "assets/hacked.png" in error_msg
                assert "not in allowed paths" in error_msg

