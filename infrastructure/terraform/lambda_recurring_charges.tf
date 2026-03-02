# ==============================================================================
# Recurring Charge Operations Lambda and Consumer
# ==============================================================================
# This file defines the Lambda functions for recurring charge pattern detection
# and management, including both the API handler and the EventBridge consumer.

# ==============================================================================
# Recurring Charge Operations Lambda (API Handler)
# ==============================================================================

resource "aws_lambda_function" "recurring_charge_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-recurring-charge-operations"
  handler          = "handlers/recurring_charge_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 60
  memory_size      = 512  # More memory for ML operations
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]
  
  # Attach ML dependencies layer
  layers = [aws_lambda_layer_version.ml_dependencies.arn]

  environment {
    variables = {
      ENVIRONMENT                      = var.environment
      RECURRING_CHARGE_PATTERNS_TABLE  = aws_dynamodb_table.recurring_charge_patterns.name
      RECURRING_CHARGE_PREDICTIONS_TABLE = aws_dynamodb_table.recurring_charge_predictions.name
      PATTERN_FEEDBACK_TABLE           = aws_dynamodb_table.pattern_feedback.name
      TRANSACTIONS_TABLE               = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE                   = aws_dynamodb_table.accounts.name
      CATEGORIES_TABLE_NAME            = aws_dynamodb_table.categories.name
      WORKFLOWS_TABLE                  = aws_dynamodb_table.workflows.name
      EVENT_BUS_NAME                   = aws_cloudwatch_event_bus.app_events.name
      ENABLE_EVENT_PUBLISHING          = "true"
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Component   = "recurring-charge-operations"
  }
}

resource "aws_cloudwatch_log_group" "recurring_charge_operations" {
  name              = "/aws/lambda/${aws_lambda_function.recurring_charge_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# ==============================================================================
# Recurring Charge Detection Consumer Lambda (EventBridge Consumer)
# ==============================================================================

resource "aws_lambda_function" "recurring_charge_detection_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-recurring-charge-detection-consumer"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "consumers/recurring_charge_detection_consumer.handler"
  runtime          = "python3.12"
  timeout          = 300  # 5 minutes for pattern detection
  memory_size      = 1024  # More memory for ML operations
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]
  
  # Attach ML dependencies layer
  layers = [aws_lambda_layer_version.ml_dependencies.arn]

  environment {
    variables = {
      ENVIRONMENT                      = var.environment
      RECURRING_CHARGE_PATTERNS_TABLE  = aws_dynamodb_table.recurring_charge_patterns.name
      RECURRING_CHARGE_PREDICTIONS_TABLE = aws_dynamodb_table.recurring_charge_predictions.name
      PATTERN_FEEDBACK_TABLE           = aws_dynamodb_table.pattern_feedback.name
      TRANSACTIONS_TABLE               = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE                   = aws_dynamodb_table.accounts.name
      CATEGORIES_TABLE_NAME            = aws_dynamodb_table.categories.name
      WORKFLOWS_TABLE                  = aws_dynamodb_table.workflows.name
      FILES_TABLE                      = aws_dynamodb_table.transaction_files.name
      FILE_MAPS_TABLE                  = aws_dynamodb_table.file_maps.name
      FZIP_JOBS_TABLE                  = aws_dynamodb_table.fzip_jobs.name
      EVENTS_TABLE                     = aws_dynamodb_table.event_store.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Component   = "recurring-charge-detection-consumer"
  }
}

resource "aws_cloudwatch_log_group" "recurring_charge_detection_consumer" {
  name              = "/aws/lambda/${aws_lambda_function.recurring_charge_detection_consumer.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# ==============================================================================
# EventBridge Rule for Recurring Charge Detection
# ==============================================================================

resource "aws_cloudwatch_event_rule" "recurring_charge_detection_events" {
  name           = "${var.project_name}-${var.environment}-recurring-charge-detection-events"
  description    = "Route recurring charge detection events to consumer"
  event_bus_name = aws_cloudwatch_event_bus.app_events.name

  event_pattern = jsonencode({
    source      = ["recurring_charge.service"]
    detail-type = ["recurring_charge.detection.requested"]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Connect EventBridge rule to Lambda consumer
resource "aws_cloudwatch_event_target" "recurring_charge_detection_consumer_target" {
  rule           = aws_cloudwatch_event_rule.recurring_charge_detection_events.name
  event_bus_name = aws_cloudwatch_event_bus.app_events.name
  target_id      = "RecurringChargeDetectionConsumerTarget"
  arn            = aws_lambda_function.recurring_charge_detection_consumer.arn

  retry_policy {
    maximum_retry_attempts       = 2
    maximum_event_age_in_seconds = 300  # 5 minutes
  }

  dead_letter_config {
    arn = aws_sqs_queue.event_dlq.arn
  }
}

# Permission for EventBridge to invoke Recurring Charge Detection Consumer
resource "aws_lambda_permission" "allow_eventbridge_recurring_charge_detection" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recurring_charge_detection_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.recurring_charge_detection_events.arn
}

