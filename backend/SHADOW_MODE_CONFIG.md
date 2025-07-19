# Shadow Mode Configuration Guide

This guide explains how to configure environment variables to control the event-driven architecture deployment modes.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_EVENT_PUBLISHING` | `true` | Enable publishing events to EventBridge |
| `ENABLE_DIRECT_TRIGGERS` | `false` | Enable direct analytics triggering (legacy mode) |

## Deployment Modes

### 1. Events-Only Mode (Production Target)
```bash
ENABLE_EVENT_PUBLISHING=true
ENABLE_DIRECT_TRIGGERS=false
```
- **Use case**: Final production deployment
- **Behavior**: Only events are published, no direct triggers
- **Risk**: Low (after validation)

### 2. Shadow Mode (Testing/Validation)
```bash
ENABLE_EVENT_PUBLISHING=true
ENABLE_DIRECT_TRIGGERS=true
```
- **Use case**: Side-by-side comparison and validation
- **Behavior**: Both events AND direct triggers run in parallel
- **Risk**: Medium (dual processing overhead)

### 3. Direct-Only Mode (Legacy Fallback)
```bash
ENABLE_EVENT_PUBLISHING=false
ENABLE_DIRECT_TRIGGERS=true
```
- **Use case**: Emergency rollback scenario
- **Behavior**: Only direct triggers, no events
- **Risk**: Low (original behavior)

### 4. Disabled Mode (Testing Only)
```bash
ENABLE_EVENT_PUBLISHING=false
ENABLE_DIRECT_TRIGGERS=false
```
- **Use case**: Testing without any analytics triggers
- **Behavior**: No analytics processing triggered
- **Risk**: High (analytics will become stale)

## Migration Strategy

### Phase 1: Deploy with Shadow Mode
1. Deploy with `ENABLE_EVENT_PUBLISHING=true` and `ENABLE_DIRECT_TRIGGERS=true`
2. Monitor CloudWatch logs for successful event publishing
3. Verify EventBridge rules are routing events correctly
4. Compare analytics results between event-driven and direct approaches

### Phase 2: Validate Event Processing
1. Deploy analytics consumer Lambda functions
2. Monitor consumer execution and success rates
3. Compare processing times and error rates
4. Ensure analytics data consistency

### Phase 3: Cutover to Events-Only
1. After successful validation, set `ENABLE_DIRECT_TRIGGERS=false`
2. Monitor system for 24-48 hours
3. Verify analytics continue to process correctly
4. Remove direct trigger code in future release

## Monitoring Commands

### Check Event Publishing
```bash
# View event publishing logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-file-processor \
  --filter-pattern "Event published successfully"

# Check EventBridge metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name SuccessfulInvocations \
  --dimensions Name=RuleName,Value=housef3-dev-analytics-events \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### Check Direct Trigger Activity
```bash
# View direct trigger logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/housef3-dev-file-processor \
  --filter-pattern "Direct analytics refresh triggered"
```

## Error Handling

Both event publishing and direct triggers are wrapped in try-catch blocks to ensure:
- File processing never fails due to analytics trigger failures
- Detailed logging for debugging
- Graceful degradation if one mode fails

## Terraform Configuration

Add environment variables to your Lambda function configurations:

```hcl
resource "aws_lambda_function" "file_processor" {
  # ... other configuration

  environment {
    variables = {
      ENABLE_EVENT_PUBLISHING = var.enable_event_publishing
      ENABLE_DIRECT_TRIGGERS  = var.enable_direct_triggers
      # ... other variables
    }
  }
}
```

Define variables in `variables.tf`:

```hcl
variable "enable_event_publishing" {
  description = "Enable event publishing to EventBridge"
  type        = bool
  default     = true
}

variable "enable_direct_triggers" {
  description = "Enable direct analytics triggering (for shadow mode)"
  type        = bool
  default     = false
}
``` 