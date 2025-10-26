"""
Pytest configuration and fixtures for test suite.
Provides shared fixtures like dagger_client and playwright_container.
"""
import pytest
import dagger
from src.containers import PlaywrightContainer


@pytest.fixture(scope="function")
async def dagger_client():
    """
    Function-scoped Dagger client fixture.
    Creates a Dagger connection for each test.
    """
    async with dagger.Connection() as client:
        yield client


@pytest.fixture(scope="function")
async def playwright_container(dagger_client):
    """
    Function-scoped PlaywrightContainer fixture.
    Creates a fresh Playwright container for each test.
    """
    container = await PlaywrightContainer.create(dagger_client)
    yield container



