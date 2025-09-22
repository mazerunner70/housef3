# Event-Driven File Processing Migration

## Overview

This document describes the migration from direct S3-triggered file processing to an event-driven architecture using EventBridge. The new architecture provides better scalability, observability, and separation of concerns.

## Architecture Changes

### Before (Direct S3 Processing)
```
File Upload → S3 ObjectCreated → File Processor Lambda → Direct Processing
```

### After (Event-Driven Processing)
```
File Upload → S3 ObjectCreated → S3 Event Handler → FileUploadedEvent → EventBridge
                                                                           ↓
EventBridge → File Processor Consumer → FileProcessedEvent → EventBridge
                                                                ↓
EventBridge → [Analytics, Categorization, Audit] Consumers
```

## New Components

### 1. S3 Event Handler (`handlers/s3_event_handler.py`)
- **Purpose**: Lightweight handler that publishes FileUploadedEvent to EventBridge
- **Trigger**: S3 ObjectCreated events
- **Actions**: 
  - Extracts file metadata from S3
  - Publishes FileUploadedEvent with file details
  - Handles restore package filtering

### 2. File Processor Consumer (`consumers/file_processor_consumer.py`)
- **Purpose**: Processes uploaded files and extracts transactions
- **Trigger**: FileUploadedEvent from EventBridge
- **Actions**:
  - Downloads and analyzes files
  - Extracts transactions using existing file processor service
  - Publishes FileProcessedEvent with transaction IDs

### 3. Updated EventBridge Rules
- **File Processor Rule**: Routes `file.uploaded` events to File Processor Consumer
- **Updated Categorization Rule**: Now listens for `file.processed` events instead of `transactions.created`
- **Analytics Rule**: Already configured for `file.processed` events

## Infrastructure Changes

### Lambda Functions
- **Replaced**: `file-processor` → `s3-event-handler`
- **Added**: `file-processor-consumer`
- **Updated**: S3 bucket notifications now trigger `s3-event-handler`

### EventBridge Configuration
- **New Rule**: `file-processor-events` for routing file upload events
- **Updated Rule**: `categorization-events` now processes `file.processed` events
- **Existing Rules**: Analytics and audit rules remain unchanged

### Environment Variables
- **S3 Event Handler**: Minimal config (bucket, event bus)
- **File Processor Consumer**: Full processing environment (all tables, buckets)

## Benefits

### 1. **Improved Scalability**
- Event-driven architecture allows independent scaling of components
- File processing can handle higher concurrency through EventBridge

### 2. **Better Error Handling**
- Failed events automatically route to Dead Letter Queue
- Retry policies configured per consumer type
- Comprehensive error logging and metrics

### 3. **Enhanced Observability**
- All events stored in audit trail
- Structured logging for CloudWatch Insights
- Event replay capability for debugging

### 4. **Separation of Concerns**
- S3 handler only publishes events (fast, lightweight)
- File processing isolated in dedicated consumer
- Other consumers react to processing results

### 5. **Shadow Mode Support**
- Configurable event publishing vs direct triggers
- Gradual migration capability
- Backward compatibility during transition

## Deployment Instructions

### 1. Deploy Infrastructure
```bash
cd infrastructure/terraform
terraform plan
terraform apply
```

### 2. Build and Deploy Lambda Functions
```bash
cd backend
./build_lambda_package.sh
```

### 3. Verify EventBridge Rules
- Check that `file-processor-events` rule is active
- Verify `categorization-events` rule updated to `file.processed`
- Confirm all consumers have proper permissions

### 4. Test File Upload Flow
1. Upload a test file through the frontend
2. Check CloudWatch logs for:
   - S3 Event Handler: FileUploadedEvent published
   - File Processor Consumer: File processing completed
   - Analytics/Categorization Consumers: Events received

### 5. Monitor and Validate
- Check EventBridge metrics for event throughput
- Monitor Dead Letter Queue for failed events
- Verify transaction extraction still works correctly

## Configuration Options

### Shadow Mode Variables
- `ENABLE_EVENT_PUBLISHING`: Controls EventBridge event publishing (default: true)
- `ENABLE_DIRECT_TRIGGERS`: Controls legacy direct analytics triggering (default: false)

### Consumer Timeouts
- **S3 Event Handler**: 60 seconds (lightweight event publishing)
- **File Processor Consumer**: 600 seconds (10 minutes for file processing)
- **Other Consumers**: 300 seconds (5 minutes for business logic)

## Rollback Plan

If issues arise, rollback is possible by:

1. **Revert S3 Bucket Notification**:
   ```hcl
   lambda_function_arn = aws_lambda_function.file_processor.arn
   ```

2. **Disable Event Publishing**:
   ```bash
   export ENABLE_EVENT_PUBLISHING=false
   export ENABLE_DIRECT_TRIGGERS=true
   ```

3. **Restore Original File Processor**:
   - Redeploy original `file_processor.py` as Lambda function
   - Update S3 notification to trigger original processor

## Testing

### Unit Tests
- Event structure validation ✓
- Consumer initialization ✓
- Error handling paths

### Integration Tests
- End-to-end file upload flow
- EventBridge event routing
- Consumer processing validation

### Performance Tests
- File processing throughput
- Event publishing latency
- Consumer scaling behavior

## Monitoring

### Key Metrics
- **Event Publishing Rate**: FileUploadedEvent/FileProcessedEvent throughput
- **Processing Latency**: Time from upload to transaction extraction
- **Error Rates**: Failed events in Dead Letter Queue
- **Consumer Health**: Lambda function success/error rates

### CloudWatch Dashboards
- EventBridge event flow visualization
- Consumer performance metrics
- Error rate trending
- Processing time distribution

## Next Steps

1. **Deploy and Test**: Complete infrastructure deployment and validation
2. **Performance Tuning**: Optimize consumer memory/timeout settings
3. **Monitoring Setup**: Configure CloudWatch alarms and dashboards
4. **Documentation**: Update API documentation with new event flow
5. **Training**: Brief team on new architecture and debugging approaches

## Files Modified

### New Files
- `backend/src/handlers/s3_event_handler.py`
- `backend/src/consumers/file_processor_consumer.py`
- `backend/test_event_driven_file_processing.py`

### Modified Files
- `infrastructure/terraform/eventbridge_rules.tf`
- `infrastructure/terraform/lambda_consumers.tf`
- `infrastructure/terraform/lambda.tf`
- `infrastructure/terraform/s3_file_storage.tf`

### Event Models
- `FileUploadedEvent`: Already defined in `models/events.py`
- `FileProcessedEvent`: Already defined in `models/events.py`

This migration maintains full backward compatibility while providing a more robust, scalable, and observable file processing architecture.
