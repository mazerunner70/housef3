# Run tests before packaging
resource "null_resource" "run_tests" {
  provisioner "local-exec" {
    working_dir = "../../backend"
    command     = "chmod +x run_tests.sh && ./run_tests.sh"
  }
}

# Package Lambda code
data "archive_file" "lambda_code" {
  depends_on  = [null_resource.run_tests]
  type        = "zip"
  source_dir  = "../../backend/src"
  output_path = "../../backend/lambda.zip"
}

# File Operations Lambda
resource "aws_lambda_function" "file_operations" {
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "${var.project_name}-${var.environment}-file-operations"
  handler          = "handlers/file_operations.handler"
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FIELD_MAPS_TABLE    = aws_dynamodb_table.field_maps.name
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
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "${var.project_name}-${var.environment}-file-processor"
  handler          = "handlers/file_processor.handler"
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 60
  memory_size     = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
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
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "${var.project_name}-${var.environment}-account-operations"
  handler          = "handlers/account_operations.handler"
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  
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
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "${var.project_name}-${var.environment}-transaction-operations"
  handler          = "handlers/transaction_operations.handler"
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = data.archive_file.lambda_code.output_base64sha256

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
  name = "dynamodb-access-v2"
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
          aws_dynamodb_table.field_maps.arn,
          "${aws_dynamodb_table.field_maps.arn}/index/*"
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

output "lambda_getcolors_name" {
  value = aws_lambda_function.getcolors.function_name
}

resource "aws_lambda_function" "getcolors" {
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "${var.project_name}-getcolors"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "handlers/getcolors.handler"
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 128

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