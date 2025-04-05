# =========================================
# DYNAMODB TABLE FOR FILE METADATA
# =========================================
# This file contains configurations for the DynamoDB table
# used to store metadata for files in the file storage system.

# DynamoDB table for file metadata
resource "aws_dynamodb_table" "file_metadata" {
  name         = "${var.project_name}-${var.environment}-file-metadata"
  billing_mode = "PAY_PER_REQUEST"  # On-demand capacity mode
  hash_key     = "fileId"           # Partition key

  attribute {
    name = "fileId"
    type = "S"  # String
  }

  attribute {
    name = "userId"
    type = "S"  # String
  }

  attribute {
    name = "uploadDate"
    type = "S"  # String (ISO format date)
  }

  # Global Secondary Index for querying files by user
  global_secondary_index {
    name               = "UserIndex"
    hash_key           = "userId"
    range_key          = "uploadDate"
    projection_type    = "ALL"
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  # Set time-to-live attribute (optional, for temporary files)
  ttl {
    attribute_name = "expiryDate"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-file-metadata"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs
output "dynamodb_table_name" {
  description = "The name of the DynamoDB file metadata table"
  value       = aws_dynamodb_table.file_metadata.name
}

output "dynamodb_table_arn" {
  description = "The ARN of the DynamoDB file metadata table"
  value       = aws_dynamodb_table.file_metadata.arn
} 