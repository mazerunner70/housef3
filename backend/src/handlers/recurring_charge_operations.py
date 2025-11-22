"""
Recurring Charge Operations Handler.

This module provides API endpoints for recurring charge pattern detection,
management, and predictions.
"""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
from models.recurring_charge import (
    RecurringChargePattern,
    RecurringChargePatternUpdate,
    RecurringChargePrediction,
)
from utils.db.recurring_charges import (
    get_pattern_by_id_from_db,
    list_patterns_by_user_from_db,
    update_pattern_in_db,
    list_predictions_by_user_from_db,
    checked_mandatory_pattern,
)
from utils.lambda_utils import (
    create_response,
    mandatory_path_parameter,
    mandatory_query_parameter,
    optional_query_parameter,
    parse_and_validate_json,
)
from utils.handler_decorators import (
    api_handler,
    standard_error_handling,
    require_authenticated_user,
)
from services.event_service import event_service
from models.events import BaseEvent


# ============================================================================
# Handler Functions
# ============================================================================

@api_handler()
def detect_recurring_charges_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Trigger recurring charge detection for a user.
    
    POST /api/recurring-charges/detect
    
    Request body:
    {
        "accountId": "optional-account-id",  # Filter to specific account
        "minOccurrences": 3,                 # Minimum pattern occurrences
        "minConfidence": 0.6,                # Minimum confidence threshold
        "maxTransactions": 10000             # Maximum transactions to analyze (default: 10000)
    }
    
    Returns:
    {
        "message": "Detection started",
        "operationId": "op_20250107_123456_abc"
    }
    """
    # Parse optional parameters
    body = json.loads(event.get("body", "{}"))
    account_id = body.get("accountId")
    min_occurrences = body.get("minOccurrences", 3)
    min_confidence = body.get("minConfidence", 0.6)
    max_transactions = body.get("maxTransactions", 10000)
    
    # Validate parameters
    if min_occurrences < 2:
        raise ValueError("minOccurrences must be at least 2")
    if not (0.0 <= min_confidence <= 1.0):
        raise ValueError("minConfidence must be between 0.0 and 1.0")
    if max_transactions < 10:
        raise ValueError("maxTransactions must be at least 10")
    if max_transactions > 50000:
        raise ValueError("maxTransactions must not exceed 50000")
    
    # Create operation tracking record
    from services.operation_tracking_service import (
        operation_tracking_service,
        OperationType,
    )
    
    # Generate operation ID
    from datetime import datetime
    operation_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}"
    
    # Start operation tracking
    # Convert float to Decimal for DynamoDB compatibility
    context = {
        "userId": user_id,
        "accountId": account_id,
        "minOccurrences": min_occurrences,
        "minConfidence": Decimal(str(min_confidence)),  # Convert float to Decimal
        "maxTransactions": max_transactions,
    }
    
    operation_tracking_service.start_operation(
        operation_type=OperationType.RECURRING_CHARGE_DETECTION,
        entity_id=account_id or user_id,
        user_id=user_id,
        context=context,
        operation_id=operation_id,
    )
    
    # Publish event to trigger async detection
    detection_event = BaseEvent(
        event_id=str(uuid.uuid4()),
        event_type="recurring_charge.detection.requested",
        event_version="1.0",
        timestamp=int(datetime.now().timestamp() * 1000),
        source="recurring_charge.service",
        user_id=user_id,
        correlation_id=operation_id,
        data={
            "operationId": operation_id,
            "accountId": account_id,
            "minOccurrences": min_occurrences,
            "minConfidence": min_confidence,
            "maxTransactions": max_transactions,
        },
    )
    
    success = event_service.publish_event(detection_event)
    
    if not success:
        raise Exception("Failed to publish detection event")
    
    logger.info(f"Published recurring charge detection event for user {user_id}, operation {operation_id}")
    
    return {
        "message": "Recurring charge detection started",
        "operationId": operation_id,
    }


@api_handler()
def get_patterns_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get recurring charge patterns for a user.
    
    GET /api/recurring-charges/patterns?active=true&limit=50
    
    Query parameters:
    - active: Filter by active status (optional)
    - limit: Maximum number of patterns to return (default: 50)
    
    Returns:
    {
        "patterns": [...],
        "metadata": {
            "totalPatterns": 10,
            "activePatterns": 8
        }
    }
    """
    # Parse query parameters
    active_filter = optional_query_parameter(event, "active")
    limit = int(optional_query_parameter(event, "limit") or "50")
    
    # Convert active filter to boolean if provided
    active_bool: Optional[bool] = None
    if active_filter is not None:
        active_bool = active_filter.lower() in ("true", "1", "yes")
    
    # Get patterns from database
    patterns = list_patterns_by_user_from_db(user_id, active=active_bool, limit=limit)
    
    # Serialize patterns
    pattern_dicts = [
        pattern.model_dump(by_alias=True, mode="json") for pattern in patterns
    ]
    
    # Calculate metadata
    active_count = sum(1 for p in patterns if p.active)
    
    return {
        "patterns": pattern_dicts,
        "metadata": {
            "totalPatterns": len(pattern_dicts),
            "activePatterns": active_count,
        },
    }


