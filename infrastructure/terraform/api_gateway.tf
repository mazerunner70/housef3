resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-${var.environment}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["http://localhost:5173"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
    allow_headers = ["Authorization", "Content-Type", "Origin", "Accept", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
    max_age      = 600
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

resource "aws_apigatewayv2_integration" "getcolors" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.getcolors.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for getcolors endpoint"
}

resource "aws_apigatewayv2_route" "getcolors" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /colors"
  target             = "integrations/${aws_apigatewayv2_integration.getcolors.id}"
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

# File Transaction Routes
resource "aws_apigatewayv2_route" "get_file_transactions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files/{id}/transactions"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "delete_file_transactions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /files/{id}/transactions"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
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

# S3 direct upload URL route
resource "aws_apigatewayv2_route" "get_s3_upload_url" {
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
  route_key          = "PUT /files/{id}/unassociate"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File associate route
resource "aws_apigatewayv2_route" "associate_file" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /files/{id}/associate"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File balance update route
resource "aws_apigatewayv2_route" "file_balance" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /files/{id}/balance"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File closing balance update route
resource "aws_apigatewayv2_route" "file_closing_balance" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /files/{id}/closing-balance"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File metadata route
resource "aws_apigatewayv2_route" "get_file_metadata" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files/{id}/metadata"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File field map route
resource "aws_apigatewayv2_route" "update_file_field_map" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /files/{id}/file-map"
  target             = "integrations/${aws_apigatewayv2_integration.file_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# File preview route
resource "aws_apigatewayv2_route" "get_file_preview" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /files/{id}/preview"
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

# Account deletion route
resource "aws_apigatewayv2_route" "delete_accounts" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /accounts"
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

# Delete account files route
resource "aws_apigatewayv2_route" "delete_account_files" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /accounts/{id}/files"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account transactions route
resource "aws_apigatewayv2_route" "get_account_transactions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /accounts/{id}/transactions"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Account timeline route
resource "aws_apigatewayv2_route" "account_file_timeline" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /accounts/{id}/timeline"
  target             = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Transaction operations integration
resource "aws_apigatewayv2_integration" "transaction_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.transaction_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for transaction operations"
}

# Transaction Routes
resource "aws_apigatewayv2_route" "get_transactions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /transactions"
  target             = "integrations/${aws_apigatewayv2_integration.transaction_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "delete_transaction" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /transactions/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.transaction_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Field map routes
resource "aws_apigatewayv2_integration" "field_map_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.file_map_operations.invoke_arn
  payload_format_version = "2.0"
}

# Create field map
resource "aws_apigatewayv2_route" "create_field_map" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /file-maps"
  target             = "integrations/${aws_apigatewayv2_integration.field_map_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Get field map by ID
resource "aws_apigatewayv2_route" "get_field_map" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /file-maps/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.field_map_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# List field maps
resource "aws_apigatewayv2_route" "list_field_maps" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /file-maps"
  target             = "integrations/${aws_apigatewayv2_integration.field_map_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Update field map
resource "aws_apigatewayv2_route" "update_field_map" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /file-maps/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.field_map_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Delete field map
resource "aws_apigatewayv2_route" "delete_field_map" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /file-maps/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.field_map_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Categories Operations Integration
resource "aws_apigatewayv2_integration" "category_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.categories_lambda.invoke_arn # From lambda_categories.tf
  payload_format_version = "2.0"
  description            = "Lambda integration for category CRUD operations"
}

# Create Category route
resource "aws_apigatewayv2_route" "create_category" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# List Categories route
resource "aws_apigatewayv2_route" "list_categories" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /categories"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Get Categories Hierarchy route
resource "aws_apigatewayv2_route" "get_categories_hierarchy" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /categories/hierarchy"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Get Category by ID route
resource "aws_apigatewayv2_route" "get_category" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /categories/{categoryId}"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Update Category by ID route
resource "aws_apigatewayv2_route" "update_category" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /categories/{categoryId}"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Delete Category by ID route
resource "aws_apigatewayv2_route" "delete_category" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /categories/{categoryId}"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Phase 2.1 Rule Testing & Preview API Endpoints

# Test Category Rule route
resource "aws_apigatewayv2_route" "test_category_rule" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/test-rule"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Preview Category Matches route
resource "aws_apigatewayv2_route" "preview_category_matches" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /categories/{categoryId}/preview-matches"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Validate Regex Pattern route
resource "aws_apigatewayv2_route" "validate_regex_pattern" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/validate-regex"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Generate Pattern route
resource "aws_apigatewayv2_route" "generate_pattern" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/generate-pattern"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Generate Category Suggestions route
resource "aws_apigatewayv2_route" "generate_category_suggestions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /transactions/{transactionId}/category-suggestions"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Apply Category Rules Bulk route
resource "aws_apigatewayv2_route" "apply_category_rules_bulk" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/apply-rules-bulk"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Category Rule Management routes

