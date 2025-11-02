"""
Analytics database operations.

This module provides CRUD operations for analytics data and processing status.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import Binary

from models import (
    AnalyticsData,
    AnalyticsProcessingStatus,
    AnalyticType,
)
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
)
from .helpers import batch_write_items

logger = logging.getLogger(__name__)


# =============================================================================
# Analytics Data Operations
# =============================================================================

def store_analytics_data(analytics_data: AnalyticsData) -> None:
    """
    Store computed analytics data in DynamoDB.
    
    Args:
        analytics_data: The AnalyticsData object to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    item = analytics_data.to_dynamodb_item()
    tables.analytics_data.put_item(Item=item)
    logger.info(f"Stored analytics data: {analytics_data.analytic_type.value} for user {analytics_data.user_id}, period {analytics_data.time_period}")


@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_analytics_data")
def get_analytics_data(
    user_id: str,
    analytic_type: AnalyticType,
    time_period: str,
    account_id: Optional[str] = None
) -> Optional[AnalyticsData]:
    """
    Retrieve specific analytics data from DynamoDB.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        time_period: The time period (e.g., '2024-12')
        account_id: Optional account ID (None for cross-account)
        
    Returns:
        AnalyticsData object if found, None otherwise
    """
    pk = f"{user_id}#{analytic_type.value}"
    account_part = account_id or 'ALL'
    sk = f"{time_period}#{account_part}"
    
    response = tables.analytics_data.get_item(
        Key={'pk': pk, 'sk': sk}
    )
    
    if 'Item' in response:
        return AnalyticsData.from_dynamodb_item(response['Item'])
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_analytics_data_for_user")
def list_analytics_data_for_user(
    user_id: str,
    analytic_type: AnalyticType,
    time_range_prefix: Optional[str] = None
) -> List[AnalyticsData]:
    """
    List analytics data for a user and analytic type, optionally filtered by time range.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        time_range_prefix: Optional time range prefix (e.g., '2024' for all of 2024)
        
    Returns:
        List of AnalyticsData objects
    """
    pk = f"{user_id}#{analytic_type.value}"
    
    if time_range_prefix:
        # Query with time range filter
        response = tables.analytics_data.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(time_range_prefix)
        )
    else:
        # Query all for this analytic type
        response = tables.analytics_data.query(
            KeyConditionExpression=Key('pk').eq(pk)
        )
    
    analytics_data = []
    for item in response.get('Items', []):
        analytics_data.append(AnalyticsData.from_dynamodb_item(item))
    
    return analytics_data