@api_handler(require_ownership=("id", "pattern"))
def get_pattern_handler(event: Dict[str, Any], user_id: str, pattern: RecurringChargePattern) -> Dict[str, Any]:
    """
    Get a specific recurring charge pattern.
    
    GET /api/recurring-charges/patterns/{id}
    
    Returns:
    {
        "pattern": {...}
    }
    """
    return {"pattern": pattern.model_dump(by_alias=True, mode="json")}


@api_handler(require_ownership=("id", "pattern"))
def update_pattern_handler(event: Dict[str, Any], user_id: str, pattern: RecurringChargePattern) -> Dict[str, Any]:
    """
    Update a recurring charge pattern.
    
    PATCH /api/recurring-charges/patterns/{id}
    
    Request body:
    {
        "active": false,
        "autoCategorize": true,
        "suggestedCategoryId": "category-uuid"
    }
    
    Returns:
    {
        "message": "Pattern updated successfully",
        "pattern": {...}
    }
    """
    # Parse and validate update data
    update_data, error_response = parse_and_validate_json(event, RecurringChargePatternUpdate)
    if error_response:
        raise ValueError(error_response["message"])
    
    assert update_data is not None
    
    # Update the pattern model with the validated DTO
    pattern.update_model_details(update_data)
    
    # Persist the updated pattern to database
    updated_pattern = update_pattern_in_db(pattern)
    
    return {
        "message": "Pattern updated successfully",
        "pattern": updated_pattern.model_dump(by_alias=True, mode="json"),
    }


@api_handler()
def get_predictions_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get upcoming recurring charge predictions.
    
    GET /api/recurring-charges/predictions?days=30
    
    Query parameters:
    - days: Number of days to look ahead (default: 30)
    
    Returns:
    {
        "predictions": [...],
        "metadata": {
            "totalPredictions": 5,
            "daysAhead": 30
        }
    }
    """
    # Parse query parameters
    days_ahead = int(optional_query_parameter(event, "days") or "30")
    
    if days_ahead < 1 or days_ahead > 365:
        raise ValueError("days must be between 1 and 365")
    
    # Get predictions from database
    predictions = list_predictions_by_user_from_db(user_id, days_ahead=days_ahead)
    
    # Serialize predictions
    prediction_dicts = [
        prediction.model_dump(by_alias=True, mode="json") for prediction in predictions
    ]
    
    return {
        "predictions": prediction_dicts,
        "metadata": {
            "totalPredictions": len(prediction_dicts),
            "daysAhead": days_ahead,
        },
    }


@api_handler(require_ownership=("id", "pattern"))
def apply_pattern_to_category_handler(
    event: Dict[str, Any], user_id: str, pattern: RecurringChargePattern
) -> Dict[str, Any]:
    """
    Link a recurring charge pattern to a category for auto-categorization.
    
    POST /api/recurring-charges/patterns/{id}/apply-category
    
    Request body:
    {
        "categoryId": "category-uuid",
        "autoCategorize": true
    }
    
    Returns:
    {
        "message": "Pattern linked to category successfully",
        "pattern": {...}
    }
    """
    # Parse request body
    body = json.loads(event.get("body", "{}"))
    category_id = body.get("categoryId")
    auto_categorize = body.get("autoCategorize", True)
    
    if not category_id:
        raise ValueError("categoryId is required")
    
    # Validate category exists and belongs to user
    from utils.db_utils import checked_mandatory_category
    from utils.db.base import NotFound, NotAuthorized
    try:
        checked_mandatory_category(uuid.UUID(category_id), user_id)
    except (NotFound, NotAuthorized):
        raise ValueError("Category not found or does not belong to user")
    
    # Create update DTO and apply to pattern
    update_data = RecurringChargePatternUpdate(
        suggestedCategoryId=uuid.UUID(category_id),
        autoCategorize=auto_categorize,
    )
    pattern.update_model_details(update_data)
    
    # Persist the updated pattern to database
    updated_pattern = update_pattern_in_db(pattern)
    
    return {
        "message": "Pattern linked to category successfully",
        "pattern": updated_pattern.model_dump(by_alias=True, mode="json"),
    }


# ============================================================================
# Main Handler
# ============================================================================

@require_authenticated_user
@standard_error_handling
def handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Main handler for recurring charge operations.
    
    Routes requests to appropriate handler functions based on route.
    """
    route = event.get("routeKey")
    if not route:
        raise ValueError("Route not specified")
    
    # Route to appropriate handler
    route_map = {
        "POST /recurring-charges/detect": detect_recurring_charges_handler,
        "GET /recurring-charges/patterns": get_patterns_handler,
        "GET /recurring-charges/patterns/{id}": get_pattern_handler,
        "PATCH /recurring-charges/patterns/{id}": update_pattern_handler,
        "GET /recurring-charges/predictions": get_predictions_handler,
        "POST /recurring-charges/patterns/{id}/apply-category": apply_pattern_to_category_handler,
    }
    
    handler_func = route_map.get(route)
    if not handler_func:
        raise ValueError(f"Unsupported route: {route}")
    
    return handler_func(event, user_id)

