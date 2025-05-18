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
      rm -rf build lambda_deploy.zip
      mkdir -p build
      
      # Install only Lambda runtime dependencies directly to build directory
      pip install -r requirements-lambda.txt -t build/
      
      # Copy source code
      cp -r src/* build/
      
      # Clean up unnecessary files
      find build -type d -name "__pycache__" -exec rm -rf {} +
      find build -type d -name "*.dist-info" -exec rm -rf {} +
      find build -type d -name "*.egg-info" -exec rm -rf {} +
      find build -type f -name "*.pyc" -delete
      find build -type f -name "*.pyo" -delete
      find build -type f -name "*.so" -delete
      find build -type f -name "*.dylib" -delete
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
      
      # Check package size
      PACKAGE_SIZE=$(stat -c %s lambda_deploy.zip)
      MAX_SIZE=2621440  # 2.5MB in bytes
      
      echo "Final package size:"
      ls -lh lambda_deploy.zip
      
      if [ "$PACKAGE_SIZE" -gt "$MAX_SIZE" ]; then
        echo "Error: Lambda package size ($PACKAGE_SIZE bytes) exceeds maximum allowed size ($MAX_SIZE bytes)"
        echo "Largest files in package:"
        unzip -l lambda_deploy.zip | sort -k1nr | head -n 10
        exit 1
      fi
      
      # Cleanup
      rm -rf .venv_test build
      
      echo "Build process complete!"
      echo "Final working directory:"
      pwd
      echo "Lambda package location:"
      ls -l lambda_deploy.zip
    EOF
  }
}

# File Operations Lambda
resource "aws_lambda_function" "file_operations" {
  filename         = "${path.module}/../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-operations"
  handler          = "handlers/file_operations.handler"
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = filebase64sha256("../../backend/lambda_deploy.zip")
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
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 60
  memory_size     = 256
  source_code_hash = filebase64sha256("../../backend/lambda_deploy.zip")
  depends_on      = [null_resource.prepare_lambda]
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      FILES_TABLE         = aws_dynamodb_table.transaction_files.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      FILE_MAPS_TABLE    = aws_dynamodb_table.file_maps.name
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
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = filebase64sha256("../../backend/lambda_deploy.zip")
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
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = filebase64sha256("../../backend/lambda_deploy.zip")
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

# Get Colors Lambda
resource "aws_lambda_function" "getcolors" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-getcolors"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "handlers/getcolors.handler"
  source_code_hash = filebase64sha256("../../backend/lambda_deploy.zip")
  runtime         = "python3.11"
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
          aws_dynamodb_table.file_maps.arn,
          "${aws_dynamodb_table.file_maps.arn}/index/*"
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