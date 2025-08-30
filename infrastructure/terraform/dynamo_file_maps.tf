resource "aws_dynamodb_table" "file_maps" {
  name         = "${var.project_name}-${var.environment}-file-maps"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "fileMapId"

  attribute {
    name = "fileMapId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "accountId"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "userId"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "AccountIdIndex"
    hash_key        = "accountId"
    projection_type = "ALL"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

output "file_maps_table_name" {
  value = aws_dynamodb_table.file_maps.name
}

output "file_maps_table_arn" {
  value = aws_dynamodb_table.file_maps.arn
} 