"""
Integration tests for TypeScript workflow with playable-template-pixi.

These tests verify:
- Template loading from templates/playable-template-pixi/
- npm installation and dependency setup
- TypeScript compilation with npm run build
- dist/ output generation

Run individual test:
  pytest tests/integration/test_typescript_workflow.py::test_template_loads -v

Run all TypeScript tests:
  pytest tests/integration/test_typescript_workflow.py -v
"""
import pytest
import dagger
from pathlib import Path
from src.main import initialize_workspace


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_template_loads_successfully():
    """Test 1: Verify template loads from templates/playable-template-pixi/"""
    print("\n=== Test 1: Template Loading ===")
    
    async with dagger.Connection() as client:
        # Initialize workspace with template
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Check that template files exist
        files = await workspace.ls(".")
        print(f"Files in workspace: {files}")
        
        # Verify key template files are present (check with and without trailing slash)
        assert "src/" in files or "src" in files, "src/ directory missing"
        assert "assets/" in files or "assets" in files, "assets/ directory missing"
        assert "package.json" in files, "package.json missing"
        assert "tsconfig.json" in files, "tsconfig.json missing"
        assert "node_modules/" in files or "node_modules" in files, "node_modules missing (npm install failed)"
        
        # Check src/ contents
        src_files = await workspace.ls("src")
        print(f"Files in src/: {src_files}")
        assert "Game.ts" in src_files, "Game.ts missing"
        assert "index.ts" in src_files, "index.ts missing"
        assert "index.html" in src_files, "index.html missing"
        
        print("✅ Template loaded successfully")


@pytest.mark.asyncio
async def test_typescript_file_modification():
    """Test 2: Verify TypeScript files can be read and modified"""
    print("\n=== Test 2: TypeScript File Modification ===")
    
    async with dagger.Connection() as client:
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Read existing Game.ts
        game_ts_content = await workspace.read_file("src/Game.ts")
        print(f"Game.ts length: {len(game_ts_content)} chars")
        assert len(game_ts_content) > 100, "Game.ts content too short"
        assert "export class Game" in game_ts_content, "Game class not found"
        
        # Modify Game.ts - add a simple comment
        modified_content = "// Modified for testing\n" + game_ts_content
        workspace = workspace.write_file("src/Game.ts", modified_content)
        
        # Read back and verify
        new_content = await workspace.read_file("src/Game.ts")
        assert "Modified for testing" in new_content, "Modification not saved"
        
        print("✅ TypeScript files can be modified")


@pytest.mark.asyncio
async def test_build_process_succeeds():
    """Test 3: Verify TypeScript build process works
    
    Uses Node.js which has full worker_threads support needed by webpack.
    """
    print("\n=== Test 3: Build Process ===")
    
    async with dagger.Connection() as client:
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Step 1: Run type check
        print("Step 1: Running type check: npx tsc --noEmit")
        type_check_result = await workspace.exec(["npx", "tsc", "--noEmit"])
        print(f"Type check exit code: {type_check_result.exit_code}")
        assert type_check_result.exit_code == 0, f"Type check failed: {type_check_result.stdout}"
        print("✅ Type check passed")
        
        # Step 2: Run build (use exec_mut to persist dist/ directory)
        print("Step 2: Running build: npm run build")
        build_result = await workspace.exec_mut(["npm", "run", "build"])
        print(f"Build exit code: {build_result.exit_code}")
        assert build_result.exit_code == 0, f"Build failed: {build_result.stderr}"
        print("✅ Build succeeded")
        
        # Step 3: Check dist/ directory was created
        dist_files = await workspace.ls("dist")
        print(f"dist/ contents: {dist_files}")
        
        assert len(dist_files) > 0, "dist/ directory is empty"
        assert any(".html" in f for f in dist_files), "No HTML file in dist/"
        
        print("✅ dist/ created with HTML output")


@pytest.mark.asyncio
async def test_build_with_simple_modification():
    """Test 4: Verify build works after simple code modification"""
    print("\n=== Test 4: Build After Modification ===")
    
    async with dagger.Connection() as client:
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Modify Game.ts to add a simple property
        game_ts = await workspace.read_file("src/Game.ts")
        
        # Add a new property to the Game class (after the first property declaration)
        modified_game = game_ts.replace(
            "private app: PIXI.Application;",
            "private app: PIXI.Application;\n  private testProperty: string = 'test';"
        )
        
        workspace = workspace.write_file("src/Game.ts", modified_game)
        
        # Build should still succeed
        print("Running: npm run build (after modification)")
        build_result = await workspace.exec_mut(["npm", "run", "build"])
        
        print(f"Build exit code: {build_result.exit_code}")
        
        if build_result.exit_code != 0:
            print(f"Build stderr: {build_result.stderr}")
        
        assert build_result.exit_code == 0, f"Build failed after modification: {build_result.stderr}"
        
        print("✅ Build succeeded after modification")


