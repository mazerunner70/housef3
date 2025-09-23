# Event Consumer Lambda Functions
#
# This file defines the Lambda functions that consume events from EventBridge
# and their connections to the EventBridge rules.

# ==============================================================================
# CONSUMER LAMBDA FUNCTIONS
# ==============================================================================
# All consumer functions use the same deployment package (lambda_deploy.zip)
# created by the backend build process

# ==============================================================================
# Analytics Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "analytics_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-analytics-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/analytics_consumer.handler"
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      EVENTS_TABLE           = aws_dynamodb_table.event_store.name
      ANALYTICS_DATA_TABLE   = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
      ACCOUNTS_TABLE         = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE     = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME  = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE        = aws_dynamodb_table.file_maps.name
      FILES_TABLE            = aws_dynamodb_table.transaction_files.name
      FZIP_JOBS_TABLE        = aws_dynamodb_table.fzip_jobs.name
      WORKFLOWS_TABLE        = aws_dynamodb_table.workflows.name
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
  arn            = aws_lambda_function.analytics_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
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
# File Processor Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "file_processor_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-processor-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/file_processor_consumer.handler"
  runtime          = "python3.12"
  timeout          = 600  # 10 minutes for file processing
  memory_size      = 1024  # More memory for file processing
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      EVENTS_TABLE           = aws_dynamodb_table.event_store.name
      ACCOUNTS_TABLE         = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE     = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME  = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE        = aws_dynamodb_table.file_maps.name
      FILES_TABLE            = aws_dynamodb_table.transaction_files.name
      FZIP_JOBS_TABLE        = aws_dynamodb_table.fzip_jobs.name
      FILE_STORAGE_BUCKET    = aws_s3_bucket.file_storage.bucket
      ENABLE_EVENT_PUBLISHING = "true"
      ENABLE_DIRECT_TRIGGERS = "false"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "file-processor-consumer"
  }
}

# Connect EventBridge file processor rule to Lambda
resource "aws_cloudwatch_event_target" "file_processor_consumer_target" {
  rule           = aws_cloudwatch_event_rule.file_processor_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "FileProcessorConsumerTarget"
  arn            = aws_lambda_function.file_processor_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
    maximum_event_age_in_seconds = 300  # 5 minutes for file processing
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke File Processor Consumer
resource "aws_lambda_permission" "allow_eventbridge_file_processor" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.file_processor_events.arn
}

# ==============================================================================
# Categorization Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "categorization_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-categorization-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/categorization_consumer.handler"
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      EVENTS_TABLE          = aws_dynamodb_table.event_store.name
      ACCOUNTS_TABLE        = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE    = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE       = aws_dynamodb_table.file_maps.name
      FILES_TABLE           = aws_dynamodb_table.transaction_files.name
      FZIP_JOBS_TABLE       = aws_dynamodb_table.fzip_jobs.name
      WORKFLOWS_TABLE       = aws_dynamodb_table.workflows.name
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
  arn            = aws_lambda_function.categorization_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
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
# File Deletion Consumer Lambda
# ==============================================================================

# Note: The old file_deletion_consumer has been replaced by the voting system
# consisting of generic_vote_aggregator_consumer and file_deletion_executor_consumer

# ==============================================================================
# Generic Vote Aggregator Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "generic_vote_aggregator_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-generic-vote-aggregator-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/generic_vote_aggregator.handler"
  runtime          = "python3.12"
  timeout          = 300  # 5 minutes for vote coordination
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                   = var.environment
      EVENTS_TABLE                 = aws_dynamodb_table.event_store.name
      WORKFLOWS_TABLE              = aws_dynamodb_table.workflows.name
      ENABLE_EVENT_PUBLISHING      = "true"
      VOTE_TIMEOUT_MINUTES         = "5"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "generic-vote-aggregator-consumer"
  }
}

# Connect EventBridge vote aggregator rule to Lambda
resource "aws_cloudwatch_event_target" "generic_vote_aggregator_consumer_target" {
  rule           = aws_cloudwatch_event_rule.vote_aggregator_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "GenericVoteAggregatorConsumerTarget"
  arn            = aws_lambda_function.generic_vote_aggregator_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
    maximum_event_age_in_seconds = 300  # 5 minutes for vote coordination
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke Generic Vote Aggregator Consumer
resource "aws_lambda_permission" "allow_eventbridge_generic_vote_aggregator" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.generic_vote_aggregator_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.vote_aggregator_events.arn
}

# ==============================================================================
# File Deletion Executor Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "file_deletion_executor_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-deletion-executor-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/file_deletion_executor.handler"
  runtime          = "python3.12"
  timeout          = 300  # 5 minutes for file deletion execution
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                   = var.environment
      EVENTS_TABLE                 = aws_dynamodb_table.event_store.name
      ACCOUNTS_TABLE               = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE           = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME        = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE              = aws_dynamodb_table.file_maps.name
      FILES_TABLE                  = aws_dynamodb_table.transaction_files.name
      FZIP_JOBS_TABLE              = aws_dynamodb_table.fzip_jobs.name
      WORKFLOWS_TABLE              = aws_dynamodb_table.workflows.name
      FILE_STORAGE_BUCKET          = aws_s3_bucket.file_storage.bucket
      ENABLE_EVENT_PUBLISHING      = "true"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "file-deletion-executor-consumer"
  }
}

