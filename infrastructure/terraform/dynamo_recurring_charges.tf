# =========================================
# DYNAMODB TABLES FOR RECURRING CHARGE DETECTION
# =========================================
# This file contains configurations for the DynamoDB tables
# used for ML-based recurring charge pattern detection.

# =========================================
# Recurring Charge Patterns Table
# =========================================
# Stores detected recurring charge patterns with ML features
resource "aws_dynamodb_table" "recurring_charge_patterns" {
  name         = "${var.project_name}-${var.environment}-recurring-charge-patterns"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "patternId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "patternId"
    type = "S"
  }

  attribute {
    name = "suggestedCategoryId"
    type = "S"
  }

  attribute {
    name = "active"
    type = "S" # Using string for boolean to allow GSI
  }

  # GSI to query patterns by category
  global_secondary_index {
    name            = "CategoryIdIndex"
    hash_key        = "suggestedCategoryId"
    projection_type = "ALL"
  }

  # GSI to query active patterns by user
  global_secondary_index {
    name            = "UserIdActiveIndex"
    hash_key        = "userId"
    range_key       = "active"
    projection_type = "ALL"
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
    Name        = "${var.project_name}-${var.environment}-recurring-charge-patterns"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Table for storing ML-detected recurring charge patterns"
    Feature     = "recurring-charge-detection"
  }
}

# =========================================
# Recurring Charge Predictions Table
# =========================================
# Stores predictions for next occurrences of recurring charges
resource "aws_dynamodb_table" "recurring_charge_predictions" {
  name         = "${var.project_name}-${var.environment}-recurring-charge-predictions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "patternId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "patternId"
    type = "S"
  }

  attribute {
    name = "nextExpectedDate"
    type = "N" # Number (timestamp)
  }

  # GSI to query predictions by expected date
  global_secondary_index {
    name            = "UserIdDateIndex"
    hash_key        = "userId"
    range_key       = "nextExpectedDate"
    projection_type = "ALL"
  }

  # Enable point-in-time recovery for data protection
  point_in_time_recovery {
    enabled = true
  }

  # Enable server-side encryption
  server_side_encryption {
    enabled = true
  }

  # Set TTL on predictions (they expire after the expected date passes)
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-recurring-charge-predictions"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Table for storing predictions of next recurring charge occurrences"
    Feature     = "recurring-charge-detection"
  }
}

# =========================================
# Pattern Feedback Table
# =========================================
# Stores user feedback on pattern detection for ML improvement
resource "aws_dynamodb_table" "pattern_feedback" {
  name         = "${var.project_name}-${var.environment}-pattern-feedback"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"
  range_key    = "feedbackId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "feedbackId"
    type = "S"
  }

  attribute {
    name = "patternId"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N" # Number (timestamp)
  }

  # GSI to query feedback by pattern
  global_secondary_index {
    name            = "PatternIdIndex"
    hash_key        = "patternId"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # GSI to query feedback by user and timestamp
  global_secondary_index {
    name            = "UserIdTimestampIndex"
    hash_key        = "userId"
    range_key       = "timestamp"
    projection_type = "ALL"
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
    Name        = "${var.project_name}-${var.environment}-pattern-feedback"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Description = "Table for storing user feedback on recurring charge pattern detection"
    Feature     = "recurring-charge-detection"
  }
}

# =========================================
# Outputs
# =========================================

output "recurring_charge_patterns_table_name" {
  description = "The name of the DynamoDB recurring charge patterns table"
  value       = aws_dynamodb_table.recurring_charge_patterns.name
}

output "recurring_charge_patterns_table_arn" {
  description = "The ARN of the DynamoDB recurring charge patterns table"
  value       = aws_dynamodb_table.recurring_charge_patterns.arn
}

output "recurring_charge_predictions_table_name" {
  description = "The name of the DynamoDB recurring charge predictions table"
  value       = aws_dynamodb_table.recurring_charge_predictions.name
}

output "recurring_charge_predictions_table_arn" {
  description = "The ARN of the DynamoDB recurring charge predictions table"
  value       = aws_dynamodb_table.recurring_charge_predictions.arn
}

output "pattern_feedback_table_name" {
  description = "The name of the DynamoDB pattern feedback table"
  value       = aws_dynamodb_table.pattern_feedback.name
}

output "pattern_feedback_table_arn" {
  description = "The ARN of the DynamoDB pattern feedback table"
  value       = aws_dynamodb_table.pattern_feedback.arn
}

