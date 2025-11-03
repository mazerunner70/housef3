"""
Unit tests for recurring charge models.

Tests cover:
- RecurrenceFrequency enum
- TemporalPatternType enum
- RecurringChargePattern model
- RecurringChargePrediction model
- PatternFeedback model
- DynamoDB serialization/deserialization
- Enum conversion and preservation
- Validation rules
"""

import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import ValidationError

from models.recurring_charge import (
    RecurringChargePattern,
    RecurrenceFrequency,
    TemporalPatternType,
    RecurringChargePrediction,
    PatternFeedback
)


class TestRecurrenceFrequency:
    """Test cases for RecurrenceFrequency enum."""

    def test_enum_values(self):
        """Test that all frequency values are defined correctly."""
        assert RecurrenceFrequency.DAILY.value == "daily"
        assert RecurrenceFrequency.WEEKLY.value == "weekly"
        assert RecurrenceFrequency.BI_WEEKLY.value == "bi_weekly"
        assert RecurrenceFrequency.SEMI_MONTHLY.value == "semi_monthly"
        assert RecurrenceFrequency.MONTHLY.value == "monthly"
        assert RecurrenceFrequency.BI_MONTHLY.value == "bi_monthly"
        assert RecurrenceFrequency.QUARTERLY.value == "quarterly"
        assert RecurrenceFrequency.SEMI_ANNUALLY.value == "semi_annually"
        assert RecurrenceFrequency.ANNUALLY.value == "annually"
        assert RecurrenceFrequency.IRREGULAR.value == "irregular"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        freq = RecurrenceFrequency("monthly")
        assert freq == RecurrenceFrequency.MONTHLY
        assert isinstance(freq, RecurrenceFrequency)


class TestTemporalPatternType:
    """Test cases for TemporalPatternType enum."""

    def test_enum_values(self):
        """Test that all pattern type values are defined correctly."""
        assert TemporalPatternType.DAY_OF_WEEK.value == "day_of_week"
        assert TemporalPatternType.DAY_OF_MONTH.value == "day_of_month"
        assert TemporalPatternType.FIRST_WORKING_DAY.value == "first_working_day"
        assert TemporalPatternType.LAST_WORKING_DAY.value == "last_working_day"
        assert TemporalPatternType.FIRST_DAY_OF_MONTH.value == "first_day_of_month"
        assert TemporalPatternType.LAST_DAY_OF_MONTH.value == "last_day_of_month"
        assert TemporalPatternType.WEEKEND.value == "weekend"
        assert TemporalPatternType.WEEKDAY.value == "weekday"
        assert TemporalPatternType.FLEXIBLE.value == "flexible"

    def test_enum_from_string(self):
        """Test creating enum from string value."""
        pattern = TemporalPatternType("day_of_month")
        assert pattern == TemporalPatternType.DAY_OF_MONTH
        assert isinstance(pattern, TemporalPatternType)


