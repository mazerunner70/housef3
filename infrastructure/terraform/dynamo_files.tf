# =========================================
# DYNAMODB TABLE FOR TRANSACTION FILES
# =========================================
# This file contains configurations for the DynamoDB table
# used to store metadata for transaction files in the file storage system.

# DynamoDB table for transaction files
resource "aws_dynamodb_table" "transaction_files" {
  name         = "${var.project_name}-${var.environment}-transaction-files"
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
  
  attribute {
    name = "accountId"
    type = "S"  # String (for financial account association)
  }

  # Global Secondary Index for querying files by user
  global_secondary_index {
    name               = "UserIndex"
    hash_key           = "userId"
    range_key          = "uploadDate"
    projection_type    = "ALL"
  }
  
  # Global Secondary Index for querying files by account
  global_secondary_index {
    name               = "AccountIdIndex"
    hash_key           = "accountId"
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
    Name        = "${var.project_name}-${var.environment}-transaction-files"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Table for storing transaction file metadata with support for financial processing"
  }
}

# Outputs
output "transaction_files_table_name" {
  description = "The name of the DynamoDB transaction files table"
  value       = aws_dynamodb_table.transaction_files.name
}

output "transaction_files_table_arn" {
  description = "The ARN of the DynamoDB transaction files table"
  value       = aws_dynamodb_table.transaction_files.arn
} 