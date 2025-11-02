"""
Handler for transfer-related operations.
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional
import uuid

from services.transfer_detection_service import TransferDetectionService
from utils.db.base import tables
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
        table = tables.transactions
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



def _parse_date_range_parameters(event: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    """Parse date range parameters from event."""
    start_date_param = optional_query_parameter(event, "startDate")
    end_date_param = optional_query_parameter(event, "endDate")
    
    if not (start_date_param and end_date_param):
        return None, None
    
    try:
        from datetime import datetime
        start_date_ts = int(start_date_param)
        end_date_ts = int(end_date_param)
        
        # Convert to datetime objects for logging
        start_date = datetime.fromtimestamp(start_date_ts / 1000)
        end_date = datetime.fromtimestamp(end_date_ts / 1000)
        
        logger.info(f"Filtering paired transfers from {start_date.isoformat()} to {end_date.isoformat()}")
        return start_date_ts, end_date_ts
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid date format: {e}")
        raise ValueError("Invalid date format. Expected milliseconds since epoch")


def _get_transfer_transactions_with_pagination(
    user_id: str, 
    transfer_category_ids: list, 
    start_date_ts: Optional[int] = None, 
    end_date_ts: Optional[int] = None
) -> list:
    """Get transfer transactions with pagination."""
    from utils.db_utils import list_user_transactions
    
    transfer_transactions = []
    last_evaluated_key = None
    
    while True:
        if start_date_ts and end_date_ts:
            batch_result, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                category_ids=transfer_category_ids,
                start_date_ts=start_date_ts,
                end_date_ts=end_date_ts,
                last_evaluated_key=last_evaluated_key,
                limit=500
            )
        else:
            batch_result, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                category_ids=transfer_category_ids,
                last_evaluated_key=last_evaluated_key,
                limit=500
            )
        
        transfer_transactions.extend(batch_result)
        
        if not last_evaluated_key:
            break
    
    return transfer_transactions


def _find_transfer_pairs(transfer_transactions: list, transfer_service: TransferDetectionService) -> list:
    """Find transfer pairs from transactions."""
    paired_transfers = []
    processed_transaction_ids = set()
    
    for tx in transfer_transactions:
        if str(tx.transaction_id) in processed_transaction_ids:
            continue
            
        # Look for matching transfer transaction
        for other_tx in transfer_transactions:
            if _is_valid_transfer_pair(tx, other_tx, processed_transaction_ids, transfer_service):
                outgoing_tx, incoming_tx = _determine_transfer_direction(tx, other_tx)
                if outgoing_tx and incoming_tx:
                    paired_transfers.append(_create_transfer_pair_response(outgoing_tx, incoming_tx))
                    processed_transaction_ids.add(str(tx.transaction_id))
                    processed_transaction_ids.add(str(other_tx.transaction_id))
                    break
    
    return paired_transfers


def _is_valid_transfer_pair(
    tx: Any, 
    other_tx: Any, 
    processed_transaction_ids: set, 
    transfer_service: TransferDetectionService
) -> bool:
    """Check if two transactions form a valid transfer pair."""
    return (
        str(other_tx.transaction_id) != str(tx.transaction_id) and
        str(other_tx.transaction_id) not in processed_transaction_ids and
        tx.account_id != other_tx.account_id and
        transfer_service._transactions_could_be_transfer_pair(tx, other_tx)
    )


def _determine_transfer_direction(tx: Any, other_tx: Any) -> tuple[Optional[Any], Optional[Any]]:
    """Determine which transaction is outgoing and which is incoming."""
    if tx.amount < 0 and other_tx.amount > 0:
        return tx, other_tx
    elif tx.amount > 0 and other_tx.amount < 0:
        return other_tx, tx
    else:
        return None, None  # Skip if both same sign


def _create_transfer_pair_response(outgoing_tx: Any, incoming_tx: Any) -> Dict[str, Any]:
    """Create transfer pair response object."""
    return {
        "outgoingTransaction": outgoing_tx.model_dump(by_alias=True, mode="json"),
        "incomingTransaction": incoming_tx.model_dump(by_alias=True, mode="json"),
        "amount": abs(outgoing_tx.amount),
        "dateDifference": abs(outgoing_tx.date - incoming_tx.date) // (1000 * 60 * 60 * 24)  # Days
    }


@api_handler()
def get_paired_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get existing paired transfer transactions for a user."""
    logger.info(f"Getting paired transfers for user {user_id}")
    
    # Parse parameters
    start_date_ts, end_date_ts = _parse_date_range_parameters(event)
    count_only_param = optional_query_parameter(event, "count_only")
    
    # Initialize transfer detection service
    transfer_service = TransferDetectionService()
    
    # Get transfer category IDs for this user
    transfer_category_ids = list(transfer_service._get_transfer_category_ids(user_id))
    
    if not transfer_category_ids:
        # No transfer categories exist, return empty result
        logger.info(f"No transfer categories found for user {user_id}")
        if count_only_param == "true":
            return {"count": 0}
        return {
            "pairedTransfers": [],
            "count": 0,
            "dateRange": {
                "startDate": start_date_ts,
                "endDate": end_date_ts
            } if start_date_ts and end_date_ts else None
        }
    
    # Get transfer transactions with pagination
    transfer_transactions = _get_transfer_transactions_with_pagination(
        user_id, transfer_category_ids, start_date_ts, end_date_ts
    )
    
    # Find transfer pairs
    paired_transfers = _find_transfer_pairs(transfer_transactions, transfer_service)
    
    logger.info(f"Found {len(paired_transfers)} existing transfer pairs")
    
    # If only count is requested, return just the count
    if count_only_param == "true":
        return {"count": len(paired_transfers)}
    
    return {
        "pairedTransfers": paired_transfers,
        "count": len(paired_transfers),
        "dateRange": {
            "startDate": start_date_ts,
            "endDate": end_date_ts
        } if start_date_ts and end_date_ts else None
    }


