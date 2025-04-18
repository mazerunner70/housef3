resource "aws_dynamodb_table" "field_maps" {
  name           = "${var.project_name}-${var.environment}-field-maps"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "fieldMapId"
  
  attribute {
    name = "fieldMapId"
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
    name               = "UserIdIndex"
    hash_key           = "userId"
    projection_type    = "ALL"
  }

  global_secondary_index {
    name               = "AccountIdIndex"
    hash_key           = "accountId"
    projection_type    = "ALL"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

output "field_maps_table_name" {
  value = aws_dynamodb_table.field_maps.name
}

output "field_maps_table_arn" {
  value = aws_dynamodb_table.field_maps.arn
} 