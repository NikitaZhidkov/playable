"""
Playwright container for testing games.
Provides a reusable containerized Playwright environment.
"""
from typing import Self
import dagger
from dagger import ReturnType, Directory
import logging
from .base_container import BaseContainer

logger = logging.getLogger(__name__)


class PlaywrightContainer(BaseContainer):
    """
    Reusable Playwright container for testing games.
    Container is initialized once and can be reset between tests.
    """
    
    def __init__(self, client: dagger.Client, ctr: dagger.Container):
        """
        Initialize PlaywrightContainer.
        
        Args:
            client: Dagger client instance
            ctr: Pre-configured Playwright container
        """
        self._client = client
        self._ctr = ctr
        self._base_ctr = ctr  # Store base container for reset
    
    @classmethod
    async def create(cls, client: dagger.Client) -> Self:
        """
        Create a new PlaywrightContainer with Playwright pre-installed.
        
        Args:
            client: Dagger client instance
        
        Returns:
            Configured PlaywrightContainer instance
        """
        logger.info("Creating PlaywrightContainer with Playwright image...")
        
        # Create base Playwright container with npm dependencies
        ctr = (
            client.container()
            .from_("mcr.microsoft.com/playwright:v1.49.0-jammy")
            .with_workdir("/app")
            # Create package.json and install playwright locally (pin exact version)
            .with_new_file("/app/package.json", '{"dependencies": {"playwright": "1.49.0"}}')
            .with_exec(["npm", "install"], expect=ReturnType.ANY)
        )
        
        # Sync to ensure the container is ready
        ctr = await ctr.sync()
        
        logger.info("PlaywrightContainer created successfully")
        return cls(client, ctr)
    
    @property
    def client(self) -> dagger.Client:
        """Get the Dagger client instance."""
        return self._client
    
    def container(self) -> dagger.Container:
        """Get the underlying Dagger container."""
        return self._ctr
    
    def reset(self) -> Self:
        """
        Reset the container to clean state by clearing /app directory.
        Keeps Playwright and node_modules but removes game files.
        """
        # Reset to base container (with Playwright installed but no game files)
        self._ctr = self._base_ctr
        logger.debug("PlaywrightContainer reset to clean state")
        return self
    
    def copy_directory(self, source_dir: Directory, target_path: str = ".") -> Self:
        """
        Copy a directory into the container at /app.
        
        Args:
            source_dir: The Dagger Directory to copy
            target_path: Where to copy it in the container (default: ".")
        
        Returns:
            Self for method chaining
        """
        self._ctr = self._ctr.with_directory(f"/app/{target_path}" if target_path != "." else "/app", source_dir)
        return self
    
    def with_test_script(self, test_script: str) -> Self:
        """
        Add the test runner script to the container.
        
        Args:
            test_script: JavaScript test script content
        
        Returns:
            Self for method chaining
        """
        self._ctr = self._ctr.with_new_file("/app/test-runner.js", test_script)
        return self