def _validate_transfer_pair_ids(pair: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Validate and extract transaction IDs from transfer pair."""
    outgoing_tx_id = pair.get("outgoingTransactionId")
    incoming_tx_id = pair.get("incomingTransactionId")
    
    if not outgoing_tx_id or not incoming_tx_id:
        return None, None, "Missing transaction IDs"
    
    return outgoing_tx_id, incoming_tx_id, None


def _get_and_validate_transactions(
    outgoing_tx_id: str, 
    incoming_tx_id: str, 
    user_id: str
) -> tuple[Optional[Any], Optional[Any], Optional[str]]:
    """Get and validate transactions for transfer pair."""
    # Get transactions
    outgoing_tx = get_transaction_by_id(uuid.UUID(outgoing_tx_id))
    incoming_tx = get_transaction_by_id(uuid.UUID(incoming_tx_id))
    
    if not outgoing_tx or not incoming_tx:
        return None, None, "One or both transactions not found"
    
    # Verify transactions belong to user
    if outgoing_tx.user_id != user_id or incoming_tx.user_id != user_id:
        return None, None, "Unauthorized access to transactions"
    
    return outgoing_tx, incoming_tx, None


def _process_single_transfer_pair(
    pair: Dict[str, Any], 
    user_id: str, 
    transfer_service: TransferDetectionService
) -> tuple[Optional[Dict[str, str]], Optional[Dict[str, Any]]]:
    """Process a single transfer pair and return success or failure result."""
    # Validate transaction IDs
    outgoing_tx_id, incoming_tx_id, validation_error = _validate_transfer_pair_ids(pair)
    if validation_error or not outgoing_tx_id or not incoming_tx_id:
        return None, {"pair": pair, "error": validation_error or "Missing transaction IDs"}
    
    # Get and validate transactions
    outgoing_tx, incoming_tx, transaction_error = _get_and_validate_transactions(
        outgoing_tx_id, incoming_tx_id, user_id
    )
    if transaction_error or not outgoing_tx or not incoming_tx:
        return None, {"pair": pair, "error": transaction_error or "Transaction validation failed"}
    
    # Mark as transfer pair
    success = transfer_service.mark_as_transfer_pair(outgoing_tx, incoming_tx, user_id)
    
    if success:
        return {
            "outgoingTransactionId": outgoing_tx_id,
            "incomingTransactionId": incoming_tx_id
        }, None
    else:
        return None, {"pair": pair, "error": "Failed to mark as transfer pair"}


@api_handler()
def bulk_mark_transfers_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Mark multiple detected transfer pairs as transfers."""
    # Parse request body
    body = json.loads(event.get("body", "{}"))
    transfer_pairs = body.get("transferPairs", [])
    
    if not transfer_pairs:
        raise ValueError("No transfer pairs provided")
    
    # Get the date range that was scanned to update checked range after successful approvals
    scanned_start_date = body.get("scannedStartDate")  # milliseconds since epoch
    scanned_end_date = body.get("scannedEndDate")      # milliseconds since epoch
    
    # Initialize transfer detection service
    transfer_service = TransferDetectionService()
    
    successful_pairs = []
    failed_pairs = []
    
    for pair in transfer_pairs:
        try:
            success_result, failure_result = _process_single_transfer_pair(pair, user_id, transfer_service)
            
            if success_result:
                successful_pairs.append(success_result)
            elif failure_result:
                failed_pairs.append(failure_result)
                
        except Exception as e:
            logger.error(f"Error processing transfer pair: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            failed_pairs.append({
                "pair": pair,
                "error": str(e)
            })
    
    # Update checked date range in user preferences if we have successful approvals and date range info
    if successful_pairs and scanned_start_date and scanned_end_date:
        try:
            import asyncio
            from services.user_preferences_service import UserPreferencesService
            prefs_service = UserPreferencesService()
            
            # Get current transfer preferences
            current_prefs = asyncio.run(prefs_service.get_transfer_preferences(user_id))
            
            # Update the checked date range to extend to the scanned range
            updated_prefs = {
                **current_prefs,
                'checkedDateRangeStart': scanned_start_date,
                'checkedDateRangeEnd': scanned_end_date
            }
            
            # Save updated preferences
            asyncio.run(prefs_service.update_transfer_preferences(user_id, updated_prefs))
            
            logger.info(f"Updated checked date range for user {user_id}: {scanned_start_date} to {scanned_end_date}")
            
        except Exception as e:
            logger.warning(f"Failed to update checked date range after bulk approval: {str(e)}")
            # Don't fail the entire operation if preference update fails
    
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
