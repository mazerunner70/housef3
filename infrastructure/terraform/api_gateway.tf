resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-${var.environment}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["http://localhost:3000", "https://${var.domain_name}"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["Authorization", "Content-Type"]
    max_age      = 300
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name            = "${var.project_name}-${var.environment}-cognito"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.main.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

resource "aws_apigatewayv2_integration" "colors" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.colors.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for colors endpoint"
}

resource "aws_apigatewayv2_route" "colors" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /colors"
  target             = "integrations/${aws_apigatewayv2_integration.colors.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File Operations Integration
resource "aws_apigatewayv2_integration" "file_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.file_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for file operations endpoints"
}

# File listing route
resource "aws_apigatewayv2_route" "list_files" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Get single file route
resource "aws_apigatewayv2_route" "get_file" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# List files by account route
resource "aws_apigatewayv2_route" "list_files_by_account" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files/account/{accountId}"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File upload URL route
resource "aws_apigatewayv2_route" "get_upload_url" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /files/upload"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File download URL route
resource "aws_apigatewayv2_route" "get_download_url" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files/{id}/download"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File deletion route
resource "aws_apigatewayv2_route" "delete_file" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /files/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File unassociate route
resource "aws_apigatewayv2_route" "unassociate_file" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /files/{id}/unassociate"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File associate route
resource "aws_apigatewayv2_route" "associate_file" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /files/{id}/associate"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File balance update route
resource "aws_apigatewayv2_route" "file_balance" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /files/{id}/balance"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account Operations Integration
resource "aws_apigatewayv2_integration" "account_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.account_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for account operations endpoints"
}

# Account creation route
resource "aws_apigatewayv2_route" "create_account" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /accounts"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account listing route
resource "aws_apigatewayv2_route" "list_accounts" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /accounts"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account details route
resource "aws_apigatewayv2_route" "get_account" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /accounts/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account update route
resource "aws_apigatewayv2_route" "update_account" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /accounts/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account deletion route
resource "aws_apigatewayv2_route" "delete_account" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /accounts/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account files route
resource "aws_apigatewayv2_route" "account_files" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /accounts/{id}/files"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File upload for account route
resource "aws_apigatewayv2_route" "account_file_upload" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /accounts/{id}/files"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip            = "$context.identity.sourceIp"
      requestTime   = "$context.requestTime"
      httpMethod    = "$context.httpMethod"
      routeKey      = "$context.routeKey"
      status        = "$context.status"
      protocol      = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage  = "$context.error.message"
    })
  }
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/api-gateway/${var.project_name}-${var.environment}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Lambda permission to allow API Gateway to invoke the function
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.colors.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/colors"
}

# Lambda permission for file operations
resource "aws_lambda_permission" "file_operations" {
  statement_id  = "AllowAPIGatewayInvokeFiles"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/files*"
}

# Lambda permission for account operations
resource "aws_lambda_permission" "account_operations" {
  statement_id  = "AllowAPIGatewayInvokeAccounts"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.account_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/accounts*"
}

# Outputs
output "api_endpoint" {
  value = "${aws_apigatewayv2_stage.main.invoke_url}/colors"
}

output "api_files_endpoint" {
  value = "${aws_apigatewayv2_stage.main.invoke_url}/files"
}

output "api_accounts_endpoint" {
  value = "${aws_apigatewayv2_stage.main.invoke_url}/accounts"
}

output "api_stage" {
  value = aws_apigatewayv2_stage.main.name
} 