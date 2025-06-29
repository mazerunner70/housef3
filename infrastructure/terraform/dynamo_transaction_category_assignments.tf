# =========================================
# DYNAMODB TABLE FOR TRANSACTION CATEGORY ASSIGNMENTS
# =========================================
# This file contains configurations for the DynamoDB table
# used to store transaction-to-category assignments with suggestion workflow support.
# Supports multiple categories per transaction and category assignment status tracking.

resource "aws_dynamodb_table" "transaction_category_assignments" {
  name           = "${var.project_name}-${var.environment}-transaction-category-assignments"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "transactionId"
  range_key      = "categoryId"

  # Primary key attributes
  attribute {
    name = "transactionId"
    type = "S"
  }

  attribute {
    name = "categoryId"
    type = "S"
  }

  # Attributes for Global Secondary Indexes
  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"  # "suggested" or "confirmed"
  }

  attribute {
    name = "assignedAt"
    type = "N"  # Timestamp in milliseconds
  }

  attribute {
    name = "confidence"
    type = "N"  # Confidence score (0.0 to 1.0) stored as decimal
  }

  attribute {
    name = "ruleId"
    type = "S"  # Which rule triggered this assignment
  }

  # GSI to query assignments by user and status (for review workflow)
  global_secondary_index {
    name               = "UserIdStatusIndex"
    hash_key           = "userId"
    range_key          = "status"
    projection_type    = "ALL"
  }

  # GSI to query assignments by category (to see all transactions in a category)
  global_secondary_index {
    name               = "CategoryIdIndex"
    hash_key           = "categoryId"
    range_key          = "assignedAt"
    projection_type    = "ALL"
  }

  # GSI to query suggested assignments by user (for review dashboard)
  global_secondary_index {
    name               = "UserIdAssignedAtIndex"
    hash_key           = "userId"
    range_key          = "assignedAt"
    projection_type    = "ALL"
  }

  # GSI to query assignments by confidence score (for analytics)
  global_secondary_index {
    name               = "CategoryIdConfidenceIndex"
    hash_key           = "categoryId"
    range_key          = "confidence"
    projection_type    = "ALL"
  }

  # GSI to query assignments by rule (for rule effectiveness analysis)
  global_secondary_index {
    name               = "RuleIdIndex"
    hash_key           = "ruleId"
    range_key          = "assignedAt"
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
    Name        = "${var.project_name}-${var.environment}-transaction-category-assignments"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Junction table for transaction-category assignments with suggestion workflow support"
  }
}

# Outputs for the transaction category assignments table
output "transaction_category_assignments_table_name" {
  description = "The name of the DynamoDB transaction category assignments table"
  value       = aws_dynamodb_table.transaction_category_assignments.name
}

output "transaction_category_assignments_table_arn" {
  description = "The ARN of the DynamoDB transaction category assignments table"
  value       = aws_dynamodb_table.transaction_category_assignments.arn
} 