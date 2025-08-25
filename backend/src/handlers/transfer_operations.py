"""
Handler for transfer-related operations.
"""

import json
import logging
from typing import Dict, Any, Optional
import uuid

from utils.lambda_utils import create_response
from utils.auth import get_user_from_event
from services.transfer_detection_service import TransferDetectionService
from utils.db_utils import get_transactions_table
from models.transaction import Transaction

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


def detect_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Detect potential transfer transactions for a user."""
    try:
        logger.info(f"Starting transfer detection for user {user_id}")
        
        # Get optional date range parameter
        query_params = event.get("queryStringParameters", {}) or {}
        date_range_days = int(query_params.get("dateRange", 7))
        
        # Initialize transfer detection service
        transfer_service = TransferDetectionService()
        
        # Detect transfers
        transfer_pairs = transfer_service.detect_transfers_for_user(user_id, date_range_days)
        
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
        
        return create_response(200, {
            "transfers": response_data,
            "count": len(response_data)
        })
        
    except Exception as e:
        logger.error(f"Error detecting transfers: {str(e)}")
        return create_response(500, {"message": "Error detecting transfers"})


def mark_transfer_pair_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Mark two transactions as a transfer pair."""
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        
        outgoing_tx_id = body.get("outgoingTransactionId")
        incoming_tx_id = body.get("incomingTransactionId")
        
        if not outgoing_tx_id or not incoming_tx_id:
            return create_response(400, {"message": "Both transaction IDs are required"})
        
        # Get transactions
        outgoing_tx = get_transaction_by_id(uuid.UUID(outgoing_tx_id))
        incoming_tx = get_transaction_by_id(uuid.UUID(incoming_tx_id))
        
        if not outgoing_tx or not incoming_tx:
            return create_response(404, {"message": "One or both transactions not found"})
        
        # Verify transactions belong to user
        if outgoing_tx.user_id != user_id or incoming_tx.user_id != user_id:
            return create_response(403, {"message": "Unauthorized access to transactions"})
        
        # Initialize transfer detection service
        transfer_service = TransferDetectionService()
        
        # Mark as transfer pair
        success = transfer_service.mark_as_transfer_pair(outgoing_tx, incoming_tx, user_id)
        
        if success:
            return create_response(200, {"message": "Transfer pair marked successfully"})
        else:
            return create_response(500, {"message": "Error marking transfer pair"})
        
    except json.JSONDecodeError:
        return create_response(400, {"message": "Invalid JSON in request body"})
    except Exception as e:
        logger.error(f"Error marking transfer pair: {str(e)}")
        return create_response(500, {"message": "Error marking transfer pair"})



def get_paired_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get existing paired transfer transactions for a user."""
    try:
        logger.info(f"Getting paired transfers for user {user_id}")
        
        # Get optional date range parameter
        query_params = event.get("queryStringParameters", {}) or {}
        date_range_days = query_params.get("dateRange")
        
        # Initialize transfer detection service
        transfer_service = TransferDetectionService()
        
        # Get transfer category IDs for this user
        transfer_category_ids = list(transfer_service._get_transfer_category_ids(user_id))
        
        if not transfer_category_ids:
            # No transfer categories exist, return empty result
            logger.info(f"No transfer categories found for user {user_id}")
            return create_response(200, {
                "pairedTransfers": [],
                "count": 0
            })
        
        # Get transfer transactions with optional date range filtering
        from utils.db_utils import list_user_transactions
        
        if date_range_days:
            try:
                from datetime import datetime, timedelta
                days = int(date_range_days)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                start_date_ts = int(start_date.timestamp() * 1000)
                end_date_ts = int(end_date.timestamp() * 1000)
                
                logger.info(f"Filtering paired transfers to last {days} days")
                
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
                        
            except (ValueError, TypeError):
                logger.warning(f"Invalid dateRange parameter: {date_range_days}, falling back to all transfers")
                # Fallback to getting all transfer transactions
                transfer_transactions, _, _ = list_user_transactions(
                    user_id=user_id,
                    category_ids=transfer_category_ids,
                    limit=1000
                )
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
        
        return create_response(200, {
            "pairedTransfers": paired_transfers,
            "count": len(paired_transfers)
        })
        
    except Exception as e:
        logger.error(f"Error getting paired transfers: {str(e)}")
        return create_response(500, {"message": "Error getting paired transfers"})


def bulk_mark_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Mark multiple detected transfer pairs as transfers."""
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        
        transfer_pairs = body.get("transferPairs", [])
        
        if not transfer_pairs:
            return create_response(400, {"message": "No transfer pairs provided"})
        
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
                failed_pairs.append({
                    "pair": pair,
                    "error": str(e)
                })
        
        return create_response(200, {
            "successful": successful_pairs,
            "failed": failed_pairs,
            "successCount": len(successful_pairs),
            "failureCount": len(failed_pairs)
        })
        
    except json.JSONDecodeError:
        return create_response(400, {"message": "Invalid JSON in request body"})
    except Exception as e:
        logger.error(f"Error bulk marking transfer pairs: {str(e)}")
        return create_response(500, {"message": "Error bulk marking transfer pairs"})


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main handler for transfer operations."""
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user["id"]
        
        # Get route from event
        route = event.get("routeKey")
        if not route:
            return create_response(400, {"message": "Route not specified"})
        
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
            return create_response(400, {"message": f"Unsupported route: {route}"})
            
    except Exception as e:
        logger.error(f"Error in transfer operations handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"})
