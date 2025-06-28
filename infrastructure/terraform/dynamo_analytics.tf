resource "aws_dynamodb_table" "analytics_data" {
  name           = "${var.project_name}-${var.environment}-analytics-data"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "analyticType"
    type = "S"
  }

  # Global Secondary Index for querying by user_id and analytic_type
  global_secondary_index {
    name            = "UserAnalyticsIndex"
    hash_key        = "userId"
    range_key       = "analyticType"
    projection_type = "ALL"
  }

  # TTL configuration for automatic data cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "analytics-data-storage"
  }
}

resource "aws_dynamodb_table" "analytics_status" {
  name           = "${var.project_name}-${var.environment}-analytics-status"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pk"
  range_key      = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "computationNeeded"
    type = "S"
  }

  attribute {
    name = "processingPriority"
    type = "N"
  }

  # Global Secondary Index for finding analytics that need computation
  global_secondary_index {
    name            = "ComputationNeededIndex"
    hash_key        = "computationNeeded"
    range_key       = "processingPriority"
    projection_type = "ALL"
  }

  # TTL config for automatic cleanup of old status records
  ttl {
    attribute_name = "ttl"
    enabled = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "analytics-processing-status"
  }
}

# Outputs for the analytics tables
output "analytics_data_table_name" {
  description = "Name of the Analytics Data DynamoDB table"
  value       = aws_dynamodb_table.analytics_data.name
}

output "analytics_data_table_arn" {
  description = "ARN of the Analytics Data DynamoDB table"
  value       = aws_dynamodb_table.analytics_data.arn
}

output "analytics_status_table_name" {
  description = "Name of the Analytics Status DynamoDB table"
  value       = aws_dynamodb_table.analytics_status.name
}

output "analytics_status_table_arn" {
  description = "ARN of the Analytics Status DynamoDB table"
  value       = aws_dynamodb_table.analytics_status.arn
} 