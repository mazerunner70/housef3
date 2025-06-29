import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from models.transaction import Transaction, TransactionCategoryAssignment, CategoryAssignmentStatus
from models.category import Category
from utils.auth import get_user_from_event
from utils.db_utils import list_user_transactions, get_transactions_table
from utils.lambda_utils import create_response, mandatory_path_parameter

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

        # Serialize transactions with string conversion for amount and balance
        serialized_transactions = []
        for t in transactions_list:
            transaction_data = t.model_dump(by_alias=True)
            if transaction_data.get("amount") is not None:
                transaction_data["amount"] = str(transaction_data["amount"])
            if transaction_data.get("balance") is not None:
                transaction_data["balance"] = str(transaction_data["balance"])
            serialized_transactions.append(transaction_data)

        response_data: Dict[str, Any] = {
            "transactions": serialized_transactions,
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
        
        transaction = Transaction.from_dynamodb_item(response['Item'])
        if transaction.user_id != user_id:
            return create_response(403, {"message": "Unauthorized to delete this transaction"})
        
        # Delete the transaction
        get_transactions_table().delete_item(Key={'transactionId': transaction_id})
        
        # Trigger analytics refresh for transaction deletion
        try:
            from utils.analytics_utils import trigger_analytics_for_transaction_change
            trigger_analytics_for_transaction_change(user_id, 'delete')
            logger.info(f"Analytics refresh triggered for transaction deletion: {transaction_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger analytics for transaction deletion: {str(e)}")
        
        return create_response(200, {"message": "Transaction deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting transaction {transaction_id if 'transaction_id' in locals() else 'UNKNOWN'} for user {user_id}: {str(e)}", exc_info=True)
        return create_response(500, {"message": "Internal server error deleting transaction."})

# --- Category Assignment Confirmation Handlers ---

def confirm_category_suggestions_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Confirm category suggestions for a transaction
    POST /transactions/{transactionId}/confirm-suggestions
    Body: { "confirmedCategoryIds": ["uuid1", "uuid2"], "primaryCategoryId": "uuid1" }
    """
    try:
        transaction_id = mandatory_path_parameter(event, 'transactionId')
        
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
            confirmed_category_ids = body_data.get('confirmedCategoryIds', [])
            primary_category_id = body_data.get('primaryCategoryId')
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        if not confirmed_category_ids:
            return create_response(400, {"error": "At least one category must be confirmed"})
        
        # Get transaction from database
        response = get_transactions_table().get_item(Key={'transactionId': transaction_id})
        if 'Item' not in response:
            return create_response(404, {"error": "Transaction not found"})
        
        transaction = Transaction.from_dynamodb_item(response['Item'])
        if transaction.user_id != user_id:
            return create_response(403, {"error": "Unauthorized to modify this transaction"})
        
        # Confirm the specified category suggestions
        confirmed_count = 0
        for category_id_str in confirmed_category_ids:
            category_uuid = uuid.UUID(category_id_str)
            if transaction.confirm_category_assignment(category_uuid):
                confirmed_count += 1
        
        # Set primary category if specified
        if primary_category_id:
            primary_uuid = uuid.UUID(primary_category_id)
            if primary_uuid in [uuid.UUID(cid) for cid in confirmed_category_ids]:
                transaction.set_primary_category(primary_uuid)
            else:
                return create_response(400, {"error": "Primary category must be one of the confirmed categories"})
        
        # Update transaction in database
        transaction_item = transaction.to_dynamodb_item()
        get_transactions_table().put_item(Item=transaction_item)
        
        return create_response(200, {
            "transactionId": transaction_id,
            "confirmedCount": confirmed_count,
            "primaryCategoryId": str(transaction.primary_category_id) if transaction.primary_category_id else None,
            "totalCategories": len(transaction.confirmed_categories)
        })
        
    except ValueError as ve:
        logger.warning(f"Invalid transaction ID or category ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error confirming category suggestions: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def remove_category_assignment_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Remove a category assignment from a transaction
    DELETE /transactions/{transactionId}/categories/{categoryId}
    """
    try:
        transaction_id = mandatory_path_parameter(event, 'transactionId')
        category_id = mandatory_path_parameter(event, 'categoryId')
        
        # Get transaction from database
        response = get_transactions_table().get_item(Key={'transactionId': transaction_id})
        if 'Item' not in response:
            return create_response(404, {"error": "Transaction not found"})
        
        transaction = Transaction.from_dynamodb_item(response['Item'])
        if transaction.user_id != user_id:
            return create_response(403, {"error": "Unauthorized to modify this transaction"})
        
        # Remove the category assignment
        category_uuid = uuid.UUID(category_id)
        removed = transaction.remove_category_assignment(category_uuid)
        
        if not removed:
            return create_response(404, {"error": "Category assignment not found"})
        
        # Update transaction in database
        transaction_item = transaction.to_dynamodb_item()
        get_transactions_table().put_item(Item=transaction_item)
        
        return create_response(200, {
            "transactionId": transaction_id,
            "categoryId": category_id,
            "removed": True,
            "remainingCategories": len(transaction.confirmed_categories)
        })
        
    except ValueError as ve:
        logger.warning(f"Invalid transaction ID or category ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error removing category assignment: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def set_primary_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Set the primary category for a transaction
    PUT /transactions/{transactionId}/primary-category
    Body: { "categoryId": "uuid" }
    """
    try:
        transaction_id = mandatory_path_parameter(event, 'transactionId')
        
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
            category_id = body_data.get('categoryId')
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        if not category_id:
            return create_response(400, {"error": "Category ID is required"})
        
        # Get transaction from database
        response = get_transactions_table().get_item(Key={'transactionId': transaction_id})
        if 'Item' not in response:
            return create_response(404, {"error": "Transaction not found"})
        
        transaction = Transaction.from_dynamodb_item(response['Item'])
        if transaction.user_id != user_id:
            return create_response(403, {"error": "Unauthorized to modify this transaction"})
        
        # Set primary category
        category_uuid = uuid.UUID(category_id)
        success = transaction.set_primary_category(category_uuid)
        
        if not success:
            return create_response(400, {"error": "Category must be assigned to transaction before setting as primary"})
        
        # Update transaction in database
        transaction_item = transaction.to_dynamodb_item()
        get_transactions_table().put_item(Item=transaction_item)
        
        return create_response(200, {
            "transactionId": transaction_id,
            "primaryCategoryId": category_id,
            "success": True
        })
        
    except ValueError as ve:
        logger.warning(f"Invalid transaction ID or category ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error setting primary category: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def add_manual_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Add a manual category assignment to a transaction
    POST /transactions/{transactionId}/categories
    Body: { "categoryId": "uuid", "isPrimary": false }
    """
    try:
        transaction_id = mandatory_path_parameter(event, 'transactionId')
        
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
            category_id = body_data.get('categoryId')
            is_primary = body_data.get('isPrimary', False)
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        if not category_id:
            return create_response(400, {"error": "Category ID is required"})
        
        # Get transaction from database
        response = get_transactions_table().get_item(Key={'transactionId': transaction_id})
        if 'Item' not in response:
            return create_response(404, {"error": "Transaction not found"})
        
        transaction = Transaction.from_dynamodb_item(response['Item'])
        if transaction.user_id != user_id:
            return create_response(403, {"error": "Unauthorized to modify this transaction"})
        
        # Add manual category
        category_uuid = uuid.UUID(category_id)
        transaction.add_manual_category(category_uuid, set_as_primary=is_primary)
        
        # Update transaction in database
        transaction_item = transaction.to_dynamodb_item()
        get_transactions_table().put_item(Item=transaction_item)
        
        return create_response(201, {
            "transactionId": transaction_id,
            "categoryId": category_id,
            "isPrimary": is_primary,
            "totalCategories": len(transaction.confirmed_categories)
        })
        
    except ValueError as ve:
        logger.warning(f"Invalid transaction ID or category ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error adding manual category: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

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
    elif route == "POST /transactions/{transactionId}/confirm-suggestions":
        return confirm_category_suggestions_handler(event, user_id)
    elif route == "DELETE /transactions/{transactionId}/categories/{categoryId}":
        return remove_category_assignment_handler(event, user_id)
    elif route == "PUT /transactions/{transactionId}/primary-category":
        return set_primary_category_handler(event, user_id)
    elif route == "POST /transactions/{transactionId}/categories":
        return add_manual_category_handler(event, user_id)
    
    logger.warning(f"Unsupported route: {route}")
    return create_response(400, {"message": f"Unsupported route: {route}"})
            