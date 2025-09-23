# Terraform configuration for Workflows DynamoDB table

# Workflows table for tracking long-running operations (renamed from operations)
resource "aws_dynamodb_table" "workflows" {
  name         = "${var.project_name}-${var.environment}-workflows"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "operationId"

  attribute {
    name = "operationId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "operationType"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "N"
  }

  # GSI to query operations by user ID and creation date
  global_secondary_index {
    name            = "UserOperationsIndex"
    hash_key        = "userId"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI to query operations by status
  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # GSI to query operations by type
  global_secondary_index {
    name            = "OperationTypeIndex"
    hash_key        = "operationType"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  # TTL configuration for automatic cleanup
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs for the workflows table
output "workflows_table_name" {
  description = "Name of the workflows DynamoDB table"
  value       = aws_dynamodb_table.workflows.name
}

output "workflows_table_arn" {
  description = "ARN of the workflows DynamoDB table"
  value       = aws_dynamodb_table.workflows.arn
}
