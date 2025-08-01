# =========================================
# S3 BUCKET FOR FILE MANAGEMENT SYSTEM
# =========================================
# This file contains configurations for the S3 bucket 
# used to store user-uploaded files through the file management system.

# File Storage S3 Bucket
resource "aws_s3_bucket" "file_storage" {
  bucket = "${var.project_name}-${var.environment}-file-storage"
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-file-storage"
    Description = "S3 bucket for file storage and management"
  })

  # S3 Bucket Logging Configuration
  logging {
    target_bucket = aws_s3_bucket.s3_access_logs.id
    target_prefix = "s3-access-logs/file-storage/"
  }
}

# Enable versioning for the file storage bucket
resource "aws_s3_bucket_versioning" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption for security
resource "aws_s3_bucket_server_side_encryption_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Configure CORS for browser uploads and downloads
resource "aws_s3_bucket_cors_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  cors_rule {
    allowed_headers = [
      "*",
      "Content-Type",
      "x-amz-meta-accountid",
      "x-amz-date",
      "x-amz-algorithm",
      "x-amz-credential",
      "x-amz-security-token",
      "authorization"
    ]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["https://${aws_cloudfront_distribution.frontend.domain_name}", "http://localhost:5173"]
    expose_headers  = ["ETag", "Content-Type", "Content-Length", "Content-Disposition", "x-amz-request-id"]
    max_age_seconds = 3600
  }
}

# Configure lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  rule {
    id     = "delete-incomplete-multipart-uploads"
    status = "Enabled"

    # Delete incomplete multipart uploads after 7 days
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
    
    # Filter with empty prefix to apply to all objects
    filter {
      prefix = ""
    }
  }
  
  rule {
    id     = "transition-to-ia"
    status = "Enabled"
    
    # Apply to all objects in the bucket
    filter {
      prefix = ""
    }
    
    # Move objects to infrequent access after 30 days
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
    
    # Optional: Move to Glacier after 90 days
    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# IAM policy document for file storage access
data "aws_iam_policy_document" "file_storage_policy" {
  # Allow CloudFront to access objects
  statement {
    sid    = "AllowCloudFrontServicePrincipal"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions = [
      "s3:GetObject"
    ]
    resources = [
      "${aws_s3_bucket.file_storage.arn}/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend.arn]
    }
  }
  
  # Allow authenticated users to perform file operations
  statement {
    sid    = "AllowAuthenticatedUploads"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::661792079381:user/terraform-housef2", aws_iam_role.lambda_exec.arn]
    }
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:PutObjectAcl"
    ]
    resources = [
      "${aws_s3_bucket.file_storage.arn}/*"
    ]
  }

  # Deny non-HTTPS requests
  statement {
    sid    = "DenyNonHTTPSRequests"
    effect = "Deny"
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    actions = [
      "s3:*"
    ]
    resources = [
      aws_s3_bucket.file_storage.arn,
      "${aws_s3_bucket.file_storage.arn}/*"
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

# Apply file storage bucket policy
resource "aws_s3_bucket_policy" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id
  policy = data.aws_iam_policy_document.file_storage_policy.json
}

# Block public access to the file storage bucket
resource "aws_s3_bucket_public_access_block" "file_storage" {
  bucket = aws_s3_bucket.file_storage.id

  block_public_acls       = true
  block_public_policy     = true   # ✅ BLOCK public policies
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Configure S3 event notifications to trigger file processor Lambda
resource "aws_s3_bucket_notification" "file_upload_notification" {
  bucket = aws_s3_bucket.file_storage.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ""  # Process all file types
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# Outputs for the file storage resources
output "file_storage_bucket_name" {
  description = "The name of the file storage bucket"
  value       = aws_s3_bucket.file_storage.bucket
}

output "file_storage_bucket_arn" {
  description = "The ARN of the file storage bucket"
  value       = aws_s3_bucket.file_storage.arn
}

# Lambda execution role with permission to access file storage
resource "aws_iam_role_policy" "lambda_file_storage_access" {
  name   = "file-storage-s3-access"
  role   = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.file_storage.arn,
          "${aws_s3_bucket.file_storage.arn}/*"
        ]
      }
    ]
  })
} 