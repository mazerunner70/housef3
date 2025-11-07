"""
Recurring Charge Detection Consumer Lambda.

This Lambda function consumes events from EventBridge that request recurring
charge pattern detection and processes them asynchronously.

Event Types Processed:
- recurring_charge.detection.requested: Trigger ML-based pattern detection

The consumer uses the RecurringChargeDetectionService to analyze transaction
history and identify recurring patterns, then saves them to DynamoDB.
"""

import json
import logging
import os
import sys
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    if "/var/task" not in sys.path:
        sys.path.insert(0, "/var/task")
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    logger.info("Successfully adjusted Python path for Lambda environment")
except Exception as e:
    logger.exception(f"Import path setup error: {str(e)}", exc_info=True)
    raise

# Import after path fixing
from consumers.base_consumer import BaseEventConsumer, EventProcessingError
from models.events import BaseEvent
from services.recurring_charge_detection_service import RecurringChargeDetectionService
from services.recurring_charge_prediction_service import RecurringChargePredictionService
from utils.db.transactions import list_user_transactions
from utils.db.recurring_charges import batch_create_patterns_in_db
from models.transaction import Transaction
from models.recurring_charge import RecurringChargePatternCreate
import uuid

# Operation tracking
from services.operation_tracking_service import (
    operation_tracking_service,
    OperationStatus,
)


