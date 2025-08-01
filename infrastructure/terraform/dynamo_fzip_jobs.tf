# =========================================
# DYNAMODB TABLE FOR FZIP JOBS
# =========================================
# This file contains configurations for the unified DynamoDB table
# used to store FZIP (Financial ZIP) backup/restore job status and metadata.
# Also supports legacy import/export job compatibility.

resource "aws_dynamodb_table" "fzip_jobs" {
  name           = "${var.project_name}-${var.environment}-fzip-jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "jobId"

  attribute {
    name = "jobId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "jobType"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "N"
  }

  attribute {
    name = "expiresAt"
    type = "N"
  }

  # Global Secondary Index for querying jobs by user and creation date
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "createdAt"
    projection_type    = "ALL"
  }

  # Global Secondary Index for querying jobs by type (backup/restore, legacy export/import)
  global_secondary_index {
    name               = "JobTypeIndex"
    hash_key           = "jobType"
    range_key          = "createdAt"
    projection_type    = "ALL"
  }

  # Global Secondary Index for querying jobs by status
  global_secondary_index {
    name               = "StatusIndex"
    hash_key           = "status"
    range_key          = "createdAt"
    projection_type    = "ALL"
  }

  # Global Secondary Index for querying jobs by user and type
  global_secondary_index {
    name               = "UserJobTypeIndex"
    hash_key           = "userId"
    range_key          = "jobType"
    projection_type    = "ALL"
  }

  # Global Secondary Index for expired jobs cleanup
  global_secondary_index {
    name               = "ExpiresAtIndex"
    hash_key           = "expiresAt"
    projection_type    = "ALL"
  }

  # Enable TTL for automatic cleanup of old FZIP jobs
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-fzip-jobs"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "FZIP backup and restore jobs"
  }
}

# Outputs for the FZIP jobs table
output "fzip_jobs_table_name" {
  description = "The name of the DynamoDB FZIP jobs table"
  value       = aws_dynamodb_table.fzip_jobs.name
}

output "fzip_jobs_table_arn" {
  description = "The ARN of the DynamoDB FZIP jobs table"
  value       = aws_dynamodb_table.fzip_jobs.arn
}

# =========================================
# FZIP PACKAGES S3 BUCKET
# =========================================
# Unified S3 bucket for storing FZIP packages (backup/restore, legacy import/export)

resource "aws_s3_bucket" "fzip_packages" {
  bucket = "${var.project_name}-${var.environment}-fzip-packages"
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "fzip-packages"
  }

  # S3 Bucket Logging Configuration
  logging {
    target_bucket = aws_s3_bucket.s3_access_logs.id
    target_prefix = "s3-access-logs/fzip-packages/"
  }
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "fzip_packages_versioning" {
  bucket = aws_s3_bucket.fzip_packages.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "fzip_packages_lifecycle" {
  bucket = aws_s3_bucket.fzip_packages.id
  
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
resource "aws_s3_bucket_public_access_block" "fzip_packages_public_access_block" {
  bucket = aws_s3_bucket.fzip_packages.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Policy for FZIP Packages
resource "aws_s3_bucket_policy" "fzip_packages_policy" {
  bucket = aws_s3_bucket.fzip_packages.id
  
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
        Resource = "${aws_s3_bucket.fzip_packages.arn}/*"
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
        Resource = "${aws_s3_bucket.fzip_packages.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "AES256"
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
          aws_s3_bucket.fzip_packages.arn,
          "${aws_s3_bucket.fzip_packages.arn}/*"
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

# Outputs for the FZIP packages bucket
output "fzip_packages_bucket_name" {
  description = "The name of the S3 FZIP packages bucket"
  value       = aws_s3_bucket.fzip_packages.bucket
}

output "fzip_packages_bucket_arn" {
  description = "The ARN of the S3 FZIP packages bucket"
  value       = aws_s3_bucket.fzip_packages.arn
} 