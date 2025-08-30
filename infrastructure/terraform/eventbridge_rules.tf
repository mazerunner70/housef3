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
    source = ["transaction.service", "account.service"]
    detail-type = [
      "file.processed",
      "transactions.created",
      "transaction.updated",
      "transactions.deleted",
      "account.created",
      "account.updated",
      "account.deleted"
    ]
    # Only process successful file processing events
    detail = {
      data = {
        processingStatus = [
          {
            "anything-but" : "failed"
          }
        ]
      }
    }
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "analytics-event-routing"
  }
}

# =============================================================================
# CATEGORIZATION CONSUMER RULES  
# =============================================================================

# Rule for categorization events - captures transaction creation events for auto-categorization
resource "aws_cloudwatch_event_rule" "categorization_events" {
  name           = "${var.project_name}-${var.environment}-categorization-events"
  description    = "Route transaction creation events for categorization"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source      = ["transaction.service"]
    detail-type = ["transactions.created"]
    # Only process events with actual transactions
    detail = {
      data = {
        transactionCount = [
          {
            "numeric" : [">", 0]
          }
        ]
      }
    }
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