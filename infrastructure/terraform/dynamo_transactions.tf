# Terraform configuration for Transactions DynamoDB table

# Transaction table for storing parsed financial transactions
resource "aws_dynamodb_table" "transactions" {
  name           = "${var.project_name}-${var.environment}-transactions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "transactionId"
  
  attribute {
    name = "transactionId"
    type = "S"
  }
  
  attribute {
    name = "fileId"
    type = "S"
  }
  
  attribute {
    name = "userId"
    type = "S"
  }
  
  # GSI to query transactions by file ID
  global_secondary_index {
    name               = "FileIdIndex"
    hash_key           = "fileId"
    projection_type    = "ALL"
  }
  
  # GSI to query transactions by user ID
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    projection_type    = "ALL"
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs for the transactions table
output "transactions_table_name" {
  description = "Name of the transactions DynamoDB table"
  value       = aws_dynamodb_table.transactions.name
}

output "transactions_table_arn" {
  description = "ARN of the transactions DynamoDB table"
  value       = aws_dynamodb_table.transactions.arn
} 