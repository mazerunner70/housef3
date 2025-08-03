# Event Consumer Lambda Functions
#
# This file defines the Lambda functions that consume events from EventBridge
# and their connections to the EventBridge rules.

# ==============================================================================
# LAMBDA ZIP DATA SOURCE
# ==============================================================================

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../../backend/src"
  output_path = "../../backend/lambda_consumers.zip"
  excludes    = ["__pycache__", "*.pyc", "*.pyo", "*.pyd", ".pytest_cache", ".coverage"]
}

# ==============================================================================
# Analytics Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "analytics_consumer" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.environment}-analytics-consumer"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "consumers.analytics_consumer.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 512
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      EVENTS_TABLE         = aws_dynamodb_table.event_store.name
      ANALYTICS_DATA_TABLE = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
      ACCOUNTS_TABLE       = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE   = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE      = aws_dynamodb_table.file_maps.name
      FILES_TABLE          = aws_dynamodb_table.transaction_files.name
      FZIP_JOBS_TABLE      = aws_dynamodb_table.fzip_jobs.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "analytics-consumer"
  }
}

# Connect EventBridge analytics rule to Lambda
resource "aws_cloudwatch_event_target" "analytics_consumer_target" {
  rule           = aws_cloudwatch_event_rule.analytics_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "AnalyticsConsumerTarget"
  arn           = aws_lambda_function.analytics_consumer.arn

  retry_policy {
    maximum_retry_attempts = 2
    maximum_event_age_in_seconds = 60
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
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.environment}-categorization-consumer"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "consumers.categorization_consumer.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 512
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      EVENTS_TABLE         = aws_dynamodb_table.event_store.name
      ACCOUNTS_TABLE       = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE   = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE      = aws_dynamodb_table.file_maps.name
      FILES_TABLE          = aws_dynamodb_table.transaction_files.name
      FZIP_JOBS_TABLE      = aws_dynamodb_table.fzip_jobs.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "categorization-consumer"
  }
}

# Connect EventBridge categorization rule to Lambda
resource "aws_cloudwatch_event_target" "categorization_consumer_target" {
  rule           = aws_cloudwatch_event_rule.categorization_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "CategorizationConsumerTarget"
  arn           = aws_lambda_function.categorization_consumer.arn

  retry_policy {
    maximum_retry_attempts = 2
    maximum_event_age_in_seconds = 60
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
  runtime          = "python3.12"
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

# Connect EventBridge audit rule to Lambda
resource "aws_cloudwatch_event_target" "audit_consumer_target" {
  rule           = aws_cloudwatch_event_rule.audit_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "AuditConsumerTarget"
  arn           = aws_lambda_function.audit_consumer.arn

  retry_policy {
    maximum_retry_attempts = 2
    maximum_event_age_in_seconds = 60
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

# IAM Policy for Event Consumers
resource "aws_iam_policy" "event_consumer_policy" {
  name = "${var.environment}-event-consumer-policy"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.event_store.arn,
          "${aws_dynamodb_table.event_store.arn}/index/*",
          aws_dynamodb_table.analytics_data.arn,
          "${aws_dynamodb_table.analytics_data.arn}/index/*",
          aws_dynamodb_table.analytics_status.arn,
          "${aws_dynamodb_table.analytics_status.arn}/index/*",
          aws_dynamodb_table.accounts.arn,
          "${aws_dynamodb_table.accounts.arn}/index/*",
          aws_dynamodb_table.transactions.arn,
          "${aws_dynamodb_table.transactions.arn}/index/*",
          aws_dynamodb_table.categories.arn,
          "${aws_dynamodb_table.categories.arn}/index/*",
          aws_dynamodb_table.file_maps.arn,
          "${aws_dynamodb_table.file_maps.arn}/index/*",
          aws_dynamodb_table.transaction_files.arn,
          "${aws_dynamodb_table.transaction_files.arn}/index/*",
          aws_dynamodb_table.fzip_jobs.arn,
          "${aws_dynamodb_table.fzip_jobs.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = aws_cloudwatch_event_bus.app_events.arn
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueUrl"
        ]
        Resource = aws_sqs_queue.event_dlq.arn
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
