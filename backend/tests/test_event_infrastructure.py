"""
Tests for the event infrastructure including event models, service, and consumers.
"""
import json
import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import our event infrastructure
from models.events import (
    BaseEvent, FileProcessedEvent, 
    TransactionUpdatedEvent, AccountCreatedEvent
)
from services.event_service import EventService
from consumers.base_consumer import BaseEventConsumer, EventProcessingError


class TestEventModels:
    """Test event model creation and serialization"""
    
    def test_base_event_creation(self):
        """Test creating a base event"""
        event = BaseEvent(
            event_id=str(uuid.uuid4()),
            event_type="test.event",
            event_version="1.0",
            timestamp=int(datetime.now().timestamp() * 1000),
            source="test.service",
            user_id="test-user",
            data={"key": "value"}
        )
        
        assert event.event_id is not None
        assert event.event_type == "test.event"
        assert event.source == "test.service"
        assert event.user_id == "test-user"
        assert event.data is not None and event.data["key"] == "value"
    
    def test_event_bridge_format(self):
        """Test converting event to EventBridge format"""
        event = BaseEvent(
            event_id="test-123",
            event_type="test.event",
            event_version="1.0",
            timestamp=1234567890000,
            source="test.service",
            user_id="test-user",
            data={"key": "value"}
        )
        
        eb_format = event.to_eventbridge_format()
        
        assert eb_format["Source"] == "test.service"
        assert eb_format["DetailType"] == "test.event"
        
        detail = json.loads(eb_format["Detail"])
        assert detail["eventId"] == "test-123"
        assert detail["userId"] == "test-user"
        assert detail["data"]["key"] == "value"  # detail is guaranteed to have data
    
    def test_file_processed_event(self):
        """Test FileProcessedEvent creation"""
        event = FileProcessedEvent(
            user_id="test-user",
            file_id="file-123",
            account_id="account-456",
            transaction_count=10,
            duplicate_count=2
        )
        
        assert event.event_type == "file.processed"
        assert event.source == "transaction.service"
        assert event.user_id == "test-user"
        assert event.data is not None
        assert event.data["fileId"] == "file-123"
        assert event.data["transactionCount"] == 10
        assert event.data["duplicateCount"] == 2
    
    def test_file_processed_event_with_transactions(self):
        """Test FileProcessedEvent with transaction IDs"""
        event = FileProcessedEvent(
            user_id="test-user",
            file_id="file-123",
            account_id="account-456",
            transaction_count=3,
            duplicate_count=0,
            processing_status='success',
            transaction_ids=["tx-1", "tx-2", "tx-3"]
        )
        
        assert event.event_type == "file.processed"
        assert event.data is not None
        assert event.data["transactionCount"] == 3
        assert len(event.data["transactionIds"]) == 3
        assert "tx-1" in event.data["transactionIds"]


class TestEventService:
    """Test event publishing service"""
    
    @patch('utils.event_dao.get_event_bus_name')
    def test_event_service_initialization(self, mock_get_event_bus_name):
        """Test EventService initialization"""
        mock_get_event_bus_name.return_value = "test-bus"
        
        service = EventService()
        
        assert service.event_bus_name == "test-bus"
        mock_get_event_bus_name.assert_called_once()
    
    @patch('utils.event_dao.publish_event_to_eventbridge')
    def test_publish_event_success(self, mock_publish_event):
        """Test successful event publishing"""
        mock_publish_event.return_value = True
        
        service = EventService()
        
        event = FileProcessedEvent(
            user_id="test-user",
            file_id="file-123",
            account_id="account-456",
            transaction_count=5,
            duplicate_count=1
        )
        
        result = service.publish_event(event)
        
        assert result is True
        mock_publish_event.assert_called_once()
        
        # Verify the event was converted to EventBridge format before calling DAO
        call_args = mock_publish_event.call_args[0]
        eventbridge_entry = call_args[0]
        assert eventbridge_entry['Source'] == 'transaction.service'
        assert eventbridge_entry['DetailType'] == 'file.processed'
        assert 'EventBusName' not in eventbridge_entry  # DAO should add this
    
    @patch('utils.event_dao.publish_event_to_eventbridge')
    def test_publish_event_failure(self, mock_publish_event):
        """Test event publishing failure handling"""
        mock_publish_event.return_value = False
        
        service = EventService()
        
        event = BaseEvent(
            event_id="test-123",
            event_type="test.event",
            event_version="1.0",
            timestamp=1234567890000,
            source="test.service",
            user_id="test-user"
        )
        
        result = service.publish_event(event)
        
        assert result is False
        mock_publish_event.assert_called_once()
    
    @patch('utils.event_dao.publish_events_batch_to_eventbridge')
    def test_publish_events_batch(self, mock_publish_batch):
        """Test batch event publishing"""
        mock_publish_batch.return_value = 5
        
        service = EventService()
        
        events = [
            FileProcessedEvent(
                user_id="test-user",
                file_id=f"file-{i}",
                account_id="account-456",
                transaction_count=i + 1,
                duplicate_count=0
            )
            for i in range(5)
        ]
        
        result = service.publish_events_batch(events)  # type: ignore
        
        assert result == 5
        mock_publish_batch.assert_called_once()
        
        # Verify events were converted to EventBridge format
        call_args = mock_publish_batch.call_args[0]
        event_entries = call_args[0]
        assert len(event_entries) == 5
        assert all('Source' in entry for entry in event_entries)
        assert all('DetailType' in entry for entry in event_entries)
    
    @patch('utils.event_dao.eventbridge_health_check')
    def test_health_check(self, mock_health_check):
        """Test event service health check"""
        mock_health_check.return_value = {
            'status': 'healthy',
            'event_bus_name': 'test-bus',
            'event_bus_arn': 'arn:aws:events:eu-west-2:123456789:event-bus/test-bus'
        }
        
        service = EventService()
        
        health = service.health_check()
        
        assert health['status'] == 'healthy'
        assert health['event_bus_name'] == 'test-bus'
        assert 'event_bus_arn' in health
        mock_health_check.assert_called_once()


