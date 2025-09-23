# Event-Driven File Deletion System Design

## Overview

This document describes the implementation of an event-driven file deletion system that coordinates multiple consumers to ensure proper processing before file deletion occurs. The system replaces direct synchronous file deletion with an asynchronous, coordinated approach.

## Problem Statement

Previously, file deletion was performed synchronously in a single handler, which:
- Deleted transactions immediately
- Deleted file content from S3
- Deleted file metadata from DynamoDB
- Updated account derived values

This approach didn't allow other consumers (analytics, categorization, etc.) to process the file and its transactions before deletion, potentially losing important data processing opportunities.

## Solution Architecture

### Event Flow

```
1. User requests file deletion
   ↓
2. FileDeleteRequestedEvent published
   ↓
3. Multiple consumers process the file/transactions while they still exist
   ↓
4. Each consumer publishes ConsumerCompletionEvent when done
   ↓
5. File Deletion Consumer waits for all expected consumers
   ↓
6. Actual file deletion performed
   ↓
7. FileDeletedEvent published for cleanup notifications
```

### Key Components

#### 1. Events

**FileDeleteRequestedEvent**
- Published when file deletion is initiated
- Contains file metadata and coordination ID
- Allows consumers to process while file/transactions still exist

**ConsumerCompletionEvent**
- Published by consumers when they finish processing
- Contains coordination ID and processing status
- Enables coordination between multiple consumers

**FileDeletedEvent**
- Published after actual deletion is complete
- Used for cleanup and notifications

#### 2. File Deletion Consumer

**Location**: `backend/src/consumers/file_deletion_consumer.py`

**Responsibilities**:
- Coordinates file deletion across multiple consumers
- Waits for all expected consumers to signal completion
- Performs actual file deletion after coordination
- Handles timeout scenarios
- Publishes completion events

**Coordination Logic**:
- Maintains in-memory coordination state
- Tracks expected vs completed consumers
- Implements timeout mechanism (5 minutes default)
- Proceeds with deletion when all consumers complete or timeout occurs

#### 3. Updated Consumers

**Analytics Consumer** (`analytics_consumer.py`):
- Listens to `file.delete_requested` events
- Queues analytics processing for affected data
- Publishes completion event when done

**Categorization Consumer** (`categorization_consumer.py`):
- Listens to `file.delete_requested` events
- Processes transactions for categorization before deletion
- Publishes completion event when done

#### 4. Updated File Operations Handler

**Location**: `backend/src/handlers/file_operations.py`

**Changes**:
- `delete_file_handler` now publishes `FileDeleteRequestedEvent`
- Returns HTTP 202 (Accepted) instead of 200 (OK)
- Includes coordination ID in response
- Maintains fallback to direct deletion if events disabled

### Configuration

#### Environment Variables

- `ENABLE_EVENT_PUBLISHING`: Enable/disable event-driven approach
- `COORDINATION_TIMEOUT_MINUTES`: How long to wait for consumers (default: 5)
- `EXPECTED_CONSUMERS`: Comma-separated list of consumers to wait for

#### Expected Consumers

Currently configured to wait for:
- `analytics_consumer`
- `categorization_consumer`

Additional consumers can be added by updating the `EXPECTED_CONSUMERS` environment variable.

## Infrastructure

### EventBridge Rules

**File Deletion Events Rule**:
- Matches `file.delete_requested` and `consumer.completion` events
- Routes to File Deletion Consumer Lambda

**Updated Analytics Rule**:
- Added `file.delete_requested` to event pattern
- Triggers analytics processing before deletion

**Updated Categorization Rule**:
- Added `file.delete_requested` to event pattern
- Triggers categorization processing before deletion

### Lambda Functions

**File Deletion Consumer Lambda**:
- Runtime: Python 3.9
- Timeout: 5 minutes
- Memory: 512 MB
- Environment variables for coordination configuration

## Coordination Mechanism

### How It Works

1. **Registration**: When `FileDeleteRequestedEvent` is received, coordination state is created with:
   - Coordination ID (UUID)
   - User ID and File ID
   - Set of expected consumers
   - Start timestamp

2. **Tracking**: As consumers complete processing, they publish `ConsumerCompletionEvent`:
   - Consumer name is added to completed set
   - Processing status is recorded
   - Coordination readiness is evaluated

3. **Completion**: Deletion proceeds when:
   - All expected consumers have completed, OR
   - Timeout period has elapsed (5 minutes default)

4. **Cleanup**: Coordination state is cleaned up after deletion

### Timeout Handling

