"""
Handler for transfer-related operations.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
import uuid

from services.transfer_detection_service import TransferDetectionService
from utils.db_utils import get_transactions_table
from models.transaction import Transaction
from utils.lambda_utils import (
    create_response,
    optional_query_parameter,
    mandatory_body_parameter
)
from utils.handler_decorators import api_handler, standard_error_handling
from utils.auth import get_user_from_event

logger = logging.getLogger(__name__)


def get_transaction_by_id(transaction_id: uuid.UUID) -> Optional[Transaction]:
    """Get a transaction by its ID."""
    try:
        table = get_transactions_table()
        if not table:
            return None
        
        response = table.get_item(Key={'transactionId': str(transaction_id)})
        item = response.get('Item')
        
        if not item:
            return None
        
        return Transaction.from_dynamodb_item(item)
    except Exception as e:
        logger.error(f"Error getting transaction {transaction_id}: {str(e)}")
        return None


@api_handler()
def detect_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Detect potential transfer transactions for a user."""
    logger.info(f"Starting transfer detection for user {user_id}")
    
    # Get date range parameters - startDate and endDate are required
    start_date_param = optional_query_parameter(event, "startDate")
    end_date_param = optional_query_parameter(event, "endDate")
    
    # Parse date range
    if start_date_param and end_date_param:
        # Parse specific start and end dates as milliseconds since epoch
        try:
            from datetime import datetime
            start_date_ts = int(start_date_param)
            end_date_ts = int(end_date_param)
            
            # Convert to datetime objects for logging
            start_date = datetime.fromtimestamp(start_date_ts / 1000)
            end_date = datetime.fromtimestamp(end_date_ts / 1000)
            
            logger.info(f"Using date range: {start_date.isoformat()} to {end_date.isoformat()}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid date format: {e}")
            raise ValueError("Invalid date format. Expected milliseconds since epoch")
    else:
        # Default: last 7 days if no dates provided
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_date_ts = int(start_date.timestamp() * 1000)
        end_date_ts = int(end_date.timestamp() * 1000)
        
        logger.info(f"Using default date range: 7 days ({start_date.isoformat()} to {end_date.isoformat()})")
    
    # Initialize transfer detection service
    transfer_service = TransferDetectionService()
    
    # Detect transfers using date range
    transfer_pairs = transfer_service.detect_transfers_for_user_in_range(user_id, start_date_ts, end_date_ts)
    
    # Convert to response format
    response_data = []
    for outgoing_tx, incoming_tx in transfer_pairs:
        response_data.append({
            "outgoingTransaction": outgoing_tx.model_dump(by_alias=True, mode="json"),
            "incomingTransaction": incoming_tx.model_dump(by_alias=True, mode="json"),
            "amount": abs(outgoing_tx.amount),
            "dateDifference": abs(outgoing_tx.date - incoming_tx.date) // (1000 * 60 * 60 * 24)  # Days
        })
    
    logger.info(f"Found {len(response_data)} potential transfer pairs")
    
    return {
        "transfers": response_data,
        "count": len(response_data),
        "dateRange": {
            "startDate": start_date_ts,
            "endDate": end_date_ts
        }
    }


