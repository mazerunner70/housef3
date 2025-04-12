import json
from typing import Dict, Any
import pytest
from src.handlers.list_imports import handler

@pytest.mark.unit
def test_list_imports_success() -> None:
    """Test successful execution of list_imports handler"""
    # Arrange
    event: Dict[str, Any] = {}
    context: Dict[str, Any] = {}

    # Act
    response = handler(event, context)

    # Assert
    assert response["statusCode"] == 200
    assert "Content-Type" in response["headers"]
    assert response["headers"]["Content-Type"] == "application/json"
    
    body = json.loads(response["body"])
    assert "colors" in body
    assert isinstance(body["colors"], list)
    assert len(body["colors"]) == 4
    
    expected_colors = ["Cerulean", "Crimson", "Sage", "Amber"]
    assert body["colors"] == expected_colors

@pytest.mark.unit
def test_cors_headers() -> None:
    """Test that CORS headers are properly set"""
    # Arrange
    event: Dict[str, Any] = {}
    context: Dict[str, Any] = {}

    # Act
    response = handler(event, context)

    # Assert
    headers = response["headers"]
    assert "Access-Control-Allow-Origin" in headers
    assert "Access-Control-Allow-Methods" in headers
    assert "Access-Control-Allow-Headers" in headers
    assert headers["Access-Control-Allow-Methods"] == "GET"
    assert "Content-Type" in headers["Access-Control-Allow-Headers"]
    assert "Authorization" in headers["Access-Control-Allow-Headers"]

@pytest.mark.unit
def test_response_structure() -> None:
    """Test the structure of the response object"""
    # Arrange
    event: Dict[str, Any] = {}
    context: Dict[str, Any] = {}

    # Act
    response = handler(event, context)

    # Assert
    assert isinstance(response, dict)
    required_keys = ["statusCode", "headers", "body"]
    for key in required_keys:
        assert key in response
    
    assert isinstance(response["statusCode"], int)
    assert isinstance(response["headers"], dict)
    assert isinstance(response["body"], str)
    
    # Verify body can be parsed as JSON
    body = json.loads(response["body"])
    assert isinstance(body, dict)

@pytest.mark.unit
def test_error_handling() -> None:
    """Test error handling by simulating an exception"""
    # Arrange
    event = None  # This should trigger a TypeError
    context: Dict[str, Any] = {}

    # Act
    response = handler(event, context)

    # Assert
    assert response["statusCode"] == 500
    assert "Content-Type" in response["headers"]
    assert response["headers"]["Content-Type"] == "application/json"
    
    body = json.loads(response["body"])
    assert "error" in body
    assert "message" in body
    assert body["error"] == "Internal server error" 