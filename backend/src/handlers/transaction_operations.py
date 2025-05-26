import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from models.transaction import Transaction
from utils.auth import get_user_from_event
from utils.db_utils import list_user_transactions, get_transactions_table
from utils.lambda_utils import create_response

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
        ignore_dup_str = query_params.get("ignoreDup", "false") # Get ignoreDup, default to "false"
        ignore_dup = ignore_dup_str.lower() == "true" # Convert to boolean

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
        logger.info(f"  Filters: StartDateTS={start_date_ts}, EndDateTS={end_date_ts}, Accounts={account_ids}, Categories={category_ids}, Type={transaction_type}, Search='{search_term}', IgnoreDup={ignore_dup}")
        logger.info(f"  SortOrder (for date): {sort_order}")

        transactions_list, new_last_evaluated_key, items_on_this_page = list_user_transactions(
            user_id=user_id, 
            limit=page_size, 
            last_evaluated_key=last_evaluated_key,
            start_date_ts=start_date_ts,      
            end_date_ts=end_date_ts,        
            account_ids=account_ids,
            transaction_type=transaction_type,
            search_term=search_term,
            sort_order_date=sort_order,
            ignore_dup=ignore_dup
        )
        
        total_items_for_response = items_on_this_page

        if items_on_this_page == 0:
            if current_page_for_response == 1 and not new_last_evaluated_key:
                # No items on the first page, and no indication of more pages.
                total_pages_for_response = 0
            else:
                # No items on current page, but it's either not the first page
                # or there might be more pages (new_last_evaluated_key is present).
                # In this case, total_pages is effectively the current page,
                # or current_page + 1 if LEK suggests more data coming.
                total_pages_for_response = current_page_for_response + 1 if new_last_evaluated_key else current_page_for_response
        else: # items_on_this_page > 0
            if new_last_evaluated_key:
                # Items on this page, and there's a key for the next page.
                total_pages_for_response = current_page_for_response + 1
            else:
                # Items on this page, but no key for the next page (this is the last page).
                total_pages_for_response = current_page_for_response

        response_data: Dict[str, Any] = {
            "transactions": [t.model_dump(by_alias=True) for t in transactions_list],
            "pagination": {
                "currentPage": current_page_for_response,
                "pageSize": page_size,
                "totalItems": total_items_for_response, # Number of items on the current page
                "totalPages": total_pages_for_response,
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
        
        transaction = Transaction.from_flat_dict(response['Item'])
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
    # Get route from event
    route = event.get('routeKey')
    if not route:
        return create_response(400, {"message": "Missing route key"})
        
    # Get user from event
    user = get_user_from_event(event)
    if not user:
        return create_response(401, {"message": "Unauthorized"})
    user_id = user.get('id')
    if not user_id:
        return create_response(401, {"message": "Unauthorized"})
        
    logger.info(f"Processing {route} request for user {user_id}")

    if route == "GET /transactions":
        return get_transactions_handler(event, user_id)
    elif route == "DELETE /transactions/{id}":
            # Ensure pathParameters and id exist, or handle error
        if "pathParameters" not in event or "id" not in event["pathParameters"]:
            logger.warning(f"Missing transaction ID in DELETE request path: {event.get('path')}")
            return create_response(400, {"message": "Transaction ID missing in path."})
        return delete_transaction_handler(event, user_id)
    logger.warning(f"Unsupported route: {route}")
    return create_response(400, {"message": f"Unsupported route: {route}"})
            