@api_handler()
def mark_transfer_pair_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Mark two transactions as a transfer pair."""
    # Extract required parameters from request body
    outgoing_tx_id = mandatory_body_parameter(event, "outgoingTransactionId")
    incoming_tx_id = mandatory_body_parameter(event, "incomingTransactionId")
    
    # Get transactions
    outgoing_tx = get_transaction_by_id(uuid.UUID(outgoing_tx_id))
    incoming_tx = get_transaction_by_id(uuid.UUID(incoming_tx_id))
    
    if not outgoing_tx or not incoming_tx:
        from utils.auth import NotFound
        raise NotFound("One or both transactions not found")
    
    # Verify transactions belong to user
    if outgoing_tx.user_id != user_id or incoming_tx.user_id != user_id:
        from utils.auth import NotAuthorized
        raise NotAuthorized("Unauthorized access to transactions")
    
    # Initialize transfer detection service
    transfer_service = TransferDetectionService()
    
    # Mark as transfer pair
    success = transfer_service.mark_as_transfer_pair(outgoing_tx, incoming_tx, user_id)
    
    if not success:
        raise RuntimeError("Failed to mark transfer pair")
    
    return {"message": "Transfer pair marked successfully"}



@api_handler()
def get_paired_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get existing paired transfer transactions for a user."""
    logger.info(f"Getting paired transfers for user {user_id}")
    
    # Get date range parameters - both are optional (if not provided, returns all)
    start_date_param = optional_query_parameter(event, "startDate")
    end_date_param = optional_query_parameter(event, "endDate")
    
    # Parse date range
    start_date_ts = None
    end_date_ts = None
    
    if start_date_param and end_date_param:
        # Parse specific start and end dates as milliseconds since epoch
        try:
            from datetime import datetime
            start_date_ts = int(start_date_param)
            end_date_ts = int(end_date_param)
            
            # Convert to datetime objects for logging
            start_date = datetime.fromtimestamp(start_date_ts / 1000)
            end_date = datetime.fromtimestamp(end_date_ts / 1000)
            
            logger.info(f"Filtering paired transfers from {start_date.isoformat()} to {end_date.isoformat()}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid date format: {e}")
            raise ValueError("Invalid date format. Expected milliseconds since epoch")
    
    # Initialize transfer detection service
    transfer_service = TransferDetectionService()
    
    # Get transfer category IDs for this user
    transfer_category_ids = list(transfer_service._get_transfer_category_ids(user_id))
    
    if not transfer_category_ids:
        # No transfer categories exist, return empty result
        logger.info(f"No transfer categories found for user {user_id}")
        return {
            "pairedTransfers": [],
            "count": 0,
            "dateRange": {
                "startDate": start_date_ts,
                "endDate": end_date_ts
            } if start_date_ts and end_date_ts else None
        }
    
    # Get transfer transactions with optional date range filtering
    from utils.db_utils import list_user_transactions
    
    if start_date_ts and end_date_ts:
        # Get transfer transactions within date range with pagination
        transfer_transactions = []
        last_evaluated_key = None
        
        while True:
            batch_result, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                category_ids=transfer_category_ids,
                start_date_ts=start_date_ts,
                end_date_ts=end_date_ts,
                last_evaluated_key=last_evaluated_key,
                limit=500
            )
            
            transfer_transactions.extend(batch_result)
            
            if not last_evaluated_key:
                break
    else:
        # No date range specified, get all transfer transactions with pagination
        transfer_transactions = []
        last_evaluated_key = None
        
        while True:
            batch_result, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                category_ids=transfer_category_ids,
                last_evaluated_key=last_evaluated_key,
                limit=500
            )
            
            transfer_transactions.extend(batch_result)
            
            if not last_evaluated_key:
                break
    
    # Group transfer transactions by account and find pairs
    paired_transfers = []
    processed_transaction_ids = set()
    
    for tx in transfer_transactions:
        if str(tx.transaction_id) in processed_transaction_ids:
            continue
            
        # Look for matching transfer transaction
        for other_tx in transfer_transactions:
            if (str(other_tx.transaction_id) != str(tx.transaction_id) and
                str(other_tx.transaction_id) not in processed_transaction_ids and
                tx.account_id != other_tx.account_id and
                transfer_service._transactions_could_be_transfer_pair(tx, other_tx)):
                
                # Determine which is outgoing (negative) and incoming (positive)
                if tx.amount < 0 and other_tx.amount > 0:
                    outgoing_tx, incoming_tx = tx, other_tx
                elif tx.amount > 0 and other_tx.amount < 0:
                    outgoing_tx, incoming_tx = other_tx, tx
                else:
                    continue  # Skip if both same sign
                
                paired_transfers.append({
                    "outgoingTransaction": outgoing_tx.model_dump(by_alias=True, mode="json"),
                    "incomingTransaction": incoming_tx.model_dump(by_alias=True, mode="json"),
                    "amount": abs(outgoing_tx.amount),
                    "dateDifference": abs(outgoing_tx.date - incoming_tx.date) // (1000 * 60 * 60 * 24)  # Days
                })
                
                # Mark both as processed
                processed_transaction_ids.add(str(tx.transaction_id))
                processed_transaction_ids.add(str(other_tx.transaction_id))
                break
    
    logger.info(f"Found {len(paired_transfers)} existing transfer pairs")
    
    return {
        "pairedTransfers": paired_transfers,
        "count": len(paired_transfers),
        "dateRange": {
            "startDate": start_date_ts,
            "endDate": end_date_ts
        } if start_date_ts and end_date_ts else None
    }


