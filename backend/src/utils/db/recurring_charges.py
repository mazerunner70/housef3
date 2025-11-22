"""
Recurring Charge Pattern database operations.

This module provides CRUD operations for recurring charge patterns,
predictions, and feedback.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from boto3.dynamodb.conditions import Key, Attr

from models.recurring_charge import (
    RecurringChargePattern,
    RecurringChargePatternCreate,
    RecurringChargePatternUpdate,
    RecurringChargePrediction,
    RecurringChargePredictionCreate,
    PatternFeedback,
    PatternFeedbackCreate
)
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    NotFound,
    NotAuthorized,
)

logger = logging.getLogger(__name__)

# Constants
DB_TABLE_NOT_INITIALIZED_ERROR = "Database table not initialized"


# ============================================================================
# Helper Functions
# ============================================================================

def checked_mandatory_pattern(pattern_id: uuid.UUID, user_id: str) -> RecurringChargePattern:
    """
    Check if pattern exists and user has access to it.
    
    Args:
        pattern_id: ID of the pattern
        user_id: ID of the user requesting access
        
    Returns:
        RecurringChargePattern object if found and authorized
        
    Raises:
        NotFound: If pattern doesn't exist
        NotAuthorized: If user doesn't own the pattern
    """
    from .base import NotAuthorized, check_user_owns_resource
    
    if not pattern_id:
        raise NotFound("Pattern ID is required")
    
    pattern = _get_pattern(pattern_id)
    if not pattern:
        raise NotFound("Recurring charge pattern not found")
    
    check_user_owns_resource(pattern.user_id, user_id)
    return pattern


# ============================================================================
# Internal Getter (not exported)
# ============================================================================

@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("_get_pattern")
def _get_pattern(pattern_id: uuid.UUID) -> Optional[RecurringChargePattern]:
    """
    Retrieve a recurring charge pattern by ID (no user validation).
    INTERNAL USE ONLY - external code should use checked_mandatory_pattern.
    
    Args:
        pattern_id: The pattern ID
        
    Returns:
        RecurringChargePattern object if found, None otherwise
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized")
        return None
    
    # Note: This requires scanning since we don't have the user_id
    # For better performance, consider using a GSI on patternId alone
    logger.debug(f"DB: Getting pattern {str(pattern_id)}")
    
    # Scan for the pattern (inefficient but necessary without user_id)
    response = table.scan(
        FilterExpression='patternId = :pid',
        ExpressionAttributeValues={':pid': str(pattern_id)}
    )
    
    items = response.get('Items', [])
    if items:
        return RecurringChargePattern.from_dynamodb_item(items[0])
    return None


# ============================================================================
# Pattern CRUD Operations
# ============================================================================

@dynamodb_operation("create_pattern_in_db")
def create_pattern_in_db(pattern_create: RecurringChargePatternCreate) -> RecurringChargePattern:
    """
    Persist a new recurring charge pattern to DynamoDB.
    
    Args:
        pattern_create: The RecurringChargePatternCreate DTO with pattern data
        
    Returns:
        The created RecurringChargePattern object
        
    Raises:
        ConnectionError: If database table is not initialized
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized for create_pattern_in_db")
        raise ConnectionError(DB_TABLE_NOT_INITIALIZED_ERROR)
    
    # Instantiate the full model from the Create DTO
    pattern_data = pattern_create.model_dump(by_alias=False)
    pattern = RecurringChargePattern(**pattern_data)
    
    table.put_item(Item=pattern.to_dynamodb_item())
    logger.info(f"DB: Pattern {str(pattern.pattern_id)} created successfully for user {pattern.user_id}.")
    return pattern


@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_pattern_by_id_from_db")
def get_pattern_by_id_from_db(pattern_id: uuid.UUID, user_id: str) -> Optional[RecurringChargePattern]:
    """
    Retrieve a recurring charge pattern by ID and user ID.
    
    DEPRECATED: Use checked_mandatory_pattern() instead for better error handling.
    This function is kept for backward compatibility with existing code.
    
    Args:
        pattern_id: The pattern ID
        user_id: The user ID (for access control)
        
    Returns:
        RecurringChargePattern object if found and owned by user, None otherwise
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized for get_pattern_by_id_from_db")
        return None
    
    logger.debug(f"DB: Getting pattern {str(pattern_id)} for user {user_id}")
    response = table.get_item(Key={'userId': user_id, 'patternId': str(pattern_id)})
    item = response.get('Item')
    
    if item:
        return RecurringChargePattern.from_dynamodb_item(item)
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_patterns_by_user_from_db")
def list_patterns_by_user_from_db(
    user_id: str,
    active: Optional[bool] = None,
    min_confidence: Optional[float] = None,
    limit: Optional[int] = None
) -> List[RecurringChargePattern]:
    """
    List recurring charge patterns for a user with optional filters.
    
    Args:
        user_id: The user ID
        active: If True, only return active patterns; if False, only inactive; if None, return all
        min_confidence: Optional minimum confidence score filter
        limit: Optional maximum number of patterns to return
        
    Returns:
        List of RecurringChargePattern objects
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized for list_patterns_by_user_from_db")
        return []
    
    logger.debug(f"DB: Listing patterns for user {user_id}, active: {active}, min_confidence: {min_confidence}, limit: {limit}")
    
    # Query by userId (partition key)
    response = table.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )
    
    items = response.get('Items', [])
    patterns = [RecurringChargePattern.from_dynamodb_item(item) for item in items]
    
    # Apply filters
    if active is not None:
        patterns = [p for p in patterns if p.active == active]
    
    if min_confidence is not None:
        patterns = [p for p in patterns if p.confidence_score >= min_confidence]
    
    # Apply limit
    if limit is not None and limit > 0:
        patterns = patterns[:limit]
    
    logger.info(f"DB: Found {len(patterns)} patterns for user {user_id}")
    return patterns


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_pattern_in_db")
def update_pattern_in_db(
    pattern: RecurringChargePattern
) -> RecurringChargePattern:
    """
    Update a recurring charge pattern in the database.
    
    Args:
        pattern: The RecurringChargePattern instance to save (already updated)
        
    Returns:
        The same RecurringChargePattern object after successful save
        
    Raises:
        ConnectionError: If table not initialized
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized for update_pattern_in_db")
        raise ConnectionError(DB_TABLE_NOT_INITIALIZED_ERROR)
    
    # Save updates to DynamoDB
    table.put_item(Item=pattern.to_dynamodb_item())
    
    logger.info(f"DB: Pattern {str(pattern.pattern_id)} updated successfully")
    return pattern


