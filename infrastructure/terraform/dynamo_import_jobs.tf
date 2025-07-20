# Data sources for AWS account and region information
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Centralized S3 Access Logging Bucket
resource "aws_s3_bucket" "s3_access_logs" {
  bucket = "${var.project_name}-${var.environment}-s3-access-logs"
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "s3-access-logs"
  }
}

# S3 Bucket Public Access Block for Centralized Logging Bucket
resource "aws_s3_bucket_public_access_block" "s3_access_logs_public_access_block" {
  bucket = aws_s3_bucket.s3_access_logs.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket ACL for Log Delivery (Centralized)
resource "aws_s3_bucket_acl" "s3_access_logs_acl" {
  bucket = aws_s3_bucket.s3_access_logs.id
  acl    = "log-delivery-write"
}

# S3 Bucket Policy for HTTPS-only access (Centralized)
resource "aws_s3_bucket_policy" "s3_access_logs_policy" {
  bucket = aws_s3_bucket.s3_access_logs.id
  
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
        Resource = "${aws_s3_bucket.s3_access_logs.arn}/*"
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
        Resource = "${aws_s3_bucket.s3_access_logs.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption-aws-kms-key-id" = "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
          }
        }
      },
      {
        Sid    = "DenyNonHTTPSRequests"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.s3_access_logs.arn,
          "${aws_s3_bucket.s3_access_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Import Packages Logging Bucket
resource "aws_s3_bucket" "import_packages_logs" {
  bucket = "${var.environment}-import-packages-logs"
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "import-packages-logs"
  }
}

# Dedicated CloudFront Logging Bucket
resource "aws_s3_bucket" "cloudfront_logs" {
  bucket = "${var.project_name}-${var.environment}-cloudfront-logs"
  
  tags = {
    Environment = var.environment
    Project     = "housef3"
    Component   = "cloudfront-logs"
  }
}

# Disable ownership controls to allow ACLs for CloudFront logging
resource "aws_s3_bucket_ownership_controls" "cloudfront_logs_ownership" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# S3 Bucket ACL for CloudFront Logging
resource "aws_s3_bucket_acl" "cloudfront_logs_acl" {
  bucket = aws_s3_bucket.cloudfront_logs.id
  acl    = "log-delivery-write"
}

# S3 Bucket Public Access Block for CloudFront Logging Bucket
resource "aws_s3_bucket_public_access_block" "cloudfront_logs_public_access_block" {
  bucket = aws_s3_bucket.cloudfront_logs.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Policy for CloudFront Logging (HTTPS-only)
resource "aws_s3_bucket_policy" "cloudfront_logs_policy" {
  bucket = aws_s3_bucket.cloudfront_logs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyNonHTTPSRequests"
        Effect = "Deny"
        Principal = {
          AWS = "*"
        }
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.cloudfront_logs.arn,
          "${aws_s3_bucket.cloudfront_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

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
  
  target_bucket = aws_s3_bucket.s3_access_logs.id
  target_prefix = "s3-access-logs/import-packages/"
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
    
    filter {
      prefix = ""
    }
    
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

# Data source for Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../backend/src"
  output_path = "${path.module}/lambda_import_operations.zip"
  excludes    = ["__pycache__", "*.pyc", "tests", "venv"]
}

# Lambda Function for Import Operations
resource "aws_lambda_function" "import_operations" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.environment}-import-operations"
  role            = aws_iam_role.lambda_exec.arn
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
      FILES_TABLE          = aws_dynamodb_table.transaction_files.name
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
          aws_dynamodb_table.transaction_files.arn,
          "${aws_dynamodb_table.transaction_files.arn}/index/*",
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
resource "aws_apigatewayv2_integration" "import_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.import_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for import operations endpoints"
}

# Import routes
resource "aws_apigatewayv2_route" "import_post" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /import"
  target             = "integrations/${aws_apigatewayv2_integration.import_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "import_get" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /import"
  target             = "integrations/${aws_apigatewayv2_integration.import_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "import_status_get" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /import/{importId}/status"
  target             = "integrations/${aws_apigatewayv2_integration.import_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "import_delete" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /import/{importId}"
  target             = "integrations/${aws_apigatewayv2_integration.import_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "import_upload_post" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /import/{importId}/upload"
  target             = "integrations/${aws_apigatewayv2_integration.import_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "import_operations_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.import_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
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