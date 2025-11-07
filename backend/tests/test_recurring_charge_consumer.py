"""
Unit tests for recurring charge detection consumer.
"""

import json
import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock, Mock
import pytest

from consumers.recurring_charge_detection_consumer import RecurringChargeDetectionConsumer
from models.events import BaseEvent
from models.transaction import Transaction
from models.recurring_charge import RecurringChargePatternCreate, RecurrenceFrequency, TemporalPatternType


def _create_test_event(user_id="test-user-id", operation_id="op_123"):
    """Helper to create a test detection event"""
    return BaseEvent(
        event_id=str(uuid.uuid4()),
        event_type="recurring_charge.detection.requested",
        event_version="1.0",
        timestamp=int(datetime.now().timestamp() * 1000),
        source="recurring_charge.service",
        user_id=user_id,
        correlation_id=operation_id,
        data={
            "operationId": operation_id,
            "accountId": None,
            "minOccurrences": 3,
            "minConfidence": 0.6,
        },
    )


def _create_test_transaction(user_id="test-user-id", amount=15.99, description="NETFLIX"):
    """Helper to create a test transaction"""
    return Transaction(
        transactionId=uuid.uuid4(),
        userId=user_id,
        fileId=uuid.uuid4(),
        accountId=uuid.uuid4(),
        date=int(datetime.now().timestamp() * 1000),
        amount=Decimal(str(amount)),
        description=description,
        transactionType="debit",
    )


def _create_test_pattern(user_id="test-user-id"):
    """Helper to create a test pattern"""
    return RecurringChargePatternCreate(
        userId=user_id,
        merchantPattern="NETFLIX",
        frequency=RecurrenceFrequency.MONTHLY,
        temporalPatternType=TemporalPatternType.DAY_OF_MONTH,
        dayOfMonth=15,
        amountMean=Decimal("15.99"),
        amountStd=Decimal("0.00"),
        amountMin=Decimal("15.99"),
        amountMax=Decimal("15.99"),
        confidenceScore=0.95,
        transactionCount=12,
        firstOccurrence=int(datetime(2024, 1, 15).timestamp() * 1000),
        lastOccurrence=int(datetime(2024, 12, 15).timestamp() * 1000),
        active=True,
    )


# ==============================================================================
# Test Consumer Initialization
# ==============================================================================


def test_consumer_initialization():
    """Test consumer initializes correctly"""
    consumer = RecurringChargeDetectionConsumer()
    assert consumer.consumer_name == "recurring_charge_detection_consumer"
    assert consumer.detection_service is not None
    assert consumer.prediction_service is not None


def test_should_process_event():
    """Test event filtering"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Should process detection request events
    event = _create_test_event()
    assert consumer.should_process_event(event) is True
    
    # Should not process other events
    other_event = BaseEvent(
        event_id=str(uuid.uuid4()),
        event_type="file.processed",
        event_version="1.0",
        timestamp=int(datetime.now().timestamp() * 1000),
        source="transaction.service",
        user_id="test-user-id",
        data={},
    )
    assert consumer.should_process_event(other_event) is False


# ==============================================================================
# Test Event Processing
# ==============================================================================


@patch("src.consumers.recurring_charge_detection_consumer.operation_tracking_service")
@patch("src.consumers.recurring_charge_detection_consumer.save_prediction_to_db")
@patch("src.consumers.recurring_charge_detection_consumer.batch_create_patterns_in_db")
@patch("src.consumers.recurring_charge_detection_consumer.list_account_transactions")
def test_process_event_success(mock_list_txs, mock_batch_create, mock_save_pred, mock_tracking):
    """Test successful event processing"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock transactions
    transactions = [_create_test_transaction() for _ in range(20)]
    mock_list_txs.return_value = transactions
    
    # Mock pattern detection
    patterns = [_create_test_pattern()]
    consumer.detection_service.detect_recurring_patterns = Mock(return_value=patterns)
    
    # Mock pattern creation - batch_create_patterns_in_db returns int
    mock_batch_create.return_value = 1
    
    # Mock prediction generation
    consumer.prediction_service.predict_next_occurrence = Mock(return_value=None)
    
    # Process event
    event = _create_test_event()
    consumer.process_event(event)
    
    # Verify operations
    assert mock_list_txs.called
    assert consumer.detection_service.detect_recurring_patterns.called
    assert mock_batch_create.called
    
    # Verify operation tracking updates
    assert mock_tracking.update_operation_status.call_count >= 3  # Multiple status updates


