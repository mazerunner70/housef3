# Field map operations Lambda function
resource "aws_lambda_function" "field_map_operations" {
  filename         = data.archive_file.lambda_code.output_path
  function_name    = "${var.project_name}-${var.environment}-field-map-operations"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "handlers.field_map_operations.handler"
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  runtime         = "python3.9"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      FIELD_MAPS_TABLE = aws_dynamodb_table.field_maps.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch log group for field map operations Lambda
resource "aws_cloudwatch_log_group" "field_map_operations" {
  name              = "/aws/lambda/${aws_lambda_function.field_map_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Lambda permission for API Gateway to invoke field map operations
resource "aws_lambda_permission" "api_gateway_field_maps" {
  statement_id  = "AllowAPIGatewayInvokeFieldMaps"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.field_map_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Output the Lambda function name
output "lambda_field_map_operations_name" {
  description = "The name of the field map operations Lambda function"
  value       = aws_lambda_function.field_map_operations.function_name
} 