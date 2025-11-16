"""
Base types and classes for validators.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class ValidationResult:
    """Result of a validation check.
    
    Attributes:
        passed: Whether validation passed successfully
        error_message: Optional error message if validation failed
        failures: List of specific failure messages
        retry_count: Number of retry attempts for this validation
        workspace: Optional updated workspace (for validators that modify workspace)
    """
    passed: bool
    error_message: Optional[str] = None
    failures: List[str] = field(default_factory=list)
    retry_count: int = 0
    workspace: Optional[Any] = None  # Optional updated workspace

