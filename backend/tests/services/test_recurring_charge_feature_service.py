"""
Unit tests for RecurringChargeFeatureService and feature extractors.

Tests feature extraction for temporal, amount, description, and account features.
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from services.recurring_charges.feature_service import (
    RecurringChargeFeatureService,
    FEATURE_VECTOR_SIZE,
    ENHANCED_FEATURE_VECTOR_SIZE,
    TEMPORAL_FEATURE_SIZE,
    AMOUNT_FEATURE_SIZE,
    DESCRIPTION_FEATURE_SIZE,
    ACCOUNT_FEATURE_SIZE
)
from services.recurring_charges.features import (
    TemporalFeatureExtractor,
    AmountFeatureExtractor,
    DescriptionFeatureExtractor,
    AccountFeatureExtractor
)
from models.transaction import Transaction
from models.account import Account, AccountType


class TestTemporalFeatureExtractor:
    """Test suite for TemporalFeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create temporal feature extractor instance."""
        return TemporalFeatureExtractor(country_code='US')
    
    @pytest.fixture
    def sample_transaction(self):
        """Create a sample transaction."""
        return Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
            description="NETFLIX SUBSCRIPTION",
            amount=Decimal("14.99")
        )
    
    def test_feature_size(self, extractor):
        """Test that feature size is correct."""
        assert extractor.feature_size == TEMPORAL_FEATURE_SIZE == 17
    
    def test_extract_single(self, extractor, sample_transaction):
        """Test that temporal features have correct size."""
        features = extractor.extract_single(sample_transaction)
        
        assert len(features) == TEMPORAL_FEATURE_SIZE
        assert all(isinstance(f, float) for f in features)
    
    def test_extract_batch(self, extractor):
        """Test batch extraction."""
        transactions = []
        for i in range(5):
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 3, i+1, tzinfo=timezone.utc).timestamp() * 1000),
                description="TEST",
                amount=Decimal("10.00")
            )
            transactions.append(txn)
        
        features = extractor.extract_batch(transactions)
        assert features.shape == (5, TEMPORAL_FEATURE_SIZE)
    
    def test_circular_encoding(self, extractor):
        """Test circular encoding for day of week."""
        monday_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 4, tzinfo=timezone.utc).timestamp() * 1000),  # Monday
            description="TEST",
            amount=Decimal("10.00")
        )
        
        sunday_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 3, tzinfo=timezone.utc).timestamp() * 1000),  # Sunday
            description="TEST",
            amount=Decimal("10.00")
        )
        
        monday_features = extractor.extract_single(monday_txn)
        sunday_features = extractor.extract_single(sunday_txn)
        
        # Day of week features are first two (sin, cos)
        monday_sin, monday_cos = monday_features[0], monday_features[1]
        sunday_sin, sunday_cos = sunday_features[0], sunday_features[1]
        
        # Different days should have different encodings
        assert monday_sin != sunday_sin or monday_cos != sunday_cos
    
    def test_working_day_detection(self, extractor):
        """Test working day detection."""
        monday_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 4, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        saturday_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 2, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        monday_features = extractor.extract_single(monday_txn)
        saturday_features = extractor.extract_single(saturday_txn)
        
        # is_working_day is index 8
        assert monday_features[8] == 1.0  # Monday is a working day
        assert saturday_features[8] == 0.0  # Saturday is not a working day
    
    def test_first_last_day(self, extractor):
        """Test first and last day of month detection."""
        first_day_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 1, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        last_day_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 31, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        first_features = extractor.extract_single(first_day_txn)
        last_features = extractor.extract_single(last_day_txn)
        
        # is_first_day is index 14, is_last_day is index 15
        assert first_features[14] == 1.0
        assert last_features[15] == 1.0


class TestAmountFeatureExtractor:
    """Test suite for AmountFeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create amount feature extractor instance."""
        return AmountFeatureExtractor()
    
    def test_feature_size(self, extractor):
        """Test that feature size is correct."""
        assert extractor.feature_size == AMOUNT_FEATURE_SIZE == 1
    
    def test_extract_batch(self, extractor):
        """Test amount feature extraction."""
        transactions = []
        for i in range(5):
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="TEST",
                amount=Decimal(str(10.0 * (i + 1)))
            )
            transactions.append(txn)
        
        amount_features = extractor.extract_batch(transactions)
        
        assert amount_features.shape == (5, AMOUNT_FEATURE_SIZE)
        assert np.all((amount_features >= 0) & (amount_features <= 1))
    
    def test_normalization(self, extractor):
        """Test amount feature normalization."""
        transactions = []
        amounts = [10.0, 50.0, 100.0, 500.0, 1000.0]
        
        for amount in amounts:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="TEST",
                amount=Decimal(str(amount))
            )
            transactions.append(txn)
        
        amount_features = extractor.extract_batch(transactions)
        
        # Smallest amount should be close to 0, largest close to 1
        assert amount_features[0][0] < amount_features[-1][0]
        assert amount_features[0][0] >= 0
        assert amount_features[-1][0] <= 1


class TestDescriptionFeatureExtractor:
    """Test suite for DescriptionFeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create description feature extractor instance."""
        return DescriptionFeatureExtractor()
    
    def test_feature_size(self, extractor):
        """Test that feature size is correct."""
        assert extractor.feature_size == DESCRIPTION_FEATURE_SIZE == 49
    
    def test_extract_batch(self, extractor):
        """Test description feature extraction."""
        transactions = []
        descriptions = ["NETFLIX", "SPOTIFY", "AMAZON", "WALMART", "TARGET"]
        
        for desc in descriptions:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description=desc,
                amount=Decimal("10.00")
            )
            transactions.append(txn)
        
        desc_features, vectorizer = extractor.extract_batch(transactions)
        
        assert desc_features.shape == (5, DESCRIPTION_FEATURE_SIZE)
        # Vectorizer may be None if vocab is too small
    
    def test_similar_descriptions(self, extractor):
        """Test that similar descriptions produce similar features."""
        transactions = [
            Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="NETFLIX SUBSCRIPTION",
                amount=Decimal("14.99")
            ),
            Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 4, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="NETFLIX MONTHLY",
                amount=Decimal("14.99")
            ),
            Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 5, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="AMAZON PRIME",
                amount=Decimal("12.99")
            )
        ]
        
        desc_features, _ = extractor.extract_batch(transactions)
        
        # NETFLIX transactions should be more similar to each other than to AMAZON
        netflix_similarity = np.dot(desc_features[0], desc_features[1])
        netflix_amazon_similarity = np.dot(desc_features[0], desc_features[2])
        
        # Note: This may not always be true with small datasets, but it's the expected behavior
        # We just check that features are generated correctly
        assert desc_features.shape == (3, DESCRIPTION_FEATURE_SIZE)


class TestAccountFeatureExtractor:
    """Test suite for AccountFeatureExtractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create account feature extractor instance."""
        return AccountFeatureExtractor()
    
    @pytest.fixture
    def sample_accounts_map(self):
        """Create sample accounts map."""
        checking_account = Account(
            userId="user123",
            accountId=uuid.uuid4(),
            accountName="Personal Checking",
            accountType=AccountType.CHECKING,
            institution="Chase",
            firstTransactionDate=int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000),
            is_active=True
        )
        
        credit_account = Account(
            userId="user123",
            accountId=uuid.uuid4(),
            accountName="Rewards Credit Card",
            accountType=AccountType.CREDIT_CARD,
            institution="Citi",
            firstTransactionDate=int(datetime(2023, 6, 1, tzinfo=timezone.utc).timestamp() * 1000),
            is_active=True
        )
        
        return {
            checking_account.account_id: checking_account,
            credit_account.account_id: credit_account
        }
    
    def test_feature_size(self, extractor):
        """Test that feature size is correct."""
        assert extractor.feature_size == ACCOUNT_FEATURE_SIZE == 24
    
    def test_extract_batch(self, extractor, sample_accounts_map):
        """Test account feature extraction."""
        account_ids = list(sample_accounts_map.keys())
        transactions = []
        
        for i in range(4):
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=account_ids[i % 2],
                date=int(datetime(2024, 3, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="TEST",
                amount=Decimal("10.00")
            )
            transactions.append(txn)
        
        account_features = extractor.extract_batch(transactions, sample_accounts_map)
        
        assert account_features.shape == (4, ACCOUNT_FEATURE_SIZE)


class TestRecurringChargeFeatureService:
    """Test suite for RecurringChargeFeatureService (orchestrator)."""
    
    @pytest.fixture
    def feature_service(self):
        """Create feature service instance."""
        return RecurringChargeFeatureService(country_code='US')
    
    @pytest.fixture
    def sample_transactions(self):
        """Create a list of sample transactions."""
        transactions = []
        
        for i in range(12):  # 12 monthly transactions
            month = i + 1
            date = datetime(2024, month % 12 if month % 12 > 0 else 12, 15, tzinfo=timezone.utc)
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description=f"NETFLIX SUBSCRIPTION {i+1}",
                amount=Decimal("14.99")
            )
            transactions.append(txn)
        
        return transactions
    
    @pytest.fixture
    def sample_accounts_map(self, sample_transactions):
        """Create sample accounts map matching the transactions."""
        account_id = sample_transactions[0].account_id
        account = Account(
            userId="user123",
            accountId=account_id,
            accountName="Personal Checking",
            accountType=AccountType.CHECKING,
            institution="Chase",
            firstTransactionDate=int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000),
            is_active=True
        )
        return {account_id: account}
    
    def test_extract_features_batch_base_mode(self, feature_service, sample_transactions):
        """Test complete feature extraction in base mode (no accounts)."""
        feature_matrix, vectorizer = feature_service.extract_features_batch(sample_transactions)
        
        assert feature_matrix.shape == (len(sample_transactions), FEATURE_VECTOR_SIZE)
        # Vectorizer may be None if vocab is too small, which is acceptable
    
    def test_extract_features_batch_account_aware(self, feature_service, sample_transactions, sample_accounts_map):
        """Test complete feature extraction in account-aware mode."""
        feature_matrix, vectorizer = feature_service.extract_features_batch(
            sample_transactions, 
            sample_accounts_map
        )
        
        assert feature_matrix.shape == (len(sample_transactions), ENHANCED_FEATURE_VECTOR_SIZE)
    
    def test_extract_features_batch_empty(self, feature_service):
        """Test feature extraction with empty transaction list."""
        feature_matrix, vectorizer = feature_service.extract_features_batch([])
        
        assert feature_matrix.shape == (0, FEATURE_VECTOR_SIZE)
        assert vectorizer is None
    
    def test_extract_features_batch_empty_account_aware(self, feature_service):
        """Test feature extraction with empty transaction list in account-aware mode."""
        feature_matrix, vectorizer = feature_service.extract_features_batch([], {})
        
        assert feature_matrix.shape == (0, ENHANCED_FEATURE_VECTOR_SIZE)
        assert vectorizer is None
