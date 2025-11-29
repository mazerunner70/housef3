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
    PatternFeedback,
    PatternStatus,
    PatternCriteriaValidation,
    PatternReviewAction
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
            confidenceScore=Decimal("0.95"),
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000
        )

        assert pattern.user_id == user_id
        assert pattern.merchant_pattern == "NETFLIX"
        assert pattern.frequency == RecurrenceFrequency.MONTHLY
        assert pattern.temporal_pattern_type == TemporalPatternType.DAY_OF_MONTH
        assert pattern.amount_mean == Decimal("14.99")
        assert pattern.confidence_score == Decimal("0.95")
        assert pattern.transaction_count == 12
        assert pattern.active is False  # Phase 1: patterns default to inactive
        assert pattern.auto_categorize is False
        assert pattern.tolerance_days == 2  # Default value
        assert pattern.amount_tolerance_pct == Decimal("10.0")  # Default value

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
            amountTolerancePct=Decimal("5.0"),
            confidenceScore=Decimal("0.94"),
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            featureVector=[Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0.4"), Decimal("0.5")],
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
        assert pattern.amount_tolerance_pct == Decimal("5.0")
        assert pattern.feature_vector == [Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0.4"), Decimal("0.5")]
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
                confidenceScore=Decimal("0.8"),
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
                confidenceScore=Decimal("0.8"),
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
                confidenceScore=Decimal("1.5"),  # Invalid: must be 0.0-1.0
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
            confidenceScore=Decimal("0.95"),
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            suggestedCategoryId=category_id,
            featureVector=[Decimal("0.1"), Decimal("0.2"), Decimal("0.3")],
            active=True
        )

        item = pattern.to_dynamodb_item()

        # Check that UUIDs are converted to strings
        assert item["patternId"] == str(pattern_id)
        assert item["userId"] == user_id
        assert item["suggestedCategoryId"] == str(category_id)
        
        # Check that enums are converted to values
        assert item["frequency"] == "monthly"
        assert item["temporalPatternType"] == "day_of_month"
        
        # CRITICAL: Check that boolean 'active' is converted to string for DynamoDB GSI
        assert item["active"] == "true"
        assert isinstance(item["active"], str)
        
        # Check that Decimals are preserved
        assert isinstance(item["amountMean"], Decimal)
        assert item["amountMean"] == Decimal("14.99")
        
        # CRITICAL: Check that float fields are converted to Decimal for DynamoDB
        assert isinstance(item["confidenceScore"], Decimal)
        assert item["confidenceScore"] == Decimal("0.95")
        assert isinstance(item["amountTolerancePct"], Decimal)
        assert item["amountTolerancePct"] == Decimal("10.0")
        
        # Check that feature vector floats are converted to Decimal
        assert isinstance(item["featureVector"], list)
        for val in item["featureVector"]:
            assert isinstance(val, Decimal)
        assert item["featureVector"][0] == Decimal("0.1")
        assert item["featureVector"][1] == Decimal("0.2")
        assert item["featureVector"][2] == Decimal("0.3")
        
        # Check other fields
        assert item["merchantPattern"] == "NETFLIX"
        assert item["dayOfMonth"] == 15
        assert item["transactionCount"] == 12
    
    def test_pattern_to_dynamodb_item_active_false(self):
        """Test that active=False is correctly converted to string 'false'."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="NETFLIX",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("14.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("14.99"),
            amountMax=Decimal("14.99"),
            confidenceScore=Decimal("0.95"),
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            active=False
        )
        
        item = pattern.to_dynamodb_item()
        
        # CRITICAL: Check that boolean False is converted to string 'false'
        assert item["active"] == "false"
        assert isinstance(item["active"], str)

    def test_pattern_to_dynamodb_item_boolean_conversions(self):
        """Test that all boolean fields (active, autoCategorize, criteriaValidated) are converted to 'true'/'false' strings for DynamoDB GSI compatibility."""
        # Test with autoCategorize=True, active=True, criteriaValidated=True
        pattern_true = RecurringChargePattern(
            userId="user123",
            merchantPattern="NETFLIX",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("14.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("14.99"),
            amountMax=Decimal("14.99"),
            confidenceScore=Decimal("0.95"),
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            active=True,
            autoCategorize=True,
            criteriaValidated=True
        )
        
        item_true = pattern_true.to_dynamodb_item()
        
        # CRITICAL: Check that all boolean True values are converted to string 'true'
        assert item_true["active"] == "true"
        assert isinstance(item_true["active"], str)
        assert item_true["autoCategorize"] == "true"
        assert isinstance(item_true["autoCategorize"], str)
        assert item_true["criteriaValidated"] == "true"
        assert isinstance(item_true["criteriaValidated"], str)
        
        # Test with autoCategorize=False, active=False, criteriaValidated=False
        pattern_false = RecurringChargePattern(
            userId="user123",
            merchantPattern="SPOTIFY",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("9.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("9.99"),
            amountMax=Decimal("9.99"),
            confidenceScore=Decimal("0.95"),
            transactionCount=12,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            active=False,
            autoCategorize=False,
            criteriaValidated=False
        )
        
        item_false = pattern_false.to_dynamodb_item()
        
        # CRITICAL: Check that all boolean False values are converted to string 'false'
        assert item_false["active"] == "false"
        assert isinstance(item_false["active"], str)
        assert item_false["autoCategorize"] == "false"
        assert isinstance(item_false["autoCategorize"], str)
        assert item_false["criteriaValidated"] == "false"
        assert isinstance(item_false["criteriaValidated"], str)

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
            "autoCategorize": "false",  # String from DynamoDB (stored as string for GSI)
            "active": "true",  # String from DynamoDB (stored as string for GSI)
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
        
        # CRITICAL: Check that string booleans are converted back to boolean objects
        assert pattern.active is True
        assert isinstance(pattern.active, bool)
        assert pattern.auto_categorize is False
        assert isinstance(pattern.auto_categorize, bool)
        
        # Check Decimal to int conversion for integer fields
        assert pattern.day_of_month == 15
        assert isinstance(pattern.day_of_month, int)
        assert pattern.transaction_count == 12
        assert isinstance(pattern.transaction_count, int)
        
        # Check that Decimal fields remain as Decimal
        assert pattern.confidence_score == Decimal("0.95")
        assert isinstance(pattern.confidence_score, Decimal)
        
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
            amountTolerancePct=Decimal("5.0"),
            confidenceScore=Decimal("0.98"),
            transactionCount=24,
            firstOccurrence=1640995200000,
            lastOccurrence=1704067200000,
            featureVector=[Decimal("0.5"), Decimal("0.3"), Decimal("0.8")],
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
        # Feature vector comparison - convert to list for comparison
        assert restored.feature_vector == original.feature_vector
        assert restored.cluster_id == original.cluster_id
        assert restored.auto_categorize == original.auto_categorize
        assert restored.active == original.active


class TestRecurringChargePrediction:
    """Test cases for RecurringChargePrediction model."""

    def test_create_prediction(self):
        """Test creating a prediction."""
        pattern_id = uuid.uuid4()
        
        prediction = RecurringChargePrediction(
            patternId=pattern_id,
            nextExpectedDate=1704067200000,
            expectedAmount=Decimal("14.99"),
            confidence=Decimal("0.95"),
            daysUntilDue=15,
            amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
        )

        assert prediction.pattern_id == pattern_id
        assert prediction.next_expected_date == 1704067200000
        assert prediction.expected_amount == Decimal("14.99")
        assert prediction.confidence == Decimal("0.95")
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
                confidence=Decimal("1.5"),  # Invalid
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
                confidence=Decimal("0.95"),
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
            confidence=Decimal("0.95"),
            daysUntilDue=15,
            amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
        )

        item = prediction.to_dynamodb_item()

        assert item["patternId"] == str(pattern_id)
        assert item["nextExpectedDate"] == 1704067200000
        assert item["expectedAmount"] == Decimal("14.99")
        
        # CRITICAL: Check that float confidence is converted to Decimal for DynamoDB
        assert isinstance(item["confidence"], Decimal)
        assert item["confidence"] == Decimal("0.95")
        
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
        assert prediction.confidence == Decimal("0.95")
        assert isinstance(prediction.confidence, Decimal)
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
        assert feedback.user_correction is not None
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
        assert feedback.user_correction is not None
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


class TestPatternStatus:
    """Test cases for PatternStatus enum."""
    
    def test_enum_values(self):
        """Test that all status values are defined correctly."""
        assert PatternStatus.DETECTED.value == "detected"
        assert PatternStatus.CONFIRMED.value == "confirmed"
        assert PatternStatus.ACTIVE.value == "active"
        assert PatternStatus.REJECTED.value == "rejected"
        assert PatternStatus.PAUSED.value == "paused"
    
    def test_enum_from_string(self):
        """Test creating enum from string value."""
        status = PatternStatus("active")
        assert status == PatternStatus.ACTIVE
        assert isinstance(status, PatternStatus)


class TestPatternPhase1Fields:
    """Test cases for Phase 1 review fields in RecurringChargePattern."""
    
    def test_pattern_with_matched_transaction_ids(self):
        """Test pattern with matched transaction IDs."""
        tx_id_1 = uuid.uuid4()
        tx_id_2 = uuid.uuid4()
        tx_id_3 = uuid.uuid4()
        
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="NETFLIX",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("14.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("14.99"),
            amountMax=Decimal("14.99"),
            confidenceScore=Decimal("0.95"),
            transactionCount=3,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            matchedTransactionIds=[tx_id_1, tx_id_2, tx_id_3]
        )
        
        assert pattern.matched_transaction_ids == [tx_id_1, tx_id_2, tx_id_3]
        assert pattern.matched_transaction_ids is not None
        assert len(pattern.matched_transaction_ids) == 3
    
    def test_pattern_default_status(self):
        """Test that patterns default to DETECTED status."""
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="SPOTIFY",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.FLEXIBLE,
            amountMean=Decimal("9.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("9.99"),
            amountMax=Decimal("9.99"),
            confidenceScore=Decimal("0.90"),
            transactionCount=5,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000
        )
        
        assert pattern.status == PatternStatus.DETECTED
        assert pattern.active is False  # Patterns default to inactive
        assert pattern.criteria_validated is False
        assert pattern.reviewed_by is None
        assert pattern.reviewed_at is None
    
    def test_pattern_with_review_metadata(self):
        """Test pattern with review metadata."""
        review_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="GYM MEMBERSHIP",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("50.00"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("50.00"),
            amountMax=Decimal("50.00"),
            confidenceScore=Decimal("0.98"),
            transactionCount=12,
            firstOccurrence=1640995200000,
            lastOccurrence=1704067200000,
            status=PatternStatus.CONFIRMED,
            reviewedBy="user123",
            reviewedAt=review_time,
            criteriaValidated=True
        )
        
        assert pattern.status == PatternStatus.CONFIRMED
        assert pattern.reviewed_by == "user123"
        assert pattern.reviewed_at == review_time
        assert pattern.criteria_validated is True
    
    def test_pattern_to_dynamodb_with_phase1_fields(self):
        """Test DynamoDB serialization with Phase 1 fields."""
        tx_id_1 = uuid.uuid4()
        tx_id_2 = uuid.uuid4()
        review_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        pattern = RecurringChargePattern(
            userId="user123",
            merchantPattern="COFFEE SHOP",
            frequency=RecurrenceFrequency.WEEKLY,
            temporalPatternType=TemporalPatternType.DAY_OF_WEEK,
            dayOfWeek=1,  # Tuesday
            amountMean=Decimal("4.50"),
            amountStd=Decimal("0.25"),
            amountMin=Decimal("4.00"),
            amountMax=Decimal("5.00"),
            confidenceScore=Decimal("0.85"),
            transactionCount=20,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            matchedTransactionIds=[tx_id_1, tx_id_2],
            status=PatternStatus.ACTIVE,
            reviewedBy="user123",
            reviewedAt=review_time,
            criteriaValidated=True,
            criteriaValidationErrors=["Some warning"],
            active=True
        )
        
        item = pattern.to_dynamodb_item()
        
        # Check matched transaction IDs are converted to strings
        assert item["matchedTransactionIds"] == [str(tx_id_1), str(tx_id_2)]
        assert all(isinstance(tid, str) for tid in item["matchedTransactionIds"])
        
        # Check status is stored as string value
        assert item["status"] == "active"
        
        # Check review metadata
        assert item["reviewedBy"] == "user123"
        assert item["reviewedAt"] == review_time
        
        # Check boolean fields converted to strings
        assert item["criteriaValidated"] == "true"
        assert isinstance(item["criteriaValidated"], str)
        
        # Check validation errors list preserved
        assert item["criteriaValidationErrors"] == ["Some warning"]
    
    def test_pattern_from_dynamodb_with_phase1_fields(self):
        """Test DynamoDB deserialization with Phase 1 fields."""
        tx_id_1 = uuid.uuid4()
        tx_id_2 = uuid.uuid4()
        pattern_id = uuid.uuid4()
        review_time = 1704067200000
        
        item = {
            "patternId": str(pattern_id),
            "userId": "user123",
            "merchantPattern": "COFFEE SHOP",
            "frequency": "weekly",
            "temporalPatternType": "day_of_week",
            "dayOfWeek": Decimal("1"),
            "toleranceDays": Decimal("2"),
            "amountMean": Decimal("4.50"),
            "amountStd": Decimal("0.25"),
            "amountMin": Decimal("4.00"),
            "amountMax": Decimal("5.00"),
            "amountTolerancePct": Decimal("10.0"),
            "confidenceScore": Decimal("0.85"),
            "transactionCount": Decimal("20"),
            "firstOccurrence": Decimal("1672531200000"),
            "lastOccurrence": Decimal("1704067200000"),
            "matchedTransactionIds": [str(tx_id_1), str(tx_id_2)],
            "status": "active",
            "reviewedBy": "user123",
            "reviewedAt": Decimal(str(review_time)),
            "criteriaValidated": "true",
            "criteriaValidationErrors": ["Some warning"],
            "active": "true",
            "createdAt": Decimal("1672531200000"),
            "updatedAt": Decimal("1704067200000")
        }
        
        pattern = RecurringChargePattern.from_dynamodb_item(item)
        
        # Check matched transaction IDs converted to UUIDs
        assert pattern.matched_transaction_ids == [tx_id_1, tx_id_2]
        assert pattern.matched_transaction_ids is not None
        assert all(isinstance(tid, uuid.UUID) for tid in pattern.matched_transaction_ids)
        
        # Check status converted to enum
        assert pattern.status == PatternStatus.ACTIVE
        assert isinstance(pattern.status, PatternStatus)
        
        # Check review metadata
        assert pattern.reviewed_by == "user123"
        assert pattern.reviewed_at == review_time
        assert isinstance(pattern.reviewed_at, int)
        
        # Check boolean fields converted back
        assert pattern.criteria_validated is True
        assert isinstance(pattern.criteria_validated, bool)
        
        # Check validation errors preserved
        assert pattern.criteria_validation_errors == ["Some warning"]
    
    def test_pattern_roundtrip_with_phase1_fields(self):
        """Test roundtrip serialization with Phase 1 fields."""
        tx_id_1 = uuid.uuid4()
        tx_id_2 = uuid.uuid4()
        tx_id_3 = uuid.uuid4()
        
        original = RecurringChargePattern(
            userId="user123",
            merchantPattern="GROCERY STORE",
            frequency=RecurrenceFrequency.WEEKLY,
            temporalPatternType=TemporalPatternType.DAY_OF_WEEK,
            dayOfWeek=6,  # Sunday
            amountMean=Decimal("75.00"),
            amountStd=Decimal("15.00"),
            amountMin=Decimal("50.00"),
            amountMax=Decimal("100.00"),
            confidenceScore=Decimal("0.92"),
            transactionCount=30,
            firstOccurrence=1640995200000,
            lastOccurrence=1704067200000,
            matchedTransactionIds=[tx_id_1, tx_id_2, tx_id_3],
            status=PatternStatus.CONFIRMED,
            reviewedBy="user123",
            reviewedAt=1704000000000,
            criteriaValidated=True,
            criteriaValidationErrors=[],
            active=False
        )
        
        # Serialize to DynamoDB
        item = original.to_dynamodb_item()
        
        # Deserialize back
        restored = RecurringChargePattern.from_dynamodb_item(item)
        
        # Verify all Phase 1 fields match
        assert restored.matched_transaction_ids == original.matched_transaction_ids
        assert restored.status == original.status
        assert restored.reviewed_by == original.reviewed_by
        assert restored.reviewed_at == original.reviewed_at
        assert restored.criteria_validated == original.criteria_validated
        assert restored.criteria_validation_errors == original.criteria_validation_errors
        assert restored.active == original.active


class TestPatternCriteriaValidation:
    """Test cases for PatternCriteriaValidation model."""
    
    def test_create_validation_perfect_match(self):
        """Test creating a validation result with perfect match."""
        pattern_id = uuid.uuid4()
        
        validation = PatternCriteriaValidation(
            patternId=pattern_id,
            isValid=True,
            originalCount=12,
            criteriaMatchCount=12,
            allOriginalMatchCriteria=True,
            noFalsePositives=True,
            perfectMatch=True,
            missingFromCriteria=[],
            extraFromCriteria=[],
            warnings=[],
            suggestions=["Criteria perfectly match original cluster - ready to activate"]
        )
        
        assert validation.pattern_id == pattern_id
        assert validation.is_valid is True
        assert validation.perfect_match is True
        assert len(validation.warnings) == 0
        assert len(validation.suggestions) == 1
    
    def test_create_validation_with_warnings(self):
        """Test creating a validation result with warnings."""
        pattern_id = uuid.uuid4()
        tx_id_1 = uuid.uuid4()
        tx_id_2 = uuid.uuid4()
        
        validation = PatternCriteriaValidation(
            patternId=pattern_id,
            isValid=True,
            originalCount=12,
            criteriaMatchCount=14,
            allOriginalMatchCriteria=True,
            noFalsePositives=False,
            perfectMatch=False,
            missingFromCriteria=[],
            extraFromCriteria=[tx_id_1, tx_id_2],
            warnings=["2 additional transactions match criteria"],
            suggestions=["Consider tightening merchant pattern or amount tolerance"]
        )
        
        assert validation.is_valid is True  # All originals match
        assert validation.perfect_match is False  # But has extras
        assert len(validation.extra_from_criteria) == 2
        assert len(validation.warnings) == 1
        assert len(validation.suggestions) == 1


class TestPatternReviewAction:
    """Test cases for PatternReviewAction model."""
    
    def test_create_review_action_confirm(self):
        """Test creating a confirm review action."""
        pattern_id = uuid.uuid4()
        
        action = PatternReviewAction(
            patternId=pattern_id,
            userId="user123",
            action="confirm",
            activateImmediately=True
        )
        
        assert action.pattern_id == pattern_id
        assert action.user_id == "user123"
        assert action.action == "confirm"
        assert action.activate_immediately is True
    
    def test_create_review_action_reject(self):
        """Test creating a reject review action."""
        pattern_id = uuid.uuid4()
        
        action = PatternReviewAction(
            patternId=pattern_id,
            userId="user123",
            action="reject",
            notes="This is not a recurring charge"
        )
        
        assert action.action == "reject"
        assert action.notes == "This is not a recurring charge"
    
    def test_create_review_action_edit(self):
        """Test creating an edit review action."""
        pattern_id = uuid.uuid4()
        category_id = uuid.uuid4()
        
        action = PatternReviewAction(
            patternId=pattern_id,
            userId="user123",
            action="edit",
            editedMerchantPattern="NETFLIX.*STREAMING",
            editedAmountTolerancePct=Decimal("15.0"),
            editedToleranceDays=3,
            editedSuggestedCategoryId=category_id,
            activateImmediately=False
        )
        
        assert action.action == "edit"
        assert action.edited_merchant_pattern == "NETFLIX.*STREAMING"
        assert action.edited_amount_tolerance_pct == Decimal("15.0")
        assert action.edited_tolerance_days == 3
        assert action.edited_suggested_category_id == category_id
    
    def test_review_action_validation_invalid_action(self):
        """Test that invalid action types are rejected."""
        pattern_id = uuid.uuid4()
        
        with pytest.raises(ValueError, match="action must be one of"):
            PatternReviewAction(
                patternId=pattern_id,
                userId="user123",
                action="invalid_action"
            )

