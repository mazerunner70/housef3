# Phase 3 Testing Guide: Event Consumers Validation

This guide provides comprehensive testing procedures to validate the end-to-end event-driven architecture implementation.

## Overview

Phase 3 implements event consumers that process events published by the Phase 2 publishers. The complete flow is:

1. **Publishers** (file processor, transaction operations, account operations) publish events to EventBridge
2. **EventBridge** routes events to appropriate consumers based on rules
3. **Consumers** process events and perform actions (analytics queueing, categorization, auditing)

## Pre-Deployment Testing

### 1. Unit Testing Event Consumers

```bash
# Run the existing event infrastructure tests
cd backend
python -m pytest tests/test_event_infrastructure.py -v

# Test analytics consumer specifically
python -c "
from consumers.analytics_consumer import AnalyticsEventConsumer
from models.events import FileProcessedEvent
import json

# Create test event
event = FileProcessedEvent(
    user_id='test-user',
    file_id='test-file-123',
    account_id='test-account-456',
    transaction_count=5,
    duplicate_count=0,
    processing_status='success',
    transaction_ids=['tx-1', 'tx-2', 'tx-3', 'tx-4', 'tx-5']
)

# Test consumer processing
consumer = AnalyticsEventConsumer()
print(f'Should process: {consumer.should_process_event(event)}')
print(f'Event type: {event.event_type}')
print(f'Priority: {consumer.PRIORITY_MAP.get(event.event_type)}')
"
```

### 2. Validate Event Schema Compatibility

```bash
# Test event serialization/deserialization
python -c "
from models.events import FileProcessedEvent
import json

# Create and serialize event
event = FileProcessedEvent(
    user_id='test-user',
    file_id='test-file',
    account_id='test-account',
    transaction_count=3,
    duplicate_count=0,
    transaction_ids=['tx-1', 'tx-2', 'tx-3']
)

# Convert to EventBridge format
eb_format = event.to_eventbridge_format()
print('EventBridge format:')
print(json.dumps(eb_format, indent=2))

# Verify all required fields are present
required_fields = ['Source', 'DetailType', 'Detail']
for field in required_fields:
    assert field in eb_format, f'Missing {field}'
print('✅ EventBridge format validation passed')
"
```

## Deployment Testing

### 1. Deploy Infrastructure

```bash
# Deploy the new Lambda consumers
cd infrastructure/terraform
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"

# Verify consumer functions are deployed
aws lambda list-functions --query 'Functions[?contains(FunctionName, `consumer`)].{Name:FunctionName,Runtime:Runtime,Handler:Handler}'
```

### 2. Verify EventBridge Configuration

```bash
# Check EventBridge rules and targets
aws events list-rules --event-bus-name housef3-dev-events

# Verify each rule has targets
aws events list-targets-by-rule --rule housef3-dev-analytics-events --event-bus-name housef3-dev-events
aws events list-targets-by-rule --rule housef3-dev-categorization-events --event-bus-name housef3-dev-events
aws events list-targets-by-rule --rule housef3-dev-audit-events --event-bus-name housef3-dev-events
```

### 3. Test Event Publishing

```bash
# Test event publishing manually
aws events put-events --entries '[
  {
    "Source": "transaction.service",
    "DetailType": "Application Event",
    "Detail": "{\"eventId\":\"test-123\",\"eventType\":\"file.processed\",\"userId\":\"test-user\",\"data\":{\"fileId\":\"test-file\",\"transactionCount\":3,\"transactionIds\":[\"tx-1\",\"tx-2\",\"tx-3\"]}}",
    "EventBusName": "housef3-dev-events"
  }
]'
```

## End-to-End Testing

### 1. File Upload Test

**Scenario**: Upload a transaction file and verify complete event flow.

```bash
# 1. Enable event publishing for testing
export ENABLE_EVENT_PUBLISHING=true

# 2. Upload a test file through the UI or API
# 3. Monitor CloudWatch logs for event flow

# Check file processor logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-file-processor \
  --filter-pattern "FileProcessedEvent published" \
  --start-time $(date -d "5 minutes ago" +%s)000

# Check analytics consumer logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-analytics-consumer \
  --filter-pattern "Processing file.processed event" \
  --start-time $(date -d "5 minutes ago" +%s)000

# Check categorization consumer logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-categorization-consumer \
  --filter-pattern "Processing file.processed event" \
  --start-time $(date -d "5 minutes ago" +%s)000
```

### 2. Transaction Update Test

**Scenario**: Update a transaction and verify analytics events.

```bash
# 1. Update a transaction through the UI
# 2. Check transaction operations logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-transaction-operations \
  --filter-pattern "TransactionUpdatedEvent published" \
  --start-time $(date -d "2 minutes ago" +%s)000

# 3. Check analytics consumer processed it
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-analytics-consumer \
  --filter-pattern "Processing transaction.updated event" \
  --start-time $(date -d "2 minutes ago" +%s)000
```