@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("batch_store_analytics_data")
def batch_store_analytics_data(analytics_list: List[AnalyticsData]) -> None:
    """
    Store multiple analytics data objects in batch.
    
    Args:
        analytics_list: List of AnalyticsData objects to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    # Convert to DynamoDB items and store using batch helper
    items = [analytics_data.to_dynamodb_item() for analytics_data in analytics_list]
    count = batch_write_items(
        table=tables.analytics_data,
        items=items
    )
    
    logger.info(f"Batch stored {count} analytics data objects")


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_analytics_data")
def delete_analytics_data(
    user_id: str,
    analytic_type: AnalyticType,
    time_period: str,
    account_id: Optional[str] = None
) -> bool:
    """
    Delete specific analytics data from DynamoDB.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        time_period: The time period
        account_id: Optional account ID
        
    Returns:
        True if deleted, False if not found
    """
    pk = f"{user_id}#{analytic_type.value}"
    account_part = account_id or 'ALL'
    sk = f"{time_period}#{account_part}"
    
    response = tables.analytics_data.delete_item(
        Key={'pk': pk, 'sk': sk},
        ReturnValues='ALL_OLD'
    )
    
    return 'Attributes' in response


# =============================================================================
# Analytics Processing Status Operations
# =============================================================================

@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("store_analytics_status")
def store_analytics_status(status: AnalyticsProcessingStatus) -> None:
    """
    Store analytics processing status in DynamoDB.
    
    Args:
        status: The AnalyticsProcessingStatus object to store
        
    Raises:
        ClientError: If there's a DynamoDB error
    """
    item = status.to_dynamodb_item()
    tables.analytics_status.put_item(Item=item)
    logger.info(f"Stored analytics status: {status.analytic_type.value} for user {status.user_id}")


@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_analytics_status")
def get_analytics_status(
    user_id: str,
    analytic_type: AnalyticType,
    account_id: Optional[str] = None
) -> Optional[AnalyticsProcessingStatus]:
    """
    Retrieve analytics processing status from DynamoDB.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        account_id: Optional account ID
        
    Returns:
        AnalyticsProcessingStatus object if found, None otherwise
    """
    account_part = account_id or 'ALL'
    sk = f"{analytic_type.value}#{account_part}"
    
    response = tables.analytics_status.get_item(
        Key={'pk': user_id, 'sk': sk}
    )
    
    if 'Item' in response:
        return AnalyticsProcessingStatus.from_dynamodb_item(response['Item'])
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_analytics_status_for_user")
def list_analytics_status_for_user(user_id: str) -> List[AnalyticsProcessingStatus]:
    """
    List all analytics processing status for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        List of AnalyticsProcessingStatus objects
    """
    response = tables.analytics_status.query(
        KeyConditionExpression=Key('pk').eq(user_id)
    )
    
    status_list = []
    for item in response.get('Items', []):
        status_list.append(AnalyticsProcessingStatus.from_dynamodb_item(item))
    
    return status_list


@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_analytics_status")
def update_analytics_status(
    user_id: str,
    analytic_type: AnalyticType,
    updates: Dict[str, Any],
    account_id: Optional[str] = None
) -> Optional[AnalyticsProcessingStatus]:
    """
    Update analytics processing status.
    
    Args:
        user_id: The user ID
        analytic_type: The type of analytics
        updates: Dictionary of updates to apply
        account_id: Optional account ID
        
    Returns:
        Updated AnalyticsProcessingStatus object if successful, None otherwise
    """
    account_part = account_id or 'ALL'
    sk = f"{analytic_type.value}#{account_part}"
    
    # Build update expression
    update_expression = "SET "
    expression_values = {}
    expression_names = {}
    
    for key, value in updates.items():
        if key in ['lastUpdated', 'lastComputedDate', 'dataAvailableThrough']:
            # Handle date/datetime fields
            if isinstance(value, (date, datetime)):
                expression_values[f':{key}'] = value.isoformat()
            else:
                expression_values[f':{key}'] = value
        elif key == 'status' and hasattr(value, 'value'):
            # Handle enum fields
            expression_values[f':{key}'] = value.value
        elif key == 'computationNeeded':
            # Handle Binary type for computationNeeded
            expression_values[f':{key}'] = Binary(b'\x01' if value else b'\x00')
        else:
            expression_values[f':{key}'] = value
        
        expression_names[f'#{key}'] = key
        update_expression += f"#{key} = :{key}, "
    
    # Remove trailing comma and space
    update_expression = update_expression.rstrip(', ')
    
    response = tables.analytics_status.update_item(
        Key={'pk': user_id, 'sk': sk},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ExpressionAttributeNames=expression_names,
        ReturnValues='ALL_NEW'
    )
    
    if 'Attributes' in response:
        return AnalyticsProcessingStatus.from_dynamodb_item(response['Attributes'])
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=1000)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_stale_analytics")
def list_stale_analytics(computation_needed_only: bool = True) -> List[AnalyticsProcessingStatus]:
    """
    List analytics that need recomputation (stale analytics).
    
    Args:
        computation_needed_only: If True, only return items where computation_needed=True
        
    Returns:
        List of AnalyticsProcessingStatus objects that need recomputation
    """
    if computation_needed_only:
        # Use the GSI to efficiently query for records that need computation
        binary_true = Binary(b'\x01')  # Binary type for true
        
        response = tables.analytics_status.query(
            IndexName='ComputationNeededIndex',
            KeyConditionExpression=Key('computationNeeded').eq(binary_true),
            # Order by lastUpdated to process oldest first
            ScanIndexForward=True
        )
    else:
        # If we need all records, fall back to scan
        response = tables.analytics_status.scan()
    
    status_list = []
    for item in response.get('Items', []):
        status_list.append(AnalyticsProcessingStatus.from_dynamodb_item(item))
    
    return status_list

