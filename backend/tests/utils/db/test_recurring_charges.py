"""
Unit tests for recurring charge database operations.

Tests cover:
- Pattern CRUD operations
- Prediction operations
- Feedback operations
- Access control validation
- Filtering and querying
- Batch operations
- Error handling
"""

import pytest
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch, call
from botocore.exceptions import ClientError

from models.recurring_charge import (
    RecurringChargePattern,
    RecurringChargePatternCreate,
    RecurrenceFrequency,
    TemporalPatternType,
    RecurringChargePrediction,
    RecurringChargePredictionCreate,
    PatternFeedback
)
from utils.db.recurring_charges import (
    create_pattern_in_db,
    get_pattern_by_id_from_db,
    list_patterns_by_user_from_db,
    update_pattern_in_db,
    delete_pattern_from_db,
    batch_create_patterns_in_db,
    checked_mandatory_pattern,
    save_prediction_in_db,
    list_predictions_by_user_from_db,
    save_feedback_in_db,
    list_feedback_by_pattern_from_db,
    list_all_feedback_by_user_from_db
)
from utils.db.base import NotFound, NotAuthorized


@pytest.fixture
def mock_tables():
    """Mock DynamoDB tables."""
    with patch('utils.db.recurring_charges.tables') as mock:
        mock.recurring_charge_patterns = MagicMock()
        mock.recurring_charge_predictions = MagicMock()
        mock.pattern_feedback = MagicMock()
        yield mock


@pytest.fixture
def sample_pattern_create():
    """Create a sample recurring charge pattern Create DTO for testing."""
    return RecurringChargePatternCreate(
        userId="user123",
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
        lastOccurrence=1704067200000
    )


@pytest.fixture
def sample_pattern():
    """Create a sample recurring charge pattern (full model) for testing."""
    return RecurringChargePattern(
        userId="user123",
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
        lastOccurrence=1704067200000
    )


@pytest.fixture
def sample_prediction():
    """Create a sample prediction Create DTO for testing."""
    pattern_id = uuid.uuid4()
    return RecurringChargePredictionCreate(
        patternId=pattern_id,
        nextExpectedDate=1704067200000,
        expectedAmount=Decimal("14.99"),
        confidence=0.95,
        daysUntilDue=15,
        amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
    )


@pytest.fixture
def sample_feedback_create():
    """Create a sample feedback Create DTO for testing."""
    pattern_id = uuid.uuid4()
    from models.recurring_charge import PatternFeedbackCreate
    return PatternFeedbackCreate(
        patternId=pattern_id,
        userId="user123",
        feedbackType="correct"
    )


@pytest.fixture
def sample_feedback():
    """Create a sample feedback (full model) for testing."""
    pattern_id = uuid.uuid4()
    return PatternFeedback(
        patternId=pattern_id,
        userId="user123",
        feedbackType="correct"
    )


class TestCreatePatternInDB:
    """Test cases for create_pattern_in_db."""

    def test_create_pattern_success(self, mock_tables, sample_pattern_create):
        """Test successfully creating a pattern."""
        result = create_pattern_in_db(sample_pattern_create)
        
        # Verify put_item was called
        mock_tables.recurring_charge_patterns.put_item.assert_called_once()
        call_args = mock_tables.recurring_charge_patterns.put_item.call_args
        assert call_args[1]['Item']['userId'] == "user123"
        assert call_args[1]['Item']['merchantPattern'] == "NETFLIX"
        
        # Verify the returned pattern is a RecurringChargePattern with correct data
        assert isinstance(result, RecurringChargePattern)
        assert result.user_id == "user123"
        assert result.merchant_pattern == "NETFLIX"
        assert result.frequency == RecurrenceFrequency.MONTHLY
        assert result.pattern_id is not None  # Auto-generated

    def test_create_pattern_table_not_initialized(self, sample_pattern_create):
        """Test error when table is not initialized."""
        with patch('utils.db.recurring_charges.tables') as mock:
            mock.recurring_charge_patterns = None
            
            with pytest.raises(ConnectionError, match="Database table not initialized"):
                create_pattern_in_db(sample_pattern_create)