@pytest.mark.asyncio
async def test_build_with_type_error():
    """Test 5: Verify TypeScript type checker catches type errors"""
    print("\n=== Test 5: TypeScript Type Error Detection ===")
    
    async with dagger.Connection() as client:
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Introduce a type error in Game.ts
        game_ts = await workspace.read_file("src/Game.ts")
        
        # Add code with a type error (assigning string to number)
        modified_game = game_ts.replace(
            "private app: PIXI.Application;",
            "private app: PIXI.Application;\n  private errorTest: number = 'this is wrong';"
        )
        
        workspace = workspace.write_file("src/Game.ts", modified_game)
        
        # Type check should fail
        print("Running: npx tsc --noEmit (with type error)")
        type_check_result = await workspace.exec_mut(["npx", "tsc", "--noEmit"])
        
        print(f"Type check exit code: {type_check_result.exit_code}")
        print(f"Type check output: {type_check_result.stdout[:500]}")
        
        assert type_check_result.exit_code != 0, "Type check should have failed with type error"
        assert "error" in type_check_result.stdout.lower() or "Game.ts" in type_check_result.stdout, "Type check output should contain error"
        
        print("✅ TypeScript type checker correctly caught type error")


@pytest.mark.asyncio
async def test_validate_build_function_success():
    """Test 6: Integration test for validate_build() function directly"""
    print("\n=== Test 6: validate_build() Function ===")
    
    from src.validators.build_validator import validate_build
    
    async with dagger.Connection() as client:
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Add a simple test case file
        test_case_content = '{"expectedOutput": "test", "input": {}}'
        workspace = workspace.write_file("test_case_1.json", test_case_content)
        
        # Run validate_build
        result = await validate_build(workspace, retry_count=0)
        
        print(f"Build validation result: passed={result.passed}")
        
        # Assertions
        assert result.passed is True, f"Build should pass: {result.error_message}"
        assert result.failures == [], f"Should have no failures: {result.failures}"
        assert result.retry_count == 0, "Retry count should be 0 on success"
        assert result.workspace is not None, "Should return updated workspace"
        
        # Verify dist/ was created with expected files
        dist_files = await result.workspace.ls("dist")
        assert "index.html" in dist_files, "index.html should be in dist/"
        assert "config.json" in dist_files, "config.json should be copied to dist/"
        assert "MANIFEST.json" in dist_files, "MANIFEST.json should be copied to dist/"
        assert "test_case_1.json" in dist_files, "test_case_1.json should be copied to dist/"
        
        print("✅ validate_build() integration test passed")


@pytest.mark.asyncio
async def test_validate_build_function_type_error():
    """Test 7: Integration test for validate_build() with type errors"""
    print("\n=== Test 7: validate_build() with Type Errors ===")
    
    from src.validators.build_validator import validate_build
    
    async with dagger.Connection() as client:
        workspace = await initialize_workspace(client, context_dir=None)
        
        # Add test case
        test_case_content = '{"expectedOutput": "test", "input": {}}'
        workspace = workspace.write_file("test_case_1.json", test_case_content)
        
        # Introduce a type error
        game_ts = await workspace.read_file("src/Game.ts")
        modified_game = game_ts.replace(
            "private app: PIXI.Application;",
            "private app: PIXI.Application;\n  private errorTest: number = 'this is wrong';"
        )
        workspace = workspace.write_file("src/Game.ts", modified_game)
        
        # Run validate_build
        result = await validate_build(workspace, retry_count=0)
        
        print(f"Build validation result: passed={result.passed}")
        print(f"Error message: {result.error_message[:100] if result.error_message else 'None'}")
        
        # Assertions
        assert result.passed is False, "Build should fail with type error"
        assert result.error_message is not None, "Should have error message"
        assert "TypeScript Type Check Failed" in result.error_message, "Should mention type check failure"
        assert len(result.failures) > 0, "Should have failures"
        assert result.retry_count == 1, "Retry count should increment"
        
        print("✅ validate_build() correctly detected type error")


if __name__ == "__main__":
    # Run tests individually for debugging
    import sys
    
    print("TypeScript Workflow Integration Tests")
    print("=" * 60)
    print("\nRun with: pytest tests/integration/test_typescript_workflow.py -v")
    print("\nIndividual tests:")
    print("  pytest tests/integration/test_typescript_workflow.py::test_template_loads_successfully -v")
    print("  pytest tests/integration/test_typescript_workflow.py::test_typescript_file_modification -v")
    print("  pytest tests/integration/test_typescript_workflow.py::test_build_process_succeeds -v")
    print("  pytest tests/integration/test_typescript_workflow.py::test_build_with_simple_modification -v")
    print("  pytest tests/integration/test_typescript_workflow.py::test_build_with_type_error -v")
    print("  pytest tests/integration/test_typescript_workflow.py::test_validate_build_function_success -v")
    print("  pytest tests/integration/test_typescript_workflow.py::test_validate_build_function_type_error -v")

