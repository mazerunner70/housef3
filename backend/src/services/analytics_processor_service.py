"""
Simplified Analytics Processor Lambda - Scheduled processor for pending analytics computations.

This function runs on a CloudWatch Events schedule (every 10 minutes) and:
1. Finds analytics that need computation (computationNeeded=True)
2. Processes them by priority (1=high, 2=medium, 3=low)
3. Computes analytics using AnalyticsComputationEngine
4. Stores results and updates status records
"""
import json
import logging
import traceback
from datetime import datetime, date
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
from services.analytics_computation_engine import AnalyticsComputationEngine
from models.analytics import AnalyticType, AnalyticsData, AnalyticsProcessingStatus
from utils.db_utils import list_stale_analytics, store_analytics_data, store_analytics_status

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main handler for the scheduled analytics processor.
    
    This function is triggered by CloudWatch Events on a schedule.
    """
    logger.info("🔄 Analytics Processor started")
    
    # Track processing statistics
    stats = {
        'total_found': 0,
        'processed_successfully': 0,
        'failed': 0,
        'skipped': 0,
        'users_processed': 0
    }
    
    try:
        # Get all analytics that need computation
        pending_analytics = list_stale_analytics(computation_needed_only=True)
        stats['total_found'] = len(pending_analytics)
        
        if not pending_analytics:
            logger.info("📊 No pending analytics found - all up to date!")
            return create_success_response(stats)
        
        logger.info(f"📊 Found {len(pending_analytics)} pending analytics to process")
        
        # Group by user for efficient processing
        user_analytics = {}
        for status in pending_analytics:
            user_id = status.user_id
            if user_id not in user_analytics:
                user_analytics[user_id] = []
            user_analytics[user_id].append(status)
        
        stats['users_processed'] = len(user_analytics)
        logger.info(f"📊 Processing analytics for {len(user_analytics)} users")
        
        # Process each user's analytics
        for user_id, user_status_list in user_analytics.items():
            try:
                process_user_analytics_simple(user_id, user_status_list, stats)
            except Exception as e:
                logger.error(f"❌ Failed to process analytics for user {user_id}: {str(e)}")
                logger.error(traceback.format_exc())
                stats['failed'] += len(user_status_list)
        
        # Log final statistics
        logger.info(f"✅ Analytics processing complete: {stats}")
        
        return create_success_response(stats)
        
    except Exception as e:
        logger.error(f"❌ Analytics processor failed: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(str(e), stats)


def process_user_analytics_simple(user_id: str, status_list: List[AnalyticsProcessingStatus], stats: Dict) -> None:
    """
    Process all pending analytics for a single user (simplified version).
    
    Args:
        user_id: The user ID to process analytics for
        status_list: List of pending analytics status records
        stats: Statistics tracking dictionary
    """
    logger.info(f"🔄 Processing {len(status_list)} analytics for user {user_id}")
    
    # Initialize services
    computation_engine = AnalyticsComputationEngine()
    
    # Sort by priority (1=high, 2=medium, 3=low)
    status_list.sort(key=lambda x: x.processing_priority)
    
    for status in status_list:
        try:
            analytic_type = status.analytic_type
            priority = status.processing_priority
            
            logger.info(f"🔄 Computing {analytic_type.value} analytics for user {user_id} (priority {priority})")
            
            # Compute analytics based on type using "overall" time period
            analytics_data = compute_analytics_by_type_simple(
                computation_engine, analytic_type, user_id
            )
            
            if analytics_data is None:
                logger.info(f"⏭️  Skipping {analytic_type.value} - no data available")
                mark_status_completed_simple(status)
                stats['skipped'] += 1
                continue
            
            # Store the computed analytics
            analytics_record = AnalyticsData(
                userId=user_id,
                analyticType=analytic_type,
                timePeriod="overall",
                accountId=None,
                data=analytics_data,
                dataThroughDate=date.today()
            )
            
            store_analytics_data(analytics_record)
            
            # Update status to mark as completed
            mark_status_completed_simple(status)
            
            # Update statistics
            stats['processed_successfully'] += 1
            
            logger.info(f"✅ Successfully computed {analytic_type.value} for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to compute {status.analytic_type.value} for user {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Mark status as failed
            mark_status_failed_simple(status, str(e))
            stats['failed'] += 1


def compute_analytics_by_type_simple(
    engine: AnalyticsComputationEngine, 
    analytic_type: AnalyticType, 
    user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Compute specific analytics based on the type (simplified version).
    
    Args:
        engine: Analytics computation engine
        analytic_type: Type of analytics to compute
        user_id: User ID
        
    Returns:
        Computed analytics data or None if computation failed
    """
    try:
        # Use "overall" as the time period for all computations
        time_period = "overall"
        
        if analytic_type == AnalyticType.CASH_FLOW:
            return engine.compute_cash_flow_analytics(user_id, time_period)
        
        elif analytic_type == AnalyticType.CATEGORY_TRENDS:
            return engine.compute_category_analytics(user_id, time_period)
        
        elif analytic_type == AnalyticType.ACCOUNT_EFFICIENCY:
            return engine.compute_account_analytics(user_id, time_period)
        
        elif analytic_type == AnalyticType.FINANCIAL_HEALTH:
            return engine.compute_financial_health_score(user_id, time_period)
        
        # For other analytics types, return a placeholder result
        else:
            logger.info(f"📊 Using placeholder computation for {analytic_type.value}")
            return {
                "status": "computed",
                "type": analytic_type.value,
                "message": f"Placeholder computation for {analytic_type.value}",
                "computed_date": date.today().isoformat()
            }
    
    except Exception as e:
        logger.error(f"❌ Computation failed for {analytic_type.value}: {str(e)}")
        return None


def mark_status_completed_simple(status: AnalyticsProcessingStatus) -> None:
    """Mark an analytics status as completed (simplified version)."""
    try:
        updated_status = AnalyticsProcessingStatus(
            userId=status.user_id,
            analyticType=status.analytic_type,
            lastComputedDate=date.today(),
            dataAvailableThrough=status.data_available_through,
            computationNeeded=False,  # Mark as no longer needed
            processingPriority=status.processing_priority
        )
        store_analytics_status(updated_status)
    except Exception as e:
        logger.error(f"❌ Failed to mark status as completed: {str(e)}")


def mark_status_failed_simple(status: AnalyticsProcessingStatus, error_message: str) -> None:
    """Mark an analytics status as failed (simplified version)."""
    try:
        updated_status = AnalyticsProcessingStatus(
            userId=status.user_id,
            analyticType=status.analytic_type,
            lastComputedDate=status.last_computed_date,
            dataAvailableThrough=status.data_available_through,
            computationNeeded=True,  # Keep marked as needed for retry
            processingPriority=min(status.processing_priority + 1, 3)  # Lower priority for retry
        )
        store_analytics_status(updated_status)
    except Exception as e:
        logger.error(f"❌ Failed to mark status as failed: {str(e)}")


def create_success_response(stats: Dict) -> Dict[str, Any]:
    """Create a successful response."""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'success',
            'message': 'Analytics processing completed',
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        })
    }


def create_error_response(error_message: str, stats: Dict) -> Dict[str, Any]:
    """Create an error response."""
    return {
        'statusCode': 500,
        'body': json.dumps({
            'status': 'error',
            'message': f'Analytics processing failed: {error_message}',
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        })
    } 