class TestGetPatternByIdFromDB:
    """Test cases for get_pattern_by_id_from_db."""

    def test_get_pattern_success(self, mock_tables, sample_pattern):
        """Test successfully retrieving a pattern."""
        pattern_id = sample_pattern.pattern_id
        user_id = "user123"
        
        # Mock DynamoDB response
        mock_tables.recurring_charge_patterns.get_item.return_value = {
            'Item': sample_pattern.to_dynamodb_item()
        }
        
        result = get_pattern_by_id_from_db(pattern_id, user_id)
        
        # Verify get_item was called with correct key
        mock_tables.recurring_charge_patterns.get_item.assert_called_once()
        call_args = mock_tables.recurring_charge_patterns.get_item.call_args
        assert call_args[1]['Key']['userId'] == user_id
        assert call_args[1]['Key']['patternId'] == str(pattern_id)
        
        # Verify pattern is returned
        assert result is not None
        assert result.user_id == user_id
        assert result.merchant_pattern == "NETFLIX"

    def test_get_pattern_not_found(self, mock_tables):
        """Test retrieving non-existent pattern returns None."""
        pattern_id = uuid.uuid4()
        user_id = "user123"
        
        # Mock empty response
        mock_tables.recurring_charge_patterns.get_item.return_value = {}
        
        result = get_pattern_by_id_from_db(pattern_id, user_id)
        
        assert result is None

    def test_get_pattern_table_not_initialized(self):
        """Test error when table is not initialized."""
        with patch('utils.db.recurring_charges.tables') as mock:
            mock.recurring_charge_patterns = None
            
            result = get_pattern_by_id_from_db(uuid.uuid4(), "user123")
            assert result is None


