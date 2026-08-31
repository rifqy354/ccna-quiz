import pytest
import pytest_asyncio

# Use auto mode so async fixtures work with @pytest.fixture
pytest_plugins = ['pytest_asyncio']

# Set mode to auto so async fixtures work without explicit decorator
import pytest_asyncio.plugin
pytest_asyncio.plugin.MODE = pytest_asyncio.plugin.Mode.AUTO
