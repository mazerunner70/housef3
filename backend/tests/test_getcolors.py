import json
import os
from typing import Dict, Any
import pytest
from src.handlers.getcolors import handler

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
def enable_test_mode(monkeypatch):
    """Enable test mode for the handler"""
    monkeypatch.setenv("TESTING", "true")

@pytest.fixture
def mock_event() -> Dict[str, Any]:
    """Create a mock API Gateway event"""
    return {
        "version": "2.0",
        "routeKey": "GET /colors",
        "rawPath": "/colors",
        "rawQueryString": "",
        "headers": {
            "accept": "*/*",
            "content-length": "0",
            "host": "api.example.com",
            "user-agent": "curl/7.64.1",
            "x-amzn-trace-id": "Root=1-5e6722a7-cc56xmpl46db7ae02d4da47dd",
            "x-forwarded-for": "72.21.198.66",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https"
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "http": {
                "method": "GET",
                "path": "/colors",
                "protocol": "HTTP/1.1",
                "sourceIp": "72.21.198.66",
                "userAgent": "curl/7.64.1"
            },
            "requestId": "id",
            "routeKey": "GET /colors",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390,
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-id",
                        "email": "test@example.com",
                        "auth_time": "2024-01-01T00:00:00Z"
                    }
                }
            }
        },
        "isBase64Encoded": False
    }

class MockContext:
    """Mock Lambda context object."""
    def __init__(self):
        self.aws_request_id = "test-request-id"

@pytest.fixture
def mock_context() -> Dict[str, Any]:
    """Create a mock Lambda context"""
    return {
        "aws_request_id": "test-request-id",
        "function_name": "test-function",
        "memory_limit_in_mb": 128,
        "invoked_function_arn": "arn:aws:lambda:us-east-1:123456789012:function:test-function",
        "log_group_name": "/aws/lambda/test-function",
        "log_stream_name": "2020/03/12/[$LATEST]abcdef123456",
    }

@pytest.mark.unit
def test_getcolors_success(mock_event: Dict[str, Any], mock_context: Any, enable_test_mode) -> None:
    """Test successful execution of getcolors handler"""
    response = handler(mock_event, mock_context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    assert "colors" in body
    assert isinstance(body["colors"], list)
    assert len(body["colors"]) > 0
    assert "metadata" in body
    assert "totalColors" in body["metadata"]
    assert body["metadata"]["totalColors"] == len(body["colors"])
    assert "user" in body
    assert body["user"]["id"] == "test-user-id"

@pytest.mark.unit
def test_getcolors_unauthorized(mock_event: Dict[str, Any], mock_context: Any) -> None:
    """Test unauthorized request"""
    # Remove authorizer from event
    mock_event["requestContext"]["authorizer"] = {}
    
    response = handler(mock_event, mock_context)
    assert response["statusCode"] == 401
    body = json.loads(response["body"])
    assert body["message"] == "Unauthorized"

@pytest.mark.unit
def test_getcolors_error(mock_event: Dict[str, Any], mock_context: Any) -> None:
    """Test error handling"""
    # Set event to None to trigger error
    response = handler(None, mock_context)
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["message"] == "Internal server error"

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