### 3. Account Operations Test

**Scenario**: Create/update/delete account and verify events.

```bash
# Test account creation
# Monitor account operations logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-account-operations \
  --filter-pattern "AccountCreatedEvent published" \
  --start-time $(date -d "2 minutes ago" +%s)000
```

## Validation Checklist

### ✅ Event Publishing Validation

- [ ] File processor publishes `FileProcessedEvent` with transaction IDs
- [ ] Transaction operations publish `TransactionUpdatedEvent` and `TransactionsDeletedEvent`
- [ ] Account operations publish `AccountCreatedEvent`, `AccountUpdatedEvent`, `AccountDeletedEvent`
- [ ] All events include required fields (eventId, eventType, userId, data)
- [ ] Events are published to correct EventBridge bus

### ✅ Event Routing Validation

- [ ] Analytics events route to analytics consumer
- [ ] Categorization events route to categorization consumer  
- [ ] All events route to audit consumer
- [ ] Event routing rules work correctly
- [ ] Dead letter queues receive failed events

### ✅ Consumer Processing Validation

- [ ] Analytics consumer creates `AnalyticsProcessingStatus` records
- [ ] Categorization consumer applies rules to new transactions
- [ ] Audit consumer stores events in event store table
- [ ] Consumers handle errors gracefully
- [ ] Consumer metrics are logged to CloudWatch

### ✅ End-to-End Flow Validation

- [ ] File upload → events published → consumers process → analytics queued
- [ ] Transaction update → events published → analytics queued
- [ ] Account changes → events published → analytics queued
- [ ] Category suggestions created for new transactions
- [ ] Complete audit trail in event store

## Monitoring and Debugging

### CloudWatch Insights Queries

```sql
-- Event publishing metrics
fields @timestamp, @message
| filter @message like /FileProcessedEvent published/
| sort @timestamp desc
| limit 20

-- Analytics consumer metrics  
fields @timestamp, @message
| filter @message like /ANALYTICS_METRICS/
| sort @timestamp desc
| limit 20

-- Categorization consumer metrics
fields @timestamp, @message  
| filter @message like /CATEGORIZATION_METRICS/
| sort @timestamp desc
| limit 20

-- Error tracking across all consumers
fields @timestamp, @message
| filter @message like /ERROR/ or @message like /Failed/
| sort @timestamp desc
| limit 50
```

### Event Store Queries

```bash
# Check audit records in event store
aws dynamodb scan \
  --table-name housef3-dev-event-store \
  --filter-expression "eventType = :type" \
  --expression-attribute-values '{":type": {"S": "file.processed"}}' \
  --limit 5

# Check analytics status records
aws dynamodb scan \
  --table-name housef3-dev-analytics-status \
  --filter-expression "computationNeeded = :needed" \
  --expression-attribute-values '{":needed": {"BOOL": true}}' \
  --limit 10
```

### Performance Metrics

```bash
# Lambda execution metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=housef3-dev-analytics-consumer \
  --start-time $(date -d "1 hour ago" --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average,Maximum

# EventBridge metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name SuccessfulInvocations \
  --dimensions Name=RuleName,Value=housef3-dev-analytics-events \
  --start-time $(date -d "1 hour ago" --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum
```

## Troubleshooting Common Issues

### Event Not Published

1. Check publisher logs for event creation errors
2. Verify EventBridge bus permissions
3. Check shadow mode environment variables
4. Validate event schema format

### Event Not Routed to Consumer

1. Verify EventBridge rule patterns match event types
2. Check consumer Lambda function deployment
3. Verify IAM permissions for EventBridge to invoke Lambda
4. Check dead letter queue for failed deliveries

### Consumer Processing Failures

1. Check consumer logs for error details
2. Verify DynamoDB table permissions
3. Check consumer timeout settings
4. Validate event data format compatibility

### Missing Analytics Processing

1. Verify analytics consumer creates status records
2. Check analytics processor picks up queued work
3. Monitor analytics processing Lambda logs
4. Validate analytics status table permissions

## Success Criteria

✅ **Phase 3 is successful when**:

1. **Event Flow Complete**: File upload → events published → consumers process → analytics queued
2. **Zero Data Loss**: All events are captured and processed
3. **Performance Acceptable**: Event processing under 30 seconds end-to-end
4. **Error Rate Low**: Consumer error rate below 1%
5. **Audit Complete**: All events logged in event store
6. **Analytics Functional**: Analytics processing continues to work via events
7. **Categorization Active**: New transactions get category suggestions

## Next Steps After Phase 3

1. **Monitor for 24-48 hours** in shadow mode
2. **Compare results** between event-driven and direct approaches
3. **Validate performance** meets requirements
4. **Prepare for cutover** to events-only mode
5. **Plan Phase 4** - remove direct triggers and enable pure event mode 