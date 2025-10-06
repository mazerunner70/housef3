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
from typing import List, Dict, Optional, Tuple, Set, NamedTuple
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


class MinimalTransaction(NamedTuple):
    """Minimal transaction data for memory-efficient transfer detection."""
    transaction_id: str
    account_id: str
    amount: Decimal
    date: int  # timestamp in milliseconds
    abs_amount: Decimal


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

    def detect_transfers_for_user_in_range(self, user_id: str, start_date_ts: int, end_date_ts: int) -> List[Tuple[Transaction, Transaction]]:
        """
        Detect potential transfer transactions for a user within a specific date range.
        
        Args:
            user_id: The user ID to analyze
            start_date_ts: Start date timestamp in milliseconds
            end_date_ts: End date timestamp in milliseconds
            
        Returns:
            List of tuples containing matched transfer transactions (outgoing, incoming)
        """
        try:
            # Process transfer detection in batches using timestamps
            all_transfer_pairs = self._detect_transfers_in_date_range(
                user_id=user_id,
                start_date_ts=start_date_ts,
                end_date_ts=end_date_ts
            )
            
            logger.info(f"Detected {len(all_transfer_pairs)} potential transfer pairs for user {user_id} in date range")
            return all_transfer_pairs
            
        except Exception as e:
            logger.error(f"Error detecting transfers for user {user_id} in date range: {str(e)}")
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

    def _detect_transfers_in_date_range(
        self, 
        user_id: str, 
        start_date_ts: int,
        end_date_ts: int
    ) -> List[Tuple[Transaction, Transaction]]:
        """
        Fast transfer detection using sliding window algorithm.
        
        Algorithm:
        1. Sliding window moves back in time with 3-day overlap
        2. Minimal memory usage - only essential transaction data
        3. Sort by abs(amount) for efficient matching
        4. Early termination when amount difference exceeds tolerance
        
        Args:
            user_id: The user ID
            start_date_ts: Start date timestamp in milliseconds
            end_date_ts: End date timestamp in milliseconds
            
        Returns:
            List of all transfer pairs found in the date range
        """
        from datetime import datetime, timedelta
        
        logger.info(f"Starting sliding window transfer detection for user {user_id}")
        
        # Convert to datetime for window calculations
        start_date = datetime.fromtimestamp(start_date_ts / 1000)
        end_date = datetime.fromtimestamp(end_date_ts / 1000)
        
        # Window parameters
        window_days = 14  # 2-week windows
        overlap_days = 3  # 3-day overlap
        
        all_transfer_pairs = []
        processed_tx_ids = set()
        
        # Calculate sliding window parameters
        start_day_increment = window_days - overlap_days  # Days to move window start each iteration
        total_days = (end_date - start_date).days
        loop_size = max(1, (total_days // start_day_increment) + 1)  # Ensure at least 1 iteration
        
        logger.info(f"Sliding window: {total_days} total days, {start_day_increment} day increments, {loop_size} windows to process")
        
        # Process windows with simple for loop
        for i in range(loop_size):
            # Calculate window boundaries
            current_end = end_date - timedelta(days=i * start_day_increment)
            window_start = max(start_date, current_end - timedelta(days=window_days))
            
            # Convert to timestamps
            window_start_ts = int(window_start.timestamp() * 1000)
            window_end_ts = int(current_end.timestamp() * 1000)
            
            logger.info(f"Processing window {i+1}/{loop_size}: {window_start.date()} to {current_end.date()}")
            
            # Get transactions for this window
            window_transactions = self._get_user_transactions_in_range(
                user_id, window_start_ts, window_end_ts
            )
            
            logger.info(f"Window returned {len(window_transactions)} transactions")
            
            if len(window_transactions) < 2:
                logger.debug(f"Skipping window {i+1} - insufficient transactions for transfer detection")
                continue
            
            # Find transfers in this window using amount-sorted algorithm
            window_pairs = self._sliding_window_transfer_detection(
                window_transactions, processed_tx_ids
            )
            
            all_transfer_pairs.extend(window_pairs)
            logger.debug(f"Window {i+1} found {len(window_pairs)} transfer pairs")
        
        logger.info(f"Sliding window completed: processed {loop_size} windows")
        
        logger.info(f"Sliding window algorithm found {len(all_transfer_pairs)} transfer pairs")
        return all_transfer_pairs

    def _get_user_transactions_in_range(self, user_id: str, start_date_ts: int, end_date_ts: int) -> List[Transaction]:
        """Get uncategorized user transactions within a specific date range for transfer detection."""
        from utils.db_utils import list_user_transactions
        
        # Get only uncategorized transactions within the date range with pagination
        # This prevents detect from returning transactions that are already marked as transfers
        all_transactions = []
        last_evaluated_key = None
        consecutive_empty_batches = 0
        max_consecutive_empty_batches = 3  # Prevent infinite loops
        
        while True:
            batch_result, last_evaluated_key, _ = list_user_transactions(
                user_id=user_id,
                start_date_ts=start_date_ts,
                end_date_ts=end_date_ts,
                last_evaluated_key=last_evaluated_key,
                limit=1000,
                ignore_dup=True,  # Only consider non-duplicate transactions for transfer detection
                uncategorized_only=True  # Only get transactions without categories to avoid returning already marked transfers
            )
            
            all_transactions.extend(batch_result)
            
            # Debug logging for pagination behavior
            logger.debug(f"Pagination batch for user {user_id}: returned {len(batch_result)} items, "
                        f"has_last_evaluated_key={last_evaluated_key is not None}, "
                        f"total_so_far={len(all_transactions)}")
            
            if last_evaluated_key:
                logger.debug(f"LastEvaluatedKey present: {last_evaluated_key}")
            
            # Track consecutive empty batches to prevent infinite loops
            if len(batch_result) == 0:
                consecutive_empty_batches += 1
                logger.warning(f"Empty batch {consecutive_empty_batches}/{max_consecutive_empty_batches} for user {user_id} - "
                              f"DynamoDB returned LastEvaluatedKey={last_evaluated_key is not None} with 0 items")
                if consecutive_empty_batches >= max_consecutive_empty_batches:
                    logger.warning(f"Breaking pagination after {consecutive_empty_batches} consecutive empty batches "
                                  f"for user {user_id} - DynamoDB GSI pagination issue detected")
                    break
            else:
                consecutive_empty_batches = 0  # Reset counter when we get results
            
            # Normal termination condition
            if not last_evaluated_key:
                logger.info(f"Pagination complete for user {user_id} - no more LastEvaluatedKey")
                break
        
        logger.debug(f"Retrieved {len(all_transactions)} transactions for user {user_id} in range")
        return all_transactions

    def _get_batch_transactions(
        self,
        user_id: str,
        start_date_ts: int,
        end_date_ts: int
    ) -> List[Transaction]:
        """Get all uncategorized transactions for a specific date range batch."""
        batch_transactions = []
        last_evaluated_key = None
        consecutive_empty_batches = 0
        max_consecutive_empty_batches = 3  # Prevent infinite loops
        
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
            
            # Debug logging for uncategorized transactions
            logger.debug(f"Uncategorized batch for user {user_id}: returned {len(batch_result)} items, "
                        f"has_last_evaluated_key={last_evaluated_key is not None}, "
                        f"total_so_far={len(batch_transactions)}")
            
            # Track consecutive empty batches to prevent infinite loops
            if len(batch_result) == 0:
                consecutive_empty_batches += 1
                logger.warning(f"Empty uncategorized batch {consecutive_empty_batches}/{max_consecutive_empty_batches} for user {user_id} - "
                              f"DynamoDB returned LastEvaluatedKey={last_evaluated_key is not None} with 0 items")
                if consecutive_empty_batches >= max_consecutive_empty_batches:
                    logger.warning(f"Breaking uncategorized pagination after {consecutive_empty_batches} consecutive empty batches "
                                  f"for user {user_id} - DynamoDB GSI pagination issue detected")
                    break
            else:
                consecutive_empty_batches = 0  # Reset counter when we get results
            
            # Normal termination condition
            if not last_evaluated_key:
                logger.info(f"Uncategorized pagination complete for user {user_id} - no more LastEvaluatedKey")
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
    
    def _sliding_window_transfer_detection(
        self, 
        transactions: List[Transaction], 
        processed_tx_ids: Set[str]
    ) -> List[Tuple[Transaction, Transaction]]:
        """
        Simple sliding window transfer detection with minimal memory usage.
        
        Algorithm:
        1. Convert to minimal transaction objects for memory efficiency
        2. Sort by abs(amount) for efficient matching
        3. For each transaction, look at earlier ones where amount + earlier.amount < tolerance
        4. Early termination when amount difference is too large
        
        Args:
            transactions: List of transactions in current window
            processed_tx_ids: Set of already processed transaction IDs
            
        Returns:
            List of transfer pairs (outgoing, incoming)
        """
        # Convert to minimal objects for memory efficiency
        minimal_txs = []
        tx_lookup = {}  # Map minimal tx back to full transaction
        
        for tx in transactions:
            tx_id = str(tx.transaction_id)
            if tx_id in processed_tx_ids:
                continue
                
            minimal_tx = MinimalTransaction(
                transaction_id=tx_id,
                account_id=str(tx.account_id),
                amount=tx.amount,
                date=tx.date,
                abs_amount=abs(tx.amount)
            )
            minimal_txs.append(minimal_tx)
            tx_lookup[tx_id] = tx
        
        if len(minimal_txs) < 2:
            return []
        
        # Sort by abs(amount) for efficient matching
        minimal_txs.sort(key=lambda tx: tx.abs_amount)
        
        transfer_pairs = []
        matched_ids = set()
        tolerance = Decimal('0.01')
        max_date_diff_ms = 7 * 24 * 60 * 60 * 1000  # 7 days
        
        logger.debug(f"Processing {len(minimal_txs)} transactions in window")
        
        # For each transaction, look at earlier ones in the sorted list
        for i, tx in enumerate(minimal_txs):
            if tx.transaction_id in matched_ids:
                continue
            
            # Look at earlier transactions in reverse order (closest amounts first)
            for j in range(i - 1, -1, -1):
                earlier_tx = minimal_txs[j]
                
                if earlier_tx.transaction_id in matched_ids:
                    continue
                
                # Early termination: if amount difference is too large, break
                # Since list is sorted, all earlier transactions will have even larger differences
                amount_diff = abs(tx.abs_amount - earlier_tx.abs_amount)
                if amount_diff > tolerance:
                    break  # No point checking further - all earlier amounts are smaller
                
                # Check if amounts sum to near zero (transfer condition)
                amount_sum = abs(tx.amount + earlier_tx.amount)
                if amount_sum > tolerance:
                    continue
                
                # Must be different accounts
                if tx.account_id == earlier_tx.account_id:
                    continue
                
                # Must be within date window
                date_diff = abs(tx.date - earlier_tx.date)
                if date_diff > max_date_diff_ms:
                    continue
                
                # Must have opposite signs
                if (tx.amount > 0 and earlier_tx.amount > 0) or (tx.amount < 0 and earlier_tx.amount < 0):
                    continue
                
                # Found a match!
                tx_full = tx_lookup[tx.transaction_id]
                earlier_tx_full = tx_lookup[earlier_tx.transaction_id]
                
                # Determine outgoing vs incoming
                if tx.amount < 0:
                    transfer_pairs.append((tx_full, earlier_tx_full))  # (outgoing, incoming)
                else:
                    transfer_pairs.append((earlier_tx_full, tx_full))  # (outgoing, incoming)
                
                # Mark both as matched
                matched_ids.add(tx.transaction_id)
                matched_ids.add(earlier_tx.transaction_id)
                processed_tx_ids.add(tx.transaction_id)
                processed_tx_ids.add(earlier_tx.transaction_id)
                
                logger.debug(f"Matched transfer: {tx.transaction_id} <-> {earlier_tx.transaction_id}")
                break  # Found match for this transaction, move to next
        
        logger.debug(f"Window found {len(transfer_pairs)} transfer pairs")
        return transfer_pairs

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
