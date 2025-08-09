# =========================================
# S3 ACCESS LOGS BUCKET
# =========================================
# Centralized S3 bucket for storing access logs from other S3 buckets


resource "aws_s3_bucket" "s3_access_logs" {
  bucket = "${var.project_name}-${var.environment}-s3-access-logs"



  tags = {
    Environment = var.environment
    Project     = var.project_name
    Component   = "s3-access-logs"
  }

  # Note: Access logs bucket logs to frontend bucket to avoid self-referential loop
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "s3_access_logs_versioning" {
  bucket = aws_s3_bucket.s3_access_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket ACL Configuration - Required for CloudFront logging
resource "aws_s3_bucket_acl" "s3_access_logs_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.s3_access_logs_ownership]
  bucket     = aws_s3_bucket.s3_access_logs.id
  acl        = "log-delivery-write"
}

# S3 Bucket Ownership Controls - Required for ACL
resource "aws_s3_bucket_ownership_controls" "s3_access_logs_ownership" {
  bucket = aws_s3_bucket.s3_access_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# S3 Bucket Lifecycle Configuration
resource "aws_s3_bucket_lifecycle_configuration" "s3_access_logs_lifecycle" {
  bucket = aws_s3_bucket.s3_access_logs.id

  rule {
    id     = "cleanup_old_logs"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 90 # Keep logs for 90 days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "s3_access_logs_public_access_block" {
  bucket = aws_s3_bucket.s3_access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Policy for Access Logs - Minimal policy for security
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

# Outputs for the S3 access logs bucket
output "s3_access_logs_bucket_name" {
  description = "The name of the S3 access logs bucket"
  value       = aws_s3_bucket.s3_access_logs.bucket
}

output "s3_access_logs_bucket_arn" {
  description = "The ARN of the S3 access logs bucket"
  value       = aws_s3_bucket.s3_access_logs.arn
}

# =========================================
# UNIFIED LOGGING BUCKET OUTPUTS
# =========================================

# Outputs for the unified logging bucket
output "unified_logs_bucket_name" {
  description = "The name of the unified logging bucket"
  value       = aws_s3_bucket.s3_access_logs.bucket
}

output "unified_logs_bucket_arn" {
  description = "The ARN of the unified logging bucket"
  value       = aws_s3_bucket.s3_access_logs.arn
} 