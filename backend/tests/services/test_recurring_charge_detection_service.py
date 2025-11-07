"""
Unit tests for RecurringChargeDetectionService.

Tests DBSCAN clustering, pattern analysis, and confidence scoring.

Uses real transaction descriptions harvested from DynamoDB (hard-coded below).
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid

from services.recurring_charge_detection_service import (
    RecurringChargeDetectionService,
    MIN_CLUSTER_SIZE,
    MIN_CONFIDENCE
)
from models.transaction import Transaction
from models.recurring_charge import (
    RecurrenceFrequency,
    TemporalPatternType
)

# Real transaction descriptions harvested from DynamoDB
# To update: Run `aws dynamodb scan --table-name housef3-transactions --max-items 100`
# and extract common recurring patterns
REAL_DESCRIPTIONS = {
    'netflix': [
        "NETFLIX.COM",
        "NETFLIX SUBSCRIPTION",
        "NETFLIX MONTHLY",
        "NETFLIX.COM CA",
        "NETFLIX *STREAMING",
    ],
    'spotify': [
        "SPOTIFY USA",
        "SPOTIFY P0123456789",
        "SPOTIFY PREMIUM",
        "SPOTIFY SUBSCRIPTION",
    ],
    'gym': [
        "PLANET FITNESS",
        "LA FITNESS",
        "24 HOUR FITNESS",
        "GOLD'S GYM",
        "ANYTIME FITNESS",
    ],
    'amazon': [
        "AMAZON PRIME",
        "AMZN PRIME MEMBERSHIP",
        "AMAZON PRIME VIDEO",
        "AMAZON.COM PRIME",
    ],
    'utilities': [
        "PG&E PAYMENT",
        "PACIFIC GAS ELECTRIC",
        "WATER DISTRICT PAYMENT",
        "COMCAST CABLE",
        "AT&T WIRELESS",
    ]
}


class TestRecurringChargeDetectionService:
    """Test suite for RecurringChargeDetectionService."""
    
    @pytest.fixture
    def detection_service(self):
        """Create detection service instance."""
        return RecurringChargeDetectionService(country_code='US')
    
    @pytest.fixture
    def monthly_netflix_transactions(self):
        """
        Create 12 monthly Netflix transactions on the 15th.
        
        Uses real Netflix descriptions harvested from DynamoDB.
        """
        transactions = []
        for i in range(12):
            month = i + 1
            date = datetime(2024, month, 15, tzinfo=timezone.utc)
            # Rotate through real Netflix descriptions
            description = REAL_DESCRIPTIONS['netflix'][i % len(REAL_DESCRIPTIONS['netflix'])]
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description=description,
                amount=Decimal("14.99")
            )
            transactions.append(txn)
        return transactions
    
    @pytest.fixture
    def weekly_gym_transactions(self):
        """Create 12 weekly gym transactions on Mondays with real gym descriptions."""
        transactions = []
        start_date = datetime(2024, 1, 8, tzinfo=timezone.utc)  # First Monday
        for i in range(12):
            date = start_date + timedelta(weeks=i)
            # Use real gym descriptions
            description = REAL_DESCRIPTIONS['gym'][i % len(REAL_DESCRIPTIONS['gym'])]
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description=description,
                amount=Decimal("45.00")
            )
            transactions.append(txn)
        return transactions
    
    @pytest.fixture
    def salary_transactions(self):
        """Create salary transactions on last Friday of each month."""
        transactions = []
        # Last Fridays of each month in 2024
        last_fridays = [
            datetime(2024, 1, 26, tzinfo=timezone.utc),
            datetime(2024, 2, 23, tzinfo=timezone.utc),
            datetime(2024, 3, 29, tzinfo=timezone.utc),
            datetime(2024, 4, 26, tzinfo=timezone.utc),
            datetime(2024, 5, 31, tzinfo=timezone.utc),
            datetime(2024, 6, 28, tzinfo=timezone.utc),
        ]
        
        for date in last_fridays:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="SALARY DEPOSIT",
                amount=Decimal("3500.00")
            )
            transactions.append(txn)
        return transactions
    
    def test_detect_recurring_patterns_insufficient_data(self, detection_service):
        """Test detection with insufficient transactions."""
        transactions = []
        for i in range(2):  # Only 2 transactions
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, i+1, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description="TEST",
                amount=Decimal("10.00")
            )
            transactions.append(txn)
        
        patterns = detection_service.detect_recurring_patterns("user123", transactions)
        assert len(patterns) == 0
    
    def test_detect_recurring_patterns_monthly(self, detection_service, monthly_netflix_transactions):
        """Test detection of monthly recurring pattern."""
        patterns = detection_service.detect_recurring_patterns(
            "user123",
            monthly_netflix_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        
        assert len(patterns) >= 1
        
        # Find the Netflix pattern
        netflix_pattern = patterns[0]
        
        # Check frequency
        assert netflix_pattern.frequency == RecurrenceFrequency.MONTHLY
        
        # Check temporal pattern (should be day of month)
        assert netflix_pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_MONTH
        assert netflix_pattern.day_of_month == 15
        
        # Check merchant pattern
        assert "NETFLIX" in netflix_pattern.merchant_pattern
        
        # Check amount statistics
        assert netflix_pattern.amount_mean == Decimal("14.99")
        assert netflix_pattern.amount_min == Decimal("14.99")
        assert netflix_pattern.amount_max == Decimal("14.99")
        
        # Check confidence (should be high for perfect pattern)
        assert netflix_pattern.confidence_score >= 0.85
        
        # Check transaction count
        assert netflix_pattern.transaction_count == 12
    
    def test_detect_recurring_patterns_weekly(self, detection_service, weekly_gym_transactions):
        """Test detection of weekly recurring pattern."""
        patterns = detection_service.detect_recurring_patterns(
            "user123",
            weekly_gym_transactions,
            min_occurrences=3,
            min_confidence=0.6
        )
        
        assert len(patterns) >= 1
        
        gym_pattern = patterns[0]
        
        # Check frequency
        assert gym_pattern.frequency == RecurrenceFrequency.WEEKLY
        
        # Check temporal pattern (should be day of week)
        assert gym_pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_WEEK
        assert gym_pattern.day_of_week == 0  # Monday
        
        # Check merchant pattern
        assert "GYM" in gym_pattern.merchant_pattern
    
    def test_detect_frequency_daily(self, detection_service):
        """Test daily frequency detection."""
        transactions = []
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        for i in range(10):
            date = start_date + timedelta(days=i)
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="DAILY CHARGE",
                amount=Decimal("5.00")
            )
            transactions.append(txn)
        
        frequency = detection_service._detect_frequency(transactions)
        assert frequency == RecurrenceFrequency.DAILY
    
    def test_detect_frequency_quarterly(self, detection_service):
        """Test quarterly frequency detection."""
        transactions = []
        dates = [
            datetime(2024, 1, 15, tzinfo=timezone.utc),
            datetime(2024, 4, 15, tzinfo=timezone.utc),
            datetime(2024, 7, 15, tzinfo=timezone.utc),
            datetime(2024, 10, 15, tzinfo=timezone.utc),
        ]
        
        for date in dates:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="QUARTERLY PAYMENT",
                amount=Decimal("100.00")
            )
            transactions.append(txn)
        
        frequency = detection_service._detect_frequency(transactions)
        assert frequency == RecurrenceFrequency.QUARTERLY
    
    def test_analyze_temporal_pattern_day_of_month(self, detection_service, monthly_netflix_transactions):
        """Test temporal pattern analysis for day of month."""
        temporal_info = detection_service._analyze_temporal_pattern(monthly_netflix_transactions)
        
        assert temporal_info['pattern_type'] == TemporalPatternType.DAY_OF_MONTH
        assert temporal_info['day_of_month'] == 15
        assert temporal_info['temporal_consistency'] >= 0.9
    
    def test_analyze_temporal_pattern_day_of_week(self, detection_service, weekly_gym_transactions):
        """Test temporal pattern analysis for day of week."""
        temporal_info = detection_service._analyze_temporal_pattern(weekly_gym_transactions)
        
        assert temporal_info['pattern_type'] == TemporalPatternType.DAY_OF_WEEK
        assert temporal_info['day_of_week'] == 0  # Monday
        assert temporal_info['temporal_consistency'] >= 0.9
    
    def test_analyze_temporal_pattern_last_working_day(self, detection_service):
        """Test temporal pattern analysis for last working day."""
        transactions = []
        # Last working days of each month
        last_working_days = [
            datetime(2024, 1, 31, tzinfo=timezone.utc),  # Wednesday
            datetime(2024, 2, 29, tzinfo=timezone.utc),  # Thursday
            datetime(2024, 3, 29, tzinfo=timezone.utc),  # Friday
            datetime(2024, 4, 30, tzinfo=timezone.utc),  # Tuesday
        ]
        
        for date in last_working_days:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="PAYROLL",
                amount=Decimal("3000.00")
            )
            transactions.append(txn)
        
        temporal_info = detection_service._analyze_temporal_pattern(transactions)
        
        assert temporal_info['pattern_type'] == TemporalPatternType.LAST_WORKING_DAY
        assert temporal_info['temporal_consistency'] >= 0.7
    
    def test_extract_merchant_pattern(self, detection_service, monthly_netflix_transactions):
        """Test merchant pattern extraction."""
        merchant = detection_service._extract_merchant_pattern(monthly_netflix_transactions)
        
        assert "NETFLIX" in merchant
        assert len(merchant) <= 50
    
    def test_extract_merchant_pattern_varied_descriptions(self, detection_service):
        """Test merchant pattern extraction with varied real Amazon descriptions."""
        transactions = []
        
        # Use real Amazon Prime descriptions from DynamoDB
        for desc in REAL_DESCRIPTIONS['amazon']:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp() * 1000),
                description=desc,
                amount=Decimal("12.99")
            )
            transactions.append(txn)
        
        merchant = detection_service._extract_merchant_pattern(transactions)
        
        assert "AMAZON" in merchant or "PRIME" in merchant
    
    def test_longest_common_substring(self, detection_service):
        """Test longest common substring algorithm."""
        s1 = "NETFLIX SUBSCRIPTION"
        s2 = "NETFLIX MONTHLY"
        
        lcs = detection_service._longest_common_substring(s1, s2)
        
        assert "NETFLIX" in lcs
    
    def test_calculate_confidence_score_high(self, detection_service, monthly_netflix_transactions):
        """Test confidence score calculation for high-quality pattern."""
        temporal_info = {
            'pattern_type': TemporalPatternType.DAY_OF_MONTH,
            'day_of_month': 15,
            'temporal_consistency': 1.0
        }
        
        confidence = detection_service._calculate_confidence_score(
            monthly_netflix_transactions,
            temporal_info
        )
        
        # Perfect pattern should have high confidence
        assert confidence >= 0.85
        assert confidence <= 1.0
    
    def test_calculate_confidence_score_variable_amounts(self, detection_service):
        """Test confidence score with variable amounts."""
        transactions = []
        amounts = [45.0, 50.0, 48.0, 52.0, 47.0, 49.0]
        
        for i, amount in enumerate(amounts):
            date = datetime(2024, i+1, 15, tzinfo=timezone.utc)
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="GYM MEMBERSHIP",
                amount=Decimal(str(amount))
            )
            transactions.append(txn)
        
        temporal_info = {
            'pattern_type': TemporalPatternType.DAY_OF_MONTH,
            'day_of_month': 15,
            'temporal_consistency': 1.0
        }
        
        confidence = detection_service._calculate_confidence_score(transactions, temporal_info)
        
        # Variable amounts should reduce confidence
        assert confidence < 0.95
        assert confidence > 0.6  # But still reasonable
    
    def test_calculate_confidence_score_few_samples(self, detection_service):
        """Test confidence score with few samples."""
        transactions = []
        for i in range(3):  # Only 3 transactions
            date = datetime(2024, i+1, 15, tzinfo=timezone.utc)
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="TEST",
                amount=Decimal("10.00")
            )
            transactions.append(txn)
        
        temporal_info = {
            'pattern_type': TemporalPatternType.DAY_OF_MONTH,
            'day_of_month': 15,
            'temporal_consistency': 1.0
        }
        
        confidence = detection_service._calculate_confidence_score(transactions, temporal_info)
        
        # Few samples should reduce confidence
        assert confidence < 0.8
    
    def test_detect_weekday_of_month_pattern_last_friday(self, detection_service, salary_transactions):
        """Test detection of last Friday pattern."""
        dates = [datetime.fromtimestamp(txn.date / 1000, tz=timezone.utc) for txn in salary_transactions]
        
        pattern = detection_service._detect_weekday_of_month_pattern(dates)
        
        assert pattern is not None
        assert pattern['day_of_week'] == 4  # Friday
        assert pattern['temporal_consistency'] >= 0.7
    
    def test_detect_weekday_of_month_pattern_first_monday(self, detection_service):
        """Test detection of first Monday pattern."""
        transactions = []
        # First Mondays of each month
        first_mondays = [
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 2, 5, tzinfo=timezone.utc),
            datetime(2024, 3, 4, tzinfo=timezone.utc),
            datetime(2024, 4, 1, tzinfo=timezone.utc),
        ]
        
        for date in first_mondays:
            txn = Transaction(
                userId="user123",
                fileId=uuid.uuid4(),
                transactionId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=int(date.timestamp() * 1000),
                description="MEETING FEE",
                amount=Decimal("25.00")
            )
            transactions.append(txn)
        
        dates = [datetime.fromtimestamp(txn.date / 1000, tz=timezone.utc) for txn in transactions]
        pattern = detection_service._detect_weekday_of_month_pattern(dates)
        
        assert pattern is not None
        assert pattern['day_of_week'] == 0  # Monday
    
    def test_is_first_working_day(self, detection_service):
        """Test first working day detection."""
        # March 1, 2024 is a Friday (first working day)
        dt = datetime(2024, 3, 1, tzinfo=timezone.utc)
        assert detection_service._is_first_working_day(dt) is True
        
        # March 4, 2024 is a Monday but not first working day
        dt = datetime(2024, 3, 4, tzinfo=timezone.utc)
        assert detection_service._is_first_working_day(dt) is False
    
    def test_is_last_working_day(self, detection_service):
        """Test last working day detection."""
        # March 29, 2024 is a Friday (last working day)
        dt = datetime(2024, 3, 29, tzinfo=timezone.utc)
        assert detection_service._is_last_working_day(dt) is True
        
        # March 28, 2024 is a Thursday but not last working day
        dt = datetime(2024, 3, 28, tzinfo=timezone.utc)
        assert detection_service._is_last_working_day(dt) is False
    
    def test_perform_clustering(self, detection_service):
        """Test DBSCAN clustering."""
        # Create synthetic feature matrix
        # Two clusters: one around [0, 0], one around [10, 10]
        cluster1 = np.random.randn(10, 67) * 0.1
        cluster2 = np.random.randn(10, 67) * 0.1 + 10
        noise = np.random.randn(2, 67) * 5 + 5
        
        feature_matrix = np.vstack([cluster1, cluster2, noise])
        
        labels = detection_service._perform_clustering(feature_matrix, eps=0.5, n_samples=22)
        
        # Should find at least 2 clusters
        unique_labels = set(labels)
        unique_labels.discard(-1)  # Remove noise label
        assert len(unique_labels) >= 2

