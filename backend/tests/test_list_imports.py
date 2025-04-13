import json
import os
from typing import Dict, Any
import pytest
from src.handlers.list_imports import handler

@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    # Store original value
    original_testing = os.environ.get("TESTING")
    
    # Set testing mode only for success tests
    os.environ["TESTING"] = "false"
    yield
    
    # Restore original value
    if original_testing is not None:
        os.environ["TESTING"] = original_testing
    else:
        os.environ.pop("TESTING", None)

@pytest.fixture
def enable_test_mode():
    """Enable test mode for specific tests."""
    os.environ["TESTING"] = "true"
    yield
    os.environ["TESTING"] = "false"

@pytest.fixture
def mock_event() -> Dict[str, Any]:
    """Create a mock event with authentication context."""
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-id",
                        "email": "test@example.com",
                        "auth_time": "2024-01-01T00:00:00Z"
                    }
                }
            }
        }
    }

class MockContext:
    """Mock Lambda context object."""
    def __init__(self):
        self.aws_request_id = "test-request-id"

@pytest.fixture
def mock_context() -> Any:
    """Create a mock Lambda context."""
    return MockContext()

@pytest.mark.unit
def test_list_imports_success(mock_event: Dict[str, Any], mock_context: Any, enable_test_mode) -> None:
    """Test successful execution of list_imports handler"""
    # Act
    response = handler(mock_event, mock_context)

    # Assert
    assert response["statusCode"] == 200
    assert "Content-Type" in response["headers"]
    assert response["headers"]["Content-Type"] == "application/json"
    
    body = json.loads(response["body"])
    assert "colors" in body
    assert isinstance(body["colors"], list)
    assert len(body["colors"]) == 4
    
    expected_colors = [
        {
            "name": "Cerulean",
            "hex": "#007BA7",
            "category": "blue"
        },
        {
            "name": "Crimson",
            "hex": "#DC143C",
            "category": "red"
        },
        {
            "name": "Sage",
            "hex": "#BCB88A",
            "category": "green"
        },
        {
            "name": "Amber",
            "hex": "#FFBF00",
            "category": "yellow"
        }
    ]
    assert body["colors"] == expected_colors
    
    # Check user info
    assert "user" in body
    assert body["user"]["id"] == "test-user-id"
    assert body["user"]["email"] == "test@example.com"
    assert body["user"]["scope"] == "read"
    
    # Check metadata
    assert "metadata" in body
    assert body["metadata"]["totalColors"] == 4
    assert body["metadata"]["timestamp"] == "test-request-id"
    assert body["metadata"]["version"] == "1.0.0"

@pytest.mark.unit
def test_cors_headers(mock_event: Dict[str, Any], mock_context: Any, enable_test_mode) -> None:
    """Test that CORS headers are properly set"""
    # Act
    response = handler(mock_event, mock_context)

    # Assert
    headers = response["headers"]
    assert "Access-Control-Allow-Origin" in headers
    assert "Access-Control-Allow-Methods" in headers
    assert "Access-Control-Allow-Headers" in headers
    assert headers["Access-Control-Allow-Methods"] == "GET,OPTIONS"
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert "Content-Type" in headers["Access-Control-Allow-Headers"]
    assert "Authorization" in headers["Access-Control-Allow-Headers"]

@pytest.mark.unit
def test_options_request() -> None:
    """Test handling of OPTIONS request"""
    # Arrange
    event = {
        "requestContext": {
            "http": {
                "method": "OPTIONS"
            }
        }
    }
    context = MockContext()

    # Act
    response = handler(event, context)

    # Assert
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "OK"

@pytest.mark.unit
def test_unauthorized_request() -> None:
    """Test handling of unauthorized request"""
    # Arrange
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {}  # Empty claims
                }
            }
        }
    }
    context = MockContext()

    # Act
    response = handler(event, context)

    # Assert
    assert response["statusCode"] == 401
    body = json.loads(response["body"])
    assert body["message"] == "Unauthorized"

@pytest.mark.unit
@pytest.mark.parametrize("test_input,expected_status", [
    (None, 500),  # Test None event
    ({}, 401),  # Test empty event
    ({"requestContext": {}}, 401),  # Test missing authorizer
    ({"requestContext": {"authorizer": {}}}, 401),  # Test empty authorizer
    ({"requestContext": {"authorizer": {"jwt": {}}}}, 401),  # Test empty JWT
])
def test_error_handling(test_input: Any, expected_status: int) -> None:
    """Test error handling for various invalid inputs"""
    # Arrange
    context = MockContext()

    # Act
    response = handler(test_input, context)

    # Assert
    assert response["statusCode"] == expected_status
    assert "Content-Type" in response["headers"]
    assert response["headers"]["Content-Type"] == "application/json"
    
    body = json.loads(response["body"])
    assert "message" in body
    if expected_status == 500:
        assert body["message"] == "Internal server error"
    else:
        assert body["message"] == "Unauthorized" 