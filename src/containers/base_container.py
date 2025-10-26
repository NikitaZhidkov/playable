"""
Abstract base class for containers that can hold and execute game files.
Both Workspace and PlaywrightContainer inherit from this.
"""
from abc import ABC, abstractmethod
from typing import Self
import dagger
from dagger import Container, Directory


class BaseContainer(ABC):
    """Abstract base class for containers with common interface."""
    
    @property
    @abstractmethod
    def client(self) -> dagger.Client:
        """Get the Dagger client instance."""
        pass
    
    @abstractmethod
    def container(self) -> Container:
        """Get the underlying Dagger container."""
        pass
    
    @abstractmethod
    def reset(self) -> Self:
        """Reset the container to a clean state."""
        pass
    
    @abstractmethod
    def copy_directory(self, source_dir: Directory, target_path: str = ".") -> Self:
        """
        Copy a directory into the container.
        
        Args:
            source_dir: The Dagger Directory to copy
            target_path: Where to copy it in the container (default: ".")
        
        Returns:
            Self for method chaining
        """
        pass

