resource "aws_dynamodb_table" "analytics_data" {
  name           = "${var.prefix}-analytics-data"
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
    Name = "${var.prefix}-analytics-data"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "analytics_status" {
  name           = "${var.prefix}-analytics-status"
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
    name = "lastUpdated"
    type = "S"
  }

  attribute {
    name = "processingPriority"
    type = "N"
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

  tags = {
    Name = "${var.prefix}-analytics-status"
    Environment = var.environment
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