"""
Categorization Event Consumer Lambda

This Lambda function consumes events from EventBridge that contain new transactions
and applies category rules to automatically categorize them.

Event Types Processed:
- file.processed: Apply rules to newly created transactions from file uploads

The consumer uses the existing CategoryRuleEngine to apply rules and create
category suggestions for manual review.
"""

import json
import logging
import os
import sys
import traceback
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    if '/var/task' not in sys.path:
        sys.path.insert(0, '/var/task')
    
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        
    logger.info("Successfully adjusted Python path for Lambda environment")
except Exception as e:
    logger.error(f"Import path setup error: {str(e)}")
    raise

# Import after path fixing
from consumers.base_consumer import BaseEventConsumer
from models.events import BaseEvent, FileDeletionVoteEvent
from models.category import CategorySuggestionStrategy
from services.category_rule_engine import CategoryRuleEngine
from services.event_service import event_service
from utils.db_utils import list_categories_by_user_from_db
from utils.db.base import tables

# Event publishing configuration
ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'


class CategorizationEventConsumer(BaseEventConsumer):
    """Consumer for events that contain transactions requiring categorization"""
    
    # Event types that should trigger categorization
    CATEGORIZATION_EVENT_TYPES = {
        'file.processed',        # New transactions from file uploads
        'file.deletion.requested'  # Process before file deletion
    }
    
    def __init__(self):
        super().__init__("categorization_consumer")
        self.rule_engine = CategoryRuleEngine()
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Only process events that contain new transactions"""
        return event.event_type in self.CATEGORIZATION_EVENT_TYPES
    
    def process_event(self, event: BaseEvent) -> None:
        """Apply category rules to transactions in the event"""
        try:
            event_type = event.event_type
            user_id = event.user_id
            
            logger.info(f"Processing {event_type} event {event.event_id} for categorization")
            
            # Extract transaction IDs based on event type
            transaction_ids = self._extract_transaction_ids(event)
            
            if not transaction_ids:
                logger.info(f"No transaction IDs found in event {event.event_id}")
                return
            
            logger.info(f"Found {len(transaction_ids)} transactions to categorize")
            
            # Get user categories
            categories = list_categories_by_user_from_db(user_id)
            if not categories:
                logger.info(f"No categories found for user {user_id}, skipping categorization")
                return
            
            # Count categories with rules
            categories_with_rules = [cat for cat in categories if cat.rules]
            logger.info(f"Found {len(categories_with_rules)} categories with rules out of {len(categories)} total categories")
            
            if not categories_with_rules:
                logger.info(f"No categories have rules defined, skipping categorization")
                return
            
            # Apply categorization to the specific transactions
            results = self._categorize_transactions(user_id, transaction_ids, categories)
            
            # Log results for monitoring
            self._log_categorization_metrics(event, results)
            
            # Publish vote event for coordination (if this is a file deletion request)
            if event_type == 'file.deletion.requested' and ENABLE_EVENT_PUBLISHING:
                self._publish_deletion_vote(event, 'proceed')
                
        except Exception as e:
            logger.error(f"Error processing categorization event {event.event_id}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            
            # Publish deny vote for coordination (if this is a file deletion request)
            if event.event_type == 'file.deletion.requested' and ENABLE_EVENT_PUBLISHING:
                try:
                    self._publish_deletion_vote(event, 'deny', str(e))
                except Exception as vote_error:
                    logger.error(f"Failed to publish deletion vote: {str(vote_error)}")
            
            raise
    
    def _extract_transaction_ids(self, event: BaseEvent) -> List[str]:
        """Extract transaction IDs from event data"""
        try:
            if event.event_type == 'file.processed':
                # FileProcessedEvent includes transactionIds in data
                if event.data is None:
                    logger.warning("Event data is None")
                    return []
                transaction_ids = event.data.get('transactionIds', [])
                logger.info(f"Extracted {len(transaction_ids)} transaction IDs from file.processed event")
                return transaction_ids
            elif event.event_type == 'file.deletion.requested':
                # For file deletion, get all transactions for the file
                if event.data is None:
                    logger.warning("Event data is None")
                    return []
                file_id = event.data.get('fileId')
                if not file_id:
                    logger.warning("No fileId in file.deletion.requested event")
                    return []
                
                # Get all transactions for this file
                from utils.db_utils import list_file_transactions
                import uuid
                try:
                    transactions = list_file_transactions(uuid.UUID(file_id))
                    transaction_ids = [str(tx.transaction_id) for tx in transactions]
                    logger.info(f"Extracted {len(transaction_ids)} transaction IDs from file {file_id} for deletion processing")
                    return transaction_ids
                except Exception as e:
                    logger.error(f"Error getting transactions for file {file_id}: {str(e)}")
                    return []
            
            # Add handling for other event types as needed
            logger.warning(f"Unknown event type for transaction extraction: {event.event_type}")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting transaction IDs from event: {str(e)}")
            return []
    
    def _categorize_transactions(
        self, 
        user_id: str, 
        transaction_ids: List[str], 
        categories: List[Any]
    ) -> Dict[str, int]:
        """Apply category rules to specific transactions"""
        
        stats = {
            'processed': 0,
            'suggestions_created': 0,
            'transactions_categorized': 0,
            'errors': 0
        }
        
        try:
            # Process each transaction individually
            for transaction_id in transaction_ids:
                try:
                    # Get the transaction from database
                    from models.transaction import Transaction
                    response = tables.transactions.get_item(Key={'transactionId': transaction_id})
                    if 'Item' not in response:
                        logger.warning(f"Transaction {transaction_id} not found")
                        stats['errors'] += 1
                        continue
                    
                    transaction = Transaction.from_dynamodb_item(response['Item'])
                    if transaction.user_id != user_id:
                        logger.warning(f"Transaction {transaction_id} does not belong to user {user_id}")
                        stats['errors'] += 1
                        continue
                    
                    # Apply categorization rules
                    suggestions = self.rule_engine.categorize_transaction(
                        transaction=transaction,
                        user_categories=categories,
                        suggestion_strategy=CategorySuggestionStrategy.ALL_MATCHES
                    )
                    
                    if suggestions:
                        # Add suggestions to the transaction
                        for suggestion in suggestions:
                            transaction.add_category_suggestion(
                                category_id=suggestion.category_id,
                                confidence=suggestion.confidence,
                                rule_id=suggestion.rule_id
                            )
                        
                        # Save the updated transaction
                        from utils.db_utils import update_transaction
                        update_transaction(transaction)
                        
                        stats['suggestions_created'] += len(suggestions)
                        stats['transactions_categorized'] += 1
                        
                        logger.info(f"Applied {len(suggestions)} category suggestions to transaction {transaction_id}")
                    else:
                        logger.debug(f"No category matches found for transaction {transaction_id}")
                    
                    stats['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing transaction {transaction_id}: {str(e)}")
                    stats['errors'] += 1
                    continue
            
            logger.info(f"Categorization completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in transaction categorization: {str(e)}")
            stats['errors'] += len(transaction_ids)
            return stats
    
    def _log_categorization_metrics(self, event: BaseEvent, results: Dict[str, int]):
        """Log metrics for monitoring and debugging"""
        try:
            metrics = {
                'event_type': event.event_type,
                'event_id': event.event_id,
                'user_id': event.user_id,
                'processed': results['processed'],
                'suggestions_created': results['suggestions_created'],
                'transactions_categorized': results['transactions_categorized'],
                'errors': results['errors'],
                'success_rate': (results['processed'] - results['errors']) / max(results['processed'], 1)
            }
            
            # Log as structured JSON for CloudWatch insights
            logger.info(f"CATEGORIZATION_METRICS: {json.dumps(metrics)}")
            
        except Exception as e:
            logger.warning(f"Failed to log categorization metrics: {str(e)}")
    
    def _publish_deletion_vote(self, original_event: BaseEvent, decision: str, reason: Optional[str] = None):
        """Publish deletion vote event for coordination"""
        try:
            if not original_event.data or not original_event.data.get('fileId'):
                logger.error("Cannot publish deletion vote: missing fileId in original event")
                return
            
            file_id = original_event.data['fileId']
            request_id = original_event.data.get('requestId') or original_event.correlation_id or original_event.event_id
            
            vote_event = FileDeletionVoteEvent(
                user_id=original_event.user_id,
                file_id=file_id,
                request_id=request_id,
                voter=self.get_voter_id(),
                decision=decision,
                reason=reason
            )
            
            success = event_service.publish_event(vote_event)
            if success:
                logger.info(f"Published deletion vote for file {file_id}, decision: {decision}")
            else:
                logger.error(f"Failed to publish deletion vote for file {file_id}")
                
        except Exception as e:
            logger.error(f"Error publishing deletion vote: {str(e)}")
            raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for categorization events from EventBridge.
    
    Expected event format from EventBridge:
    {
        "version": "0",
        "id": "event-id", 
        "detail-type": "Application Event",
        "source": "transaction.service",
        "detail": {
            "eventId": "...",
            "eventType": "file.processed",
            "userId": "...",
            "data": {
                "transactionIds": ["tx-1", "tx-2", ...],
                ...
            }
        }
    }
    """
    try:
        logger.info(f"Categorization consumer received event: {json.dumps(event)}")
        
        consumer = CategorizationEventConsumer()
        result = consumer.handle_eventbridge_event(event, context)
        
        logger.info(f"Categorization consumer completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Categorization consumer failed: {str(e)}")
        logger.error(f"Event: {json.dumps(event)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # Return failure but don't raise - let EventBridge handle retries
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Categorization consumer failed',
                'message': str(e)
            })
        }