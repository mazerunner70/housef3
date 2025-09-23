# Run tests and prepare Lambda package
resource "null_resource" "prepare_lambda" {
  triggers = {
    source_code_hash = "${sha256(file("../../backend/requirements.txt"))}-${sha256(file("../../backend/build_lambda_package.sh"))}-${sha256(join("", [for f in fileset("../../backend/src", "**") : filesha256("../../backend/src/${f}")]))}"
  }

  provisioner "local-exec" {
    working_dir = "../../backend"
    command     = "./build_lambda_package.sh"
  }
}

# Restore Consumer Lambda (S3-triggered)
resource "aws_lambda_function" "restore_consumer" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-restore-consumer"
  handler          = "consumers/restore_consumer.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 300
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                  = var.environment
      FZIP_JOBS_TABLE              = aws_dynamodb_table.fzip_jobs.name
      FZIP_PACKAGES_BUCKET         = aws_s3_bucket.fzip_packages.bucket
      FZIP_RESTORE_PACKAGES_BUCKET = aws_s3_bucket.fzip_packages.bucket
      ACCOUNTS_TABLE               = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE           = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME        = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE              = aws_dynamodb_table.file_maps.name
      FILES_TABLE                  = aws_dynamodb_table.transaction_files.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Component   = "restore-consumer"
  }
}

resource "aws_cloudwatch_log_group" "restore_consumer" {
  name              = "/aws/lambda/${aws_lambda_function.restore_consumer.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Allow S3 to invoke Restore Consumer
resource "aws_lambda_permission" "allow_s3_restore_consumer" {
  statement_id  = "AllowExecutionFromS3RestoreConsumer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restore_consumer.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.fzip_packages.arn
}

# Calculate source code hash from source files and build script
locals {
  source_code_hash = "${sha256(file("../../backend/requirements.txt"))}-${sha256(file("../../backend/build_lambda_package.sh"))}-${sha256(join("", [for f in fileset("../../backend/src", "**") : filesha256("../../backend/src/${f}")]))}"

  # Dynamic version management - read from build script output or use provided version
  app_version_raw = var.app_version != null ? var.app_version : (
    fileexists("../../backend/.current_version") ?
    trimspace(file("../../backend/.current_version")) :
    "${var.semver_base}.1"
  )

  # Transform version to valid Lambda alias name (replace dots with underscores)
  app_version = replace(local.app_version_raw, ".", "_")
}

# File Operations Lambda
resource "aws_lambda_function" "file_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-operations"
  handler          = "handlers/file_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 300
  memory_size      = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FILE_MAPS_TABLE     = aws_dynamodb_table.file_maps.name
      WORKFLOWS_TABLE     = aws_dynamodb_table.workflows.name
      DEPLOYMENT_VERSION  = "v4"
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# S3 Event Handler Lambda (replaces direct file processor)
resource "aws_lambda_function" "s3_event_handler" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-s3-event-handler"
  handler          = "handlers/s3_event_handler.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 60
  memory_size      = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      FILE_STORAGE_BUCKET    = aws_s3_bucket.file_storage.id
      EVENT_BUS_NAME         = aws_cloudwatch_event_bus.app_events.name
      ENABLE_EVENT_PUBLISHING = "true"
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Account Operations Lambda
resource "aws_lambda_function" "account_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-account-operations"
  handler          = "handlers/account_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT         = var.environment
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Transaction Operations Lambda
resource "aws_lambda_function" "transaction_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-transaction-operations"
  handler          = "handlers/transaction_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                            = var.environment
      TRANSACTIONS_TABLE                     = aws_dynamodb_table.transactions.name
      FILES_TABLE                            = aws_dynamodb_table.transaction_files.name
      ACCOUNTS_TABLE                         = aws_dynamodb_table.accounts.name
      TRANSACTION_CATEGORY_ASSIGNMENTS_TABLE = aws_dynamodb_table.transaction_category_assignments.name
      CATEGORIES_TABLE_NAME                  = aws_dynamodb_table.categories.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Transfer Operations Lambda
resource "aws_lambda_function" "transfer_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-transfer-operations"
  handler          = "handlers/transfer_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 60
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT                            = var.environment
      TRANSACTIONS_TABLE                     = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE                         = aws_dynamodb_table.accounts.name
      CATEGORIES_TABLE_NAME                  = aws_dynamodb_table.categories.name
      TRANSACTION_CATEGORY_ASSIGNMENTS_TABLE = aws_dynamodb_table.transaction_category_assignments.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Component   = "transfer-operations"
  }
}