If consumers don't complete within the timeout period:
- Warning is logged with missing consumers
- Deletion proceeds anyway to prevent indefinite blocking
- System remains resilient to consumer failures

### Error Handling

- Consumer failures are logged but don't block deletion
- Failed consumers can publish completion events with error status
- Coordination continues even if some consumers fail
- Timeout ensures system doesn't hang indefinitely

## Benefits

### 1. Data Processing Preservation
- Analytics can process data before deletion
- Categorization can complete before transactions are removed
- Other consumers can perform cleanup or archival

### 2. System Resilience
- Timeout prevents indefinite blocking
- Consumer failures don't prevent deletion
- Fallback to direct deletion if events disabled

### 3. Scalability
- Easy to add new consumers to coordination
- Event-driven architecture scales naturally
- Asynchronous processing improves responsiveness

### 4. Observability
- Coordination events provide audit trail
- Consumer completion tracking
- Timeout and error logging

## API Changes

### File Deletion Endpoint

**Before**:
```http
DELETE /files/{id}
Response: 200 OK
{
  "message": "File deleted successfully",
  "fileId": "uuid",
  "metadata": {
    "transactionsDeleted": 42
  }
}
```

**After**:
```http
DELETE /files/{id}
Response: 202 Accepted
{
  "message": "File deletion initiated successfully",
  "fileId": "uuid",
  "coordinationId": "coordination-uuid",
  "metadata": {
    "transactionCount": 42,
    "status": "deletion_requested"
  }
}
```

### Backward Compatibility

- Fallback to synchronous deletion if `ENABLE_EVENT_PUBLISHING=false`
- Existing error handling preserved
- Same authorization and validation logic

## Monitoring and Debugging

### CloudWatch Metrics

- Consumer completion rates
- Coordination timeout occurrences
- File deletion success/failure rates
- Processing time metrics

### Logging

- Structured JSON logs for coordination events
- Consumer completion tracking
- Timeout and error scenarios
- File deletion audit trail

### Debugging

1. **Check coordination state**: Look for coordination ID in logs
2. **Track consumer completion**: Search for completion events by coordination ID
3. **Monitor timeouts**: Check for timeout warnings in File Deletion Consumer logs
4. **Verify event publishing**: Ensure events are being published to EventBridge

## Testing Strategy

### Unit Tests

- Event creation and serialization
- Coordination logic (completion tracking, timeout handling)
- Consumer completion event publishing
- Error scenarios and fallbacks

### Integration Tests

- End-to-end file deletion flow
- Multiple consumer coordination
- Timeout scenarios
- Event publishing and consumption

### Load Testing

- High-volume file deletions
- Consumer performance under load
- Coordination scalability
- EventBridge throughput

## Future Enhancements

### 1. Dynamic Consumer Discovery
- Auto-discover consumers instead of static configuration
- Consumer registration mechanism
- Health checks for active consumers

### 2. Priority-Based Coordination
- Critical vs optional consumers
- Proceed if critical consumers complete
- Configurable consumer priorities

### 3. Retry Mechanisms
- Retry failed consumer processing
- Exponential backoff for coordination
- Dead letter queue for failed coordinations

### 4. Enhanced Monitoring
- Real-time coordination dashboards
- Consumer performance metrics
- Alerting for coordination failures

## Deployment Considerations

### Rolling Deployment

1. Deploy new consumers first (backward compatible)
2. Deploy File Deletion Consumer
3. Update EventBridge rules
4. Enable event publishing via environment variable
5. Monitor coordination success rates

### Rollback Plan

1. Disable event publishing (`ENABLE_EVENT_PUBLISHING=false`)
2. System falls back to direct deletion
3. Remove new infrastructure if needed
4. Revert consumer changes

### Configuration Management

- Environment-specific consumer lists
- Timeout configuration per environment
- Feature flags for gradual rollout

## Security Considerations

### Authorization

- Same file ownership validation as before
- Consumer completion events include user context
- Coordination IDs are UUIDs (not guessable)

### Data Protection

- File and transaction data remains available during coordination
- No sensitive data in coordination events
- Proper cleanup after deletion

### Access Control

- Lambda execution roles have minimal required permissions
- EventBridge rules restrict event sources
- S3 deletion permissions only for File Deletion Consumer

## Conclusion

The event-driven file deletion system provides a robust, scalable solution for coordinating multiple consumers before file deletion. It maintains system resilience through timeout mechanisms while enabling proper data processing by all interested consumers.

The implementation preserves backward compatibility and provides clear monitoring and debugging capabilities. The system can be extended to support additional consumers and enhanced coordination mechanisms as needed.
