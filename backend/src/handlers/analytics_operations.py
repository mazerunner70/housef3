"""
Analytics Operations Handler

Provides API endpoints for analytics data:
- GET /analytics/{analytic_type} - Retrieve computed analytics by type
- POST /analytics/refresh - Trigger manual computation refresh  
- GET /analytics/status - Check analytics computation status
"""

import json
import logging
import traceback
import uuid
from datetime import datetime, date
from typing import Dict, Any, Optional
from decimal import Decimal

from models.analytics import AnalyticType, AnalyticsProcessingStatus
from utils.db_utils import (
    get_analytics_data, store_analytics_status,
    list_stale_analytics
)
from utils.auth import get_user_from_event
from utils.lambda_utils import mandatory_path_parameter, optional_query_parameter
from services.analytics_computation_engine import AnalyticsComputationEngine

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Custom JSON encoder to handle Decimal, UUID, and date values
class AnalyticsEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if hasattr(obj, 'model_dump'):  # Pydantic models
            return obj.model_dump(by_alias=True)
        return super(AnalyticsEncoder, self).default(obj)


def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create an API Gateway response object."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, cls=AnalyticsEncoder)
    }


def get_analytics_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    GET /analytics/{analytic_type} - Retrieve computed analytics by type.
    """
    try:
        # Get analytic type from path parameters
        analytic_type_str = mandatory_path_parameter(event, 'analytic_type')

        # Parse optional query parameters
        time_period = optional_query_parameter(event, 'time_period')
        if time_period is None:
            time_period = 'overall'
        
        account_id = optional_query_parameter(event, 'account_id')
        # account_id can remain None

        # Validate and convert analytic type
        try:
            analytic_type = AnalyticType(analytic_type_str.lower())
        except ValueError:
            return create_response(400, {
                "error": "Invalid analytic type",
                "message": f"'{analytic_type_str}' is not a valid analytic type",
                "valid_types": [t.value for t in AnalyticType]
            })

        logger.info(f"Retrieving {analytic_type.value} analytics for user {user_id}")

        # Try to get existing computed analytics
        analytics_data = get_analytics_data(
            user_id=user_id,
            analytic_type=analytic_type,
            time_period=time_period,
            account_id=account_id
        )

        if analytics_data:
            # Return existing computed analytics
            return create_response(200, {
                "status": "success",
                "analytic_type": analytic_type.value,
                "time_period": time_period,
                "account_id": account_id,
                "data": analytics_data.data,
                "computed_date": analytics_data.computed_date,
                "data_through_date": analytics_data.data_through_date,
                "cache_status": "hit"
            })
        else:
            # No computed analytics available - compute on demand
            try:
                computation_engine = AnalyticsComputationEngine()
                computed_data = compute_analytics_on_demand(
                    computation_engine, analytic_type, user_id, time_period
                )

                if computed_data is None:
                    return create_response(404, {
                        "error": "Analytics unavailable",
                        "message": f"Insufficient data to compute {analytic_type.value} analytics"
                    })

                return create_response(200, {
                    "status": "success",
                    "analytic_type": analytic_type.value,
                    "data": computed_data,
                    "cache_status": "computed_on_demand"
                })

            except Exception as compute_error:
                logger.error(f"Failed to compute analytics on demand: {str(compute_error)}")
                return create_response(500, {
                    "error": "Computation failed",
                    "message": f"Failed to compute {analytic_type.value} analytics"
                })

    except Exception as e:
        logger.error(f"Error retrieving analytics: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {
            "error": "Internal server error",
            "message": "Failed to retrieve analytics data"
        })


def refresh_analytics_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    POST /analytics/refresh - Trigger manual computation refresh.
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        analytic_types = body.get('analytic_types', [])
        force_refresh = body.get('force', False)

        logger.info(f"Manual analytics refresh requested for user {user_id}")

        # If no specific types requested, refresh all types
        if not analytic_types:
            analytic_types = [t.value for t in AnalyticType]

        # Validate analytic types
        valid_types = []
        invalid_types = []

        for type_str in analytic_types:
            try:
                analytic_type = AnalyticType(type_str.lower())
                valid_types.append(analytic_type)
            except ValueError:
                invalid_types.append(type_str)

        if invalid_types:
            return create_response(400, {
                "error": "Invalid analytic types",
                "invalid_types": invalid_types,
                "valid_types": [t.value for t in AnalyticType]
            })

        # Create processing status records to trigger computation
        refresh_results = []

        for analytic_type in valid_types:
            try:
                status_record = AnalyticsProcessingStatus(
                    userId=user_id,
                    analyticType=analytic_type,
                    lastComputedDate=None if force_refresh else date.today(),
                    dataAvailableThrough=date.today(),
                    computationNeeded=True,
                    processingPriority=1  # High priority for manual refresh
                )

                store_analytics_status(status_record)

                refresh_results.append({
                    "analytic_type": analytic_type.value,
                    "status": "queued",
                    "message": "Analytics refresh queued for processing"
                })

            except Exception as e:
                logger.error(f"Failed to queue {analytic_type.value} for refresh: {str(e)}")
                refresh_results.append({
                    "analytic_type": analytic_type.value,
                    "status": "error",
                    "message": f"Failed to queue for refresh: {str(e)}"
                })

        successful = len([r for r in refresh_results if r["status"] == "queued"])

        return create_response(200, {
            "status": "refresh_initiated",
            "message": f"Analytics refresh initiated for {successful} types",
            "results": refresh_results
        })

    except json.JSONDecodeError:
        return create_response(400, {
            "error": "Invalid JSON",
            "message": "Request body must be valid JSON"
        })
    except Exception as e:
        logger.error(f"Error refreshing analytics: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {
            "error": "Internal server error",
            "message": "Failed to initiate analytics refresh"
        })


def get_analytics_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    GET /analytics/status - Check analytics computation status.
    """
    try:
        logger.info(f"Checking analytics status for user {user_id}")

        # Get analytics status for the user
        try:
            status_records = list_stale_analytics(
                computation_needed_only=False
            )
        except Exception as e:
            logger.warning(f"Failed to get analytics status: {str(e)}")
            status_records = []

        # Format status information
        status_info = []
        for status in status_records:
            status_info.append({
                "analytic_type": status.analytic_type.value,
                "last_computed": status.last_computed_date.isoformat() if status.last_computed_date else None,
                "computation_needed": status.computation_needed,
                "processing_priority": status.processing_priority,
                "status": "pending" if status.computation_needed else "available"
            })

        # If no status records found, create default status
        if not status_info:
            for analytic_type in AnalyticType:
                status_info.append({
                    "analytic_type": analytic_type.value,
                    "last_computed": None,
                    "computation_needed": True,
                    "processing_priority": 2,
                    "status": "not_computed"
                })

        # Sort by analytic type for consistent ordering
        status_info.sort(key=lambda x: x["analytic_type"])

        # Calculate summary statistics
        total = len(status_info)
        pending = len([s for s in status_info if s["computation_needed"]])

        return create_response(200, {
            "status": "success",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_analytics": total,
                "pending_computation": pending,
                "up_to_date": total - pending
            },
            "analytics_status": status_info
        })

    except Exception as e:
        logger.error(f"Error getting analytics status: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {
            "error": "Internal server error",
            "message": "Failed to retrieve analytics status"
        })