# Analytics Operations Lambda
resource "aws_lambda_function" "analytics_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-analytics-operations"
  handler          = "handlers/analytics_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 300
  memory_size      = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      ANALYTICS_DATA_TABLE   = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
      TRANSACTIONS_TABLE     = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE         = aws_dynamodb_table.accounts.name
      FILES_TABLE            = aws_dynamodb_table.transaction_files.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Workflow Tracking Lambda
resource "aws_lambda_function" "workflow_tracking" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-workflow-tracking"
  handler          = "handlers/workflow_tracking.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      WORKFLOWS_TABLE  = aws_dynamodb_table.workflows.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Get Colors Lambda
resource "aws_lambda_function" "getcolors" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-getcolors"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handlers/getcolors.handler"
  source_code_hash = base64encode(local.source_code_hash)
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      DYNAMODB_ACCOUNTS_TABLE     = aws_dynamodb_table.accounts.name
      DYNAMODB_FILES_TABLE        = aws_dynamodb_table.transaction_files.name
      DYNAMODB_TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
      S3_BUCKET                   = aws_s3_bucket.file_storage.id
      TESTING                     = "false"
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Trigger for S3 Event Handler
resource "aws_lambda_permission" "allow_s3_event_handler" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_event_handler.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.file_storage.arn
}

# IAM Role and Policies
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_exec.name
}

