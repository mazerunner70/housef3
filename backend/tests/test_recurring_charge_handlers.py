"""
Unit tests for recurring charge operations handler.
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
import pytest

from handlers import recurring_charge_operations as ops
from models.recurring_charge import (
    RecurringChargePattern,
    RecurrenceFrequency,
    TemporalPatternType,
)


def _auth_headers(user_id="test-user-id"):
    """Helper to create authentication headers"""
    return {
        "headers": {"Authorization": "Bearer test"},
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": user_id,
                        "email": "test@example.com",
                        "auth_time": "2024-01-01T00:00:00Z",
                    }
                }
            }
        },
    }


def _create_test_pattern(user_id="test-user-id"):
    """Helper to create a test pattern"""
    return RecurringChargePattern(
        patternId=uuid.uuid4(),
        userId=user_id,
        merchantPattern="NETFLIX",
        frequency=RecurrenceFrequency.MONTHLY,
        temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
        dayOfMonth=15,
        amountMean=Decimal("15.99"),
        amountStd=Decimal("0.00"),
        amountMin=Decimal("15.99"),
        amountMax=Decimal("15.99"),
        confidenceScore=0.95,
        transactionCount=12,
        firstOccurrence=int(datetime(2024, 1, 15).timestamp() * 1000),
        lastOccurrence=int(datetime(2024, 12, 15).timestamp() * 1000),
        active=True,
    )


# ==============================================================================
# Test Detect Recurring Charges Handler
# ==============================================================================


@patch("src.handlers.recurring_charge_operations.event_service")
@patch("src.handlers.recurring_charge_operations.operation_tracking_service")
def test_detect_recurring_charges_success(mock_tracking, mock_event_service):
    """Test successful detection request"""
    mock_event_service.publish_event.return_value = True
    mock_tracking.start_operation.return_value = "op_123"
    
    event = {
        **_auth_headers(),
        "routeKey": "POST /recurring-charges/detect",
        "body": json.dumps({
            "minOccurrences": 3,
            "minConfidence": 0.6,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "operationId" in body
    assert "message" in body
    assert "detection started" in body["message"].lower()
    
    # Verify event was published
    assert mock_event_service.publish_event.called


@patch("src.handlers.recurring_charge_operations.event_service")
@patch("src.handlers.recurring_charge_operations.operation_tracking_service")
def test_detect_recurring_charges_with_account_filter(mock_tracking, mock_event_service):
    """Test detection with account filter"""
    mock_event_service.publish_event.return_value = True
    mock_tracking.start_operation.return_value = "op_123"
    
    account_id = str(uuid.uuid4())
    event = {
        **_auth_headers(),
        "routeKey": "POST /recurring-charges/detect",
        "body": json.dumps({
            "accountId": account_id,
            "minOccurrences": 5,
            "minConfidence": 0.7,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    
    # Verify event includes account filter
    call_args = mock_event_service.publish_event.call_args
    event_obj = call_args[0][0]
    assert event_obj.data["accountId"] == account_id
    assert event_obj.data["minOccurrences"] == 5
    # Use approximate comparison for float
    assert abs(event_obj.data["minConfidence"] - 0.7) < 0.001


def test_detect_recurring_charges_invalid_min_occurrences():
    """Test validation of minOccurrences parameter"""
    event = {
        **_auth_headers(),
        "routeKey": "POST /recurring-charges/detect",
        "body": json.dumps({
            "minOccurrences": 1,  # Too low
            "minConfidence": 0.6,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 400


def test_detect_recurring_charges_invalid_confidence():
    """Test validation of minConfidence parameter"""
    event = {
        **_auth_headers(),
        "routeKey": "POST /recurring-charges/detect",
        "body": json.dumps({
            "minOccurrences": 3,
            "minConfidence": 1.5,  # Out of range
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 400


# ==============================================================================
# Test Get Patterns Handler
# ==============================================================================


@patch("src.handlers.recurring_charge_operations.list_patterns_by_user_from_db")
def test_get_patterns_success(mock_list):
    """Test successful pattern listing"""
    patterns = [_create_test_pattern() for _ in range(3)]
    mock_list.return_value = patterns
    
    event = {
        **_auth_headers(),
        "routeKey": "GET /recurring-charges/patterns",
        "queryStringParameters": {"limit": "50"},
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "patterns" in body
    assert len(body["patterns"]) == 3
    assert "metadata" in body
    assert body["metadata"]["totalPatterns"] == 3


@patch("src.handlers.recurring_charge_operations.list_patterns_by_user_from_db")
def test_get_patterns_with_active_filter(mock_list):
    """Test pattern listing with active filter"""
    patterns = [_create_test_pattern()]
    mock_list.return_value = patterns
    
    event = {
        **_auth_headers(),
        "routeKey": "GET /recurring-charges/patterns",
        "queryStringParameters": {"active": "true", "limit": "50"},
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    
    # Verify active filter was passed
    call_args = mock_list.call_args
    assert call_args[1]["active"] is True


# ==============================================================================
# Test Update Pattern Handler
# ==============================================================================


@patch("src.handlers.recurring_charge_operations.update_pattern_in_db")
@patch("src.handlers.recurring_charge_operations.get_pattern_by_id_from_db")
def test_update_pattern_success(mock_get, mock_update):
    """Test successful pattern update"""
    pattern = _create_test_pattern()
    
    mock_get.return_value = pattern
    # Mock returns the same pattern instance that was passed to it
    mock_update.return_value = pattern
    
    event = {
        **_auth_headers(),
        "routeKey": "PATCH /recurring-charges/patterns/{id}",
        "pathParameters": {"id": str(pattern.pattern_id)},
        "body": json.dumps({
            "active": False,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "pattern" in body
    
    # Verify update_pattern_in_db was called with the pattern instance
    mock_update.assert_called_once()
    call_args = mock_update.call_args[0]
    assert len(call_args) == 1  # Should only receive the pattern
    assert call_args[0] == pattern


@patch("src.handlers.recurring_charge_operations.get_pattern_by_id_from_db")
def test_update_pattern_not_found(mock_get):
    """Test update of non-existent pattern"""
    mock_get.return_value = None
    
    event = {
        **_auth_headers(),
        "routeKey": "PATCH /recurring-charges/patterns/{id}",
        "pathParameters": {"id": str(uuid.uuid4())},
        "body": json.dumps({
            "active": False,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 404


# ==============================================================================
# Test Apply Pattern to Category Handler
# ==============================================================================


@patch("src.handlers.recurring_charge_operations.update_pattern_in_db")
@patch("src.handlers.recurring_charge_operations.get_category_by_id_from_db")
@patch("src.handlers.recurring_charge_operations.get_pattern_by_id_from_db")
def test_apply_pattern_to_category_success(mock_get_pattern, mock_get_category, mock_update):
    """Test successful pattern-category linking"""
    pattern = _create_test_pattern()
    category_id = uuid.uuid4()
    
    mock_get_pattern.return_value = pattern
    mock_get_category.return_value = MagicMock()  # Mock category
    mock_update.return_value = pattern
    
    event = {
        **_auth_headers(),
        "routeKey": "POST /recurring-charges/patterns/{id}/apply-category",
        "pathParameters": {"id": str(pattern.pattern_id)},
        "body": json.dumps({
            "categoryId": str(category_id),
            "autoCategorize": True,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "pattern" in body
    
    # Verify update_pattern_in_db was called with the pattern instance
    mock_update.assert_called_once()
    call_args = mock_update.call_args[0]
    assert len(call_args) == 1  # Should only receive the pattern
    assert call_args[0] == pattern


@patch("src.handlers.recurring_charge_operations.get_category_by_id_from_db")
@patch("src.handlers.recurring_charge_operations.get_pattern_by_id_from_db")
def test_apply_pattern_to_category_invalid_category(mock_get_pattern, mock_get_category):
    """Test linking to non-existent category"""
    pattern = _create_test_pattern()
    
    mock_get_pattern.return_value = pattern
    mock_get_category.return_value = None  # Category not found
    
    event = {
        **_auth_headers(),
        "routeKey": "POST /recurring-charges/patterns/{id}/apply-category",
        "pathParameters": {"id": str(pattern.pattern_id)},
        "body": json.dumps({
            "categoryId": str(uuid.uuid4()),
            "autoCategorize": True,
        }),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 400


# ==============================================================================
# Test Get Predictions Handler
# ==============================================================================


@patch("src.handlers.recurring_charge_operations.list_predictions_by_user_from_db")
def test_get_predictions_success(mock_list):
    """Test successful prediction listing"""
    mock_list.return_value = []
    
    event = {
        **_auth_headers(),
        "routeKey": "GET /recurring-charges/predictions",
        "queryStringParameters": {"days": "30"},
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "predictions" in body
    assert "metadata" in body
    assert body["metadata"]["daysAhead"] == 30


def test_get_predictions_invalid_days():
    """Test validation of days parameter"""
    event = {
        **_auth_headers(),
        "routeKey": "GET /recurring-charges/predictions",
        "queryStringParameters": {"days": "500"},  # Out of range
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 400


# ==============================================================================
# Test Route Handling
# ==============================================================================


def test_unsupported_route():
    """Test handling of unsupported route"""
    event = {
        **_auth_headers(),
        "routeKey": "GET /recurring-charges/invalid",
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 400


def test_missing_route():
    """Test handling of missing route"""
    event = {
        **_auth_headers(),
    }
    
    resp = ops.handler(event, None)
    assert resp["statusCode"] == 400

