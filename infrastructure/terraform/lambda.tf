# Run tests and prepare Lambda package
resource "null_resource" "prepare_lambda" {
  triggers = {
    source_code_hash = "${sha256(file("../../backend/requirements.txt"))}-${sha256(join("", [for f in fileset("../../backend/src", "**"): filesha256("../../backend/src/${f}")])) }"
  }

  provisioner "local-exec" {
    working_dir = "../../backend"
    command     = <<EOF
      echo "Current working directory:"
      pwd
      
      # Create test venv and install all dependencies for testing
      python -m venv .venv_test
      source .venv_test/bin/activate
      pip install -r requirements.txt
      
      # Run tests
      chmod +x run_tests.sh && ./run_tests.sh
      
      # Deactivate test venv
      deactivate
      
      # Setup build
      rm -rf build
      mkdir -p build
      
      # Install only Lambda runtime dependencies directly to build directory
      python3.10 -m pip install \
        -r requirements-lambda.txt \
        -t build/ \
        --platform manylinux2014_x86_64 \
        --python-version 3.10 \
        --only-binary=:all:
      
      # Copy source code
      cp -r src/* build/
      
      # Clean up unnecessary files
      find build -type d -name "__pycache__" -exec rm -rf {} +
      find build -type f -name "*.pyc" -delete
      find build -type f -name "*.pyo" -delete
      find build -type f -name "*.dll" -delete
      find build -type f -name "*.exe" -delete
      find build -type f -name "*.bat" -delete
      find build -type f -name "*.sh" -delete
      find build -type f -name "*.txt" -delete
      find build -type f -name "*.md" -delete
      find build -type f -name "*.rst" -delete
      find build -type f -name "*.html" -delete
      find build -type f -name "*.css" -delete
      find build -type f -name "*.js" -delete
      find build -type f -name "*.json" -delete
      find build -type f -name "*.xml" -delete
      find build -type f -name "*.yaml" -delete
      find build -type f -name "*.yml" -delete
      find build -type f -name "*.ini" -delete
      find build -type f -name "*.cfg" -delete
      find build -type f -name "*.conf" -delete
      find build -type f -name "*.log" -delete
      find build -type f -name "*.dat" -delete
      find build -type f -name "*.db" -delete
      find build -type f -name "*.sqlite" -delete
      find build -type f -name "*.sqlite3" -delete
      find build -type f -name "*.pdb" -delete
      find build -type f -name "*.pyd" -delete
      find build -type f -name "*.pyi" -delete
      find build -type f -name "*.pyx" -delete
      find build -type f -name "*.pxd" -delete
      find build -type f -name "*.pxi" -delete
      find build -type f -name "*.h" -delete
      find build -type f -name "*.c" -delete
      find build -type f -name "*.cpp" -delete
      find build -type f -name "*.cc" -delete
      find build -type f -name "*.cxx" -delete
      find build -type f -name "*.hpp" -delete
      find build -type f -name "*.hh" -delete
      find build -type f -name "*.hxx" -delete
      find build -type f -name "*.f" -delete
      find build -type f -name "*.f90" -delete
      find build -type f -name "*.f95" -delete
      find build -type f -name "*.f03" -delete
      find build -type f -name "*.f08" -delete
      find build -type f -name "*.for" -delete
      find build -type f -name "*.ftn" -delete
      
      # Create deployment package
      cd build
      zip -r ../lambda_deploy.zip .
      cd ..
      
      # Cleanup
      rm -rf build .venv_test
      
      echo "Build process complete!"
      echo "Final working directory:"
      pwd
      echo "Lambda package location:"
      ls -l lambda_deploy.zip
    EOF
  }
}

# Calculate source code hash from source files
locals {
  source_code_hash = "${sha256(file("../../backend/requirements.txt"))}-${sha256(join("", [for f in fileset("../../backend/src", "**"): filesha256("../../backend/src/${f}")])) }"
}

# File Operations Lambda
resource "aws_lambda_function" "file_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-operations"
  handler          = "handlers/file_operations.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 300
  memory_size     = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FILE_MAPS_TABLE    = aws_dynamodb_table.file_maps.name
      DEPLOYMENT_VERSION  = "v4"
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# File Processor Lambda
resource "aws_lambda_function" "file_processor" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-processor"
  handler          = "handlers/file_processor.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 60
  memory_size     = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      FILES_TABLE           = aws_dynamodb_table.transaction_files.name
      TRANSACTIONS_TABLE    = aws_dynamodb_table.transactions.name
      FILE_STORAGE_BUCKET   = aws_s3_bucket.file_storage.id
      ACCOUNTS_TABLE        = aws_dynamodb_table.accounts.name
      FILE_MAPS_TABLE       = aws_dynamodb_table.file_maps.name
      ANALYTICS_DATA_TABLE  = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
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
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]
  
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
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
      FILES_TABLE        = aws_dynamodb_table.transaction_files.name
      ACCOUNTS_TABLE     = aws_dynamodb_table.accounts.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Analytics Operations Lambda
resource "aws_lambda_function" "analytics_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-analytics-operations"
  handler          = "handlers/analytics_operations.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 300
  memory_size     = 512
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      ANALYTICS_DATA_TABLE  = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
      TRANSACTIONS_TABLE    = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE        = aws_dynamodb_table.accounts.name
      FILES_TABLE           = aws_dynamodb_table.transaction_files.name
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
  role            = aws_iam_role.lambda_exec.arn
  handler         = "handlers/getcolors.handler"
  source_code_hash = base64encode(local.source_code_hash)
  runtime         = "python3.10"
  timeout         = 30
  memory_size     = 128
  depends_on      = [null_resource.prepare_lambda]

  environment {
    variables = {
      DYNAMODB_ACCOUNTS_TABLE = aws_dynamodb_table.accounts.name
      DYNAMODB_FILES_TABLE   = aws_dynamodb_table.transaction_files.name
      DYNAMODB_TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
      S3_BUCKET             = aws_s3_bucket.file_storage.id
      TESTING              = "false"
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Trigger for File Processor
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor.function_name
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
          "${aws_dynamodb_table.analytics_status.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "file_operations" {
  name              = "/aws/lambda/${aws_lambda_function.file_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "file_processor" {
  name              = "/aws/lambda/${aws_lambda_function.file_processor.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "account_operations" {
  name              = "/aws/lambda/${aws_lambda_function.account_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cloudwatch_log_group" "transaction_operations" {
  name              = "/aws/lambda/${aws_lambda_function.transaction_operations.function_name}"
  retention_in_days = 7

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
  handler          = "handlers/analytics_processor.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 300  # 5 minutes timeout for processing
  memory_size     = 512  # More memory for analytics processing
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      ANALYTICS_DATA_TABLE  = aws_dynamodb_table.analytics_data.name
      ANALYTICS_STATUS_TABLE = aws_dynamodb_table.analytics_status.name
      TRANSACTIONS_TABLE    = aws_dynamodb_table.transactions.name
      ACCOUNTS_TABLE        = aws_dynamodb_table.accounts.name
      FILES_TABLE           = aws_dynamodb_table.transaction_files.name
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
      "${aws_dynamodb_table.categories.arn}/index/*"
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
# End Categories Lambda IAM Resources

# Categories Lambda Function
resource "aws_lambda_function" "categories_lambda" {
  function_name = "${var.project_name}-${var.environment}-categories-lambda"
  role          = aws_iam_role.categories_lambda_role.arn
  handler       = "handlers/category_operations.handler" # Updated handler
  runtime       = "python3.10"
  timeout       = 30 # seconds
  memory_size   = 256 # MB

  filename         = "../../backend/lambda_deploy.zip"     # Use common deployment package
  source_code_hash = base64encode(local.source_code_hash) # Use common source_code_hash
  depends_on       = [null_resource.prepare_lambda]        # Add dependency

  environment {
    variables = {
      CATEGORIES_TABLE_NAME = aws_dynamodb_table.categories.name # Ensure aws_dynamodb_table.categories is defined
      ENVIRONMENT           = var.environment
      LOG_LEVEL             = "INFO"
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

output "lambda_file_processor_name" {
  value = aws_lambda_function.file_processor.function_name
}

output "lambda_account_operations_name" {
  value = aws_lambda_function.account_operations.function_name
}

output "lambda_transaction_operations_name" {
  value = aws_lambda_function.transaction_operations.function_name
}

output "lambda_analytics_operations_name" {
  description = "Name of the Analytics Operations Lambda function"
  value = aws_lambda_function.analytics_operations.function_name
}

output "lambda_analytics_operations_arn" {
  description = "ARN of the Analytics Operations Lambda function"
  value = aws_lambda_function.analytics_operations.arn
}

output "lambda_analytics_operations_invoke_arn" {
  description = "Invoke ARN of the Analytics Operations Lambda function"
  value = aws_lambda_function.analytics_operations.invoke_arn
}

output "lambda_analytics_processor_name" {
  description = "Name of the Analytics Processor Lambda function"
  value = aws_lambda_function.analytics_processor.function_name
}

output "lambda_analytics_processor_arn" {
  description = "ARN of the Analytics Processor Lambda function"
  value = aws_lambda_function.analytics_processor.arn
}

output "lambda_getcolors_name" {
  value = aws_lambda_function.getcolors.function_name
}

output "categories_lambda_name" {
  description = "Name of the Categories Lambda function"
  value       = aws_lambda_function.categories_lambda.function_name
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
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = base64encode(local.source_code_hash)
  depends_on       = [null_resource.prepare_lambda]

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      FILE_MAPS_TABLE   = aws_dynamodb_table.file_maps.name
      FILES_TABLE       = aws_dynamodb_table.transaction_files.name
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

# Output the Lambda function name
output "lambda_file_map_operations_name" {
  description = "The name of the file map operations Lambda function"
  value       = aws_lambda_function.file_map_operations.function_name
} 