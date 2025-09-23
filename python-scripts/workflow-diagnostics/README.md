# Workflow Diagnostics Tools

This directory contains comprehensive diagnostic tools for monitoring and tracking workflow operations, particularly useful for monitoring file deletion success rates and other long-running operations.

## Files

- **`workflow_diagnostics.py`** - Main Python CLI tool with full diagnostic capabilities
- **`workflow_diagnostics.sh`** - Shell wrapper script with convenient shortcuts
- **`workflow_config.env`** - Environment configuration file
- **`README.md`** - This documentation file

## Quick Start

1. **Set up environment** (optional):
   ```bash
   source workflow_config.env
   ```

2. **Quick system overview**:
   ```bash
   ./workflow_diagnostics.sh
   ```

3. **Check system health**:
   ```bash
   ./workflow_diagnostics.sh health --hours 24
   ```

## Main Commands

### Basic Usage
```bash
# Quick system summary
./workflow_diagnostics.sh summary

# System health analysis
./workflow_diagnostics.sh health [--hours N]

# List operations with filters
./workflow_diagnostics.sh list [--status STATUS] [--type TYPE] [--hours N]

# Check specific operation
./workflow_diagnostics.sh status <operation-id>

# Show operation logs
./workflow_diagnostics.sh logs <operation-id>

# Real-time monitoring
./workflow_diagnostics.sh monitor [operation-id]
```

### Advanced Usage
```bash
# Monitor all active operations continuously
./workflow_diagnostics.sh watch

# Show recent failures
./workflow_diagnostics.sh failures

# Show only active operations
./workflow_diagnostics.sh active

# Quick connectivity check
./workflow_diagnostics.sh check
```

## Python CLI Direct Usage

For more advanced usage, you can call the Python script directly:

```bash
# Get detailed help
python3 workflow_diagnostics.py --help

# List failed operations from last 48 hours
python3 workflow_diagnostics.py list --status failed --hours 48 --limit 100

# Monitor specific operation with custom interval
python3 workflow_diagnostics.py monitor op_20250120_143022_abc --interval 2

# Get comprehensive health report
python3 workflow_diagnostics.py health --hours 168  # Last week
```

## Operation Status Types

- **`initiated`** - Operation has been started
- **`in_progress`** - Operation is actively running
- **`waiting_for_approval`** - Waiting for approval votes (e.g., deletion approval)
- **`approved`** - All approvals received, ready to execute
- **`executing`** - Currently executing the operation
- **`completed`** - Successfully completed
- **`failed`** - Operation failed with error
- **`cancelled`** - Operation was cancelled by user
- **`denied`** - Operation was denied (e.g., insufficient approvals)

## Operation Types

- **`file_deletion`** - File deletion operations
- **`file_upload`** - File upload and processing
- **`account_modification`** - Account-level changes
- **`data_export`** - Data export operations
- **`bulk_categorization`** - Bulk transaction categorization
- **`account_migration`** - Account migration operations

## Configuration

The tools use these environment variables (set in `workflow_config.env`):

- `PROJECT_NAME` - Project name (default: housef3)
- `ENVIRONMENT` - Environment (default: dev)
- `AWS_REGION` - AWS region (default: us-east-1)
- `WORKFLOWS_TABLE` - DynamoDB workflows table name
- `DEFAULT_TIME_WINDOW_HOURS` - Default time window for queries
- `DEFAULT_MONITOR_INTERVAL` - Default monitoring refresh interval

## Prerequisites

- Python 3.6+
- AWS CLI configured with appropriate credentials
- Access to DynamoDB operations table
- Access to CloudWatch logs (for log viewing)

## Examples

### Monitor Delete Operations
```bash
# Check recent file deletion success rate
./workflow_diagnostics.sh list --type file_deletion --hours 24

# Monitor a specific deletion operation
./workflow_diagnostics.sh monitor op_20250120_143022_abc12345

# Show logs for a failed deletion
./workflow_diagnostics.sh logs op_20250120_143022_abc12345
```

### System Health Monitoring
```bash
# Daily health check
./workflow_diagnostics.sh health --hours 24

# Weekly trend analysis
python3 workflow_diagnostics.py health --hours 168

# Continuous monitoring dashboard
./workflow_diagnostics.sh watch
```

### Troubleshooting Failed Operations
```bash
# List all failures from last 48 hours
./workflow_diagnostics.sh list --status failed --hours 48

# Get detailed logs for failed operation
./workflow_diagnostics.sh logs <failed-operation-id>

# Check system health to identify patterns
./workflow_diagnostics.sh health --hours 72
```

## Output Features

- **Color-coded status indicators** - Green for success, red for failures, etc.
- **Progress bars** - Visual progress indicators for active operations
- **Time-relative displays** - Shows "2h ago", "5m ago" for easy reading
- **Structured logging** - CloudWatch log integration with timestamps
- **Real-time updates** - Live monitoring with configurable refresh rates

## Integration with Existing Scripts

This diagnostic tool complements the existing health check script (`check_file_deletion_health.sh`) by providing:

- More comprehensive operation tracking
- Real-time monitoring capabilities
- Better filtering and search options
- Integration with the operation tracking system
- Historical trend analysis

## Troubleshooting

### Common Issues

1. **"Table not found" error**:
   - Verify `PROJECT_NAME` and `ENVIRONMENT` are correct
   - Check AWS credentials and region
   - Ensure DynamoDB table exists

2. **"No operations found"**:
   - Operations may be older than the time window
   - Try increasing `--hours` parameter
   - Check if operation tracking is enabled in the backend

3. **"AWS credentials not configured"**:
   - Run `aws configure` to set up credentials
   - Or set AWS environment variables (AWS_ACCESS_KEY_ID, etc.)

4. **Log viewing fails**:
   - Ensure CloudWatch logs access permissions
   - Check if Lambda functions are deployed
   - Verify log group names match your environment

### Getting Help

- Use `--help` flag with any command for detailed usage
- Check the main project documentation for operation tracking setup
- Review CloudWatch logs for backend operation tracking issues