# Add Rule to Category route
resource "aws_apigatewayv2_route" "add_rule_to_category" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/{categoryId}/rules"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Update Category Rule route
resource "aws_apigatewayv2_route" "update_category_rule" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "PUT /categories/{categoryId}/rules/{ruleId}"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Delete Category Rule route
resource "aws_apigatewayv2_route" "delete_category_rule" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /categories/{categoryId}/rules/{ruleId}"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Phase 4.1 Pattern Extraction & Smart Category Creation routes

# Suggest Category from Transaction route
resource "aws_apigatewayv2_route" "suggest_category_from_transaction" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/suggest-from-transaction"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Extract Patterns route
resource "aws_apigatewayv2_route" "extract_patterns" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/extract-patterns"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Create Category with Rule route
resource "aws_apigatewayv2_route" "create_category_with_rule" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/create-with-rule"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Reset and Reapply Categories route
resource "aws_apigatewayv2_route" "reset_and_reapply_categories" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /categories/reset-and-reapply"
  target             = "integrations/${aws_apigatewayv2_integration.category_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Analytics Operations Integration
resource "aws_apigatewayv2_integration" "analytics_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.analytics_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for analytics operations endpoints"
}

# Analytics routes
resource "aws_apigatewayv2_route" "get_analytics" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /analytics"
  target             = "integrations/${aws_apigatewayv2_integration.analytics_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "refresh_analytics" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /analytics/refresh"
  target             = "integrations/${aws_apigatewayv2_integration.analytics_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "get_analytics_status" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /analytics/status"
  target             = "integrations/${aws_apigatewayv2_integration.analytics_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Export Operations Integration
resource "aws_apigatewayv2_integration" "export_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.export_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for export operations endpoints"
}

# Export routes
resource "aws_apigatewayv2_route" "initiate_export" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /export"
  target             = "integrations/${aws_apigatewayv2_integration.export_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "list_exports" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /export"
  target             = "integrations/${aws_apigatewayv2_integration.export_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "get_export_status" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /export/{exportId}/status"
  target             = "integrations/${aws_apigatewayv2_integration.export_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "get_export_download" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /export/{exportId}/download"
  target             = "integrations/${aws_apigatewayv2_integration.export_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "delete_export" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "DELETE /export/{exportId}"
  target             = "integrations/${aws_apigatewayv2_integration.export_operations.id}"
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
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Lambda permission to allow API Gateway to invoke the function
resource "aws_lambda_permission" "api_gateway_colors" {
  statement_id  = "AllowAPIGatewayInvokeColors"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.getcolors.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/colors"
}

# Lambda permission for file operations
resource "aws_lambda_permission" "api_gateway_files" {
  statement_id  = "AllowAPIGatewayInvokeFiles"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/files*"
}

# Lambda permission for upload endpoint
resource "aws_lambda_permission" "api_gateway_upload" {
  statement_id  = "AllowAPIGatewayInvokeUpload"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/files/upload"
}

# Lambda permission for account operations
resource "aws_lambda_permission" "api_gateway_accounts" {
  statement_id  = "AllowAPIGatewayInvokeAccounts"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.account_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/accounts*"
}

# Lambda permission for API Gateway to invoke transaction operations
resource "aws_lambda_permission" "api_gateway_transactions" {
  statement_id  = "AllowAPIGatewayInvokeTransactions"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transaction_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/transactions*"
}

# Lambda permission for getcolors
resource "aws_lambda_permission" "getcolors" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.getcolors.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Lambda permission for field maps
resource "aws_lambda_permission" "api_gateway_field_maps" {
  statement_id  = "AllowAPIGatewayInvokeFieldMapsLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_map_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Lambda permission for categories
resource "aws_lambda_permission" "api_gateway_categories" {
  statement_id  = "AllowAPIGatewayInvokeCategoriesLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.categories_lambda.function_name # From lambda_categories.tf
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Lambda permission for analytics
resource "aws_lambda_permission" "api_gateway_analytics" {
  statement_id  = "AllowAPIGatewayInvokeAnalyticsLambda"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.analytics_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/analytics*"
}

resource "aws_lambda_permission" "api_gateway_export" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.export_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# Outputs
output "api_endpoint" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}/dev"
}

output "api_files_endpoint" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}/dev/files"
}

output "api_accounts_endpoint" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}/dev/accounts"
}

output "api_stage" {
  value = aws_apigatewayv2_stage.main.name
} 