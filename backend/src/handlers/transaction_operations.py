import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from models.transaction import Transaction
from utils.auth import get_user_from_event
from utils.db_utils import list_user_transactions, get_transactions_table
from backend.src.utils.lambda_utils import create_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_transactions_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle GET /transactions request with filtering, sorting by date, and pagination."""
    try:
        query_params = event.get("queryStringParameters") or {}
        
        # Pagination parameters
        page_size = int(query_params.get("pageSize", 50))
        # The 'page' parameter from frontend is for UI state; DynamoDB uses lastEvaluatedKey
        current_page_for_response = int(query_params.get("page", 1)) 
        last_evaluated_key_str = query_params.get("lastEvaluatedKey")
        last_evaluated_key = json.loads(last_evaluated_key_str) if last_evaluated_key_str else None

        # Date filter parameters - now expecting millisecond timestamps
        start_date_ts_str = query_params.get("startDate")
        end_date_ts_str = query_params.get("endDate")
        
        start_date_ts: Optional[int] = None
        if start_date_ts_str:
            start_date_ts = int(start_date_ts_str)
            
        end_date_ts: Optional[int] = None
        if end_date_ts_str:
            end_date_ts = int(end_date_ts_str)
            # If frontend sends end_date as start of the day, adjust to end of day if necessary.
            # For now, assuming frontend sends precise boundary or it's handled by how it's used in list_user_transactions.

        # Filter parameters
        account_ids_str = query_params.get("accountIds")
        category_ids_str = query_params.get("categoryIds")
        # Default to 'all' if not provided or empty
        transaction_type = query_params.get("transactionType") if query_params.get("transactionType") else "all"
        search_term = query_params.get("searchTerm")

        account_ids = account_ids_str.split(',') if account_ids_str else []
        category_ids = category_ids_str.split(',') if category_ids_str else []

        # Sorting parameters (simplified: sortBy is implicitly 'date')
        # Frontend might send sortBy=date, but we only care about sortOrder here for date sorting.
        sort_order = query_params.get("sortOrder", "desc").lower()
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc' # Default to descending if invalid value

        # Log extracted parameters for now
        logger.info(f"User {user_id} requested transactions with params:")
        logger.info(f"  PageSize: {page_size}, LastEvaluatedKey: {last_evaluated_key}, CurrentPageForUI: {current_page_for_response}")
        logger.info(f"  Filters: StartDateTS={start_date_ts}, EndDateTS={end_date_ts}, Accounts={account_ids}, Categories={category_ids}, Type={transaction_type}, Search='{search_term}'")
        logger.info(f"  SortOrder (for date): {sort_order}")

        # Updated call to the modified list_user_transactions
        transactions_list, new_last_evaluated_key, total_items = list_user_transactions(
            user_id=user_id, 
            limit=page_size, 
            last_evaluated_key=last_evaluated_key,
            start_date_ts=start_date_ts,      # Pass integer timestamp
            end_date_ts=end_date_ts,        # Pass integer timestamp
            account_ids=account_ids,
            # category_ids=category_ids, # Pass if/when implemented in list_user_transactions
            transaction_type=transaction_type,
            search_term=search_term,
            sort_order_date=sort_order
        )
        
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
        if total_items == 0 and transactions_list: # If total_items is a placeholder but we got items
            pass # Keep total_pages as 0 or make an estimate if desired

        response_data: Dict[str, Any] = {
            "transactions": [t.to_dict() for t in transactions_list],
            "pagination": {
                "currentPage": current_page_for_response,
                "pageSize": page_size,
                "totalItems": total_items, 
                "totalPages": total_pages,
            }
        }
        if new_last_evaluated_key:
            response_data["pagination"]["lastEvaluatedKey"] = new_last_evaluated_key
            
        return create_response(200, response_data)

    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in lastEvaluatedKey: {query_params.get('lastEvaluatedKey')}")
        return create_response(400, {"message": "Invalid format for lastEvaluatedKey."})
    except ValueError as ve: # Catches int conversion errors for pageSize/page
        logger.warning(f"Invalid parameter value: {str(ve)}")
        return create_response(400, {"message": f"Invalid parameter value: {str(ve)}"})
    except Exception as e:
        logger.error(f"Error getting transactions for user {user_id}: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Internal server error retrieving transactions."})

def delete_transaction_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle DELETE /transactions/{id} request."""
    try:
        transaction_id = event["pathParameters"]["id"]
        
        # Get transaction to verify ownership
        response = get_transactions_table().get_item(Key={'transactionId': transaction_id})
        if 'Item' not in response:
            return create_response(404, {"message": "Transaction not found"})
        
        transaction = Transaction.from_dict(response['Item'])
        if transaction.user_id != user_id:
            return create_response(403, {"message": "Unauthorized to delete this transaction"})
        
        # Delete the transaction
        get_transactions_table().delete_item(Key={'transactionId': transaction_id})
        return create_response(200, {"message": "Transaction deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting transaction {transaction_id if 'transaction_id' in locals() else 'UNKNOWN'} for user {user_id}: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Internal server error deleting transaction."})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler for transaction operations."""
    try:
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        
        user_id = user["id"]
        # Method and path for routing
        http_method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
        path = event.get("requestContext", {}).get("http", {}).get("path", "") # e.g. /api/transactions or /api/transactions/some-id

        logger.info(f"Transaction handler invoked: Method={http_method}, Path={path}, UserID={user_id}")

        # Simplified routing based on method and path pattern
        if http_method == "GET" and path == "/api/transactions": # Assuming API Gateway route is /api/transactions
            return get_transactions_handler(event, user_id)
        elif http_method == "DELETE" and path.startswith("/api/transactions/"):
             # Ensure pathParameters and id exist, or handle error
            if "pathParameters" not in event or "id" not in event["pathParameters"]:
                logger.warning(f"Missing transaction ID in DELETE request path: {path}")
                return create_response(400, {"message": "Transaction ID missing in path."})
            return delete_transaction_handler(event, user_id)
        else:
            logger.warning(f"Unsupported route: Method={http_method}, Path={path}")
            return create_response(400, {"message": f"Unsupported route: {http_method} {path}"})
            
    except Exception as e:
        logger.error(f"Error in transaction operations main handler: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Internal server error in handler."}) 