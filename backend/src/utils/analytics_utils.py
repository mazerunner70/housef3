"""
Utility functions for analytics operations and triggering.
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def trigger_analytics_refresh(user_id: str, priority: int = 3, 
                            analytic_types: Optional[List[str]] = None) -> bool:
    """
    Trigger analytics refresh for a user by marking analytics as needing recomputation.
    
    Args:
        user_id: The user ID to trigger analytics for
        priority: Processing priority (1=high, 2=medium, 3=low)
        analytic_types: Specific analytics to refresh (defaults to all)
        
    Returns:
        bool: True if successful, False if failed
    """
    try:
        from models.analytics import AnalyticType, AnalyticsProcessingStatus
        from utils.db_utils import store_analytics_status
        
        # Determine which analytics to refresh
        if analytic_types:
            types_to_refresh = []
            for type_str in analytic_types:
                try:
                    types_to_refresh.append(AnalyticType(type_str))
                except ValueError:
                    logger.warning(f"Invalid analytic type: {type_str}")
        else:
            types_to_refresh = list(AnalyticType)
        
        logger.info(f"Triggering analytics refresh for user {user_id}, "
                   f"priority {priority}, types: {[t.value for t in types_to_refresh]}")
        
        # Create status records for each analytics type
        success_count = 0
        for analytic_type in types_to_refresh:
            try:
                status_record = AnalyticsProcessingStatus(
                    userId=user_id,
                    analyticType=analytic_type,
                    lastComputedDate=None,
                    dataAvailableThrough=None,
                    computationNeeded=True,
                    processingPriority=priority
                )
                store_analytics_status(status_record)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to create status for {analytic_type.value}: {str(e)}")
        
        logger.info(f"Successfully triggered analytics refresh for {success_count}/{len(types_to_refresh)} analytics types")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Failed to trigger analytics refresh for user {user_id}: {str(e)}")
        return False


def trigger_analytics_for_account_change(user_id: str, change_type: str) -> bool:
    """
    Trigger analytics refresh for account-related changes.
    
    Args:
        user_id: The user ID
        change_type: Type of change (create, update, delete, associate, unassociate)
        
    Returns:
        bool: True if successful
    """
    # Different priorities based on change type
    priority_map = {
        'associate': 1,    # High priority - changes transaction-account relationships
        'unassociate': 1,  # High priority - changes transaction-account relationships
        'delete': 2,       # Medium priority - removes account data
        'create': 3,       # Low priority - new account with no transactions yet
        'update': 3        # Low priority - metadata changes
    }
    
    priority = priority_map.get(change_type, 3)
    
    # For association changes, focus on account-specific analytics
    if change_type in ['associate', 'unassociate']:
        account_focused_analytics = [
            'account_efficiency',
            'cash_flow', 
            'category_trends',
            'financial_health'
        ]
        return trigger_analytics_refresh(user_id, priority, account_focused_analytics)
    else:
        # For other account changes, refresh all analytics
        return trigger_analytics_refresh(user_id, priority)


def trigger_analytics_for_transaction_change(user_id: str, change_type: str) -> bool:
    """
    Trigger analytics refresh for transaction-related changes.
    
    Args:
        user_id: The user ID
        change_type: Type of change (edit, delete, bulk_delete)
        
    Returns:
        bool: True if successful
    """
    # Transaction changes always have medium priority
    priority = 2
    
    logger.info(f"Triggering analytics refresh for transaction {change_type} for user {user_id}")
    return trigger_analytics_refresh(user_id, priority) 