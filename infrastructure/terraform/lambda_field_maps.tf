# File map operations Lambda function
resource "aws_lambda_function" "file_map_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-file-map-operations"
  handler          = "handlers/file_map_operations.handler"
  runtime          = "python3.9"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 30
  memory_size     = 256
  source_code_hash = filebase64sha256("../../backend/lambda_deploy.zip")

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      FILE_MAPS_TABLE   = aws_dynamodb_table.file_maps.name
      FILES_TABLE       = aws_dynamodb_table.transaction_files.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch log group for file map operations Lambda
resource "aws_cloudwatch_log_group" "file_map_operations" {
  name              = "/aws/lambda/${aws_lambda_function.file_map_operations.function_name}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Lambda permission for API Gateway to invoke file map operations
resource "aws_lambda_permission" "api_gateway_file_maps" {
  statement_id  = "AllowAPIGatewayInvokeFileMaps"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_map_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Output the Lambda function name
output "lambda_file_map_operations_name" {
  description = "The name of the file map operations Lambda function"
  value       = aws_lambda_function.file_map_operations.function_name
} 