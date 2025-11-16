"""
Validators module for game validation logic.

This module contains validators for different stages of game creation:
- build_validator: TypeScript build and type checking
- playable_validator: Main VLM validation of playable
- test_case_validator: Test case execution and validation

Example usage:
    from src.validators import validate_build, validate_playable, validate_test_cases
    
    # Build validation
    result = await validate_build(workspace, retry_count=0)
    if result.passed:
        print("Build successful!")
    
    # Playable validation
    result = await validate_playable(
        workspace, container, vlm_client,
        task_description, session_id, test_run_id
    )
    
    # Test case validation
    result = await validate_test_cases(
        workspace, container, vlm_client,
        session_id, test_run_id
    )
"""

from .base import ValidationResult
from .build_validator import validate_build
from .playable_validator import validate_playable
from .test_case_validator import validate_test_cases

__all__ = [
    "ValidationResult",
    "validate_build",
    "validate_playable",
    "validate_test_cases",
]

