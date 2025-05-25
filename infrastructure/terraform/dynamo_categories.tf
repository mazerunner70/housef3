# =========================================
# DYNAMODB TABLE FOR CATEGORIES
# =========================================
# This file contains configurations for the DynamoDB table
# used to store user-defined transaction categories.

resource "aws_dynamodb_table" "categories" {
  name           = "${var.project_name}-${var.environment}-categories"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "categoryId"

  attribute {
    name = "categoryId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "name" # Used in UserIdIndex as range key
    type = "S"
  }

  attribute {
    name = "parentCategoryId" # Used in UserIdParentCategoryIdIndex as range key
    type = "S"
  }

  # GSI to query categories by user, sorted by name
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "name"
    projection_type    = "ALL"
  }

  # GSI to query categories by user and parent category
  global_secondary_index {
    name               = "UserIdParentCategoryIdIndex"
    hash_key           = "userId"
    range_key          = "parentCategoryId"
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
    Name        = "${var.project_name}-${var.environment}-categories"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Table for storing transaction categories and categorization rules"
  }
}

# Outputs for the categories table
output "categories_table_name" {
  description = "The name of the DynamoDB categories table"
  value       = aws_dynamodb_table.categories.name
}

output "categories_table_arn" {
  description = "The ARN of the DynamoDB categories table"
  value       = aws_dynamodb_table.categories.arn
} 