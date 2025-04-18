import json
import logging
from typing import Dict, Any

from models.transaction import Transaction
from utils.auth import get_user_from_event
from utils.db_utils import list_user_transactions, get_transactions_table
from utils.http import create_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_transactions_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Handle GET /transactions request."""
    try:
        transactions = list_user_transactions(user_id)
        return create_response(200, {"transactions": [t.to_dict() for t in transactions]})
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return create_response(500, {"message": "Internal server error"})

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
            return create_response(403, {"message": "Unauthorized"})
        
        # Delete the transaction
        get_transactions_table().delete_item(Key={'transactionId': transaction_id})
        return create_response(200, {"message": "Transaction deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting transaction: {str(e)}")
        return create_response(500, {"message": "Internal server error"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler for transaction operations."""
    try:
        # Get authenticated user
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        
        user_id = user["id"]
        route_key = event["routeKey"]
        
        # Route to appropriate handler
        if route_key == "GET /transactions":
            return get_transactions_handler(event, user_id)
        elif route_key == "DELETE /transactions/{id}":
            return delete_transaction_handler(event, user_id)
        else:
            return create_response(400, {"message": "Unsupported route"})
            
    except Exception as e:
        logger.error(f"Error in transaction operations handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"}) 