def compute_analytics_on_demand(
    engine: AnalyticsComputationEngine,
    analytic_type: AnalyticType,
    user_id: str,
    time_period: str = "overall"
) -> Optional[Dict[str, Any]]:
    """Compute specific analytics on demand."""
    try:
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
            return {
                "status": "computed_on_demand",
                "type": analytic_type.value,
                "message": f"On-demand computation for {analytic_type.value}",
                "computed_date": date.today().isoformat(),
                "placeholder": True
            }

    except Exception as e:
        logger.error(f"On-demand computation failed for {analytic_type.value}: {str(e)}")
        return None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for analytics operations.
    """
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user['id']
        # Get route from event
        route = event.get('routeKey')
        if not route:
            return create_response(400, {"message": "Route not specified"})
        
        logger.info(f"Request: {route}")

        # Route to appropriate handler
        if route == "GET /analytics/status":
            return get_analytics_status_handler(event, user_id)
        elif route == "GET /analytics/{analytic_type}":
            return get_analytics_handler(event, user_id)
        elif route == "POST /analytics/refresh":
            return refresh_analytics_handler(event, user_id)

        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})

    except Exception as e:
        logger.error(f"Analytics operations handler error: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return create_response(500, {
            "error": "Internal server error",
            "message": "Analytics operations handler failed"
        })
