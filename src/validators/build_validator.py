"""
Build validator for TypeScript compilation and type checking.

This module handles the validation of TypeScript builds including:
- Type checking with tsc
- Building with npm run build
- Copying critical files to dist/
- Verifying HTML output
"""
import logging
from src.validators.base import ValidationResult

logger = logging.getLogger(__name__)


async def validate_build(workspace, retry_count: int = 0) -> ValidationResult:
    """
    Validate TypeScript build and type checking.
    
    This function performs the following steps:
    1. Run TypeScript type checker (npx tsc --noEmit)
    2. Run build process (npm run build)
    3. Copy config.json and MANIFEST.json to dist/
    4. Copy test case files (test_case_*.json) to dist/
    5. Verify exactly one HTML file is produced
    6. Copy built HTML to dist/index.html for testing
    
    Args:
        workspace: The Dagger workspace container with the TypeScript project
        retry_count: Current retry attempt number (for error messages)
    
    Returns:
        ValidationResult with:
            - passed=True if build succeeds, workspace updated with copied files
            - passed=False if any step fails, with error_message and failures
    
    Example:
        >>> result = await validate_build(workspace)
        >>> if result.passed:
        ...     workspace = result.workspace
        ... else:
        ...     print(result.error_message)
    """
    logger.info("=== Build Validator - TypeScript Type Checking & Compilation ===")
    
    # Step 1: Run TypeScript type checker
    logger.info("Step 1: Running TypeScript type check: npx tsc --noEmit")
    type_check_result = await workspace.exec(["npx", "tsc", "--noEmit"])
    
    if type_check_result.exit_code != 0:
        # Type check failed - provide feedback to agent
        error_msg = f"""❌ TypeScript Type Check Failed

Type Errors:
{type_check_result.stdout}

The TypeScript type checker found errors in your code. Please fix these type errors.
Common issues:
- Type errors (wrong types, missing properties)
- Missing type definitions
- Incorrect type annotations
- Type mismatches in assignments or function calls

Please review the errors above and fix the TypeScript code."""
        
        logger.warning(f"Type check failed with exit code {type_check_result.exit_code}")
        logger.warning(f"Type check output: {type_check_result.stdout[:500]}")
        
        return ValidationResult(
            passed=False,
            error_message=error_msg,
            failures=[f"TypeScript type check failed: {type_check_result.stdout[:200]}"],
            retry_count=retry_count + 1
        )
    
    logger.info("✅ Type check passed")
    
    # Step 2: Run build
    logger.info("Step 2: Running build: npm run build")
    build_result = await workspace.exec(["npm", "run", "build"])
    
    if build_result.exit_code != 0:
        # Build failed - provide feedback to agent
        error_msg = f"""❌ Build Failed

Build Errors:
{build_result.stderr}

The build process failed. Please fix these errors.
Common issues:
- Import errors (wrong paths, missing files)
- Syntax errors
- Asset loading errors

Please review the errors above and fix the code."""
        
        logger.warning(f"Build failed with exit code {build_result.exit_code}")
        logger.warning(f"Build stderr: {build_result.stderr}")
        
        return ValidationResult(
            passed=False,
            error_message=error_msg,
            failures=[f"Build failed: {build_result.stderr[:200]}"],
            retry_count=retry_count + 1
        )
    
    # Both type check and build succeeded
    logger.info("✅ Build successful")
    logger.info(f"Build output: {build_result.stdout}")
    
    # Copy config.json, MANIFEST.json, and test case files into dist/ for testing
    # This ensures the test container has access to these files
    logger.info("Copying config and test case files into dist/ for testing...")
    
    # Get list of files in workspace root
    workspace_files = await workspace.ls(".")
    
    # Copy critical files (must exist)
    critical_files = ["config.json", "MANIFEST.json"]
    for file_name in critical_files:
        content = await workspace.read_file(file_name)
        workspace = workspace.write_file(f"dist/{file_name}", content)
        logger.info(f"Copied {file_name} to dist/")
    
    # Copy test case files (1-5 test cases, flexible - copy only if they exist)
    test_cases_copied = 0
    for i in range(1, 6):
        test_file = f"test_case_{i}.json"
        if test_file in workspace_files:
            content = await workspace.read_file(test_file)
            workspace = workspace.write_file(f"dist/{test_file}", content)
            logger.info(f"Copied {test_file} to dist/")
            test_cases_copied += 1
        else:
            logger.debug(f"Skipping {test_file}: not found in workspace")
    
    if test_cases_copied == 0:
        error_msg = "❌ No test cases found\n\nYou must create at least 1 test case (test_case_1.json through test_case_5.json).\nTest cases are required to validate the game works correctly."
        logger.error(error_msg)
        return ValidationResult(
            passed=False,
            error_message=error_msg,
            failures=["No test cases found"],
            retry_count=retry_count + 1
        )
    
    logger.info(f"Copied {test_cases_copied} test case(s) to dist/")
    
    # Copy the built HTML to index.html for testing
    # playable-scripts creates a file like "Playable_Template_v1_..._Preview.html"
    # We need it accessible as index.html for testing
    logger.info("Creating index.html for testing...")
    dist_files = await workspace.ls("dist")
    html_files = [f for f in dist_files if f.endswith('.html')]
    
    # Build should produce exactly one HTML file
    if len(html_files) != 1:
        error_msg = f"❌ Expected 1 HTML file in dist/, found {len(html_files)}: {html_files}\n\nThe build should produce exactly one bundled HTML file.\nCheck dist/ directory contents."
        logger.error(error_msg)
        return ValidationResult(
            passed=False,
            error_message=error_msg,
            failures=[f"Build produced {len(html_files)} HTML files, expected 1"],
            retry_count=retry_count + 1
        )
    
    built_html = html_files[0]
    logger.info(f"Found built HTML: {built_html}")
    html_content = await workspace.read_file(f"dist/{built_html}")
    workspace = workspace.write_file("dist/index.html", html_content)
    logger.info("Created dist/index.html for testing")
    
    # Return success with updated workspace
    return ValidationResult(
        passed=True,
        error_message=None,
        failures=[],
        retry_count=0,  # Reset retry count on success
        workspace=workspace  # Return updated workspace with copied files
    )

