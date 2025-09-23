# Event-Driven File Deletion Approval System

## Architecture Overview

```
API Call → L1 → EventBridge → [L2, L3] → L4 → L5
                                ↓        ↓    ↓
                            Vote Events → Aggregator → Final Decision
```

## Event Flow

### 1. L1 - File Operations Handler
**Receives**: API DELETE /files/{fileId}
**Sends**: `file.deletion.requested`

```json
{
  "source": "file.service",
  "detail-type": "file.deletion.requested", 
  "detail": {
    "fileId": "abc-123",
    "userId": "user-456",
    "accountId": "acc-789",
    "fileName": "transactions.csv",
    "transactionCount": 150,
    "requestId": "req-xyz"
  }
}
```

### 2. L2 - Category Management Consumer
**Receives**: `file.deletion.requested`
**Sends**: `file.deletion.vote`

```json
{
  "source": "category.service",
  "detail-type": "file.deletion.vote",
  "detail": {
    "fileId": "abc-123",
    "requestId": "req-xyz", 
    "voter": "category_manager",
    "decision": "proceed", // or "deny"
    "reason": "No active categorization rules affected",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### 3. L3 - Analytics Management Consumer  
**Receives**: `file.deletion.requested`
**Sends**: `file.deletion.vote`

```json
{
  "source": "analytics.service", 
  "detail-type": "file.deletion.vote",
  "detail": {
    "fileId": "abc-123",
    "requestId": "req-xyz",
    "voter": "analytics_manager", 
    "decision": "proceed", // or "deny"
    "reason": "Analytics processing complete",
    "timestamp": "2025-01-15T10:30:15Z"
  }
}
```

### 4. L4 - Deletion Aggregator
**Receives**: `file.deletion.vote`
**Sends**: `file.deletion.approved` OR `file.deletion.denied`

**DynamoDB Tracking Table**:
```
pk: FILE#abc-123#req-xyz
sk: VOTES
voters_required: ["category_manager", "analytics_manager"]
votes_received: {
  "category_manager": {"decision": "proceed", "timestamp": "..."},
  "analytics_manager": {"decision": "proceed", "timestamp": "..."}
}
status: "approved" // or "denied" or "waiting"
created_at: "2025-01-15T10:30:00Z"
ttl: 1737024600 // 24 hours
```

**Approval Event**:
```json
{
  "source": "deletion.aggregator",
  "detail-type": "file.deletion.approved",
  "detail": {
    "fileId": "abc-123", 
    "requestId": "req-xyz",
    "approvedBy": ["category_manager", "analytics_manager"],
    "allVotes": {...},
    "timestamp": "2025-01-15T10:30:20Z"
  }
}
```

### 5. L5 - Deletion Executor
**Receives**: `file.deletion.approved`
**Action**: Delete file + transactions
**Sends**: `file.deleted`

## Implementation Benefits

### ✅ **Advantages**
1. **Decoupled**: Each service votes independently
2. **Extensible**: Easy to add new voters (L6, L7, etc.)
3. **Configurable**: Change required voters without code changes
4. **Auditable**: Full vote history in DynamoDB
5. **Resilient**: Voters can fail independently
6. **Timeout Handling**: Aggregator can timeout missing votes

### ✅ **EventBridge Rules**
```terraform
# Route deletion requests to voters
resource "aws_cloudwatch_event_rule" "deletion_requests" {
  event_pattern = jsonencode({
    source = ["file.service"]
    detail-type = ["file.deletion.requested"]
  })
}

# Route votes to aggregator  
resource "aws_cloudwatch_event_rule" "deletion_votes" {
  event_pattern = jsonencode({
    source = ["category.service", "analytics.service"]
    detail-type = ["file.deletion.vote"]
  })
}

# Route approvals to executor
resource "aws_cloudwatch_event_rule" "deletion_approvals" {
  event_pattern = jsonencode({
    source = ["deletion.aggregator"] 
    detail-type = ["file.deletion.approved"]
  })
}
```

## Configuration-Driven Voters

The aggregator can be configured with required voters:

```python
DELETION_VOTERS_CONFIG = {
    "default": ["category_manager", "analytics_manager"],
    "large_files": ["category_manager", "analytics_manager", "backup_manager"],
    "critical_accounts": ["category_manager", "analytics_manager", "compliance_manager"]
}

def get_required_voters(file_info):
    if file_info.transaction_count > 1000:
        return DELETION_VOTERS_CONFIG["large_files"]
    elif file_info.account_type == "business":
        return DELETION_VOTERS_CONFIG["critical_accounts"] 
    else:
        return DELETION_VOTERS_CONFIG["default"]
```

## Error Handling

### Denial Scenarios
- Any voter sends `"decision": "deny"` → Immediate denial
- Timeout (no vote received) → Configurable (deny by default)
- Voter error/exception → Configurable (deny by default)

### Retry Logic
- Voters can retry their own processing
- Aggregator handles duplicate votes (idempotent)
- Timeout and cleanup via DynamoDB TTL

## Monitoring & Observability

### CloudWatch Metrics
- `DeletionRequests.Count`
- `DeletionVotes.Count` (by voter)
- `DeletionApprovals.Count`
- `DeletionDenials.Count`
- `VoterTimeout.Count`

### Tracing
Each event carries `requestId` for end-to-end tracing across all services.
