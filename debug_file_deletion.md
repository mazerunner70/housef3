# Debugging File Deletion Events

## CloudWatch Insights Queries

### 1. Find File Deletion Request by File ID
```sql
fields @timestamp, @message
| filter @message like /FileDeleteRequestedEvent/
| filter @message like /YOUR_FILE_ID_HERE/
| sort @timestamp desc
| limit 20
```

### 2. Trace Complete Deletion Flow by Coordination ID
```sql
fields @timestamp, @message, @logStream
| filter @message like /COORDINATION_ID_HERE/
| sort @timestamp asc
| limit 50
```

### 3. Find Consumer Completion Events
```sql
fields @timestamp, @message
| filter @message like /ConsumerCompletionEvent/
| filter @message like /COORDINATION_ID_HERE/
| sort @timestamp asc
```

### 4. Check for Coordination Timeouts
```sql
fields @timestamp, @message
| filter @message like /timed out/
| sort @timestamp desc
| limit 10
```

## AWS CLI Commands

### Get Recent File Deletion Events
```bash
# Get coordination events from file deletion consumer
aws logs start-query \
  --log-group-name "/aws/lambda/dev-file-deletion-consumer" \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /coordination/ | sort @timestamp desc'

# Get the query ID from the response, then:
aws logs get-query-results --query-id YOUR_QUERY_ID
```

### Search for Specific File ID
```bash
FILE_ID="your-file-id-here"

# Search across all relevant log groups
for LOG_GROUP in "/aws/lambda/dev-file-operations" "/aws/lambda/dev-file-deletion-consumer" "/aws/lambda/dev-analytics-consumer" "/aws/lambda/dev-categorization-consumer"; do
  echo "=== Searching $LOG_GROUP ==="
  aws logs filter-log-events \
    --log-group-name "$LOG_GROUP" \
    --filter-pattern "$FILE_ID" \
    --start-time $(date -d '1 hour ago' +%s)000 \
    --query 'events[*].[eventTime,message]' \
    --output table
done
```

## What to Look For

### 1. Successful Flow
```
1. File Operations: "FileDeleteRequestedEvent published for file {fileId} with coordination ID {coordId}"
2. Analytics Consumer: "Processing file.delete_requested event {eventId} for user {userId}"
3. Analytics Consumer: "Published completion event for coordination {coordId}, status: completed"
4. Categorization Consumer: "Processing file.delete_requested event {eventId} for categorization"
5. Categorization Consumer: "Published completion event for coordination {coordId}, status: completed"
6. File Deletion Consumer: "All consumers completed for coordination {coordId}, ready for deletion"
7. File Deletion Consumer: "Executing file deletion for file {fileId}"
8. File Deletion Consumer: "FileDeletedEvent published for file {fileId}"
```

### 2. Timeout Scenario
```
1-5. (Same as above, but one consumer doesn't complete)
6. File Deletion Consumer: "Coordination {coordId} timed out after PT5M, proceeding with deletion. Missing consumers: [consumer_name]"
7-8. (Deletion proceeds anyway)
```

### 3. Error Scenarios
```
- "Failed to publish FileDeleteRequestedEvent for file {fileId}"
- "Error processing categorization event {eventId}: {error}"
- "Failed to publish completion event for coordination {coordId}"
```

## Real-Time Monitoring

### CloudWatch Dashboard Query
Create a dashboard with these widgets:

1. **Event Count**: Count of FileDeleteRequestedEvent
2. **Completion Rate**: Ratio of completed vs requested deletions
3. **Timeout Rate**: Count of coordination timeouts
4. **Error Rate**: Count of failed events

### Custom Metrics (if implemented)
```bash
# View custom metrics (if you add them to the consumers)
aws cloudwatch get-metric-statistics \
  --namespace "HouseF3/FileDelection" \
  --metric-name "CoordinationTimeouts" \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum
```