@patch("src.consumers.recurring_charge_detection_consumer.operation_tracking_service")
@patch("src.consumers.recurring_charge_detection_consumer.list_account_transactions")
def test_process_event_no_transactions(mock_list_txs, mock_tracking):
    """Test processing with no transactions"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock empty transaction list
    mock_list_txs.return_value = []
    
    # Process event
    event = _create_test_event()
    consumer.process_event(event)
    
    # Verify operation completed
    final_call = mock_tracking.update_operation_status.call_args_list[-1]
    assert final_call[1]["status"].value == "completed"
    assert final_call[1]["additional_data"]["transactionsAnalyzed"] == 0


@patch("src.consumers.recurring_charge_detection_consumer.operation_tracking_service")
@patch("src.consumers.recurring_charge_detection_consumer.batch_create_patterns_in_db")
@patch("src.consumers.recurring_charge_detection_consumer.list_account_transactions")
def test_process_event_no_patterns_detected(mock_list_txs, mock_batch_create, mock_tracking):
    """Test processing when no patterns are detected"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock transactions
    transactions = [_create_test_transaction() for _ in range(5)]
    mock_list_txs.return_value = transactions
    
    # Mock no patterns detected
    consumer.detection_service.detect_recurring_patterns = Mock(return_value=[])
    
    # Process event
    event = _create_test_event()
    consumer.process_event(event)
    
    # Verify no patterns were saved
    assert not mock_batch_create.called
    
    # Verify operation completed successfully
    final_call = mock_tracking.update_operation_status.call_args_list[-1]
    assert final_call[1]["status"].value == "completed"
    assert final_call[1]["additional_data"]["patternsDetected"] == 0


@patch("src.consumers.recurring_charge_detection_consumer.operation_tracking_service")
def test_process_event_missing_operation_id(mock_tracking):
    """Test processing event without operation ID"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Create event without operation ID
    event = BaseEvent(
        event_id=str(uuid.uuid4()),
        event_type="recurring_charge.detection.requested",
        event_version="1.0",
        timestamp=int(datetime.now().timestamp() * 1000),
        source="recurring_charge.service",
        user_id="test-user-id",
        data={
            "minOccurrences": 3,
            "minConfidence": 0.6,
        },
    )
    
    # Should raise EventProcessingError
    from consumers.base_consumer import EventProcessingError
    with pytest.raises(EventProcessingError):
        consumer.process_event(event)


# ==============================================================================
# Test Transaction Fetching
# ==============================================================================


@patch("src.consumers.recurring_charge_detection_consumer.list_user_transactions")
def test_fetch_transactions_for_specific_account(mock_list_user_txs):
    """Test fetching transactions for specific account"""
    consumer = RecurringChargeDetectionConsumer()
    
    account_id = str(uuid.uuid4())
    transactions = [_create_test_transaction() for _ in range(10)]
    # list_user_transactions returns (transactions, last_key, count)
    mock_list_user_txs.return_value = (transactions, None, 10)
    
    result = consumer._fetch_transactions("test-user-id", account_id)
    
    assert len(result) == 10
    assert mock_list_user_txs.called
    # Verify it was called with the account_id filter
    call_kwargs = mock_list_user_txs.call_args.kwargs
    assert call_kwargs["user_id"] == "test-user-id"
    assert call_kwargs["account_ids"] == [uuid.UUID(account_id)]
    assert call_kwargs["sort_order_date"] == "desc"
    assert call_kwargs["ignore_dup"] is True


@patch("src.consumers.recurring_charge_detection_consumer.list_user_transactions")
def test_fetch_transactions_for_all_accounts(mock_list_user_txs):
    """Test fetching transactions for all user accounts"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock transactions across all accounts
    transactions = [_create_test_transaction() for _ in range(10)]
    # list_user_transactions returns (transactions, last_key, count)
    mock_list_user_txs.return_value = (transactions, None, 10)
    
    result = consumer._fetch_transactions("test-user-id", None)
    
    # Should fetch all user transactions
    assert len(result) == 10
    assert mock_list_user_txs.called
    # Verify it was called without account filter
    call_kwargs = mock_list_user_txs.call_args.kwargs
    assert call_kwargs["user_id"] == "test-user-id"
    assert call_kwargs["account_ids"] is None
    assert call_kwargs["sort_order_date"] == "desc"
    assert call_kwargs["ignore_dup"] is True


