#!/bin/bash

# Force non-interactive mode for AWS CLI
export AWS_PAGER=""

# Get the Lambda function name from Terraform
echo "Retrieving Lambda function name from Terraform..."
LAMBDA_NAME=$(cd /mnt/c237de8f-a133-458d-9dfc-3a4a638f0920/dev/personal/projects/2025/housef3/infrastructure/terraform && terraform output -raw lambda_getcolors_name 2>/dev/null)

if [ -z "$LAMBDA_NAME" ]; then
  echo "Error: Failed to retrieve Lambda function name from Terraform"
  exit 1
fi

echo "Lambda function name: $LAMBDA_NAME"
LOG_GROUP_NAME="/aws/lambda/$LAMBDA_NAME"
echo "Log group name: $LOG_GROUP_NAME"

# Get the most recent log stream
echo "Retrieving most recent log stream..."
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name "$LOG_GROUP_NAME" \
  --order-by LastEventTime \
  --descending \
  --limit 1 \
  --query 'logStreams[0].logStreamName' \
  --output text 2>/dev/null)

if [ -z "$LOG_STREAM" ] || [ "$LOG_STREAM" = "None" ]; then
  echo "Error: No log streams found for log group $LOG_GROUP_NAME"
  exit 1
fi

echo "Found log stream: $LOG_STREAM"

# Get all log messages
echo "===== ALL LOG MESSAGES ====="
aws logs get-log-events \
  --log-group-name "$LOG_GROUP_NAME" \
  --log-stream-name "$LOG_STREAM" \
  --limit 30 \
  --no-paginate \
  --query 'events[*].message' \
  --output text 2>/dev/null

echo "Done." 