resource "aws_iam_role_policy" "lambda_dynamodb_access" {
  name = "dynamodb-access-v3"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Effect = "Allow"
        Resource = [
          aws_dynamodb_table.transaction_files.arn,
          "${aws_dynamodb_table.transaction_files.arn}/index/*",
          aws_dynamodb_table.accounts.arn,
          "${aws_dynamodb_table.accounts.arn}/index/*",
          aws_dynamodb_table.transactions.arn,
          "${aws_dynamodb_table.transactions.arn}/index/*",
          aws_dynamodb_table.file_maps.arn,
          "${aws_dynamodb_table.file_maps.arn}/index/*",
          aws_dynamodb_table.analytics_data.arn,
          "${aws_dynamodb_table.analytics_data.arn}/index/*",
          aws_dynamodb_table.analytics_status.arn,
          "${aws_dynamodb_table.analytics_status.arn}/index/*",
          aws_dynamodb_table.categories.arn,
          "${aws_dynamodb_table.categories.arn}/index/*",
          aws_dynamodb_table.transaction_category_assignments.arn,
          "${aws_dynamodb_table.transaction_category_assignments.arn}/index/*",
          aws_dynamodb_table.fzip_jobs.arn,
          "${aws_dynamodb_table.fzip_jobs.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "s3-access-v2"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:HeadObject",
          "s3:ListBucket",
          "s3:PutObject"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.file_storage.arn,
          "${aws_s3_bucket.file_storage.arn}/*",
          aws_s3_bucket.fzip_packages.arn,
          "${aws_s3_bucket.fzip_packages.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_eventbridge_access" {
  name = "eventbridge-access-v1"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "events:PutEvents"
        ]
        Effect = "Allow"
        Resource = [
          aws_cloudwatch_event_bus.app_events.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_cloudwatch_metrics" {
  name = "cloudwatch-metrics-access-v1"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "file_operations" {
  name              = "/aws/lambda/${aws_lambda_function.file_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "s3_event_handler" {
  name              = "/aws/lambda/${aws_lambda_function.s3_event_handler.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "account_operations" {
  name              = "/aws/lambda/${aws_lambda_function.account_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "transaction_operations" {
  name              = "/aws/lambda/${aws_lambda_function.transaction_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "transfer_operations" {
  name              = "/aws/lambda/${aws_lambda_function.transfer_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "analytics_operations" {
  name              = "/aws/lambda/${aws_lambda_function.analytics_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Analytics Processor Lambda (Scheduled)
resource "aws_lambda_function" "analytics_processor" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-analytics-processor"
  handler          = "services/analytics_processor_service.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 300 # 5 minutes timeout for processing
  memory_size      = 512 # More memory for analytics processing
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT            = var.environment
      ANALYTICS_DATA_TABLE   = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
      TRANSACTIONS_TABLE     = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE         = aws_dynamodb_table.accounts.name
      FILES_TABLE            = aws_dynamodb_table.transaction_files.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "analytics_processor" {
  name              = "/aws/lambda/${aws_lambda_function.analytics_processor.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch Events Rule to trigger analytics processor every 10 minutes
resource "aws_cloudwatch_event_rule" "analytics_processor_schedule" {
  name                = "${var.project_name}-${var.environment}-analytics-processor-schedule"
  description         = "Trigger analytics processor every 10 minutes"
  schedule_expression = "rate(10 minutes)"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_event_target" "analytics_processor_target" {
  rule      = aws_cloudwatch_event_rule.analytics_processor_schedule.name
  target_id = "AnalyticsProcessorTarget"
  arn       = aws_lambda_function.analytics_processor.arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_analytics_processor" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analytics_processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.analytics_processor_schedule.arn
}

# Categories Lambda IAM Resources
data "aws_iam_policy_document" "categories_lambda_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "categories_lambda_role" {
  name               = "${var.project_name}-${var.environment}-categories-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.categories_lambda_assume_role_policy.json
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

data "aws_iam_policy_document" "categories_lambda_dynamodb_policy_doc" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      # Ensure aws_dynamodb_table.categories is defined, if not, this will need adjustment
      # Assuming it's defined in another .tf file (e.g., dynamo_categories.tf)
      aws_dynamodb_table.categories.arn,
      "${aws_dynamodb_table.categories.arn}/index/*",
      aws_dynamodb_table.transaction_category_assignments.arn,
      "${aws_dynamodb_table.transaction_category_assignments.arn}/index/*",
      aws_dynamodb_table.transactions.arn,
      "${aws_dynamodb_table.transactions.arn}/index/*"
    ]
  }
}

resource "aws_iam_policy" "categories_lambda_dynamodb_policy" {
  name        = "${var.project_name}-${var.environment}-categories-lambda-dynamodb-policy"
  description = "IAM policy for Categories Lambda to access Categories DynamoDB table"
  policy      = data.aws_iam_policy_document.categories_lambda_dynamodb_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "categories_lambda_dynamodb_attachment" {
  role       = aws_iam_role.categories_lambda_role.name
  policy_arn = aws_iam_policy.categories_lambda_dynamodb_policy.arn
}

resource "aws_iam_role_policy_attachment" "categories_lambda_basic_execution" {
  role       = aws_iam_role.categories_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# =========================================
# USER PREFERENCES LAMBDA IAM PERMISSIONS
# =========================================

data "aws_iam_policy_document" "user_preferences_lambda_dynamodb_policy_doc" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = [
      aws_dynamodb_table.user_preferences.arn,
      "${aws_dynamodb_table.user_preferences.arn}/index/*"
    ]
  }
}

resource "aws_iam_policy" "user_preferences_lambda_dynamodb_policy" {
  name        = "${var.project_name}-${var.environment}-user-preferences-lambda-dynamodb-policy"
  description = "IAM policy for User Preferences Lambda to access User Preferences DynamoDB table"
  policy      = data.aws_iam_policy_document.user_preferences_lambda_dynamodb_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "user_preferences_lambda_dynamodb_attachment" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.user_preferences_lambda_dynamodb_policy.arn
}
# End Categories Lambda IAM Resources

# Categories Lambda Function
resource "aws_lambda_function" "categories_lambda" {
  function_name = "${var.project_name}-${var.environment}-categories-lambda"
  role          = aws_iam_role.categories_lambda_role.arn
  handler       = "handlers/category_operations.handler" # Updated handler
  runtime       = "python3.12"
  timeout       = 30  # seconds
  memory_size   = 256 # MB

  filename         = "../../backend/lambda_deploy.zip"    # Use common deployment package
  source_code_hash = base64encode(local.source_code_hash) # Use common source_code_hash
  depends_on       = [null_resource.prepare_lambda]       # Add dependency

  environment {
    variables = {
      CATEGORIES_TABLE_NAME                  = aws_dynamodb_table.categories.name # Ensure aws_dynamodb_table.categories is defined
      TRANSACTION_CATEGORY_ASSIGNMENTS_TABLE = aws_dynamodb_table.transaction_category_assignments.name
      TRANSACTIONS_TABLE                     = aws_dynamodb_table.transactions.name
      ENVIRONMENT                            = var.environment
      LOG_LEVEL                              = "INFO"
      # Add other necessary environment variables if any, e.g. for utils
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}
# End Categories Lambda Function

# Export Operations Lambda
resource "aws_lambda_function" "export_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-export-operations"
  handler          = "handlers/export_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 900  # 15 minutes for export processing
  memory_size      = 1024 # More memory for large exports
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      FZIP_JOBS_TABLE       = aws_dynamodb_table.fzip_jobs.name
      ACCOUNTS_TABLE        = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE    = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE       = aws_dynamodb_table.file_maps.name
      FILES_TABLE           = aws_dynamodb_table.transaction_files.name
      ANALYTICS_DATA_TABLE  = aws_dynamodb_table.analytics_data.name
      FILE_STORAGE_BUCKET   = aws_s3_bucket.file_storage.id
      EVENT_BUS_NAME        = aws_cloudwatch_event_bus.app_events.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# FZIP Operations Lambda (Unified Backup/Restore with Import/Export compatibility)
resource "aws_lambda_function" "fzip_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-fzip-operations"
  handler          = "handlers/fzip_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 900  # 15 minutes for backup/restore processing
  memory_size      = 1024 # More memory for large operations
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]
  publish          = true # Enable versioning

  environment {
    variables = {
      ENVIRONMENT                            = var.environment
      FZIP_JOBS_TABLE                        = aws_dynamodb_table.fzip_jobs.name
      FZIP_PACKAGES_BUCKET                   = aws_s3_bucket.fzip_packages.bucket
      FZIP_RESTORE_PACKAGES_BUCKET           = aws_s3_bucket.fzip_packages.bucket
      ACCOUNTS_TABLE                         = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE                     = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME                  = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE                        = aws_dynamodb_table.file_maps.name
      FILES_TABLE                            = aws_dynamodb_table.transaction_files.name
      ANALYTICS_DATA_TABLE                   = aws_dynamodb_table.analytics_data.name
      FILE_STORAGE_BUCKET                    = aws_s3_bucket.file_storage.id
      EVENT_BUS_NAME                         = aws_cloudwatch_event_bus.app_events.name
      TRANSACTION_CATEGORY_ASSIGNMENTS_TABLE = aws_dynamodb_table.transaction_category_assignments.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Create semver alias for FZIP operations
resource "aws_lambda_alias" "fzip_operations_version" {
  name             = local.app_version
  description      = "Semver alias for FZIP operations Lambda - ${local.app_version_raw} (alias: ${local.app_version})"
  function_name    = aws_lambda_function.fzip_operations.function_name
  function_version = aws_lambda_function.fzip_operations.version
}

resource "aws_cloudwatch_log_group" "fzip_operations" {
  name              = "/aws/lambda/${aws_lambda_function.fzip_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Note: Versioned log groups are automatically created by AWS when the alias is invoked
# The log streams will show the version name like: [v1.0.0.123]

resource "aws_cloudwatch_log_group" "export_operations" {
  name              = "/aws/lambda/${aws_lambda_function.export_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "categories_lambda" {
  name              = "/aws/lambda/${aws_lambda_function.categories_lambda.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs
output "lambda_file_operations_name" {
  value = aws_lambda_function.file_operations.function_name
}

output "lambda_s3_event_handler_name" {
  value = aws_lambda_function.s3_event_handler.function_name
}

output "lambda_account_operations_name" {
  value = aws_lambda_function.account_operations.function_name
}

output "lambda_transaction_operations_name" {
  value = aws_lambda_function.transaction_operations.function_name
}

output "lambda_analytics_operations_name" {
  description = "Name of the Analytics Operations Lambda function"
  value       = aws_lambda_function.analytics_operations.function_name
}

output "lambda_analytics_operations_arn" {
  description = "ARN of the Analytics Operations Lambda function"
  value       = aws_lambda_function.analytics_operations.arn
}

output "lambda_analytics_operations_invoke_arn" {
  description = "Invoke ARN of the Analytics Operations Lambda function"
  value       = aws_lambda_function.analytics_operations.invoke_arn
}

output "lambda_analytics_processor_name" {
  description = "Name of the Analytics Processor Lambda function"
  value       = aws_lambda_function.analytics_processor.function_name
}

output "lambda_analytics_processor_arn" {
  description = "ARN of the Analytics Processor Lambda function"
  value       = aws_lambda_function.analytics_processor.arn
}

output "lambda_getcolors_name" {
  value = aws_lambda_function.getcolors.function_name
}

output "categories_lambda_name" {
  description = "Name of the Categories Lambda function"
  value       = aws_lambda_function.categories_lambda.function_name
}

output "lambda_fzip_operations_name" {
  description = "Name of the FZIP Operations Lambda function"
  value       = aws_lambda_function.fzip_operations.function_name
}

output "lambda_fzip_operations_version_alias" {
  description = "Version alias for FZIP Operations Lambda (semver)"
  value       = aws_lambda_alias.fzip_operations_version.name
}

output "lambda_fzip_operations_versioned_arn" {
  description = "ARN of the versioned FZIP Operations Lambda alias"
  value       = aws_lambda_alias.fzip_operations_version.arn
}

output "app_version_raw" {
  description = "The raw app version from build script (e.g., v1.0.0.1)"
  value       = local.app_version_raw
}

output "app_version_alias" {
  description = "The Lambda alias version (dots replaced with underscores, e.g., v1_0_0_1)"
  value       = local.app_version
}

output "categories_lambda_arn" {
  description = "ARN of the Categories Lambda function"
  value       = aws_lambda_function.categories_lambda.arn
}

output "categories_lambda_invoke_arn" {
  description = "Invoke ARN of the Categories Lambda function"
  value       = aws_lambda_function.categories_lambda.invoke_arn
}

# === Merged from lambda_field_maps.tf ===

# File map operations Lambda function
resource "aws_lambda_function" "file_map_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-map-operations"
  handler          = "handlers/file_map_operations.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILE_MAPS_TABLE     = aws_dynamodb_table.file_maps.name
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch log group for file map operations Lambda
resource "aws_cloudwatch_log_group" "file_map_operations" {
  name              = "/aws/lambda/${aws_lambda_function.file_map_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Lambda permission for API Gateway to invoke file map operations
resource "aws_lambda_permission" "api_gateway_file_maps" {
  statement_id  = "AllowAPIGatewayInvokeFileMaps"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_map_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# =========================================
# USER PREFERENCES LAMBDA FUNCTION
# =========================================

# Lambda function for user preferences operations
resource "aws_lambda_function" "user_preferences_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-user-preferences-operations"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "handlers/user_preferences_operations.handler"
  source_code_hash = base64encode(local.source_code_hash)
  runtime         = "python3.12"
  timeout         = 30
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      USER_PREFERENCES_TABLE = aws_dynamodb_table.user_preferences.name
      ACCOUNTS_TABLE         = aws_dynamodb_table.accounts.name
      ENVIRONMENT           = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Lambda permission for API Gateway to invoke user preferences operations
resource "aws_lambda_permission" "api_gateway_user_preferences" {
  statement_id  = "AllowAPIGatewayInvokeUserPreferences"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.user_preferences_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Output the Lambda function name
output "lambda_user_preferences_operations_name" {
  description = "The name of the user preferences operations Lambda function"
  value       = aws_lambda_function.user_preferences_operations.function_name
}

# Output the Lambda function name
output "lambda_file_map_operations_name" {
  description = "The name of the file map operations Lambda function"
  value       = aws_lambda_function.file_map_operations.function_name
} 