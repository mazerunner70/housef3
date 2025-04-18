# =========================================
# DYNAMODB TABLES FOR FINANCIAL ACCOUNT MANAGEMENT
# =========================================
# This file contains configurations for DynamoDB tables used to store
# financial accounts and their associated transaction files.

# Accounts table
resource "aws_dynamodb_table" "accounts" {
  name         = "${var.project_name}-${var.environment}-accounts"
  billing_mode = "PAY_PER_REQUEST"  # On-demand capacity mode
  hash_key     = "accountId"        # Partition key

  attribute {
    name = "accountId"
    type = "S"  # String
  }

  attribute {
    name = "userId"
    type = "S"  # String
  }

  attribute {
    name = "createdAt"
    type = "S"  # String (ISO format timestamp)
  }

  # Global Secondary Index for querying accounts by user
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "createdAt"
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

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs for the accounts resources
output "accounts_table_name" {
  description = "The name of the accounts DynamoDB table"
  value       = aws_dynamodb_table.accounts.name
}

output "accounts_table_arn" {
  description = "The ARN of the accounts DynamoDB table"
  value       = aws_dynamodb_table.accounts.arn
}
