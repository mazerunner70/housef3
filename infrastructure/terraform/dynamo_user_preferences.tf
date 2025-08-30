# =========================================
# DYNAMODB TABLE FOR USER PREFERENCES
# =========================================
# This file contains the configuration for the DynamoDB table used to store
# user-specific preferences and settings.

# User Preferences table
resource "aws_dynamodb_table" "user_preferences" {
  name         = "${var.project_name}-${var.environment}-user-preferences"
  billing_mode = "PAY_PER_REQUEST" # On-demand capacity mode
  hash_key     = "userId"          # Partition key

  attribute {
    name = "userId"
    type = "S" # String
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

# Outputs for the user preferences resources
output "user_preferences_table_name" {
  description = "The name of the user preferences DynamoDB table"
  value       = aws_dynamodb_table.user_preferences.name
}

output "user_preferences_table_arn" {
  description = "The ARN of the user preferences DynamoDB table"
  value       = aws_dynamodb_table.user_preferences.arn
}
