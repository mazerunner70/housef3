"""
Unit tests for TransferDetectionService sliding window algorithm.

Tests the optimized transfer detection algorithm that uses:
1. Sliding window with 3-day overlap
2. Minimal memory usage with MinimalTransaction objects
3. Amount-sorted matching with early termination
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
from unittest.mock import Mock, patch
import uuid

from services.transfer_detection_service import TransferDetectionService, MinimalTransaction
from models.transaction import Transaction


class TestTransferDetectionService:
    """Test cases for the sliding window transfer detection algorithm."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = TransferDetectionService()
        
    def create_test_transaction(
        self, 
        amount: Decimal, 
        date: datetime, 
        account_id: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Transaction:
        """Helper to create test transactions."""
        if transaction_id is None:
            transaction_id = str(uuid.uuid4())
        if account_id is None:
            account_id = str(uuid.uuid4())
            
        tx = Mock(spec=Transaction)
        tx.transaction_id = transaction_id
        tx.account_id = account_id
        tx.amount = amount
        tx.date = int(date.timestamp() * 1000)  # Convert to milliseconds
        tx.user_id = "test-user"
        return tx

    def test_minimal_transaction_creation(self):
        """Test MinimalTransaction creation and properties."""
        minimal_tx = MinimalTransaction(
            transaction_id="tx-123",
            account_id="acc-456", 
            amount=Decimal("100.50"),
            date=1640995200000,  # 2022-01-01
            abs_amount=Decimal("100.50")
        )
        
        assert minimal_tx.transaction_id == "tx-123"
        assert minimal_tx.account_id == "acc-456"
        assert minimal_tx.amount == Decimal("100.50")
        assert minimal_tx.abs_amount == Decimal("100.50")

    def test_simple_transfer_pair_detection(self):
        """Test detection of a simple transfer pair."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Create a transfer pair: $100 out of account A, $100 into account B
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a",
            transaction_id="tx-out"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"), 
            date=base_date + timedelta(hours=1),
            account_id="account-b",
            transaction_id="tx-in"
        )
        
        transactions = [tx_out, tx_in]
        processed_ids = set()
        
        # Test the sliding window detection
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 1
        outgoing, incoming = pairs[0]
        assert outgoing.amount == Decimal("-100.00")
        assert incoming.amount == Decimal("100.00")
        assert outgoing.account_id != incoming.account_id

    def test_no_matches_same_account(self):
        """Test that transactions in the same account don't match."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        tx1 = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="same-account"
        )
        tx2 = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(hours=1), 
            account_id="same-account"  # Same account
        )
        
        transactions = [tx1, tx2]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0

    def test_no_matches_same_sign(self):
        """Test that transactions with the same sign don't match."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        tx1 = self.create_test_transaction(
            amount=Decimal("100.00"),  # Both positive
            date=base_date,
            account_id="account-a"
        )
        tx2 = self.create_test_transaction(
            amount=Decimal("100.00"),  # Both positive
            date=base_date + timedelta(hours=1),
            account_id="account-b"
        )
        
        transactions = [tx1, tx2]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0

    def test_amount_tolerance_matching(self):
        """Test that amounts within tolerance are matched."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Amounts differ by $0.005 (within $0.01 tolerance)
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.005"),
            date=base_date,
            account_id="account-a"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.000"),
            date=base_date + timedelta(hours=1),
            account_id="account-b"
        )
        
        transactions = [tx_out, tx_in]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 1

    def test_amount_tolerance_exceeded(self):
        """Test that amounts outside tolerance are not matched."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Amounts differ by $0.02 (exceeds $0.01 tolerance)
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.02"),
            date=base_date,
            account_id="account-a"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(hours=1),
            account_id="account-b"
        )
        
        transactions = [tx_out, tx_in]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0

    def test_date_window_within_limit(self):
        """Test that transactions within 7-day window are matched."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(days=6),  # 6 days later (within 7-day limit)
            account_id="account-b"
        )
        
        transactions = [tx_out, tx_in]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 1

    def test_date_window_exceeded(self):
        """Test that transactions outside 7-day window are not matched."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(days=8),  # 8 days later (exceeds 7-day limit)
            account_id="account-b"
        )
        
        transactions = [tx_out, tx_in]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0

    def test_multiple_transfer_pairs(self):
        """Test detection of multiple independent transfer pairs."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # First transfer pair: $100
        tx1_out = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a",
            transaction_id="tx1-out"
        )
        tx1_in = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(hours=1),
            account_id="account-b", 
            transaction_id="tx1-in"
        )
        
        # Second transfer pair: $50
        tx2_out = self.create_test_transaction(
            amount=Decimal("-50.00"),
            date=base_date + timedelta(hours=2),
            account_id="account-c",
            transaction_id="tx2-out"
        )
        tx2_in = self.create_test_transaction(
            amount=Decimal("50.00"),
            date=base_date + timedelta(hours=3),
            account_id="account-d",
            transaction_id="tx2-in"
        )
        
        transactions = [tx1_out, tx1_in, tx2_out, tx2_in]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 2
        
        # Verify both pairs are detected
        amounts = [(pair[0].amount, pair[1].amount) for pair in pairs]
        assert (Decimal("-100.00"), Decimal("100.00")) in amounts
        assert (Decimal("-50.00"), Decimal("50.00")) in amounts

    def test_amount_sorting_optimization(self):
        """Test that amount sorting enables early termination."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Create transactions with very different amounts
        tx_small = self.create_test_transaction(
            amount=Decimal("-1.00"),
            date=base_date,
            account_id="account-a"
        )
        tx_large = self.create_test_transaction(
            amount=Decimal("1000.00"),  # Very different amount
            date=base_date + timedelta(hours=1),
            account_id="account-b"
        )
        tx_match = self.create_test_transaction(
            amount=Decimal("1.00"),  # Matches tx_small
            date=base_date + timedelta(hours=2),
            account_id="account-c"
        )
        
        transactions = [tx_small, tx_large, tx_match]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        # Should find the matching pair and ignore the large amount
        assert len(pairs) == 1
        outgoing, incoming = pairs[0]
        assert abs(outgoing.amount) == Decimal("1.00")
        assert abs(incoming.amount) == Decimal("1.00")

    def test_processed_ids_are_respected(self):
        """Test that already processed transaction IDs are skipped."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a",
            transaction_id="already-processed"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(hours=1),
            account_id="account-b"
        )
        
        transactions = [tx_out, tx_in]
        processed_ids = {"already-processed"}  # tx_out is already processed
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0  # Should not match because tx_out is already processed

    def test_empty_transaction_list(self):
        """Test handling of empty transaction list."""
        transactions = []
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0

    def test_single_transaction(self):
        """Test handling of single transaction."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        tx = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a"
        )
        
        transactions = [tx]
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 0

    @patch('services.transfer_detection_service.TransferDetectionService._get_user_transactions_in_range')
    def test_sliding_window_date_range_integration(self, mock_get_transactions):
        """Test the full sliding window algorithm with date range."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Mock transactions returned by database
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.00"),
            date=base_date,
            account_id="account-a"
        )
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"),
            date=base_date + timedelta(hours=1),
            account_id="account-b"
        )
        
        mock_get_transactions.return_value = [tx_out, tx_in]
        
        # Test the full date range method
        start_ts = int(base_date.timestamp() * 1000)
        end_ts = int((base_date + timedelta(days=1)).timestamp() * 1000)
        
        pairs = self.service._detect_transfers_in_date_range("test-user", start_ts, end_ts)
        
        assert len(pairs) == 1
        assert mock_get_transactions.called

    def test_transfer_pair_ordering(self):
        """Test that transfer pairs are correctly ordered as (outgoing, incoming)."""
        base_date = datetime(2024, 1, 1, 12, 0, 0)
        
        # Create transactions in different order
        tx_in = self.create_test_transaction(
            amount=Decimal("100.00"),  # Incoming first
            date=base_date,
            account_id="account-b"
        )
        tx_out = self.create_test_transaction(
            amount=Decimal("-100.00"),  # Outgoing second
            date=base_date + timedelta(hours=1),
            account_id="account-a"
        )
        
        transactions = [tx_in, tx_out]  # Incoming first in list
        processed_ids = set()
        
        pairs = self.service._sliding_window_transfer_detection(transactions, processed_ids)
        
        assert len(pairs) == 1
        outgoing, incoming = pairs[0]
        
        # Should always be ordered as (outgoing, incoming) regardless of input order
        assert outgoing.amount < 0  # Outgoing is negative
        assert incoming.amount > 0  # Incoming is positive

    def test_pagination_infinite_loop_prevention(self):
        """Test that pagination loops are prevented when DynamoDB returns LastEvaluatedKey with 0 items."""
        from unittest.mock import patch, MagicMock
        
        # Mock list_user_transactions to simulate the infinite loop scenario
        # Return LastEvaluatedKey with 0 items for several iterations
        mock_responses = [
            ([], {"some": "key"}, 0),  # Empty result but with LastEvaluatedKey
            ([], {"some": "key2"}, 0),  # Empty result but with LastEvaluatedKey
            ([], {"some": "key3"}, 0),  # Empty result but with LastEvaluatedKey
            ([], {"some": "key4"}, 0),  # This should trigger the infinite loop prevention
        ]
        
        with patch('services.transfer_detection_service.list_user_transactions') as mock_list:
            mock_list.side_effect = mock_responses
            
            # This should not hang indefinitely
            result = self.service._get_user_transactions_in_range(
                user_id="test-user",
                start_date_ts=1000000000000,
                end_date_ts=1000000001000
            )
            
            # Should return empty list and not hang
            assert result == []
            
            # Should have called list_user_transactions exactly 3 times before breaking
            assert mock_list.call_count == 3
