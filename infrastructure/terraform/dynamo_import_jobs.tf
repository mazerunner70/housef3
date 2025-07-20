# Import Jobs DynamoDB Table
resource "aws_dynamodb_table" "import_jobs" {
  name           = "${var.environment}-import-jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "importId"
  
  attribute {
    name = "importId"
    type = "S"
  }
  
  attribute {
    name = "userId"
    type = "S"
  }
  
  attribute {
    name = "status"
    type = "S"
  }
  
  attribute {
    name = "uploadedAt"
    type = "N"
  }
  
  attribute {
    name = "expiresAt"
    type = "N"
  }
  
  # Global Secondary Index for user-based queries
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "uploadedAt"
    projection_type    = "ALL"
  }
  
  # Global Secondary Index for status-based queries
  global_secondary_index {
    name               = "StatusIndex"
    hash_key           = "status"
    range_key          = "uploadedAt"
    projection_type    = "ALL"
  }
  
  # Global Secondary Index for expired jobs cleanup
  global_secondary_index {
    name               = "ExpiresAtIndex"
    hash_key           = "expiresAt"
    projection_type    = "ALL"
  }
  
  # TTL for automatic cleanup
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "import-jobs"
  }
}

# Import Packages S3 Bucket
resource "aws_s3_bucket" "import_packages" {
  bucket = "${var.environment}-import-packages"
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "import-packages"
  }
}

# S3 Bucket Logging Configuration
resource "aws_s3_bucket_logging" "import_packages_logging" {
  bucket = aws_s3_bucket.import_packages.id
  
  target_bucket = aws_s3_bucket.file_storage.id
  target_prefix = "logs/import-packages/"
}

# S3 Bucket ACL for Log Delivery
resource "aws_s3_bucket_acl" "file_storage_log_delivery" {
  bucket = aws_s3_bucket.file_storage.id
  acl    = "log-delivery-write"
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "import_packages_versioning" {
  bucket = aws_s3_bucket.import_packages.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "import_packages_lifecycle" {
  bucket = aws_s3_bucket.import_packages.id
  
  rule {
    id     = "cleanup_expired_packages"
    status = "Enabled"
    
    expiration {
      days = 7  # Keep packages for 7 days
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "import_packages_public_access_block" {
  bucket = aws_s3_bucket.import_packages.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Policy
resource "aws_s3_bucket_policy" "import_packages_policy" {
  bucket = aws_s3_bucket.import_packages.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.import_packages.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid    = "DenyIncorrectEncryptionHeader"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.import_packages.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
          }
        }
      },
      {
        Sid    = "DenyUnencryptedObjectUploads"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.import_packages.arn}/*"
        Condition = {
          Null = {
            "s3:x-amz-server-side-encryption" = "true"
          }
        }
      }
    ]
  })
}

# Lambda Function for Import Operations
resource "aws_lambda_function" "import_operations" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.environment}-import-operations"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handlers.import_operations.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 512
  
  environment {
    variables = {
      ENVIRONMENT           = var.environment
      IMPORT_JOBS_TABLE    = aws_dynamodb_table.import_jobs.name
      IMPORT_PACKAGES_BUCKET = aws_s3_bucket.import_packages.bucket
      ACCOUNTS_TABLE       = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE   = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE_NAME = aws_dynamodb_table.categories.name
      FILE_MAPS_TABLE      = aws_dynamodb_table.file_maps.name
      FILES_TABLE          = aws_dynamodb_table.files.name
      EXPORT_JOBS_TABLE    = aws_dynamodb_table.export_jobs.name
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "import-operations"
  }
}

# IAM Role for Import Operations Lambda
resource "aws_iam_role" "import_operations_lambda_role" {
  name = "${var.environment}-import-operations-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Import Operations Lambda
resource "aws_iam_role_policy" "import_operations_lambda_policy" {
  name = "${var.environment}-import-operations-lambda-policy"
  role = aws_iam_role.import_operations_lambda_role.id
  
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
          aws_dynamodb_table.import_jobs.arn,
          "${aws_dynamodb_table.import_jobs.arn}/index/*",
          aws_dynamodb_table.accounts.arn,
          "${aws_dynamodb_table.accounts.arn}/index/*",
          aws_dynamodb_table.transactions.arn,
          "${aws_dynamodb_table.transactions.arn}/index/*",
          aws_dynamodb_table.categories.arn,
          "${aws_dynamodb_table.categories.arn}/index/*",
          aws_dynamodb_table.file_maps.arn,
          "${aws_dynamodb_table.file_maps.arn}/index/*",
          aws_dynamodb_table.files.arn,
          "${aws_dynamodb_table.files.arn}/index/*",
          aws_dynamodb_table.export_jobs.arn,
          "${aws_dynamodb_table.export_jobs.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.import_packages.arn}/*",
          "${aws_s3_bucket.file_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.import_packages.arn,
          aws_s3_bucket.file_storage.arn
        ]
      }
    ]
  })
}

# API Gateway Integration for Import Operations
resource "aws_api_gateway_resource" "import" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "import"
}

resource "aws_api_gateway_method" "import_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.import.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "import_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.import.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "import_post_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.import.id
  http_method = aws_api_gateway_method.import_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.import_operations.invoke_arn
}

resource "aws_api_gateway_integration" "import_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.import.id
  http_method = aws_api_gateway_method.import_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.import_operations.invoke_arn
}

# Import Status Resource
resource "aws_api_gateway_resource" "import_status" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.import.id
  path_part   = "{importId}"
}

resource "aws_api_gateway_resource" "import_status_detail" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.import_status.id
  path_part   = "status"
}

resource "aws_api_gateway_method" "import_status_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.import_status_detail.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "import_status_get_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.import_status_detail.id
  http_method = aws_api_gateway_method.import_status_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.import_operations.invoke_arn
}

# Import Delete Resource
resource "aws_api_gateway_method" "import_delete" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.import_status.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "import_delete_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.import_status.id
  http_method = aws_api_gateway_method.import_delete.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.import_operations.invoke_arn
}

# Import Upload Resource
resource "aws_api_gateway_resource" "import_upload" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.import_status.id
  path_part   = "upload"
}

resource "aws_api_gateway_method" "import_upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.import_upload.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "import_upload_post_integration" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.import_upload.id
  http_method = aws_api_gateway_method.import_upload_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.import_operations.invoke_arn
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "import_operations_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.import_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# CloudWatch Log Group for Import Operations
resource "aws_cloudwatch_log_group" "import_operations_logs" {
  name              = "/aws/lambda/${aws_lambda_function.import_operations.function_name}"
  retention_in_days = 14
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "import-operations"
  }
} 