class MockTestConsumer(BaseEventConsumer):
    """Mock consumer for testing base consumer functionality"""
    
    def __init__(self):
        super().__init__("test_consumer")
        self.processed_events_list = []
    
    def should_process_event(self, event: BaseEvent) -> bool:
        # Process all events for testing
        return True
    
    def process_event(self, event: BaseEvent) -> None:
        # Simple processing - just record the event
        self.processed_events_list.append(event)
        
        # Simulate error for events with "error" in data
        if event.data and event.data.get("should_error"):
            raise ValueError("Simulated processing error")


class TestBaseConsumer:
    """Test base consumer functionality"""
    
    def test_consumer_initialization(self):
        """Test consumer initialization"""
        consumer = MockTestConsumer()
        
        assert consumer.consumer_name == "test_consumer"
        assert consumer.enable_metrics is True
        assert len(consumer.processed_events) == 0
    
    def test_process_single_event_success(self):
        """Test processing a single successful event"""
        consumer = MockTestConsumer()
        
        # Mock EventBridge event format
        event_payload = {
            'source': 'transaction.service',
            'detail-type': 'file.processed',
            'detail': json.dumps({
                'eventId': 'test-123',
                'eventVersion': '1.0',
                'timestamp': 1234567890000,
                'userId': 'test-user',
                'data': {'fileId': 'file-123'},
                'metadata': {}
            })
        }
        
        context = Mock()
        context.aws_request_id = 'request-123'
        context.get_remaining_time_in_millis = Mock(return_value=30000)
        
        result = consumer.handle_eventbridge_event(event_payload, context)
        
        assert result['statusCode'] == 200
        assert result['processed_count'] == 1
        assert result['failed_count'] == 0
        assert result['skipped_count'] == 0
        assert len(consumer.processed_events_list) == 1
        assert consumer.processed_events_list[0].event_id == 'test-123'
    
    def test_process_event_with_error(self):
        """Test processing an event that causes an error"""
        consumer = MockTestConsumer()
        
        # Event that will trigger an error
        event_payload = {
            'source': 'transaction.service',
            'detail-type': 'test.event',
            'detail': json.dumps({
                'eventId': 'error-123',
                'eventVersion': '1.0',
                'timestamp': 1234567890000,
                'userId': 'test-user',
                'data': {'should_error': True},
                'metadata': {}
            })
        }
        
        context = Mock()
        
        result = consumer.handle_eventbridge_event(event_payload, context)
        
        assert result['statusCode'] == 500  # Error should cause permanent failure
        assert result['failed_count'] == 1
        assert len(result['errors']) == 1
        assert result['errors'][0]['permanent'] is True
    
    def test_process_multiple_events(self):
        """Test processing multiple events in a batch"""
        consumer = MockTestConsumer()
        
        # SQS-style batch with multiple records
        event_payload = {
            'Records': [
                {
                    'body': json.dumps({
                        'source': 'transaction.service',
                        'detail-type': 'file.processed',
                        'detail': json.dumps({
                            'eventId': f'test-{i}',
                            'eventVersion': '1.0',
                            'timestamp': 1234567890000 + i,
                            'userId': 'test-user',
                            'data': {'fileId': f'file-{i}'},
                            'metadata': {}
                        })
                    })
                }
                for i in range(3)
            ]
        }
        
        context = Mock()
        
        result = consumer.handle_eventbridge_event(event_payload, context)
        
        assert result['statusCode'] == 200
        assert result['processed_count'] == 3
        assert result['failed_count'] == 0
        assert len(consumer.processed_events_list) == 3
    
    def test_duplicate_event_detection(self):
        """Test that duplicate events are skipped"""
        consumer = MockTestConsumer()
        
        # Same event twice
        event_payload = {
            'source': 'transaction.service',
            'detail-type': 'file.processed',
            'detail': json.dumps({
                'eventId': 'duplicate-123',
                'eventVersion': '1.0',
                'timestamp': 1234567890000,
                'userId': 'test-user',
                'data': {'fileId': 'file-123'},
                'metadata': {}
            })
        }
        
        context = Mock()
        
        # Process first time
        result1 = consumer.handle_eventbridge_event(event_payload, context)
        assert result1['processed_count'] == 1
        assert result1['skipped_count'] == 0
        
        # Process second time (should be skipped)
        result2 = consumer.handle_eventbridge_event(event_payload, context)
        assert result2['processed_count'] == 0
        assert result2['skipped_count'] == 1
        
        # Only one event should be in the processed list
        assert len(consumer.processed_events_list) == 1


if __name__ == "__main__":
    # Simple test runner for development
    import sys
    
    # Test event models
    print("Testing event models...")
    test_models = TestEventModels()
    test_models.test_base_event_creation()
    test_models.test_event_bridge_format()
    test_models.test_file_processed_event()
    test_models.test_file_processed_event_with_transactions()
    print("✅ Event models tests passed")
    
    # Test base consumer
    print("Testing base consumer...")
    test_consumer = TestBaseConsumer()
    test_consumer.test_consumer_initialization()
    test_consumer.test_process_single_event_success()
    test_consumer.test_process_multiple_events()
    test_consumer.test_duplicate_event_detection()
    print("✅ Base consumer tests passed")
    
    print("🎉 All tests passed!") 