@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_pattern_from_db")
def delete_pattern_from_db(pattern_id: uuid.UUID, user_id: str) -> bool:
    """
    Delete a recurring charge pattern.
    
    Args:
        pattern_id: The pattern ID
        user_id: The user ID (for access control)
        
    Returns:
        True if deleted successfully
        
    Raises:
        NotFound: If pattern doesn't exist
        NotAuthorized: If user doesn't own the pattern
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized for delete_pattern_from_db")
        raise ConnectionError(DB_TABLE_NOT_INITIALIZED_ERROR)
    
    # First, verify the pattern exists and belongs to the user
    existing_pattern = get_pattern_by_id_from_db(pattern_id, user_id)
    if not existing_pattern:
        raise NotFound(f"Pattern {str(pattern_id)} not found")
    
    logger.debug(f"DB: Deleting pattern {str(pattern_id)} for user {user_id}")
    
    table.delete_item(
        Key={'userId': user_id, 'patternId': str(pattern_id)}
    )
    
    logger.info(f"DB: Pattern {str(pattern_id)} deleted successfully")
    return True


@monitor_performance(operation_type="batch_write", warn_threshold_ms=1000)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("batch_create_patterns_in_db")
def batch_create_patterns_in_db(pattern_creates: List[RecurringChargePatternCreate]) -> int:
    """
    Batch create multiple recurring charge patterns.
    
    Args:
        pattern_creates: List of RecurringChargePatternCreate DTOs to create
        
    Returns:
        Number of patterns successfully created
        
    Raises:
        ConnectionError: If database table is not initialized
    """
    table = tables.recurring_charge_patterns
    if not table:
        logger.error("DB: RecurringChargePatterns table not initialized for batch_create_patterns_in_db")
        raise ConnectionError(DB_TABLE_NOT_INITIALIZED_ERROR)
    
    if not pattern_creates:
        return 0
    
    logger.debug(f"DB: Batch creating {len(pattern_creates)} patterns")
    
    # DynamoDB batch_write_item has a limit of 25 items per batch
    batch_size = 25
    total_created = 0
    
    for i in range(0, len(pattern_creates), batch_size):
        batch = pattern_creates[i:i + batch_size]
        
        with table.batch_writer() as writer:
            for pattern_create in batch:
                # Instantiate the full model from the Create DTO
                pattern_data = pattern_create.model_dump(by_alias=False)
                pattern = RecurringChargePattern(**pattern_data)
                writer.put_item(Item=pattern.to_dynamodb_item())
                total_created += 1
    
    logger.info(f"DB: Batch created {total_created} patterns successfully")
    return total_created


# ============================================================================
# Prediction Operations
# ============================================================================

@dynamodb_operation("save_prediction_in_db")
def save_prediction_in_db(prediction_create: RecurringChargePredictionCreate, user_id: str) -> RecurringChargePrediction:
    """
    Save a recurring charge prediction to DynamoDB.
    
    Args:
        prediction_create: The RecurringChargePredictionCreate DTO with prediction data
        user_id: The user ID (for composite key)
        
    Returns:
        The saved RecurringChargePrediction object
        
    Raises:
        ConnectionError: If database table is not initialized
        ValidationError: If prediction data is invalid
    """
    table = tables.recurring_charge_predictions
    if not table:
        logger.error("DB: RecurringChargePredictions table not initialized for save_prediction_in_db")
        raise ConnectionError(DB_TABLE_NOT_INITIALIZED_ERROR)
    
    # Construct the full RecurringChargePrediction model from the Create DTO
    # This validates all fields according to the model's validators
    prediction = RecurringChargePrediction(
        patternId=prediction_create.pattern_id,
        nextExpectedDate=prediction_create.next_expected_date,
        expectedAmount=prediction_create.expected_amount,
        confidence=prediction_create.confidence,
        daysUntilDue=prediction_create.days_until_due,
        amountRange=prediction_create.amount_range
    )
    
    # Convert to DynamoDB item and add userId
    item = prediction.to_dynamodb_item()
    item['userId'] = user_id  # Add userId for partition key
    
    table.put_item(Item=item)
    logger.info(f"DB: Prediction for pattern {str(prediction.pattern_id)} saved successfully")
    return prediction


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_predictions_by_user_from_db")
def list_predictions_by_user_from_db(
    user_id: str,
    days_ahead: Optional[int] = None
) -> List[RecurringChargePrediction]:
    """
    List recurring charge predictions for a user.
    
    Args:
        user_id: The user ID
        days_ahead: Optional filter for predictions within N days
        
    Returns:
        List of RecurringChargePrediction objects
    """
    table = tables.recurring_charge_predictions
    if not table:
        logger.error("DB: RecurringChargePredictions table not initialized for list_predictions_by_user_from_db")
        return []
    
    logger.debug(f"DB: Listing predictions for user {user_id}, days_ahead: {days_ahead}")
    
    # Query by userId (partition key)
    response = table.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )
    
    items = response.get('Items', [])
    predictions = [RecurringChargePrediction.from_dynamodb_item(item) for item in items]
    
    # Apply filter for days_ahead
    if days_ahead is not None:
        predictions = [p for p in predictions if p.days_until_due <= days_ahead]
    
    logger.info(f"DB: Found {len(predictions)} predictions for user {user_id}")
    return predictions


# ============================================================================
# Feedback Operations
# ============================================================================

@dynamodb_operation("save_feedback_in_db")
def save_feedback_in_db(feedback_create: PatternFeedbackCreate) -> PatternFeedback:
    """
    Save pattern feedback to DynamoDB.
    
    Args:
        feedback_create: The PatternFeedbackCreate DTO with feedback data
        
    Returns:
        The saved PatternFeedback object
        
    Raises:
        ConnectionError: If database table is not initialized
    """
    table = tables.pattern_feedback
    if not table:
        logger.error("DB: PatternFeedback table not initialized for save_feedback_in_db")
        raise ConnectionError(DB_TABLE_NOT_INITIALIZED_ERROR)
    
    # Instantiate the full model from the Create DTO
    feedback_data = feedback_create.model_dump(by_alias=False)
    feedback = PatternFeedback(**feedback_data)
    
    table.put_item(Item=feedback.to_dynamodb_item())
    logger.info(f"DB: Feedback {str(feedback.feedback_id)} saved successfully for pattern {str(feedback.pattern_id)}")
    return feedback


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_feedback_by_pattern_from_db")
def list_feedback_by_pattern_from_db(pattern_id: uuid.UUID, user_id: str) -> List[PatternFeedback]:
    """
    List feedback for a specific pattern.
    
    Args:
        pattern_id: The pattern ID
        user_id: The user ID (for access control)
        
    Returns:
        List of PatternFeedback objects
    """
    table = tables.pattern_feedback
    if not table:
        logger.error("DB: PatternFeedback table not initialized for list_feedback_by_pattern_from_db")
        return []
    
    logger.debug(f"DB: Listing feedback for pattern {str(pattern_id)}")
    
    # Query by userId and filter by patternId
    response = table.query(
        KeyConditionExpression=Key('userId').eq(user_id),
        FilterExpression=Attr('patternId').eq(str(pattern_id))
    )
    
    items = response.get('Items', [])
    feedback_list = [PatternFeedback.from_dynamodb_item(item) for item in items]
    
    logger.info(f"DB: Found {len(feedback_list)} feedback items for pattern {str(pattern_id)}")
    return feedback_list


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_all_feedback_by_user_from_db")
def list_all_feedback_by_user_from_db(user_id: str) -> List[PatternFeedback]:
    """
    List all feedback for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        List of PatternFeedback objects
    """
    table = tables.pattern_feedback
    if not table:
        logger.error("DB: PatternFeedback table not initialized for list_all_feedback_by_user_from_db")
        return []
    
    logger.debug(f"DB: Listing all feedback for user {user_id}")
    
    # Query by userId (partition key)
    response = table.query(
        KeyConditionExpression=Key('userId').eq(user_id)
    )
    
    items = response.get('Items', [])
    feedback_list = [PatternFeedback.from_dynamodb_item(item) for item in items]
    
    logger.info(f"DB: Found {len(feedback_list)} feedback items for user {user_id}")
    return feedback_list

