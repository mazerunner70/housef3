import sys
import os
import pytest
from pathlib import Path

# Add the src directory to Python path for imports
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(backend_dir))

# Ensure Python 3 is being used
def pytest_configure(config):
    """
    Validate Python version and configure pytest
    """
    if sys.version_info[0] < 3:
        raise SystemError("Python 3 is required to run these tests")
    
    # Add markers
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )

# Configure test paths
pytest_plugins = [] 