# =========================================
# EVENTBRIDGE RULES FOR EVENT ROUTING
# =========================================
# This file contains the EventBridge rules that define how events are routed
# to different consumers based on event patterns

# =============================================================================
# ANALYTICS CONSUMER RULES
# =============================================================================

# Rule for analytics events - captures events that should trigger analytics processing
resource "aws_cloudwatch_event_rule" "analytics_events" {
  name           = "${var.project_name}-${var.environment}-analytics-events"
  description    = "Route events that should trigger analytics processing"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    "$or" : [
      {
        # File processing events - only successful ones
        source = ["transaction.service"]
        detail-type = ["file.processed"]
        detail = {
          data = {
            processingStatus = [
              {
                "anything-but" : "failed"
              }
            ]
          }
        }
      },
      {
        # Transaction and account events - all of them
        source = ["transaction.service", "account.service"]
        detail-type = [
          "transactions.created",
          "transaction.updated", 
          "transactions.deleted",
          "account.created",
          "account.updated",
          "account.deleted"
        ]
      },
      {
        # File deletion events - all of them
        source = ["file.service"]
        detail-type = ["file.deletion.requested"]
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "analytics-event-routing"
  }
}

# =============================================================================
# FILE PROCESSOR CONSUMER RULES
# =============================================================================

# Rule for file upload events - captures file uploads for processing
resource "aws_cloudwatch_event_rule" "file_processor_events" {
  name           = "${var.project_name}-${var.environment}-file-processor-events"
  description    = "Route file upload events for processing"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source      = ["transaction.service"]
    detail-type = ["file.uploaded"]
    # Process all file upload events
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "file-processor-event-routing"
  }
}

# =============================================================================
# CATEGORIZATION CONSUMER RULES  
# =============================================================================

# Rule for categorization events - captures file processing events for auto-categorization
resource "aws_cloudwatch_event_rule" "categorization_events" {
  name           = "${var.project_name}-${var.environment}-categorization-events"
  description    = "Route file processing events for categorization"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    "$or" : [
      {
        # File processing events from transaction service
        source = ["transaction.service"]
        detail-type = ["file.processed"]
        detail = {
          data = {
            processingStatus = ["success"]
            transactionCount = [
              {
                "numeric" : [">", 0]
              }
            ]
          }
        }
      },
      {
        # File deletion events from file service
        source = ["file.service"]
        detail-type = ["file.deletion.requested"]
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "categorization-event-routing"
  }
}

# Rule for new category rules - triggers re-categorization when new rules are created
resource "aws_cloudwatch_event_rule" "category_rule_events" {
  name           = "${var.project_name}-${var.environment}-category-rule-events"
  description    = "Route category rule creation events for re-categorization"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source      = ["category.service"]
    detail-type = ["category.rule_created"]
    # Only process auto-apply rules
    detail = {
      data = {
        autoApply = [true]
      }
    }
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "category-rule-event-routing"
  }
}

# =============================================================================
# FILE DELETION CONSUMER RULES
# =============================================================================

