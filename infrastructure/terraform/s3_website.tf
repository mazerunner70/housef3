# =========================================
# S3 BUCKET FOR FRONTEND WEBSITE HOSTING
# =========================================
# This file contains configurations for the S3 bucket 
# used to host the frontend static website files.

resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-${var.environment}-frontend"

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-frontend"
    Description = "S3 bucket for frontend website hosting"
  })

  # Prevent accidental deletion of this S3 bucket
  lifecycle {
    prevent_destroy = true
  }
}

# Configure public access settings for website hosting
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true   # ✅ BLOCK public policies
  ignore_public_acls      = true   # ✅ IGNORE public ACLs
  restrict_public_buckets = true   # ✅ RESTRICT public buckets
}

# Enable versioning for the frontend bucket
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption for the frontend bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Update bucket policy to allow CloudFront access only
data "aws_iam_policy_document" "frontend_policy" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend.arn]
    }
  }
}

# Apply the website bucket policy
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend_policy.json

  # Ensure the bucket policy is created after the CloudFront distribution
  depends_on = [aws_cloudfront_distribution.frontend]
}

# S3 Bucket Logging Configuration for Frontend Website
resource "aws_s3_bucket_logging" "frontend_logging" {
  bucket = aws_s3_bucket.frontend.id
  
  target_bucket = aws_s3_bucket.import_packages_logs.id
  target_prefix = "logs/frontend/"
}

# Enable static website hosting configuration
resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Output the website bucket details
output "frontend_bucket_name" {
  description = "Name of the S3 bucket hosting the frontend"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_bucket_website_endpoint" {
  description = "Website endpoint for the frontend bucket"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
} 