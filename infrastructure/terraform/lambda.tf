resource "null_resource" "run_tests" {
  provisioner "local-exec" {
    working_dir = "../../backend"
    command     = "chmod +x run_tests.sh && ./run_tests.sh"
  }
}

data "archive_file" "lambda_code" {
  depends_on = [null_resource.run_tests]
  type        = "zip"
  source_dir  = "../../backend/src"
  output_path = "../../backend/lambda.zip"
}

resource "aws_lambda_function" "colors" {
  filename         = "../../backend/lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-colors"
  handler          = "handlers/list_imports.handler"
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT    = var.environment
      DYNAMODB_TABLE = aws_dynamodb_table.transaction_files.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_lambda_function" "file_operations" {
  filename         = "../../backend/lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-file-operations"
  handler          = "handlers/file_operations.handler"
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      FILES_TABLE        = aws_dynamodb_table.transaction_files.name
      ACCOUNTS_TABLE     = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_lambda_function" "file_processor" {
  filename         = "../../backend/lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-file-processor"
  handler          = "handlers/file_processor.handler"
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT    = var.environment
      FILES_TABLE    = aws_dynamodb_table.transaction_files.name
      TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_lambda_function" "account_operations" {
  filename         = "../../backend/lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-account-operations"
  handler          = "handlers/account_operations.handler"
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_exec.arn
  timeout          = 30
  memory_size      = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT    = var.environment
      ACCOUNTS_TABLE = aws_dynamodb_table.accounts.name
      FILES_TABLE    = aws_dynamodb_table.transaction_files.name
      TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Configure S3 to trigger Lambda on file uploads
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.file_storage.arn
}

# CloudWatch Log Group for file processor Lambda
resource "aws_cloudwatch_log_group" "file_processor" {
  name              = "/aws/lambda/${aws_lambda_function.file_processor.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

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

# IAM policy for Lambda to access DynamoDB
resource "aws_iam_role_policy" "lambda_dynamodb_access" {
  name   = "dynamodb-access"
  role   = aws_iam_role.lambda_exec.id
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
        Effect   = "Allow"
        Resource = [
          aws_dynamodb_table.transaction_files.arn,
          "${aws_dynamodb_table.transaction_files.arn}/index/*",
          aws_dynamodb_table.accounts.arn,
          "${aws_dynamodb_table.accounts.arn}/index/*",
          aws_dynamodb_table.transactions.arn,
          "${aws_dynamodb_table.transactions.arn}/index/*"
        ]
      }
    ]
  })
}

# CloudWatch log group for file operations Lambda
resource "aws_cloudwatch_log_group" "file_operations" {
  name              = "/aws/lambda/${aws_lambda_function.file_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch log group for account operations Lambda
resource "aws_cloudwatch_log_group" "account_operations" {
  name              = "/aws/lambda/${aws_lambda_function.account_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.colors.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs
output "lambda_function_name" {
  value = aws_lambda_function.colors.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.colors.arn
}

output "file_operations_function_name" {
  value = aws_lambda_function.file_operations.function_name
}

output "file_operations_function_arn" {
  value = aws_lambda_function.file_operations.arn
}

output "account_operations_function_name" {
  value = aws_lambda_function.account_operations.function_name
}

output "account_operations_function_arn" {
  value = aws_lambda_function.account_operations.arn
} 