# Rule for file deletion coordination events
resource "aws_cloudwatch_event_rule" "file_deletion_events" {
  name           = "${var.project_name}-${var.environment}-file-deletion-events"
  description    = "Route file deletion coordination events"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source      = ["transaction.service", "consumer.service"]
    detail-type = ["file.deletion.requested", "consumer.completion"]
    # Process all file deletion requests and consumer completion events
    "$or" : [
      {
        detail-type = ["file.deletion.requested"]
      },
      {
        detail-type = ["consumer.completion"]
        detail = {
          data = {
            originalEventType = ["file.deletion.requested"]
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "file-deletion-event-routing"
  }
}

# =============================================================================
# GENERIC VOTE AGGREGATOR CONSUMER RULES
# =============================================================================

# Rule for vote aggregation events - captures voting requests and votes
resource "aws_cloudwatch_event_rule" "vote_aggregator_events" {
  name           = "${var.project_name}-${var.environment}-vote-aggregator-events"
  description    = "Route voting-related events for aggregation and decision making"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source = ["file.service", "consumer.service", "analytics.manager.service", "category.manager.service"]
    detail-type = [
      "file.deletion.requested",
      "file.deletion.vote"
    ]
    # Process all voting-related events
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "vote-aggregator-event-routing"
  }
}

# =============================================================================
# FILE DELETION EXECUTOR CONSUMER RULES
# =============================================================================

# Rule for file deletion executor events - captures approval events
resource "aws_cloudwatch_event_rule" "file_deletion_executor_events" {
  name           = "${var.project_name}-${var.environment}-file-deletion-executor-events"
  description    = "Route file deletion approval events for execution"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source      = ["vote.aggregator"]
    detail-type = ["file.deletion.approved"]
    # Process only approved deletion events
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "file-deletion-executor-event-routing"
  }
}

# =============================================================================
# WORKFLOW TRACKING CONSUMER RULES
# =============================================================================

# Rule for workflow tracking events - captures all deletion-related events for progress tracking
resource "aws_cloudwatch_event_rule" "workflow_tracking_events" {
  name           = "${var.project_name}-${var.environment}-workflow-tracking-events"
  description    = "Route deletion-related events for workflow progress tracking"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source = ["transaction.service", "file.service", "analytics.manager.service", "category.manager.service", "vote.aggregator"]
    detail-type = [
      "file.deletion.requested",
      "file.deletion.vote",
      "file.deletion.approved", 
      "file.deletion.denied",
      "file.deletion.completed",
      "file.deletion.failed"
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "workflow-tracking-event-routing"
  }
}

# =============================================================================
# AUDIT LOGGING RULES
# =============================================================================

# Rule for audit logging - captures ALL events for compliance and debugging
resource "aws_cloudwatch_event_rule" "audit_events" {
  name           = "${var.project_name}-${var.environment}-audit-events"
  description    = "Route all events to audit logging"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  # Match all events from our application sources
  event_pattern = jsonencode({
    source = [
      "transaction.service",
      "account.service",
      "category.service",
      "file.service"
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "audit-event-routing"
  }
}

# =============================================================================
# NOTIFICATION RULES
# =============================================================================

# Rule for critical notifications - captures high-priority events
resource "aws_cloudwatch_event_rule" "notification_events" {
  name           = "${var.project_name}-${var.environment}-notification-events"
  description    = "Route critical events for user notifications"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source = ["transaction.service", "account.service"]
    detail-type = [
      "file.processed",
      "transactions.deleted",
      "account.deleted"
    ]
    # Include failed processing and bulk deletions
    "$or" : [
      {
        detail = {
          data = {
            processingStatus = ["failed"]
          }
        }
      },
      {
        detail = {
          data = {
            deletionType = ["bulk"]
          }
        }
      },
      {
        detail-type = ["account.deleted"]
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "notification-event-routing"
  }
}

# =============================================================================
# DEAD LETTER QUEUE RULES
# =============================================================================

# Rule to capture failed event processing for investigation
resource "aws_cloudwatch_event_rule" "failed_events" {
  name           = "${var.project_name}-${var.environment}-failed-events"
  description    = "Route failed events to dead letter queue"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  # This will be used by Lambda destinations for failed invocations
  event_pattern = jsonencode({
    source      = ["lambda"]
    detail-type = ["Lambda Function Invocation Result - Failure"]
    detail = {
      responseElements = {
        functionName = [
          {
            "prefix" : "${var.project_name}-${var.environment}"
          }
        ]
      }
    }
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "failed-event-routing"
  }
}

# =============================================================================
# MONITORING AND METRICS RULES
# =============================================================================

# Rule for monitoring high-volume events
resource "aws_cloudwatch_event_rule" "monitoring_events" {
  name           = "${var.project_name}-${var.environment}-monitoring-events"
  description    = "Route events for monitoring and metrics"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source = [
      "transaction.service",
      "account.service",
      "category.service"
    ]
    # Monitor all event types for metrics
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "monitoring-event-routing"
  }
}

# =============================================================================
# DEVELOPMENT AND TESTING RULES
# =============================================================================

# Rule for development/testing - only active in non-production environments
resource "aws_cloudwatch_event_rule" "debug_events" {
  count = var.environment == "dev" ? 1 : 0

  name           = "${var.project_name}-${var.environment}-debug-events"
  description    = "Route all events for debugging (dev environment only)"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  # Match all events for debugging
  event_pattern = jsonencode({
    source = [
      {
        "prefix" : "" # Matches all sources
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "debug-event-routing"
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "analytics_rule_arn" {
  description = "ARN of the analytics events rule"
  value       = aws_cloudwatch_event_rule.analytics_events.arn
}

output "file_processor_rule_arn" {
  description = "ARN of the file processor events rule"
  value       = aws_cloudwatch_event_rule.file_processor_events.arn
}

output "categorization_rule_arn" {
  description = "ARN of the categorization events rule"
  value       = aws_cloudwatch_event_rule.categorization_events.arn
}

output "audit_rule_arn" {
  description = "ARN of the audit events rule"
  value       = aws_cloudwatch_event_rule.audit_events.arn
}

output "notification_rule_arn" {
  description = "ARN of the notification events rule"
  value       = aws_cloudwatch_event_rule.notification_events.arn
}

output "monitoring_rule_arn" {
  description = "ARN of the monitoring events rule"
  value       = aws_cloudwatch_event_rule.monitoring_events.arn
}

output "file_deletion_rule_arn" {
  description = "ARN of the file deletion events rule"
  value       = aws_cloudwatch_event_rule.file_deletion_events.arn
}

output "vote_aggregator_rule_arn" {
  description = "ARN of the vote aggregator EventBridge rule"
  value       = aws_cloudwatch_event_rule.vote_aggregator_events.arn
}

output "file_deletion_executor_rule_arn" {
  description = "ARN of the file deletion executor EventBridge rule"
  value       = aws_cloudwatch_event_rule.file_deletion_executor_events.arn
}

output "workflow_tracking_rule_arn" {
  description = "ARN of the workflow tracking EventBridge rule"
  value       = aws_cloudwatch_event_rule.workflow_tracking_events.arn
} 