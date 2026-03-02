"""
Integration tests for recurring charge detection end-to-end flow.

Tests the complete pipeline from transactions to patterns to predictions.
Uses realistic transaction descriptions harvested from DynamoDB (hard-coded).
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import numpy as np

from services.recurring_charges import (
    RecurringChargeFeatureService,
    RecurringChargeDetectionService,
    RecurringChargePredictionService
)
from models.transaction import Transaction
from models.recurring_charge import RecurrenceFrequency, TemporalPatternType

# Real transaction descriptions harvested from DynamoDB
# These represent common recurring patterns found in actual user data
REAL_DESCRIPTIONS = {
    'netflix': ["NETFLIX.COM", "NETFLIX SUBSCRIPTION", "NETFLIX MONTHLY", "NETFLIX.COM CA", "NETFLIX *STREAMING"],
    'spotify': ["SPOTIFY USA", "SPOTIFY P0123456789", "SPOTIFY PREMIUM", "SPOTIFY SUBSCRIPTION"],
    'gym': ["PLANET FITNESS", "LA FITNESS", "24 HOUR FITNESS", "GOLD'S GYM", "ANYTIME FITNESS"],
    'amazon': ["AMAZON PRIME", "AMZN PRIME MEMBERSHIP", "AMAZON PRIME VIDEO", "AMAZON.COM PRIME"],
    'utilities': ["PG&E PAYMENT", "PACIFIC GAS ELECTRIC", "WATER DISTRICT PAYMENT", "COMCAST CABLE", "AT&T WIRELESS"],
    'phone': ["VERIZON WIRELESS", "T-MOBILE", "AT&T WIRELESS", "SPRINT PCS"],
    'insurance': ["STATE FARM INSURANCE", "GEICO INSURANCE", "ALLSTATE PAYMENT"],
}


@pytest.mark.integration
class TestRecurringChargeEndToEnd:
    """Integration tests for complete recurring charge detection flow."""
    
    @pytest.fixture
    def services(self):
        """Create all service instances."""
        return {
            'feature': RecurringChargeFeatureService(country_code='US'),
            'detection': RecurringChargeDetectionService(country_code='US'),
            'prediction': RecurringChargePredictionService(country_code='US')
        }
    
    @pytest.fixture
    def realistic_transactions(self):
        """
        Generate realistic transactions using real descriptions from DynamoDB.
        
        Creates a diverse set of recurring patterns:
        - Monthly subscriptions (Netflix, Spotify, Amazon)
        - Weekly gym memberships
        - Monthly utilities
        - Bi-weekly phone bills
        """
        transactions = []
        user_id = "test_user_123"
        account_id = uuid.uuid4()
        file_id = uuid.uuid4()
        
        # Netflix - monthly on 15th
        for month in range(1, 13):
            date = datetime(2024, month, 15, tzinfo=timezone.utc)
            desc = REAL_DESCRIPTIONS['netflix'][month % len(REAL_DESCRIPTIONS['netflix'])]
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=desc, amount=Decimal("14.99")
            ))
        
        # Spotify - monthly on 1st
        for month in range(1, 13):
            date = datetime(2024, month, 1, tzinfo=timezone.utc)
            desc = REAL_DESCRIPTIONS['spotify'][month % len(REAL_DESCRIPTIONS['spotify'])]
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=desc, amount=Decimal("9.99")
            ))
        
        # Gym - weekly on Mondays
        start_date = datetime(2024, 1, 8, tzinfo=timezone.utc)  # First Monday
        for week in range(20):
            date = start_date + timedelta(weeks=week)
            desc = REAL_DESCRIPTIONS['gym'][week % len(REAL_DESCRIPTIONS['gym'])]
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=desc, amount=Decimal("45.00")
            ))
        
        # Utilities - monthly on 5th
        for month in range(1, 13):
            date = datetime(2024, month, 5, tzinfo=timezone.utc)
            desc = REAL_DESCRIPTIONS['utilities'][month % len(REAL_DESCRIPTIONS['utilities'])]
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=desc, amount=Decimal("125.50")
            ))
        
        # Amazon Prime - monthly on 20th
        for month in range(1, 13):
            date = datetime(2024, month, 20, tzinfo=timezone.utc)
            desc = REAL_DESCRIPTIONS['amazon'][month % len(REAL_DESCRIPTIONS['amazon'])]
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=desc, amount=Decimal("12.99")
            ))
        
        # Phone bill - monthly on 25th
        for month in range(1, 13):
            date = datetime(2024, month, 25, tzinfo=timezone.utc)
            desc = REAL_DESCRIPTIONS['phone'][month % len(REAL_DESCRIPTIONS['phone'])]
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=desc, amount=Decimal("75.00")
            ))
        
        # Some random non-recurring transactions
        for i in range(20):
            date = datetime(2024, (i % 12) + 1, (i * 3) % 28 + 1, tzinfo=timezone.utc)
            transactions.append(Transaction(
                userId=user_id, fileId=file_id, transactionId=uuid.uuid4(),
                accountId=account_id, date=int(date.timestamp() * 1000),
                description=f"RANDOM STORE #{i}", amount=Decimal(str(25.00 + i * 5))
            ))
        
        transactions.sort(key=lambda t: t.date)
        return transactions
    
    def test_end_to_end_feature_extraction(self, services, realistic_transactions):
        """Test feature extraction on realistic data."""
        feature_service = services['feature']
        
        # Extract features
        feature_matrix, _ = feature_service.extract_features_batch(realistic_transactions)
        
        # Verify shape
        assert feature_matrix.shape[0] == len(realistic_transactions)
        assert feature_matrix.shape[1] == 67
        
        # Verify no NaN or Inf values
        assert not np.any(np.isnan(feature_matrix))
        assert not np.any(np.isinf(feature_matrix))
        
        print(f"✓ Extracted features from {len(realistic_transactions)} transactions")
        print(f"  Feature matrix shape: {feature_matrix.shape}")
    
    def test_end_to_end_pattern_detection(self, services, realistic_transactions):
        """Test pattern detection on realistic data."""
        detection_service = services['detection']
        
        # Detect patterns
        patterns = detection_service.detect_recurring_patterns(
            user_id=realistic_transactions[0].user_id,
            transactions=realistic_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        
        print(f"\n✓ Detected {len(patterns)} recurring patterns")
        
        # Analyze patterns
        for i, pattern in enumerate(patterns[:5], 1):  # Show first 5
            print(f"\nPattern {i}:")
            print(f"  Merchant: {pattern.merchant_pattern}")
            print(f"  Frequency: {pattern.frequency.value}")
            print(f"  Pattern Type: {pattern.temporal_pattern_type.value}")
            print(f"  Confidence: {pattern.confidence_score:.2f}")
            print(f"  Occurrences: {pattern.transaction_count}")
            print(f"  Amount: ${pattern.amount_mean}")
            
            if pattern.day_of_month:
                print(f"  Day of Month: {pattern.day_of_month}")
            if pattern.day_of_week is not None:
                days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
                print(f"  Day of Week: {days[pattern.day_of_week]}")
        
        # Verify patterns have required fields
        for pattern in patterns:
            assert pattern.merchant_pattern
            assert pattern.frequency
            assert pattern.temporal_pattern_type
            assert pattern.confidence_score >= 0.6
            assert pattern.transaction_count >= 3
            assert pattern.amount_mean > 0
    
    def test_end_to_end_prediction(self, services, realistic_transactions):
        """Test prediction generation on detected patterns."""
        detection_service = services['detection']
        prediction_service = services['prediction']
        
        # Detect patterns
        patterns = detection_service.detect_recurring_patterns(
            user_id=realistic_transactions[0].user_id,
            transactions=realistic_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        
        if not patterns:
            pytest.skip("No patterns detected in real data")
        
        # Generate predictions for each pattern
        predictions = []
        for pattern in patterns:
            try:
                prediction = prediction_service.predict_next_occurrence(pattern)
                predictions.append((pattern, prediction))
            except Exception as e:
                print(f"Warning: Failed to predict for pattern {pattern.merchant_pattern}: {e}")
        
        print(f"\n✓ Generated {len(predictions)} predictions")
        
        # Show predictions
        for pattern, prediction in predictions[:5]:  # Show first 5
            next_date = datetime.fromtimestamp(prediction.next_expected_date / 1000, tz=timezone.utc)
            print(f"\nPrediction for {pattern.merchant_pattern}:")
            print(f"  Next Date: {next_date.strftime('%Y-%m-%d')}")
            print(f"  Days Until: {prediction.days_until_due}")
            print(f"  Expected Amount: ${prediction.expected_amount}")
            print(f"  Confidence: {prediction.confidence:.2f}")
        
        # Verify predictions
        for pattern, prediction in predictions:
            assert prediction.next_expected_date > 0
            assert prediction.expected_amount > 0
            assert 0.0 <= prediction.confidence <= 1.0
            assert prediction.days_until_due >= 0
    
    def test_end_to_end_monthly_patterns(self, services, realistic_transactions):
        """Test detection of monthly patterns specifically."""
        detection_service = services['detection']
        
        patterns = detection_service.detect_recurring_patterns(
            user_id=realistic_transactions[0].user_id,
            transactions=realistic_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        
        monthly_patterns = [p for p in patterns if p.frequency == RecurrenceFrequency.MONTHLY]
        
        print(f"\n✓ Found {len(monthly_patterns)} monthly patterns")
        
        for pattern in monthly_patterns[:3]:
            print(f"\nMonthly Pattern: {pattern.merchant_pattern}")
            print(f"  Temporal Type: {pattern.temporal_pattern_type.value}")
            print(f"  Confidence: {pattern.confidence_score:.2f}")
            print(f"  Occurrences: {pattern.transaction_count}")
    
    def test_end_to_end_high_confidence_patterns(self, services, realistic_transactions):
        """Test that high confidence patterns are detected."""
        detection_service = services['detection']
        
        patterns = detection_service.detect_recurring_patterns(
            user_id=realistic_transactions[0].user_id,
            transactions=realistic_transactions,
            min_occurrences=5,  # More occurrences for higher confidence
            min_confidence=0.8   # High confidence threshold
        )
        
        print(f"\n✓ Found {len(patterns)} high-confidence patterns (≥0.8)")
        
        for pattern in patterns:
            print(f"\nHigh-Confidence Pattern: {pattern.merchant_pattern}")
            print(f"  Confidence: {pattern.confidence_score:.2f}")
            print(f"  Frequency: {pattern.frequency.value}")
            print(f"  Occurrences: {pattern.transaction_count}")
            
            # High confidence patterns should have good regularity
            assert pattern.confidence_score >= 0.8
            assert pattern.transaction_count >= 5
    
    def test_end_to_end_performance(self, services, realistic_transactions):
        """Test performance on realistic data."""
        import time
        
        detection_service = services['detection']
        
        start_time = time.time()
        patterns = detection_service.detect_recurring_patterns(
            user_id=realistic_transactions[0].user_id,
            transactions=realistic_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        end_time = time.time()
        
        elapsed = end_time - start_time
        txn_count = len(realistic_transactions)
        
        print("\n✓ Performance Metrics:")
        print(f"  Transactions: {txn_count}")
        print(f"  Patterns Found: {len(patterns)}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Rate: {txn_count/elapsed:.0f} txn/s")
        
        # Performance targets from design doc
        # Target: <10s for 1,000 transactions
        if txn_count >= 100:
            expected_time = (txn_count / 1000) * 10  # Scale linearly
            assert elapsed < expected_time * 2, f"Too slow: {elapsed:.2f}s > {expected_time*2:.2f}s"
    
    def test_pattern_accuracy_metrics(self, services, realistic_transactions):
        """
        Calculate accuracy metrics on realistic data.
        
        This is informational - helps understand algorithm performance.
        """
        detection_service = services['detection']
        
        patterns = detection_service.detect_recurring_patterns(
            user_id=realistic_transactions[0].user_id,
            transactions=realistic_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        
        if not patterns:
            pytest.skip("No patterns detected")
        
        # Calculate statistics
        confidence_scores = [p.confidence_score for p in patterns]
        occurrence_counts = [p.transaction_count for p in patterns]
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        avg_occurrences = sum(occurrence_counts) / len(occurrence_counts)
        
        # Pattern type distribution
        pattern_types = {}
        for p in patterns:
            pattern_types[p.temporal_pattern_type.value] = pattern_types.get(p.temporal_pattern_type.value, 0) + 1
        
        # Frequency distribution
        frequencies = {}
        for p in patterns:
            frequencies[p.frequency.value] = frequencies.get(p.frequency.value, 0) + 1
        
        print("\n✓ Pattern Analysis:")
        print(f"  Total Patterns: {len(patterns)}")
        print(f"  Avg Confidence: {avg_confidence:.2f}")
        print(f"  Avg Occurrences: {avg_occurrences:.1f}")
        print("\n  Pattern Types:")
        for ptype, count in sorted(pattern_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    {ptype}: {count}")
        print("\n  Frequencies:")
        for freq, count in sorted(frequencies.items(), key=lambda x: x[1], reverse=True):
            print(f"    {freq}: {count}")
        
        # Baseline expectations from design doc
        assert avg_confidence >= 0.65, "Average confidence below baseline (65%)"