@api_handler()
def bulk_mark_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Mark multiple detected transfer pairs as transfers."""
    # Parse request body
    body = json.loads(event.get("body", "{}"))
    transfer_pairs = body.get("transferPairs", [])
    
    if not transfer_pairs:
        raise ValueError("No transfer pairs provided")
    
    # Initialize transfer detection service
    transfer_service = TransferDetectionService()
    
    successful_pairs = []
    failed_pairs = []
    
    for pair in transfer_pairs:
        try:
            outgoing_tx_id = pair.get("outgoingTransactionId")
            incoming_tx_id = pair.get("incomingTransactionId")
            
            if not outgoing_tx_id or not incoming_tx_id:
                failed_pairs.append({
                    "pair": pair,
                    "error": "Missing transaction IDs"
                })
                continue
            
            # Get transactions
            outgoing_tx = get_transaction_by_id(uuid.UUID(outgoing_tx_id))
            incoming_tx = get_transaction_by_id(uuid.UUID(incoming_tx_id))
            
            if not outgoing_tx or not incoming_tx:
                failed_pairs.append({
                    "pair": pair,
                    "error": "One or both transactions not found"
                })
                continue
            
            # Verify transactions belong to user
            if outgoing_tx.user_id != user_id or incoming_tx.user_id != user_id:
                failed_pairs.append({
                    "pair": pair,
                    "error": "Unauthorized access to transactions"
                })
                continue
            
            # Mark as transfer pair
            success = transfer_service.mark_as_transfer_pair(outgoing_tx, incoming_tx, user_id)
            
            if success:
                successful_pairs.append({
                    "outgoingTransactionId": outgoing_tx_id,
                    "incomingTransactionId": incoming_tx_id
                })
            else:
                failed_pairs.append({
                    "pair": pair,
                    "error": "Failed to mark as transfer pair"
                })
                
        except Exception as e:
            logger.error(f"Error processing transfer pair: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            failed_pairs.append({
                "pair": pair,
                "error": str(e)
            })
    
    return {
        "successful": successful_pairs,
        "failed": failed_pairs,
        "successCount": len(successful_pairs),
        "failureCount": len(failed_pairs)
    }


@standard_error_handling
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler for transfer operations."""
    # Get user from Cognito
    user = get_user_from_event(event)
    if not user:
        from utils.auth import NotAuthorized
        raise NotAuthorized("Unauthorized")
    user_id = user["id"]
    
    # Get route from event
    route = event.get("routeKey")
    if not route:
        raise ValueError("Route not specified")
    
    logger.info(f"Transfer operation request: {route}")
    
    # Route to appropriate handler
    if route == "GET /transfers/detect":
        return detect_transfers_handler(event, user_id)
    elif route == "GET /transfers/paired":
        return get_paired_transfers_handler(event, user_id)
    elif route == "POST /transfers/mark-pair":
        return mark_transfer_pair_handler(event, user_id)
    elif route == "POST /transfers/bulk-mark":
        return bulk_mark_transfers_handler(event, user_id)
    else:
        raise ValueError(f"Unsupported route: {route}")
