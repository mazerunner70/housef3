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
  
  attribute {
    name = "status"
    type = "S"
  }
  
  attribute {
    name = "accountId"
    type = "S"
  }
  
  attribute {
    name = "importOrder"
    type = "N"
  }
  
  attribute {
    name = "date"
    type = "N"
  }
  
  attribute {
    name = "transactionHash"
    type = "N"
  }
  
  attribute {
    name = "amount"
    type = "N"
  }
  
  attribute {
    name = "balance"
    type = "N"
  }
  
  attribute {
    name = "categoryId"
    type = "S"
  }
  
  # Add missing attributes for better GSI support
  attribute {
    name = "transactionType"
    type = "S"
  }
  
  attribute {
    name = "primaryCategoryId" 
    type = "S"
  }

  # GSI to query transactions by file ID
  global_secondary_index {
    name               = "FileIdIndex"
    hash_key           = "fileId"
    projection_type    = "ALL"
  }
  
  # GSI to query transactions by user ID and sort by date
  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "date"
    projection_type    = "ALL"
  }
  
  # GSI to query transactions by status
  global_secondary_index {
    name               = "StatusIndex"
    hash_key           = "status"
    projection_type    = "ALL"
  }
  
  # GSI to query transactions by account ID with amount
  global_secondary_index {
    name               = "AccountAmountIndex"
    hash_key           = "accountId"
    range_key          = "amount"
    projection_type    = "ALL"
  }
  
  # GSI to query transactions by account ID with balance
  global_secondary_index {
    name               = "AccountBalanceIndex"
    hash_key           = "accountId"
    range_key          = "balance"
    projection_type    = "ALL"
  }
  
  # GSI to sort transactions by import order
  global_secondary_index {
    name               = "ImportOrderIndex"
    hash_key           = "fileId"
    range_key          = "importOrder"
    projection_type    = "ALL"
  }
  
  # GSI to sort transactions by account and date
  global_secondary_index {
    name               = "AccountDateIndex"
    hash_key           = "accountId"
    range_key          = "date"
    projection_type    = "ALL"
  }
  
  # GSI for efficient duplicate detection using numeric hash
  global_secondary_index {
    name               = "TransactionHashIndex"
    hash_key           = "accountId"
    range_key          = "transactionHash"
    projection_type    = "ALL"
  }
  
  # GSI to query transactions by account and category
  global_secondary_index {
    name               = "AccountCategoryIndex"
    hash_key           = "accountId"
    range_key          = "categoryId"
    projection_type    = "ALL"
  }
  
  # GSI for category-based queries with date sorting
  global_secondary_index {
    name               = "CategoryDateIndex"
    hash_key           = "primaryCategoryId"
    range_key          = "date"
    projection_type    = "ALL"
  }
  
  # GSI for status filtering with date sorting  
  global_secondary_index {
    name               = "StatusDateIndex"
    hash_key           = "status"
    range_key          = "date"
    projection_type    = "ALL"
  }
  
  # GSI for transaction type filtering with date sorting
  global_secondary_index {
    name               = "TransactionTypeIndex"
    hash_key           = "transactionType"
    range_key          = "date"
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