class TestRecurringChargePattern:
    """Test cases for RecurringChargePattern model."""

    def test_create_pattern_minimal(self):
        """Test creating a pattern with minimal required fields."""
        user_id = "user123"
        pattern = RecurringChargePattern(
            userId=user_id,
            merchantPattern="NETFLIX",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("14.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("14.99"),
            amountMax=Decimal("14.99"),
            confidenceScore=0.95,
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000
        )

        assert pattern.user_id == user_id
        assert pattern.merchant_pattern == "NETFLIX"
        assert pattern.frequency == RecurrenceFrequency.MONTHLY
        assert pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_MONTH
        assert pattern.amount_mean == Decimal("14.99")
        assert pattern.confidence_score == 0.95
        assert pattern.transaction_count == 12
        assert pattern.active is True
        assert pattern.auto_categorize is False
        assert pattern.tolerance_days == 2  # Default value
        assert pattern.amount_tolerance_pct == 10.0  # Default value

    def test_create_pattern_with_all_fields(self):
        """Test creating a pattern with all optional fields."""
        user_id = "user123"
        pattern_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        pattern = RecurringChargePattern(
            patternId=pattern_id,
            userId=user_id,
            merchantPattern="SALARY DEPOSIT",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.LAST_WORKING_DAY,
            dayOfWeek=None,
            dayOfMonth=None,
            toleranceDays=3,
            amountMean=Decimal("5500.00"),
            amountStd=Decimal("50.00"),
            amountMin=Decimal("5450.00"),
            amountMax=Decimal("5550.00"),
            amountTolerancePct=5.0,
            confidenceScore=0.94,
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            featureVector=[0.1, 0.2, 0.3, 0.4, 0.5],
            clusterId=3,
            suggestedCategoryId=category_id,
            autoCategorize=True,
            active=True
        )

        assert pattern.pattern_id == pattern_id
        assert pattern.user_id == user_id
        assert pattern.merchant_pattern == "SALARY DEPOSIT"
        assert pattern.frequency == RecurrenceFrequency.MONTHLY
        assert pattern.temporal_pattern_type == TemporalPatternType.LAST_WORKING_DAY
        assert pattern.tolerance_days == 3
        assert pattern.amount_tolerance_pct == 5.0
        assert pattern.feature_vector == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert pattern.cluster_id == 3
        assert pattern.suggested_category_id == category_id
        assert pattern.auto_categorize is True

    def test_pattern_validation_day_of_week(self):
        """Test validation of day_of_week field (0-6)."""
        with pytest.raises(ValidationError):
            RecurringChargePattern(
                userId="user123",
                merchantPattern="TEST",
                frequency=RecurrenceFrequency.WEEKLY,
                temporalPatternType=TemporalPatternType.DAY_OF_WEEK,
                dayOfWeek=7,  # Invalid: must be 0-6
                amountMean=Decimal("10.00"),
                amountStd=Decimal("0.00"),
                amountMin=Decimal("10.00"),
                amountMax=Decimal("10.00"),
                confidenceScore=0.8,
                transactionCount=5,
                firstOccurrence=1672531200000,
                lastOccurrence=1704067200000
            )

    def test_pattern_validation_day_of_month(self):
        """Test validation of day_of_month field (1-31)."""
        with pytest.raises(ValidationError):
            RecurringChargePattern(
                userId="user123",
                merchantPattern="TEST",
                frequency=RecurrenceFrequency.MONTHLY,
                temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
                dayOfMonth=32,  # Invalid: must be 1-31
                amountMean=Decimal("10.00"),
                amountStd=Decimal("0.00"),
                amountMin=Decimal("10.00"),
                amountMax=Decimal("10.00"),
                confidenceScore=0.8,
                transactionCount=5,
                firstOccurrence=1672531200000,
                lastOccurrence=1704067200000
            )

    def test_pattern_validation_confidence_score(self):
        """Test validation of confidence_score field (0.0-1.0)."""
        with pytest.raises(ValueError):
            RecurringChargePattern(
                userId="user123",
                merchantPattern="TEST",
                frequency=RecurrenceFrequency.MONTHLY,
                temporalPatternType=TemporalPatternType.FLEXIBLE,
                amountMean=Decimal("10.00"),
                amountStd=Decimal("0.00"),
                amountMin=Decimal("10.00"),
                amountMax=Decimal("10.00"),
                confidenceScore=1.5,  # Invalid: must be 0.0-1.0
                transactionCount=5,
                firstOccurrence=1672531200000,
                lastOccurrence=1704067200000
            )

    def test_pattern_to_dynamodb_item(self):
        """Test converting pattern to DynamoDB item format."""
        user_id = "user123"
        pattern_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        pattern = RecurringChargePattern(
            patternId=pattern_id,
            userId=user_id,
            merchantPattern="NETFLIX",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=15,
            amountMean=Decimal("14.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("14.99"),
            amountMax=Decimal("14.99"),
            confidenceScore=0.95,
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            suggestedCategoryId=category_id,
            featureVector=[0.1, 0.2, 0.3]
        )

        item = pattern.to_dynamodb_item()

        # Check that UUIDs are converted to strings
        assert item["patternId"] == str(pattern_id)
        assert item["userId"] == user_id
        assert item["suggestedCategoryId"] == str(category_id)
        
        # Check that enums are converted to values
        assert item["frequency"] == "monthly"
        assert item["temporalPatternType"] == "day_of_month"
        
        # Check that Decimals are preserved
        assert isinstance(item["amountMean"], Decimal)
        assert item["amountMean"] == Decimal("14.99")
        
        # Check other fields
        assert item["merchantPattern"] == "NETFLIX"
        assert item["dayOfMonth"] == 15
        assert item["confidenceScore"] == 0.95
        assert item["transactionCount"] == 12
        assert item["featureVector"] == [0.1, 0.2, 0.3]

    def test_pattern_from_dynamodb_item(self):
        """Test creating pattern from DynamoDB item."""
        pattern_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        item = {
            "patternId": str(pattern_id),
            "userId": "user123",
            "merchantPattern": "NETFLIX",
            "frequency": "monthly",  # String from DynamoDB
            "temporalPatternType": "day_of_month",  # String from DynamoDB
            "dayOfMonth": Decimal("15"),  # DynamoDB returns numbers as Decimal
            "toleranceDays": Decimal("2"),
            "amountMean": Decimal("14.99"),
            "amountStd": Decimal("0.00"),
            "amountMin": Decimal("14.99"),
            "amountMax": Decimal("14.99"),
            "amountTolerancePct": Decimal("10.0"),
            "confidenceScore": Decimal("0.95"),
            "transactionCount": Decimal("12"),
            "firstOccurrence": Decimal("1672531200000"),
            "lastOccurrence": Decimal("1704067200000"),
            "suggestedCategoryId": str(category_id),
            "autoCategorize": False,
            "active": True,
            "createdAt": Decimal("1672531200000"),
            "updatedAt": Decimal("1704067200000")
        }

        pattern = RecurringChargePattern.from_dynamodb_item(item)

        # Check UUID conversion
        assert pattern.pattern_id == pattern_id
        assert pattern.suggested_category_id == category_id
        
        # Check enum conversion - should be actual enum objects
        assert pattern.frequency == RecurrenceFrequency.MONTHLY
        assert isinstance(pattern.frequency, RecurrenceFrequency)
        assert pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_MONTH
        assert isinstance(pattern.temporal_pattern_type, TemporalPatternType)
        
        # Check that .value access works (proves they're enum objects)
        assert pattern.frequency.value == "monthly"
        assert pattern.temporal_pattern_type.value == "day_of_month"
        
        # Check Decimal to int conversion for integer fields
        assert pattern.day_of_month == 15
        assert isinstance(pattern.day_of_month, int)
        assert pattern.transaction_count == 12
        assert isinstance(pattern.transaction_count, int)
        
        # Check Decimal to float conversion for float fields
        assert pattern.confidence_score == 0.95
        assert isinstance(pattern.confidence_score, float)
        
        # Check Decimal preservation for amount fields
        assert pattern.amount_mean == Decimal("14.99")
        assert isinstance(pattern.amount_mean, Decimal)

    def test_pattern_roundtrip_serialization(self):
        """Test that pattern can be serialized to DynamoDB and back without data loss."""
        original = RecurringChargePattern(
            userId="user123",
            merchantPattern="SPOTIFY PREM",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            dayOfMonth=1,
            toleranceDays=2,
            amountMean=Decimal("9.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("9.99"),
            amountMax=Decimal("9.99"),
            amountTolerancePct=5.0,
            confidenceScore=0.98,
            transactionCount=24,
            firstOccurrence=1640995200000,
            lastOccurrence=1704067200000,
            featureVector=[0.5, 0.3, 0.8],
            clusterId=1,
            autoCategorize=True
        )

        # Serialize to DynamoDB format
        item = original.to_dynamodb_item()
        
        # Deserialize back
        restored = RecurringChargePattern.from_dynamodb_item(item)

        # Verify all fields match
        assert restored.user_id == original.user_id
        assert restored.merchant_pattern == original.merchant_pattern
        assert restored.frequency == original.frequency
        assert restored.temporal_pattern_type == original.temporal_pattern_type
        assert restored.day_of_month == original.day_of_month
        assert restored.tolerance_days == original.tolerance_days
        assert restored.amount_mean == original.amount_mean
        assert restored.confidence_score == original.confidence_score
        assert restored.transaction_count == original.transaction_count
        assert restored.feature_vector == original.feature_vector
        assert restored.cluster_id == original.cluster_id
        assert restored.auto_categorize == original.auto_categorize


class TestRecurringChargePrediction:
    """Test cases for RecurringChargePrediction model."""

    def test_create_prediction(self):
        """Test creating a prediction."""
        pattern_id = uuid.uuid4()
        
        prediction = RecurringChargePrediction(
            patternId=pattern_id,
            nextExpectedDate=1704067200000,
            expectedAmount=Decimal("14.99"),
            confidence=0.95,
            daysUntilDue=15,
            amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
        )

        assert prediction.pattern_id == pattern_id
        assert prediction.next_expected_date == 1704067200000
        assert prediction.expected_amount == Decimal("14.99")
        assert prediction.confidence == 0.95
        assert prediction.days_until_due == 15
        assert prediction.amount_range["min"] == Decimal("14.49")
        assert prediction.amount_range["max"] == Decimal("15.49")

    def test_prediction_validation_confidence(self):
        """Test validation of confidence field (0.0-1.0)."""
        pattern_id = uuid.uuid4()
        
        with pytest.raises(ValidationError):
            RecurringChargePrediction(
                patternId=pattern_id,
                nextExpectedDate=1704067200000,
                expectedAmount=Decimal("14.99"),
                confidence=1.5,  # Invalid
                daysUntilDue=15,
                amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
            )

    def test_prediction_validation_timestamp(self):
        """Test validation of timestamp (must be positive)."""
        pattern_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="Timestamp must be a positive integer"):
            RecurringChargePrediction(
                patternId=pattern_id,
                nextExpectedDate=-1000,  # Invalid: negative
                expectedAmount=Decimal("14.99"),
                confidence=0.95,
                daysUntilDue=15,
                amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
            )

    def test_prediction_to_dynamodb_item(self):
        """Test converting prediction to DynamoDB item format."""
        pattern_id = uuid.uuid4()
        
        prediction = RecurringChargePrediction(
            patternId=pattern_id,
            nextExpectedDate=1704067200000,
            expectedAmount=Decimal("14.99"),
            confidence=0.95,
            daysUntilDue=15,
            amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
        )

        item = prediction.to_dynamodb_item()

        assert item["patternId"] == str(pattern_id)
        assert item["nextExpectedDate"] == 1704067200000
        assert item["expectedAmount"] == Decimal("14.99")
        assert item["confidence"] == 0.95
        assert item["daysUntilDue"] == 15

    def test_prediction_from_dynamodb_item(self):
        """Test creating prediction from DynamoDB item."""
        pattern_id = uuid.uuid4()
        
        item = {
            "patternId": str(pattern_id),
            "nextExpectedDate": Decimal("1704067200000"),
            "expectedAmount": Decimal("14.99"),
            "confidence": Decimal("0.95"),
            "daysUntilDue": Decimal("15"),
            "amountRange": {
                "min": Decimal("14.49"),
                "max": Decimal("15.49")
            }
        }

        prediction = RecurringChargePrediction.from_dynamodb_item(item)

        assert prediction.pattern_id == pattern_id
        assert prediction.next_expected_date == 1704067200000
        assert isinstance(prediction.next_expected_date, int)
        assert prediction.expected_amount == Decimal("14.99")
        assert prediction.confidence == 0.95
        assert isinstance(prediction.confidence, float)
        assert prediction.days_until_due == 15
        assert isinstance(prediction.days_until_due, int)


class TestPatternFeedback:
    """Test cases for PatternFeedback model."""

    def test_create_feedback(self):
        """Test creating feedback."""
        pattern_id = uuid.uuid4()
        transaction_id = uuid.uuid4()
        
        feedback = PatternFeedback(
            patternId=pattern_id,
            userId="user123",
            feedbackType="correct",
            transactionId=transaction_id
        )

        assert feedback.pattern_id == pattern_id
        assert feedback.user_id == "user123"
        assert feedback.feedback_type == "correct"
        assert feedback.transaction_id == transaction_id
        assert feedback.user_correction is None
        assert feedback.timestamp is not None

    def test_feedback_validation_type(self):
        """Test validation of feedback_type field."""
        pattern_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="feedback_type must be one of"):
            PatternFeedback(
                patternId=pattern_id,
                userId="user123",
                feedbackType="invalid_type"  # Invalid
            )

    def test_feedback_valid_types(self):
        """Test all valid feedback types."""
        pattern_id = uuid.uuid4()
        valid_types = ['correct', 'incorrect', 'missed_transaction', 'false_positive']
        
        for feedback_type in valid_types:
            feedback = PatternFeedback(
                patternId=pattern_id,
                userId="user123",
                feedbackType=feedback_type
            )
            assert feedback.feedback_type == feedback_type

    def test_feedback_with_correction(self):
        """Test feedback with user correction data."""
        pattern_id = uuid.uuid4()
        correction = {
            "correct_merchant": "ACTUAL MERCHANT",
            "correct_amount": "15.99",
            "notes": "Wrong merchant pattern detected"
        }
        
        feedback = PatternFeedback(
            patternId=pattern_id,
            userId="user123",
            feedbackType="incorrect",
            userCorrection=correction
        )

        assert feedback.user_correction == correction
        assert feedback.user_correction["correct_merchant"] == "ACTUAL MERCHANT"

    def test_feedback_to_dynamodb_item(self):
        """Test converting feedback to DynamoDB item format."""
        pattern_id = uuid.uuid4()
        transaction_id = uuid.uuid4()
        
        feedback = PatternFeedback(
            patternId=pattern_id,
            userId="user123",
            feedbackType="missed_transaction",
            transactionId=transaction_id
        )

        item = feedback.to_dynamodb_item()

        assert item["patternId"] == str(pattern_id)
        assert item["userId"] == "user123"
        assert item["feedbackType"] == "missed_transaction"
        assert item["transactionId"] == str(transaction_id)

    def test_feedback_from_dynamodb_item(self):
        """Test creating feedback from DynamoDB item."""
        pattern_id = uuid.uuid4()
        feedback_id = uuid.uuid4()
        transaction_id = uuid.uuid4()
        
        item = {
            "feedbackId": str(feedback_id),
            "patternId": str(pattern_id),
            "userId": "user123",
            "feedbackType": "false_positive",
            "transactionId": str(transaction_id),
            "timestamp": Decimal("1704067200000"),
            "userCorrection": {
                "notes": "This is not recurring"
            }
        }

        feedback = PatternFeedback.from_dynamodb_item(item)

        assert feedback.feedback_id == feedback_id
        assert feedback.pattern_id == pattern_id
        assert feedback.user_id == "user123"
        assert feedback.feedback_type == "false_positive"
        assert feedback.transaction_id == transaction_id
        assert feedback.timestamp == 1704067200000
        assert isinstance(feedback.timestamp, int)
        assert feedback.user_correction["notes"] == "This is not recurring"

    def test_feedback_roundtrip_serialization(self):
        """Test that feedback can be serialized to DynamoDB and back without data loss."""
        pattern_id = uuid.uuid4()
        transaction_id = uuid.uuid4()
        correction = {"notes": "Test correction"}
        
        original = PatternFeedback(
            patternId=pattern_id,
            userId="user123",
            feedbackType="incorrect",
            transactionId=transaction_id,
            userCorrection=correction
        )

        # Serialize to DynamoDB format
        item = original.to_dynamodb_item()
        
        # Deserialize back
        restored = PatternFeedback.from_dynamodb_item(item)

        # Verify all fields match
        assert restored.pattern_id == original.pattern_id
        assert restored.user_id == original.user_id
        assert restored.feedback_type == original.feedback_type
        assert restored.transaction_id == original.transaction_id
        assert restored.user_correction == original.user_correction