def test_fetch_transactions_filters_invalid():
    """Test that invalid transactions are filtered out"""
    consumer = RecurringChargeDetectionConsumer()
    
    with patch("src.consumers.recurring_charge_detection_consumer.list_user_transactions") as mock_list:
        # Create mix of valid and invalid transactions
        valid_tx = _create_test_transaction()
        # Create invalid transactions using model_construct to bypass validation
        invalid_tx_no_date = Transaction.model_construct(
            transactionId=uuid.uuid4(),
            userId="test-user-id",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=None,  # Invalid
            amount=Decimal("15.99"),
            description="TEST",
            transactionType="debit",
        )
        invalid_tx_no_amount = Transaction.model_construct(
            transactionId=uuid.uuid4(),
            userId="test-user-id",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=int(datetime.now().timestamp() * 1000),
            amount=None,  # Invalid
            description="TEST",
            transactionType="debit",
        )
        
        # list_user_transactions returns (transactions, last_key, count)
        mock_list.return_value = ([valid_tx, invalid_tx_no_date, invalid_tx_no_amount], None, 3)
        
        result = consumer._fetch_transactions("test-user-id", str(uuid.uuid4()))
        
        # Should only return valid transaction
        assert len(result) == 1


@patch("src.consumers.recurring_charge_detection_consumer.list_user_transactions")
def test_fetch_transactions_pagination(mock_list_user_txs):
    """Test that pagination works correctly to fetch up to 10,000 transactions"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Simulate multiple pages of transactions
    page1_txs = [_create_test_transaction() for _ in range(1000)]
    page2_txs = [_create_test_transaction() for _ in range(1000)]
    page3_txs = [_create_test_transaction() for _ in range(500)]
    
    # Mock returns different pages with pagination keys
    mock_list_user_txs.side_effect = [
        (page1_txs, {"lastKey": "page2"}, 1000),
        (page2_txs, {"lastKey": "page3"}, 1000),
        (page3_txs, None, 500),  # Last page, no more pagination
    ]
    
    result = consumer._fetch_transactions("test-user-id", None)
    
    # Should fetch all pages
    assert len(result) == 2500
    assert mock_list_user_txs.call_count == 3
    
    # Verify pagination parameters
    call1_kwargs = mock_list_user_txs.call_args_list[0].kwargs
    assert call1_kwargs["limit"] == 1000
    assert call1_kwargs["last_evaluated_key"] is None
    
    call2_kwargs = mock_list_user_txs.call_args_list[1].kwargs
    assert call2_kwargs["limit"] == 1000
    assert call2_kwargs["last_evaluated_key"] == {"lastKey": "page2"}
    
    call3_kwargs = mock_list_user_txs.call_args_list[2].kwargs
    assert call3_kwargs["limit"] == 1000
    assert call3_kwargs["last_evaluated_key"] == {"lastKey": "page3"}


@patch("src.consumers.recurring_charge_detection_consumer.list_user_transactions")
def test_fetch_transactions_respects_max_limit(mock_list_user_txs):
    """Test that fetching stops at 10,000 transactions"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Simulate many pages that would exceed 10k
    def side_effect(*args, **kwargs):
        # Return 1000 transactions per page with a next key
        txs = [_create_test_transaction() for _ in range(1000)]
        return (txs, {"lastKey": "next"}, 1000)
    
    mock_list_user_txs.side_effect = side_effect
    
    result = consumer._fetch_transactions("test-user-id", None)
    
    # Should stop at 10,000 transactions
    assert len(result) == 10000
    assert mock_list_user_txs.call_count == 10  # 10 pages of 1000 each


