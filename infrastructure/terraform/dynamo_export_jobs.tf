# =========================================
# DYNAMODB TABLE FOR EXPORT JOBS
# =========================================
# This file contains configurations for the DynamoDB table
# used to store export job status and metadata.

resource "aws_dynamodb_table" "export_jobs" {
  name           = "${var.project_name}-${var.environment}-export-jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "exportId"

  attribute {
    name = "exportId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "requestedAt"
    type = "N"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # Global Secondary Index for querying exports by user and date
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "requestedAt"
    projection_type    = "ALL"
  }

  # Global Secondary Index for querying exports by status
  global_secondary_index {
    name               = "StatusIndex"
    hash_key           = "status"
    range_key          = "requestedAt"
    projection_type    = "ALL"
  }

  # Enable TTL for automatic cleanup of old export jobs
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
    Name        = "${var.project_name}-${var.environment}-export-jobs"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Table for storing export job status and metadata"
  }
}

# Outputs for the export jobs table
output "export_jobs_table_name" {
  description = "The name of the DynamoDB export jobs table"
  value       = aws_dynamodb_table.export_jobs.name
}

output "export_jobs_table_arn" {
  description = "The ARN of the DynamoDB export jobs table"
  value       = aws_dynamodb_table.export_jobs.arn
} 