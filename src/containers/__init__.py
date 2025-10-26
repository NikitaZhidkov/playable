"""
Container abstractions for Dagger-based containerized operations.
"""
from .base_container import BaseContainer
from .workspace import Workspace
from .playwright_container import PlaywrightContainer
from .dagger_utils import ExecResult, write_files_bulk

__all__ = [
    "BaseContainer",
    "Workspace",
    "PlaywrightContainer",
    "ExecResult",
    "write_files_bulk",
]