# ==============================================================================
# Test Prediction Generation
# ==============================================================================


def test_generate_predictions_success():
    """Test successful prediction generation"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock patterns - use PatternCreate since that's what detect_recurring_patterns returns
    patterns = [_create_test_pattern()]
    
    # Mock prediction - predict_next_occurrence returns RecurringChargePredictionCreate
    from models.recurring_charge import RecurringChargePredictionCreate
    prediction = RecurringChargePredictionCreate(
        patternId=uuid.uuid4(),
        nextExpectedDate=int(datetime.now().timestamp() * 1000),
        expectedAmount=Decimal("15.99"),
        confidence=0.9,
        daysUntilDue=15,
        amountRange={"min": Decimal("15.99"), "max": Decimal("15.99")},
    )
    
    with patch("src.consumers.recurring_charge_detection_consumer.save_prediction_in_db") as mock_save:
        consumer.prediction_service.predict_next_occurrence = Mock(return_value=prediction)
        
        # Generate predictions
        count = consumer._generate_predictions("test-user-id", patterns)
        
        assert count == 1
        assert mock_save.called


def test_generate_predictions_handles_errors():
    """Test prediction generation handles errors gracefully"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock patterns - use PatternCreate
    patterns = [_create_test_pattern() for _ in range(3)]
    
    # Mock prediction service to fail for some patterns
    def mock_predict(pattern):
        if pattern == patterns[1]:
            raise ValueError("Cannot predict irregular pattern")
        return None
    
    consumer.prediction_service.predict_next_occurrence = Mock(side_effect=mock_predict)
    
    # Should not raise, should continue with other patterns
    result_count = consumer._generate_predictions("test-user-id", patterns)
    
    # Should have attempted all patterns
    assert consumer.prediction_service.predict_next_occurrence.call_count == 3
    # No predictions should be saved since all return None or error
    assert result_count == 0


# ==============================================================================
# Test Operation Status Updates
# ==============================================================================


@patch("src.consumers.recurring_charge_detection_consumer.operation_tracking_service")
def test_update_operation_status_success(mock_tracking):
    """Test operation status update"""
    consumer = RecurringChargeDetectionConsumer()
    
    from services.operation_tracking_service import OperationStatus
    consumer._update_operation_status(
        operation_id="op_123",
        status=OperationStatus.IN_PROGRESS,
        progress=50,
        step_description="Processing",
    )
    
    assert mock_tracking.update_operation_status.called
    call_args = mock_tracking.update_operation_status.call_args
    assert call_args[1]["operation_id"] == "op_123"
    assert call_args[1]["status"] == OperationStatus.IN_PROGRESS
    assert call_args[1]["progress_percentage"] == 50


@patch("src.consumers.recurring_charge_detection_consumer.operation_tracking_service")
def test_update_operation_status_handles_failure(mock_tracking):
    """Test operation status update handles failures gracefully"""
    consumer = RecurringChargeDetectionConsumer()
    
    # Mock tracking service to fail
    mock_tracking.update_operation_status.side_effect = Exception("Tracking failed")
    
    # Should not raise exception
    from services.operation_tracking_service import OperationStatus
    consumer._update_operation_status(
        operation_id="op_123",
        status=OperationStatus.IN_PROGRESS,
        progress=50,
        step_description="Processing",
    )
    
    # Should have attempted the update
    assert mock_tracking.update_operation_status.called