class RecurringChargeDetectionConsumer(BaseEventConsumer):
    """Consumer for recurring charge detection events"""
    
    # Event types that should trigger detection
    DETECTION_EVENT_TYPES = {
        "recurring_charge.detection.requested",
    }
    
    def __init__(self):
        super().__init__("recurring_charge_detection_consumer")
        self.detection_service = RecurringChargeDetectionService(country_code="US")
        self.prediction_service = RecurringChargePredictionService()
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Only process detection request events"""
        return event.event_type in self.DETECTION_EVENT_TYPES
    
    def process_event(self, event: BaseEvent) -> None:
        """
        Process recurring charge detection request.
        
        This method:
        1. Fetches user transactions
        2. Runs ML-based pattern detection
        3. Saves detected patterns to database
        4. Generates predictions for next occurrences
        5. Updates operation tracking status
        """
        try:
            event_type = event.event_type
            user_id = event.user_id
            
            logger.info(f"Processing {event_type} event {event.event_id} for user {user_id}")
            
            # Extract parameters from event
            if not event.data:
                raise EventProcessingError("Event data is missing", permanent=True)
            
            operation_id = event.data.get("operationId")
            account_id = event.data.get("accountId")
            min_occurrences = event.data.get("minOccurrences", 3)
            min_confidence = event.data.get("minConfidence", 0.6)
            if min_occurrences < 1:
                raise EventProcessingError("minOccurrences must be at least 1", permanent=True)
            if not (0.0 <= min_confidence <= 1.0):
                raise EventProcessingError("minConfidence must be between 0.0 and 1.0", permanent=True)
            if not operation_id:
                raise EventProcessingError("Operation ID is missing", permanent=True)
            
            logger.info(
                f"Detection parameters: account_id={account_id}, "
                f"min_occurrences={min_occurrences}, min_confidence={min_confidence}"
            )
            
            # Update operation status to in progress
            self._update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.IN_PROGRESS,
                progress=10,
                step_description="Fetching transactions for analysis",
            )
            
            # Fetch transactions for analysis
            transactions = self._fetch_transactions(user_id, account_id)
            
            if not transactions:
                logger.info(f"No transactions found for user {user_id}")
                self._update_operation_status(
                    operation_id=operation_id,
                    status=OperationStatus.COMPLETED,
                    progress=100,
                    step_description="No transactions to analyze",
                    additional_data={
                        "patternsDetected": 0,
                        "transactionsAnalyzed": 0,
                    },
                )
                return
            
            logger.info(f"Fetched {len(transactions)} transactions for analysis")
            
            # Update operation status
            self._update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.IN_PROGRESS,
                progress=30,
                step_description=f"Analyzing {len(transactions)} transactions",
            )
            
            # Run pattern detection
            patterns = self.detection_service.detect_recurring_patterns(
                user_id=user_id,
                transactions=transactions,
                min_occurrences=min_occurrences,
                min_confidence=min_confidence,
            )
            
            logger.info(f"Detected {len(patterns)} recurring charge patterns")
            
            # Update operation status
            self._update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.IN_PROGRESS,
                progress=60,
                step_description=f"Saving {len(patterns)} detected patterns",
            )
            
            # Save patterns to database
            patterns_saved_count = 0
            predictions_created = 0
            
            if patterns:
                patterns_saved_count = batch_create_patterns_in_db(patterns)
                logger.info(f"Saved {patterns_saved_count} patterns to database")
                
                # Generate predictions for each pattern
                self._update_operation_status(
                    operation_id=operation_id,
                    status=OperationStatus.IN_PROGRESS,
                    progress=80,
                    step_description="Generating predictions for detected patterns",
                )
                
                predictions_created = self._generate_predictions(user_id, patterns)
                logger.info(f"Generated {predictions_created} predictions")
            
            # Update operation status to completed
            self._update_operation_status(
                operation_id=operation_id,
                status=OperationStatus.COMPLETED,
                progress=100,
                step_description="Pattern detection completed successfully",
                additional_data={
                    "patternsDetected": patterns_saved_count,
                    "predictionsGenerated": predictions_created,
                    "transactionsAnalyzed": len(transactions),
                },
            )
            
            logger.info(
                f"Detection completed: {patterns_saved_count} patterns, "
                f"{predictions_created} predictions, {len(transactions)} transactions analyzed"
            )
            
        except EventProcessingError:
            # Re-raise event processing errors
            raise
        except ValueError as e:
            # Validation errors are permanent
            logger.exception(f"Validation error in detection: {e}")
            # operation_id is guaranteed to be set if we got past the initial checks
            if "operation_id" in locals() and operation_id:
                self._update_operation_status(
                    operation_id=operation_id,
                    status=OperationStatus.FAILED,
                    progress=0,
                    step_description="Detection failed",
                    error_message=str(e),
                )
            raise EventProcessingError(str(e), event_id=event.event_id, permanent=True)
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error in detection: {e}")
            # operation_id is guaranteed to be set if we got past the initial checks
            if "operation_id" in locals() and operation_id:
                self._update_operation_status(
                    operation_id=operation_id,
                    status=OperationStatus.FAILED,
                    progress=0,
                    step_description="Detection failed with unexpected error",
                    error_message=str(e),
                )
            raise
    
    def _fetch_transactions(self, user_id: str, account_id: Optional[str]) -> List[Transaction]:
        """
        Fetch transactions for pattern detection.
        
        Fetches up to 10,000 most recent transactions for the user, optionally
        filtered by account. Uses pagination to avoid Lambda timeouts and
        automatically filters out duplicate transactions.
        
        Args:
            user_id: User ID
            account_id: Optional account ID to filter transactions
            
        Returns:
            List of Transaction objects sorted by date (most recent first)
        """
        try:
            # Prepare account filter if specified
            account_ids = [uuid.UUID(account_id)] if account_id else None
            
            # Fetch transactions with proper sorting (most recent first)
            # We'll paginate to get up to 10,000 transactions
            all_transactions = []
            last_key = None
            max_transactions = 10000
            page_size = 1000  # Fetch in chunks to avoid timeouts
            
            while len(all_transactions) < max_transactions:
                remaining = max_transactions - len(all_transactions)
                limit = min(page_size, remaining)
                
                transactions, last_key, _ = list_user_transactions(
                    user_id=user_id,
                    limit=limit,
                    last_evaluated_key=last_key,
                    account_ids=account_ids,
                    sort_order_date='desc',  # Most recent first!
                    ignore_dup=True,  # Automatically filter duplicates
                )
                
                if not transactions:
                    break
                    
                all_transactions.extend(transactions)
                
                # If no more pages, stop
                if not last_key:
                    break
            
            # Filter out transactions without dates or amounts
            valid_transactions = [
                tx for tx in all_transactions
                if tx.date is not None and tx.amount is not None
            ]
            
            logger.info(
                f"Fetched {len(all_transactions)} transactions, "
                f"{len(valid_transactions)} valid for analysis "
                f"(account_id={account_id or 'all accounts'})"
            )
            
            return valid_transactions
            
        except Exception as e:
            logger.exception(f"Error fetching transactions: {e}")
            raise
    
    def _generate_predictions(
        self,
        user_id: str,
        patterns: List[Any],
    ) -> int:
        """
        Generate predictions for detected patterns.
        
        Args:
            user_id: User ID
            patterns: List of RecurringChargePattern objects
            
        Returns:
            Number of predictions created
        """
        predictions_created = 0
        
        for pattern in patterns:
            try:
                # Generate prediction for next occurrence
                prediction = self.prediction_service.predict_next_occurrence(pattern)
                
                if prediction:
                    # Save prediction to database
                    from utils.db.recurring_charges import save_prediction_in_db
                    save_prediction_in_db(prediction, user_id)
                    predictions_created += 1
                    
            except ValueError as e:
                # Expected errors (e.g., pattern too irregular)
                logger.warning(f"Could not generate prediction for pattern {pattern.pattern_id}: {e}", exc_info=True)
                continue
            except Exception as e:
                # Unexpected errors - log but continue with other patterns
                logger.exception(f"Error generating prediction for pattern {pattern.pattern_id}: {e}")
                continue
        
        return predictions_created
    
    def _update_operation_status(
        self,
        operation_id: str,
        status: OperationStatus,
        progress: int,
        step_description: str,
        error_message: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update operation tracking status.
        
        Args:
            operation_id: Operation ID
            status: New status
            progress: Progress percentage (0-100)
            step_description: Description of current step
            error_message: Optional error message
            additional_data: Optional additional data to store
        """
        try:
            operation_tracking_service.update_operation_status(
                operation_id=operation_id,
                status=status,
                progress_percentage=progress,
                step_description=step_description,
                error_message=error_message,
                additional_data=additional_data,
            )
        except Exception as e:
            # Don't fail the main operation if tracking update fails
            logger.warning(f"Failed to update operation status: {e}", exc_info=True)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for recurring charge detection events from EventBridge.
    
    Expected event format from EventBridge:
    {
        "version": "0",
        "id": "event-id",
        "detail-type": "Application Event",
        "source": "recurring_charge.service",
        "detail": {
            "eventId": "...",
            "eventType": "recurring_charge.detection.requested",
            "userId": "...",
            "data": {
                "operationId": "op_20250107_123456_abc",
                "accountId": "optional-account-id",
                "minOccurrences": 3,
                "minConfidence": 0.6
            }
        }
    }
    """
    try:
        logger.info(f"Recurring charge detection consumer received event: {json.dumps(event)}")
        
        consumer = RecurringChargeDetectionConsumer()
        result = consumer.handle_eventbridge_event(event, context)
        
        logger.info("Recurring charge detection consumer completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Recurring charge detection consumer failed: {str(e)}")
        logger.error(f"Event: {json.dumps(event)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # Return failure but don't raise - let EventBridge handle retries
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Recurring charge detection consumer failed",
                "message": str(e),
            }),
        }

