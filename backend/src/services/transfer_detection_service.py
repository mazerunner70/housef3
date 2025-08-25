"""
Service for detecting and managing transfer transactions between accounts.

This service identifies transactions that represent transfers between user accounts
and provides functionality to link them appropriately.

Follows backend conventions:
- Uses CategoryCreate DTO for model creation
- Never directly instantiates Category models
- Ensures proper validation through DTO pattern
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from models.transaction import Transaction
from models.category import Category, CategoryType, CategoryCreate
from utils.db_utils import (
    list_user_transactions, 
    get_categories_table,
    list_categories_by_user_from_db,
    update_transaction,
    create_category_in_db
)

logger = logging.getLogger(__name__)


class TransferDetectionService:
    """Service for detecting and managing transfer transactions between accounts."""
    
    def __init__(self):
        self.transfer_category_cache: Dict[str, Optional[Category]] = {}
        self._transfer_category_ids_cache: Dict[str, Set[str]] = {}
    
    def detect_transfers_for_user(self, user_id: str, date_range_days: int = 7) -> List[Tuple[Transaction, Transaction]]:
        """
        Detect potential transfer transactions for a user.
        
        Args:
            user_id: The user ID to analyze
            date_range_days: Number of days to look for matching transactions (default: 7)
            
        Returns:
            List of tuples containing matched transfer transactions (outgoing, incoming)
        """
        try:
            # Process transfer detection in batches - each batch is self-sufficient
            all_transfer_pairs = self._detect_transfers_in_batches(
                user_id=user_id,
                date_range_days=date_range_days
            )
            
            logger.info(f"Detected {len(all_transfer_pairs)} potential transfer pairs for user {user_id}")
            return all_transfer_pairs
            
        except Exception as e:
            logger.error(f"Error detecting transfers for user {user_id}: {str(e)}")
            return []
    
    def _detect_transfers_in_batches(
        self, 
        user_id: str, 
        date_range_days: int
    ) -> List[Tuple[Transaction, Transaction]]:
        """
        Detect transfers in batches - each batch is self-sufficient since transfer pairs are typically close in time.
        
        Args:
            user_id: The user ID
            date_range_days: Total date range in days
            
        Returns:
            List of all transfer pairs found across all batches
        """
        from datetime import datetime, timedelta
        
        # Calculate batch size - each batch should be large enough to capture transfer pairs
        # Since transfers are usually within a few days, 14-day batches with overlap should work well
        batch_days = min(14, date_range_days)
        overlap_days = min(date_range_days, 3)  # 3-day overlap to ensure cross-batch transfers are caught
        
        all_transfer_pairs = []
        processed_global_ids = set()  # Track globally to avoid duplicates across batches
        
        end_date = datetime.now()
        current_end = end_date
        
        while True:
            # Calculate batch date range
            current_start = current_end - timedelta(days=batch_days)
            
            # Don't go beyond the requested date range
            requested_start = end_date - timedelta(days=date_range_days)
            if current_start < requested_start:
                current_start = requested_start
            
            # Convert to milliseconds since epoch
            start_date_ts = int(current_start.timestamp() * 1000)
            end_date_ts = int(current_end.timestamp() * 1000)
            
            logger.info(f"Processing transfer detection batch: {current_start.date()} to {current_end.date()}")
            
            # Get uncategorized transactions for this batch
            batch_transactions = self._get_batch_transactions(
                user_id=user_id,
                start_date_ts=start_date_ts,
                end_date_ts=end_date_ts
            )
            
            # Process transfer detection within this batch
            batch_transfer_pairs = self._detect_transfers_in_batch(
                batch_transactions, 
                date_range_days,
                processed_global_ids
            )
            
            # Add new pairs to results
            all_transfer_pairs.extend(batch_transfer_pairs)
            logger.info(f"Batch found {len(batch_transfer_pairs)} transfer pairs, total: {len(all_transfer_pairs)}")
            
            # Check if we've covered the full date range
            if current_start <= requested_start:
                break
            
            # Move to next batch with overlap
            current_end = current_start + timedelta(days=overlap_days)
        
        logger.info(f"Total transfer pairs found across all batches: {len(all_transfer_pairs)}")
        return all_transfer_pairs

    def _get_batch_transactions(
        self,
        user_id: str,
        start_date_ts: int,
        end_date_ts: int
    ) -> List[Transaction]:
        """Get all uncategorized transactions for a specific date range batch."""
        batch_transactions = []
        last_evaluated_key = None
        
        while True:
            batch_result, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                uncategorized_only=True,
                start_date_ts=start_date_ts,
                end_date_ts=end_date_ts,
                last_evaluated_key=last_evaluated_key,
                limit=500  # Reasonable page size
            )
            
            batch_transactions.extend(batch_result)
            
            # Break if no more pages
            if not last_evaluated_key:
                break
        
        return batch_transactions

    def _detect_transfers_in_batch(
        self,
        batch_transactions: List[Transaction],
        date_range_days: int,
        processed_global_ids: Set[str]
    ) -> List[Tuple[Transaction, Transaction]]:
        """Detect transfer pairs within a single batch of transactions."""
        # Group transactions by account
        account_transactions = self._group_by_account(batch_transactions)
        
        # Find potential transfer pairs within this batch
        batch_transfer_pairs = []
        processed_batch_ids: Set[str] = set()
        
        for account_id, transactions in account_transactions.items():
            for tx in transactions:
                tx_id = str(tx.transaction_id)
                
                # Skip if already processed globally or in this batch
                if tx_id in processed_global_ids or tx_id in processed_batch_ids:
                    continue
                
                # Look for matching transaction in other accounts within this batch
                matching_tx = self._find_matching_transfer(
                    tx, account_transactions, date_range_days, processed_batch_ids
                )
                
                if matching_tx:
                    matching_tx_id = str(matching_tx.transaction_id)
                    
                    # Skip if matching transaction was already processed globally
                    if matching_tx_id in processed_global_ids:
                        continue
                    
                    # Determine which is outgoing (negative) and incoming (positive)
                    if tx.amount < 0 and matching_tx.amount > 0:
                        batch_transfer_pairs.append((tx, matching_tx))
                    elif tx.amount > 0 and matching_tx.amount < 0:
                        batch_transfer_pairs.append((matching_tx, tx))
                    
                    # Mark both as processed in this batch and globally
                    processed_batch_ids.add(tx_id)
                    processed_batch_ids.add(matching_tx_id)
                    processed_global_ids.add(tx_id)
                    processed_global_ids.add(matching_tx_id)
        
        return batch_transfer_pairs

    def _group_by_account(self, transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
        """Group transactions by account ID."""
        account_groups = {}
        for tx in transactions:
            account_key = str(tx.account_id)
            if account_key not in account_groups:
                account_groups[account_key] = []
            account_groups[account_key].append(tx)
        return account_groups
    
    def _find_matching_transfer(
        self, 
        transaction: Transaction, 
        account_transactions: Dict[str, List[Transaction]], 
        date_range_days: int,
        processed_ids: Set[str]
    ) -> Optional[Transaction]:
        """
        Find a matching transaction that could be the other side of a transfer.
        
        Matching criteria:
        1. Different account
        2. Opposite amount (within tolerance)
        3. Within date range
        4. Not already processed
        """
        tx_date = datetime.fromtimestamp(transaction.date / 1000)
        date_tolerance = timedelta(days=date_range_days)
        amount_tolerance = Decimal('0.01')  # Allow for small rounding differences
        
        current_account = str(transaction.account_id)
        
        for account_id, transactions in account_transactions.items():
            if account_id == current_account:
                continue  # Skip same account
            
            for candidate in transactions:
                if str(candidate.transaction_id) in processed_ids:
                    continue
                
                # Check date range
                candidate_date = datetime.fromtimestamp(candidate.date / 1000)
                if abs((tx_date - candidate_date).total_seconds()) > date_tolerance.total_seconds():
                    continue
                
                # Check if amounts are opposite (within tolerance)
                if abs(abs(transaction.amount) - abs(candidate.amount)) <= amount_tolerance:
                    # Check if one is positive and one is negative
                    if (transaction.amount > 0 and candidate.amount < 0) or \
                       (transaction.amount < 0 and candidate.amount > 0):
                        return candidate
        
        return None
    
    def _get_transfer_category_ids(self, user_id: str) -> Set[str]:
        """Get the category IDs for transfer categories for this user."""
        if user_id in self._transfer_category_ids_cache:
            return self._transfer_category_ids_cache[user_id]
        
        try:
            categories = list_categories_by_user_from_db(user_id)
            transfer_category_ids = {
                str(cat.categoryId) for cat in categories 
                if cat.type == CategoryType.TRANSFER
            }
            self._transfer_category_ids_cache[user_id] = transfer_category_ids
            return transfer_category_ids
        except Exception as e:
            logger.warning(f"Error getting transfer categories for user {user_id}: {str(e)}")
            return set()
    
    def _is_already_transfer(self, transaction: Transaction) -> bool:
        """Check if transaction is already categorized as a transfer."""
        if not transaction.categories:
            return False
        
        # We need the user_id to get transfer categories, but it's not passed to this method
        # For now, we'll extract it from the transaction
        user_id = transaction.user_id
        transfer_category_ids = self._get_transfer_category_ids(user_id)
        
        for assignment in transaction.categories:
            if str(assignment.category_id) in transfer_category_ids:
                return True
        
        return False
    
    def get_or_create_transfer_category(self, user_id: str) -> Category:
        """
        Get or create a default transfer category for the user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Category object for transfers
        """
        if user_id in self.transfer_category_cache:
            cached_category = self.transfer_category_cache[user_id]
            if cached_category:
                return cached_category
        
        try:
            # Look for existing transfer category
            categories = list_categories_by_user_from_db(user_id)
            transfer_category = next(
                (cat for cat in categories if cat.type == CategoryType.TRANSFER), 
                None
            )
            
            if transfer_category:
                self.transfer_category_cache[user_id] = transfer_category
                return transfer_category
            
            # Create new transfer category using CategoryCreate DTO
            category_create = CategoryCreate(
                name="Transfers",
                type=CategoryType.TRANSFER,
                icon="transfer",
                color="#6B7280"  # Gray color for transfers
            )
            
            # Convert CategoryCreate to Category model and save to database
            new_category = Category(
                userId=user_id,
                **category_create.model_dump()
            )
            
            # Save to database
            create_category_in_db(new_category)
            
            self.transfer_category_cache[user_id] = new_category
            logger.info(f"Created new transfer category for user {user_id}")
            return new_category
            
        except Exception as e:
            logger.error(f"Error getting/creating transfer category for user {user_id}: {str(e)}")
            raise
    
    def mark_as_transfer_pair(self, outgoing_tx: Transaction, incoming_tx: Transaction, user_id: str) -> bool:
        """
        Mark two transactions as a transfer pair.
        
        Args:
            outgoing_tx: The outgoing transaction (negative amount)
            incoming_tx: The incoming transaction (positive amount)
            user_id: The user ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            transfer_category = self.get_or_create_transfer_category(user_id)
            
            # Add transfer category to both transactions
            outgoing_tx.add_manual_category(transfer_category.categoryId, set_as_primary=True)
            incoming_tx.add_manual_category(transfer_category.categoryId, set_as_primary=True)
            
            # Update both transactions in database
            update_transaction(outgoing_tx)
            update_transaction(incoming_tx)
            
            logger.info(f"Marked transactions {outgoing_tx.transaction_id} and {incoming_tx.transaction_id} as transfer pair")
            return True
            
        except Exception as e:
            logger.error(f"Error marking transfer pair: {str(e)}")
            return False
    

    
    def _transactions_could_be_transfer_pair(self, tx1: Transaction, tx2: Transaction) -> bool:
        """Check if two transactions could be a transfer pair."""
        # Check if amounts are opposite (within tolerance)
        amount_tolerance = Decimal('0.01')
        if abs(abs(tx1.amount) - abs(tx2.amount)) > amount_tolerance:
            return False
        
        # Check if one is positive and one is negative
        if not ((tx1.amount > 0 and tx2.amount < 0) or (tx1.amount < 0 and tx2.amount > 0)):
            return False
        
        # Check date range (within 7 days)
        date_diff = abs(tx1.date - tx2.date)
        max_date_diff = 7 * 24 * 60 * 60 * 1000  # 7 days in milliseconds
        if date_diff > max_date_diff:
            return False
        
        return True
