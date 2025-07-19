# Event Consumer Lambda Functions
#
# This file defines the Lambda functions that consume events from EventBridge
# and their connections to the EventBridge rules.

# ==============================================================================
# Analytics Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "analytics_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-analytics-consumer"
  handler          = "consumers/analytics_consumer.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 300  # 5 minutes for analytics processing
  memory_size     = 512  # More memory for analytics processing
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      ANALYTICS_STATUS_TABLE     = aws_dynamodb_table.analytics_status.name
      EVENT_BUS_NAME            = aws_cloudwatch_event_bus.app_events.name
      CATEGORIES_TABLE_NAME     = aws_dynamodb_table.categories.name
      TRANSACTIONS_TABLE        = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE            = aws_dynamodb_table.accounts.name
      FILES_TABLE               = aws_dynamodb_table.files.name
      AWS_REGION                = var.aws_region
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.event_dlq.arn
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-consumer"
  }
}

# Connect EventBridge analytics rule to Lambda
resource "aws_cloudwatch_event_target" "analytics_consumer_target" {
  rule           = aws_cloudwatch_event_rule.analytics_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "AnalyticsConsumerTarget"
  arn           = aws_lambda_function.analytics_consumer.arn

  retry_policy {
    maximum_retry_attempts = 3
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke Analytics Consumer
resource "aws_lambda_permission" "allow_eventbridge_analytics" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analytics_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.analytics_events.arn
}

# ==============================================================================
# Categorization Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "categorization_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-categorization-consumer"
  handler          = "consumers/categorization_consumer.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 300  # 5 minutes for categorization processing
  memory_size     = 512  # More memory for category rule processing
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      EVENT_BUS_NAME            = aws_cloudwatch_event_bus.app_events.name
      CATEGORIES_TABLE_NAME     = aws_dynamodb_table.categories.name
      TRANSACTIONS_TABLE        = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE            = aws_dynamodb_table.accounts.name
      FILES_TABLE               = aws_dynamodb_table.files.name
      AWS_REGION                = var.aws_region
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.event_dlq.arn
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-consumer"
  }
}

# Connect EventBridge categorization rule to Lambda
resource "aws_cloudwatch_event_target" "categorization_consumer_target" {
  rule           = aws_cloudwatch_event_rule.categorization_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "CategorizationConsumerTarget"
  arn           = aws_lambda_function.categorization_consumer.arn

  retry_policy {
    maximum_retry_attempts = 3
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke Categorization Consumer
resource "aws_lambda_permission" "allow_eventbridge_categorization" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.categorization_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.categorization_events.arn
}

# ==============================================================================
# Audit Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "audit_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-audit-consumer"
  handler          = "consumers/audit_consumer.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 120  # 2 minutes for audit logging
  memory_size     = 256  # Less memory needed for simple audit logging
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                = var.environment
      EVENT_BUS_NAME            = aws_cloudwatch_event_bus.app_events.name
      EVENT_STORE_TABLE         = aws_dynamodb_table.event_store.name
      AWS_REGION                = var.aws_region
    }
  }

  dead_letter_config {
    target_arn = aws_sqs_queue.event_dlq.arn
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "event-consumer"
  }
}

# Connect EventBridge audit rule to Lambda (captures ALL events)
resource "aws_cloudwatch_event_target" "audit_consumer_target" {
  rule           = aws_cloudwatch_event_rule.audit_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "AuditConsumerTarget"
  arn           = aws_lambda_function.audit_consumer.arn

  retry_policy {
    maximum_retry_attempts = 2  # Fewer retries for audit to avoid blocking
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke Audit Consumer
resource "aws_lambda_permission" "allow_eventbridge_audit" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.audit_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.audit_events.arn
}

# ==============================================================================
# Consumer IAM Permissions
# ==============================================================================

# Additional IAM permissions for event consumers
resource "aws_iam_policy" "event_consumer_policy" {
  name        = "${var.project_name}-${var.environment}-event-consumer-policy"
  description = "IAM policy for event consumer Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # DynamoDB permissions for all consumers
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.analytics_status.arn,
          aws_dynamodb_table.event_store.arn,
          aws_dynamodb_table.categories.arn,
          aws_dynamodb_table.transactions.arn,
          aws_dynamodb_table.accounts.arn,
          aws_dynamodb_table.files.arn,
          "${aws_dynamodb_table.categories.arn}/index/*",
          "${aws_dynamodb_table.transactions.arn}/index/*",
          "${aws_dynamodb_table.accounts.arn}/index/*",
          "${aws_dynamodb_table.files.arn}/index/*"
        ]
      },
      # SQS permissions for DLQ
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.event_dlq.arn
      },
      # CloudWatch Logs permissions
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

# Attach the policy to the Lambda execution role
resource "aws_iam_role_policy_attachment" "event_consumer_policy_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.event_consumer_policy.arn
}

# ==============================================================================
# Monitoring and Alarms
# ==============================================================================

# CloudWatch Alarms for consumer health monitoring
resource "aws_cloudwatch_metric_alarm" "analytics_consumer_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-analytics-consumer-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors analytics consumer errors"
  alarm_actions       = [] # Add SNS topic ARN for notifications

  dimensions = {
    FunctionName = aws_lambda_function.analytics_consumer.function_name
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "categorization_consumer_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-categorization-consumer-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"  # 5 minutes
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors categorization consumer errors"
  alarm_actions       = [] # Add SNS topic ARN for notifications

  dimensions = {
    FunctionName = aws_lambda_function.categorization_consumer.function_name
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ==============================================================================
# Outputs
# ==============================================================================

output "analytics_consumer_function_arn" {
  description = "ARN of the analytics consumer Lambda function"
  value       = aws_lambda_function.analytics_consumer.arn
}

output "categorization_consumer_function_arn" {
  description = "ARN of the categorization consumer Lambda function"
  value       = aws_lambda_function.categorization_consumer.arn
}

output "audit_consumer_function_arn" {
  description = "ARN of the audit consumer Lambda function"
  value       = aws_lambda_function.audit_consumer.arn
} 