class TestListPatternsByUserFromDB:
    """Test cases for list_patterns_by_user_from_db."""

    def test_list_patterns_success(self, mock_tables):
        """Test successfully listing patterns for a user."""
        user_id = "user123"
        
        # Create sample patterns
        pattern1 = RecurringChargePattern(
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
            lastOccurrence=1704067200000,
            active=True
        )
        
        pattern2 = RecurringChargePattern(
            userId=user_id,
            merchantPattern="SPOTIFY",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("9.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("9.99"),
            amountMax=Decimal("9.99"),
            confidenceScore=0.92,
            transactionCount=10,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            active=False
        )
        
        # Mock DynamoDB response
        mock_tables.recurring_charge_patterns.query.return_value = {
            'Items': [
                pattern1.to_dynamodb_item(),
                pattern2.to_dynamodb_item()
            ]
        }
        
        # Test without filters
        results = list_patterns_by_user_from_db(user_id, active_only=False)
        
        assert len(results) == 2
        assert results[0].merchant_pattern == "NETFLIX"
        assert results[1].merchant_pattern == "SPOTIFY"

    def test_list_patterns_active_only_filter(self, mock_tables):
        """Test filtering for active patterns only."""
        user_id = "user123"
        
        # Create patterns with different active status
        active_pattern = RecurringChargePattern(
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
            lastOccurrence=1704067200000,
            active=True
        )
        
        inactive_pattern = RecurringChargePattern(
            userId=user_id,
            merchantPattern="SPOTIFY",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("9.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("9.99"),
            amountMax=Decimal("9.99"),
            confidenceScore=0.92,
            transactionCount=10,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000,
            active=False
        )
        
        # Mock DynamoDB response with both patterns
        mock_tables.recurring_charge_patterns.query.return_value = {
            'Items': [
                active_pattern.to_dynamodb_item(),
                inactive_pattern.to_dynamodb_item()
            ]
        }
        
        # Test with active_only=True
        results = list_patterns_by_user_from_db(user_id, active_only=True)
        
        assert len(results) == 1
        assert results[0].merchant_pattern == "NETFLIX"
        assert results[0].active is True

    def test_list_patterns_min_confidence_filter(self, mock_tables):
        """Test filtering by minimum confidence score."""
        user_id = "user123"
        
        # Create patterns with different confidence scores
        high_conf = RecurringChargePattern(
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
        
        low_conf = RecurringChargePattern(
            userId=user_id,
            merchantPattern="SPOTIFY",
            frequency=RecurrenceFrequency.MONTHLY,
            temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
            amountMean=Decimal("9.99"),
            amountStd=Decimal("0.00"),
            amountMin=Decimal("9.99"),
            amountMax=Decimal("9.99"),
            confidenceScore=0.65,
            transactionCount=10,
            firstOccurrence=1672531200000,
            lastOccurrence=1704067200000
        )
        
        # Mock DynamoDB response
        mock_tables.recurring_charge_patterns.query.return_value = {
            'Items': [
                high_conf.to_dynamodb_item(),
                low_conf.to_dynamodb_item()
            ]
        }
        
        # Test with min_confidence=0.8
        results = list_patterns_by_user_from_db(user_id, min_confidence=0.8)
        
        assert len(results) == 1
        assert results[0].confidence_score == 0.95

    def test_list_patterns_empty_result(self, mock_tables):
        """Test listing patterns when user has none."""
        user_id = "user123"
        
        # Mock empty response
        mock_tables.recurring_charge_patterns.query.return_value = {
            'Items': []
        }
        
        results = list_patterns_by_user_from_db(user_id)
        
        assert len(results) == 0


class TestUpdatePatternInDB:
    """Test cases for update_pattern_in_db."""

    def test_update_pattern_success(self, mock_tables, sample_pattern):
        """Test successfully updating a pattern."""
        # Create update DTO and apply to pattern
        from models.recurring_charge import RecurringChargePatternUpdate
        pattern_update = RecurringChargePatternUpdate(
            active=False,
            confidenceScore=0.98
        )
        
        # Apply update to pattern
        sample_pattern.update_model_details(pattern_update)
        
        # Call update_pattern_in_db with the updated pattern
        result = update_pattern_in_db(sample_pattern)
        
        # Verify put_item was called
        mock_tables.recurring_charge_patterns.put_item.assert_called_once()
        
        # Verify result
        assert result.active is False
        assert result.confidence_score == 0.98



class TestDeletePatternFromDB:
    """Test cases for delete_pattern_from_db."""

    def test_delete_pattern_success(self, mock_tables, sample_pattern):
        """Test successfully deleting a pattern."""
        pattern_id = sample_pattern.pattern_id
        user_id = "user123"
        
        # Mock get_item response (for existence check)
        mock_tables.recurring_charge_patterns.get_item.return_value = {
            'Item': sample_pattern.to_dynamodb_item()
        }
        
        result = delete_pattern_from_db(pattern_id, user_id)
        
        # Verify delete_item was called
        mock_tables.recurring_charge_patterns.delete_item.assert_called_once()
        call_args = mock_tables.recurring_charge_patterns.delete_item.call_args
        assert call_args[1]['Key']['userId'] == user_id
        assert call_args[1]['Key']['patternId'] == str(pattern_id)
        
        assert result is True

    def test_delete_pattern_not_found(self, mock_tables):
        """Test deleting non-existent pattern raises NotFound."""
        pattern_id = uuid.uuid4()
        user_id = "user123"
        
        # Mock empty get_item response
        mock_tables.recurring_charge_patterns.get_item.return_value = {}
        
        with pytest.raises(NotFound, match="not found"):
            delete_pattern_from_db(pattern_id, user_id)


class TestBatchCreatePatternsInDB:
    """Test cases for batch_create_patterns_in_db."""

    def test_batch_create_success(self, mock_tables):
        """Test successfully batch creating patterns."""
        pattern_creates = [
            RecurringChargePatternCreate(
                userId="user123",
                merchantPattern=f"MERCHANT{i}",
                frequency=RecurrenceFrequency.MONTHLY,
                temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
                amountMean=Decimal("10.00"),
                amountStd=Decimal("0.00"),
                amountMin=Decimal("10.00"),
                amountMax=Decimal("10.00"),
                confidenceScore=0.9,
                transactionCount=5,
                firstOccurrence=1672531200000,
                lastOccurrence=1704067200000
            )
            for i in range(10)
        ]
        
        # Mock batch_writer
        mock_writer = MagicMock()
        mock_tables.recurring_charge_patterns.batch_writer.return_value.__enter__.return_value = mock_writer
        
        result = batch_create_patterns_in_db(pattern_creates)
        
        assert result == 10
        assert mock_writer.put_item.call_count == 10

    def test_batch_create_empty_list(self, mock_tables):
        """Test batch creating with empty list returns 0."""
        result = batch_create_patterns_in_db([])
        assert result == 0

    def test_batch_create_large_batch(self, mock_tables):
        """Test batch creating more than 25 items (DynamoDB limit)."""
        # Create 50 pattern Create DTOs (should be split into 2 batches)
        pattern_creates = [
            RecurringChargePatternCreate(
                userId="user123",
                merchantPattern=f"MERCHANT{i}",
                frequency=RecurrenceFrequency.MONTHLY,
                temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
                amountMean=Decimal("10.00"),
                amountStd=Decimal("0.00"),
                amountMin=Decimal("10.00"),
                amountMax=Decimal("10.00"),
                confidenceScore=0.9,
                transactionCount=5,
                firstOccurrence=1672531200000,
                lastOccurrence=1704067200000
            )
            for i in range(50)
        ]
        
        # Mock batch_writer
        mock_writer = MagicMock()
        mock_tables.recurring_charge_patterns.batch_writer.return_value.__enter__.return_value = mock_writer
        
        result = batch_create_patterns_in_db(pattern_creates)
        
        assert result == 50
        assert mock_writer.put_item.call_count == 50


class TestCheckedMandatoryPattern:
    """Test cases for checked_mandatory_pattern."""

    def test_checked_mandatory_pattern_success(self, mock_tables, sample_pattern):
        """Test successfully checking a pattern exists."""
        pattern_id = sample_pattern.pattern_id
        user_id = "user123"
        
        # Mock get_item response
        mock_tables.recurring_charge_patterns.get_item.return_value = {
            'Item': sample_pattern.to_dynamodb_item()
        }
        
        result = checked_mandatory_pattern(pattern_id, user_id)
        
        assert result is not None
        assert result.pattern_id == pattern_id

    def test_checked_mandatory_pattern_not_found(self, mock_tables):
        """Test checking non-existent pattern raises NotFound."""
        pattern_id = uuid.uuid4()
        user_id = "user123"
        
        # Mock empty response
        mock_tables.recurring_charge_patterns.get_item.return_value = {}
        
        with pytest.raises(NotFound, match="not found"):
            checked_mandatory_pattern(pattern_id, user_id)


class TestPredictionOperations:
    """Test cases for prediction operations."""

    def test_save_prediction_success(self, mock_tables, sample_prediction):
        """Test successfully saving a prediction."""
        user_id = "user123"
        
        result = save_prediction_in_db(sample_prediction, user_id)
        
        # Verify put_item was called
        mock_tables.recurring_charge_predictions.put_item.assert_called_once()
        call_args = mock_tables.recurring_charge_predictions.put_item.call_args
        assert call_args[1]['Item']['userId'] == user_id
        
        # Verify the result is a RecurringChargePrediction model with the same data
        assert isinstance(result, RecurringChargePrediction)
        assert result.pattern_id == sample_prediction.pattern_id
        assert result.next_expected_date == sample_prediction.next_expected_date
        assert result.expected_amount == sample_prediction.expected_amount
        assert result.confidence == sample_prediction.confidence
        assert result.days_until_due == sample_prediction.days_until_due
        assert result.amount_range == sample_prediction.amount_range

    def test_list_predictions_success(self, mock_tables):
        """Test successfully listing predictions."""
        user_id = "user123"
        
        # Create sample predictions
        pred1 = RecurringChargePrediction(
            patternId=uuid.uuid4(),
            nextExpectedDate=1704067200000,
            expectedAmount=Decimal("14.99"),
            confidence=0.95,
            daysUntilDue=5,
            amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
        )
        
        pred2 = RecurringChargePrediction(
            patternId=uuid.uuid4(),
            nextExpectedDate=1704153600000,
            expectedAmount=Decimal("9.99"),
            confidence=0.92,
            daysUntilDue=25,
            amountRange={"min": Decimal("9.49"), "max": Decimal("10.49")}
        )
        
        # Mock DynamoDB response
        item1 = pred1.to_dynamodb_item()
        item1['userId'] = user_id
        item2 = pred2.to_dynamodb_item()
        item2['userId'] = user_id
        
        mock_tables.recurring_charge_predictions.query.return_value = {
            'Items': [item1, item2]
        }
        
        results = list_predictions_by_user_from_db(user_id)
        
        assert len(results) == 2

    def test_list_predictions_with_days_ahead_filter(self, mock_tables):
        """Test filtering predictions by days_ahead."""
        user_id = "user123"
        
        # Create predictions with different days_until_due
        pred1 = RecurringChargePrediction(
            patternId=uuid.uuid4(),
            nextExpectedDate=1704067200000,
            expectedAmount=Decimal("14.99"),
            confidence=0.95,
            daysUntilDue=5,
            amountRange={"min": Decimal("14.49"), "max": Decimal("15.49")}
        )
        
        pred2 = RecurringChargePrediction(
            patternId=uuid.uuid4(),
            nextExpectedDate=1704153600000,
            expectedAmount=Decimal("9.99"),
            confidence=0.92,
            daysUntilDue=25,
            amountRange={"min": Decimal("9.49"), "max": Decimal("10.49")}
        )
        
        # Mock DynamoDB response
        item1 = pred1.to_dynamodb_item()
        item1['userId'] = user_id
        item2 = pred2.to_dynamodb_item()
        item2['userId'] = user_id
        
        mock_tables.recurring_charge_predictions.query.return_value = {
            'Items': [item1, item2]
        }
        
        # Filter for predictions within 10 days
        results = list_predictions_by_user_from_db(user_id, days_ahead=10)
        
        assert len(results) == 1
        assert results[0].days_until_due == 5


class TestFeedbackOperations:
    """Test cases for feedback operations."""

    def test_save_feedback_success(self, mock_tables, sample_feedback_create):
        """Test successfully saving feedback."""
        result = save_feedback_in_db(sample_feedback_create)
        
        # Verify put_item was called
        mock_tables.pattern_feedback.put_item.assert_called_once()
        
        # Verify the returned feedback is a PatternFeedback with correct data
        assert isinstance(result, PatternFeedback)
        assert result.user_id == "user123"
        assert result.feedback_type == "correct"
        assert result.feedback_id is not None  # Auto-generated

    def test_list_feedback_by_pattern(self, mock_tables):
        """Test listing feedback for a specific pattern."""
        pattern_id = uuid.uuid4()
        user_id = "user123"
        
        # Create sample feedback
        feedback = PatternFeedback(
            patternId=pattern_id,
            userId=user_id,
            feedbackType="correct"
        )
        
        # Mock DynamoDB response
        mock_tables.pattern_feedback.query.return_value = {
            'Items': [feedback.to_dynamodb_item()]
        }
        
        results = list_feedback_by_pattern_from_db(pattern_id, user_id)
        
        assert len(results) == 1
        assert results[0].pattern_id == pattern_id

    def test_list_all_feedback_by_user(self, mock_tables):
        """Test listing all feedback for a user."""
        user_id = "user123"
        
        # Create sample feedback items
        feedback1 = PatternFeedback(
            patternId=uuid.uuid4(),
            userId=user_id,
            feedbackType="correct"
        )
        
        feedback2 = PatternFeedback(
            patternId=uuid.uuid4(),
            userId=user_id,
            feedbackType="incorrect"
        )
        
        # Mock DynamoDB response
        mock_tables.pattern_feedback.query.return_value = {
            'Items': [
                feedback1.to_dynamodb_item(),
                feedback2.to_dynamodb_item()
            ]
        }
        
        results = list_all_feedback_by_user_from_db(user_id)
        
        assert len(results) == 2
        assert results[0].feedback_type == "correct"
        assert results[1].feedback_type == "incorrect"