# Connect EventBridge file deletion executor rule to Lambda
resource "aws_cloudwatch_event_target" "file_deletion_executor_consumer_target" {
  rule           = aws_cloudwatch_event_rule.file_deletion_executor_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "FileDeletionExecutorConsumerTarget"
  arn            = aws_lambda_function.file_deletion_executor_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
    maximum_event_age_in_seconds = 300  # 5 minutes for execution
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke File Deletion Executor Consumer
resource "aws_lambda_permission" "allow_eventbridge_file_deletion_executor" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_deletion_executor_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.file_deletion_executor_events.arn
}

# ==============================================================================
# Workflow Tracking Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "workflow_tracking_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-workflow-tracking-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/workflow_tracking_consumer.handler"
  runtime          = "python3.12"
  timeout          = 120  # 2 minutes for operation tracking
  memory_size      = 256  # Less memory needed for tracking updates
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      EVENTS_TABLE     = aws_dynamodb_table.event_store.name
      WORKFLOWS_TABLE  = aws_dynamodb_table.workflows.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "workflow-tracking-consumer"
  }
}

# Connect EventBridge workflow tracking rule to Lambda
resource "aws_cloudwatch_event_target" "workflow_tracking_consumer_target" {
  rule           = aws_cloudwatch_event_rule.workflow_tracking_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "WorkflowTrackingConsumerTarget"
  arn            = aws_lambda_function.workflow_tracking_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
    maximum_event_age_in_seconds = 60
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke Workflow Tracking Consumer
resource "aws_lambda_permission" "allow_eventbridge_workflow_tracking" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.workflow_tracking_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.workflow_tracking_events.arn
}

# ==============================================================================
# Audit Consumer Lambda
# ==============================================================================

resource "aws_lambda_function" "audit_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-audit-consumer"
  handler          = "consumers/audit_consumer.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 120 # 2 minutes for audit logging
  memory_size      = 256 # Less memory needed for simple audit logging
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      EVENT_BUS_NAME    = aws_cloudwatch_event_bus.app_events.name
      EVENT_STORE_TABLE = aws_dynamodb_table.event_store.name
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
  arn            = aws_lambda_function.audit_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
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
          "${aws_dynamodb_table.fzip_jobs.arn}/index/*",
          aws_dynamodb_table.workflows.arn,
          "${aws_dynamodb_table.workflows.arn}/index/*"
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
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.file_storage.arn}/*"
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

# CloudWatch Alarms for consumer health monitoring - DISABLED
# resource "aws_cloudwatch_metric_alarm" "analytics_consumer_errors" {
#   alarm_name          = "${var.project_name}-${var.environment}-analytics-consumer-errors"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "Errors"
#   namespace           = "AWS/Lambda"
#   period              = "300" # 5 minutes
#   statistic           = "Sum"
#   threshold           = "5"
#   alarm_description   = "This metric monitors analytics consumer errors"
#   alarm_actions       = [] # Add SNS topic ARN for notifications

#   dimensions = {
#     FunctionName = aws_lambda_function.analytics_consumer.function_name
#   }

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#   }
# }

# resource "aws_cloudwatch_metric_alarm" "categorization_consumer_errors" {
#   alarm_name          = "${var.project_name}-${var.environment}-categorization-consumer-errors"
#   comparison_operator = "GreaterThanThreshold"
#   evaluation_periods  = "2"
#   metric_name         = "Errors"
#   namespace           = "AWS/Lambda"
#   period              = "300" # 5 minutes
#   statistic           = "Sum"
#   threshold           = "5"
#   alarm_description   = "This metric monitors categorization consumer errors"
#   alarm_actions       = [] # Add SNS topic ARN for notifications

#   dimensions = {
#     FunctionName = aws_lambda_function.categorization_consumer.function_name
#   }

#   tags = {
#     Environment = var.environment
#     Project     = var.project_name
#   }
# }

# ==============================================================================
# Outputs
# ==============================================================================

output "analytics_consumer_function_arn" {
  description = "ARN of the analytics consumer Lambda function"
  value       = aws_lambda_function.analytics_consumer.arn
}

output "file_processor_consumer_function_arn" {
  description = "ARN of the file processor consumer Lambda function"
  value       = aws_lambda_function.file_processor_consumer.arn
}

output "categorization_consumer_function_arn" {
  description = "ARN of the categorization consumer Lambda function"
  value       = aws_lambda_function.categorization_consumer.arn
}

output "generic_vote_aggregator_consumer_function_arn" {
  description = "ARN of the generic vote aggregator consumer Lambda function"
  value       = aws_lambda_function.generic_vote_aggregator_consumer.arn
}

output "file_deletion_executor_consumer_function_arn" {
  description = "ARN of the file deletion executor consumer Lambda function"
  value       = aws_lambda_function.file_deletion_executor_consumer.arn
}

output "workflow_tracking_consumer_function_arn" {
  description = "ARN of the workflow tracking consumer Lambda function"
  value       = aws_lambda_function.workflow_tracking_consumer.arn
}

output "audit_consumer_function_arn" {
  description = "ARN of the audit consumer Lambda function"
  value       = aws_lambda_function.audit_consumer.arn
}

# Restore consumer output (defined in lambda.tf)
output "restore_consumer_function_arn" {
  description = "ARN of the restore consumer Lambda function"
  value       = aws_lambda_function.restore_consumer.arn
}
