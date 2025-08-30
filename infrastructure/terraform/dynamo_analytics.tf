resource "aws_dynamodb_table" "analytics_data" {
  name         = "${var.project_name}-${var.environment}-analytics-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

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
    Name        = "${var.project_name}-${var.environment}-analytics-data"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_dynamodb_table" "analytics_status" {
  name         = "${var.project_name}-${var.environment}-analytics-status"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

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
    name = "lastUpdated"
    type = "S"
  }

  attribute {
    name = "processingPriority"
    type = "N"
  }

  attribute {
    name = "computationNeeded"
    type = "B"
  }

  # Global Secondary Index for querying by user_id
  global_secondary_index {
    name            = "UserStatusIndex"
    hash_key        = "userId"
    range_key       = "lastUpdated"
    projection_type = "ALL"
  }

  # Global Secondary Index for processing queue (priority-based)
  global_secondary_index {
    name            = "ProcessingQueueIndex"
    hash_key        = "processingPriority"
    range_key       = "lastUpdated"
    projection_type = "ALL"
  }

  # Global Secondary Index for computation needed status
  global_secondary_index {
    name            = "ComputationNeededIndex"
    hash_key        = "computationNeeded"
    range_key       = "lastUpdated"
    projection_type = "ALL"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-analytics-status"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Output the table names for use in Lambda environment variables
output "analytics_data_table_name" {
  value = aws_dynamodb_table.analytics_data.name
}

output "analytics_status_table_name" {
  value = aws_dynamodb_table.analytics_status.name
}

output "analytics_data_table_arn" {
  value = aws_dynamodb_table.analytics_data.arn
}

output "analytics_status_table_arn" {
  value = aws_dynamodb_table.analytics_status.arn
} 