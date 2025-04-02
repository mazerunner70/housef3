import sys
import pytest

# Ensure Python 3 is being used
def pytest_configure(config):
    """
    Validate Python version and configure pytest
    """
    if sys.version_info[0] < 3:
        raise SystemError("Python 3 is required to run these tests")

# Add markers
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )

# Configure test paths
pytest_plugins = [] 