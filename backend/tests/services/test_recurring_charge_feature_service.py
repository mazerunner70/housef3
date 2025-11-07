"""
Unit tests for RecurringChargeFeatureService.

Tests feature extraction for temporal, amount, and description features.
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from services.recurring_charge_feature_service import (
    RecurringChargeFeatureService,
    FEATURE_VECTOR_SIZE,
    TEMPORAL_FEATURE_SIZE,
    AMOUNT_FEATURE_SIZE,
    DESCRIPTION_FEATURE_SIZE
)
from models.transaction import Transaction


class TestRecurringChargeFeatureService:
    """Test suite for RecurringChargeFeatureService."""
    
    @pytest.fixture
    def feature_service(self):
        """Create feature service instance."""
        return RecurringChargeFeatureService(country_code='US')
    
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
    
    @pytest.fixture
    def sample_transactions(self):
        """Create a list of sample transactions."""
        transactions = []
        
        for i in range(12):  # 12 monthly transactions
            month = i + 1
            date = datetime(2024, month, 15, tzinfo=timezone.utc)
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
    
    def test_extract_temporal_features_size(self, feature_service, sample_transaction):
        """Test that temporal features have correct size."""
        features = feature_service.extract_temporal_features(sample_transaction)
        
        assert len(features) == TEMPORAL_FEATURE_SIZE
        assert all(isinstance(f, float) for f in features)
    
    def test_extract_temporal_features_circular_encoding(self, feature_service):
        """Test circular encoding for day of week."""
        # Create transactions on Monday (0) and Sunday (6)
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
        
        monday_features = feature_service.extract_temporal_features(monday_txn)
        sunday_features = feature_service.extract_temporal_features(sunday_txn)
        
        # Day of week features are first two (sin, cos)
        monday_sin, monday_cos = monday_features[0], monday_features[1]
        sunday_sin, sunday_cos = sunday_features[0], sunday_features[1]
        
        # Monday and Sunday should be close in circular space
        # Calculate circular distance
        distance = np.sqrt((monday_sin - sunday_sin)**2 + (monday_cos - sunday_cos)**2)
        
        # Distance should be small (they're adjacent in circular space)
        assert distance < 1.0
    
    def test_extract_temporal_features_working_day(self, feature_service):
        """Test working day detection."""
        # Monday (working day)
        monday_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 4, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        # Saturday (weekend)
        saturday_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 2, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        monday_features = feature_service.extract_temporal_features(monday_txn)
        saturday_features = feature_service.extract_temporal_features(saturday_txn)
        
        # is_working_day is index 8
        assert monday_features[8] == 1.0  # Working day
        assert saturday_features[8] == 0.0  # Not working day
        
        # is_weekend is index 13
        assert monday_features[13] == 0.0  # Not weekend
        assert saturday_features[13] == 1.0  # Weekend
    
    def test_extract_temporal_features_first_last_day(self, feature_service):
        """Test first and last day of month detection."""
        # First day of month
        first_day_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 1, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        # Last day of month (March has 31 days)
        last_day_txn = Transaction(
            userId="user123",
            fileId=uuid.uuid4(),
            transactionId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime(2024, 3, 31, tzinfo=timezone.utc).timestamp() * 1000),
            description="TEST",
            amount=Decimal("10.00")
        )
        
        first_features = feature_service.extract_temporal_features(first_day_txn)
        last_features = feature_service.extract_temporal_features(last_day_txn)
        
        # is_first_day is index 14
        assert first_features[14] == 1.0
        assert last_features[14] == 0.0
        
        # is_last_day is index 15
        assert first_features[15] == 0.0
        assert last_features[15] == 1.0
    
    def test_extract_amount_features_batch(self, feature_service, sample_transactions):
        """Test amount feature extraction."""
        amount_features = feature_service.extract_amount_features_batch(sample_transactions)
        
        assert amount_features.shape == (len(sample_transactions), AMOUNT_FEATURE_SIZE)
        assert np.all((amount_features >= 0) & (amount_features <= 1))  # Normalized
    
    def test_extract_amount_features_normalization(self, feature_service):
        """Test amount feature normalization."""
        # Create transactions with varying amounts
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
        
        amount_features = feature_service.extract_amount_features_batch(transactions)
        
        # Should be normalized to [0, 1]
        assert amount_features.min() >= 0.0
        assert amount_features.max() <= 1.0
        
        # Smallest amount should have smallest feature value
        assert amount_features[0] < amount_features[-1]
    
    def test_extract_description_features_batch(self, feature_service, sample_transactions):
        """Test description feature extraction."""
        desc_features, vectorizer = feature_service.extract_description_features_batch(sample_transactions)
        
        assert desc_features.shape == (len(sample_transactions), DESCRIPTION_FEATURE_SIZE)
        assert vectorizer is not None
    
    def test_extract_description_features_similar_descriptions(self, feature_service):
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
        
        desc_features, _ = feature_service.extract_description_features_batch(transactions)
        
        # Netflix transactions should be more similar to each other than to Amazon
        netflix1 = desc_features[0]
        netflix2 = desc_features[1]
        amazon = desc_features[2]
        
        # Cosine similarity
        netflix_similarity = np.dot(netflix1, netflix2) / (np.linalg.norm(netflix1) * np.linalg.norm(netflix2) + 1e-10)
        amazon_similarity = np.dot(netflix1, amazon) / (np.linalg.norm(netflix1) * np.linalg.norm(amazon) + 1e-10)
        
        assert netflix_similarity > amazon_similarity
    
    def test_extract_features_batch_complete(self, feature_service, sample_transactions):
        """Test complete feature extraction."""
        feature_matrix, vectorizer = feature_service.extract_features_batch(sample_transactions)
        
        assert feature_matrix.shape == (len(sample_transactions), FEATURE_VECTOR_SIZE)
        assert vectorizer is not None
        
        # Check that all features are numeric
        assert not np.any(np.isnan(feature_matrix))
        assert not np.any(np.isinf(feature_matrix))
    
    def test_extract_features_batch_empty(self, feature_service):
        """Test feature extraction with empty transaction list."""
        feature_matrix, vectorizer = feature_service.extract_features_batch([])
        
        assert feature_matrix.shape == (0, FEATURE_VECTOR_SIZE)
        assert vectorizer is None
    
    def test_construct_feature_vector(self, feature_service):
        """Test feature vector construction."""
        temporal = [0.5] * TEMPORAL_FEATURE_SIZE
        amount = 0.7
        description = [0.3] * DESCRIPTION_FEATURE_SIZE
        
        vector = feature_service.construct_feature_vector(temporal, amount, description)
        
        assert len(vector) == FEATURE_VECTOR_SIZE
        assert vector[:TEMPORAL_FEATURE_SIZE] == temporal
        assert vector[TEMPORAL_FEATURE_SIZE] == amount
        assert vector[TEMPORAL_FEATURE_SIZE + 1:] == description
    
    def test_construct_feature_vector_invalid_size(self, feature_service):
        """Test feature vector construction with invalid sizes."""
        with pytest.raises(ValueError):
            feature_service.construct_feature_vector(
                [0.5] * 10,  # Wrong size
                0.7,
                [0.3] * DESCRIPTION_FEATURE_SIZE
            )
        
        with pytest.raises(ValueError):
            feature_service.construct_feature_vector(
                [0.5] * TEMPORAL_FEATURE_SIZE,
                0.7,
                [0.3] * 10  # Wrong size
            )
    
    def test_is_first_working_day(self, feature_service):
        """Test first working day detection."""
        # March 1, 2024 is a Friday (first working day)
        dt = datetime(2024, 3, 1, tzinfo=timezone.utc)
        assert feature_service._is_first_working_day(dt) is True
        
        # March 2, 2024 is a Saturday (not first working day)
        dt = datetime(2024, 3, 2, tzinfo=timezone.utc)
        assert feature_service._is_first_working_day(dt) is False
    
    def test_is_last_working_day(self, feature_service):
        """Test last working day detection."""
        # March 29, 2024 is a Friday (last working day of March)
        dt = datetime(2024, 3, 29, tzinfo=timezone.utc)
        assert feature_service._is_last_working_day(dt) is True
        
        # March 28, 2024 is a Thursday (not last working day)
        dt = datetime(2024, 3, 28, tzinfo=timezone.utc)
        assert feature_service._is_last_working_day(dt) is False
    
    def test_is_first_weekday_of_month(self, feature_service):
        """Test first weekday of month detection."""
        # March 1, 2024 is the first Friday of March
        dt = datetime(2024, 3, 1, tzinfo=timezone.utc)
        assert feature_service._is_first_weekday_of_month(dt) is True
        
        # March 8, 2024 is the second Friday of March
        dt = datetime(2024, 3, 8, tzinfo=timezone.utc)
        assert feature_service._is_first_weekday_of_month(dt) is False
    
    def test_is_last_weekday_of_month(self, feature_service):
        """Test last weekday of month detection."""
        # March 29, 2024 is the last Friday of March
        dt = datetime(2024, 3, 29, tzinfo=timezone.utc)
        assert feature_service._is_last_weekday_of_month(dt) is True
        
        # March 22, 2024 is a Friday but not the last one
        dt = datetime(2024, 3, 22, tzinfo=timezone.utc)
        assert feature_service._is_last_weekday_of_month(dt) is False

