# =========================================
# AWS EVENTBRIDGE INFRASTRUCTURE
# =========================================
# This file contains the EventBridge setup for the event-driven architecture
# including the custom event bus, event store for auditing, and dead letter queue

# Custom EventBridge Bus
resource "aws_cloudwatch_event_bus" "app_events" {
  name = "${var.project_name}-${var.environment}-events"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-driven-architecture"
  }
}

# Event store DynamoDB table for auditing and event replay
resource "aws_dynamodb_table" "event_store" {
  name           = "${var.project_name}-${var.environment}-event-store"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "eventId"
  range_key      = "timestamp"

  attribute {
    name = "eventId"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "eventType"
    type = "S"
  }

  attribute {
    name = "source"
    type = "S"
  }

  # GSI for querying events by user and timestamp
  global_secondary_index {
    name               = "UserIdTimestampIndex"
    hash_key           = "userId"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for querying by event type and timestamp
  global_secondary_index {
    name               = "EventTypeTimestampIndex"
    hash_key           = "eventType"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # GSI for querying by source system and timestamp
  global_secondary_index {
    name               = "SourceTimestampIndex"
    hash_key           = "source"
    range_key          = "timestamp"
    projection_type    = "ALL"
  }

  # Enable TTL for automatic cleanup of old events (1 year retention)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Enable point-in-time recovery for audit compliance
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-audit-store"
  }
}

# Dead letter queue for failed event processing
resource "aws_sqs_queue" "event_dlq" {
  name = "${var.project_name}-${var.environment}-event-dlq"
  
  # Retain messages for 14 days for investigation
  message_retention_seconds = 1209600  # 14 days
  
  # Enable server-side encryption
  sqs_managed_sse_enabled = true
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-dead-letter-queue"
  }
}

# DLQ for the DLQ (for catastrophic failures)
resource "aws_sqs_queue" "event_dlq_dlq" {
  name = "${var.project_name}-${var.environment}-event-dlq-dlq"
  
  # Retain messages for 30 days for deep investigation
  message_retention_seconds = 2592000  # 30 days
  
  # Enable server-side encryption
  sqs_managed_sse_enabled = true
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-dead-letter-queue-backup"
  }
}

# Redrive policy for the main DLQ
resource "aws_sqs_queue_redrive_policy" "event_dlq_redrive" {
  queue_url = aws_sqs_queue.event_dlq.id
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.event_dlq_dlq.arn
    maxReceiveCount     = 3
  })
}

# CloudWatch Log Group for EventBridge
resource "aws_cloudwatch_log_group" "eventbridge_logs" {
  name              = "/aws/events/${var.project_name}-${var.environment}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "eventbridge-logging"
  }
}

# IAM role for EventBridge to write to CloudWatch Logs
resource "aws_iam_role" "eventbridge_log_role" {
  name = "${var.project_name}-${var.environment}-eventbridge-log-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# IAM policy for EventBridge to write to CloudWatch Logs
resource "aws_iam_role_policy" "eventbridge_log_policy" {
  name = "${var.project_name}-${var.environment}-eventbridge-log-policy"
  role = aws_iam_role.eventbridge_log_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:CreateLogGroup"
        ]
        Resource = "${aws_cloudwatch_log_group.eventbridge_logs.arn}:*"
      }
    ]
  })
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "event_bus_name" {
  description = "Name of the EventBridge custom bus"
  value       = aws_cloudwatch_event_bus.app_events.name
}

output "event_bus_arn" {
  description = "ARN of the EventBridge custom bus"
  value       = aws_cloudwatch_event_bus.app_events.arn
}

output "event_store_table_name" {
  description = "Name of the event store DynamoDB table"
  value       = aws_dynamodb_table.event_store.name
}

output "event_store_table_arn" {
  description = "ARN of the event store DynamoDB table"
  value       = aws_dynamodb_table.event_store.arn
}

output "event_dlq_name" {
  description = "Name of the event dead letter queue"
  value       = aws_sqs_queue.event_dlq.name
}

output "event_dlq_arn" {
  description = "ARN of the event dead letter queue"
  value       = aws_sqs_queue.event_dlq.arn
}

output "event_dlq_url" {
  description = "URL of the event dead letter queue"
  value       = aws_sqs_queue.event_dlq.id
} 