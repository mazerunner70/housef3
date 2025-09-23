# =========================================
# LOCAL CONFIGURATION FOR API GATEWAY
# =========================================

locals {
  # Lambda function configurations
  lambda_functions = {
    getcolors                    = aws_lambda_function.getcolors
    file_operations             = aws_lambda_function.file_operations
    workflow_tracking           = aws_lambda_function.workflow_tracking
    account_operations          = aws_lambda_function.account_operations
    transaction_operations      = aws_lambda_function.transaction_operations
    transfer_operations         = aws_lambda_function.transfer_operations
    field_map_operations        = aws_lambda_function.file_map_operations
    category_operations         = aws_lambda_function.categories_lambda
    analytics_operations        = aws_lambda_function.analytics_operations
    export_operations           = aws_lambda_function.export_operations
    user_preferences_operations = aws_lambda_function.user_preferences_operations
  }

  # Special lambda with alias
  fzip_operations_arn = aws_lambda_alias.fzip_operations_version.invoke_arn
  fzip_operations_function_name = aws_lambda_alias.fzip_operations_version.arn

  # Integration configurations
  integrations = {
    getcolors = {
      lambda_key  = "getcolors"
      description = "Lambda integration for getcolors endpoint"
    }
    file_operations = {
      lambda_key  = "file_operations"
      description = "Lambda integration for file operations endpoints"
    }
    workflow_tracking = {
      lambda_key  = "workflow_tracking"
      description = "Lambda integration for workflow tracking endpoints"
    }
    account_operations = {
      lambda_key  = "account_operations"
      description = "Lambda integration for account operations endpoints"
    }
    transaction_operations = {
      lambda_key  = "transaction_operations"
      description = "Lambda integration for transaction operations"
    }
    transfer_operations = {
      lambda_key  = "transfer_operations"
      description = "Lambda integration for transfer operations"
    }
    field_map_operations = {
      lambda_key  = "field_map_operations"
      description = "Lambda integration for field map operations"
    }
    category_operations = {
      lambda_key  = "category_operations"
      description = "Lambda integration for category CRUD operations"
    }
    analytics_operations = {
      lambda_key  = "analytics_operations"
      description = "Lambda integration for analytics operations endpoints"
    }
    export_operations = {
      lambda_key  = "export_operations"
      description = "Lambda integration for export operations endpoints"
    }
    user_preferences_operations = {
      lambda_key  = "user_preferences_operations"
      description = "Lambda integration for user preferences operations endpoints"
    }
    fzip_operations = {
      lambda_key  = "fzip_operations"
      description = "Lambda integration for unified FZIP backup/restore operations (versioned)"
      use_alias   = true
    }
  }

  # Route configurations
  routes = {
    # Colors
    getcolors = {
      route_key    = "GET /colors"
      integration  = "getcolors"
      requires_auth = true
    }

    # File Operations
    get_file_transactions = {
      route_key    = "GET /files/{id}/transactions"
      integration  = "file_operations"
      requires_auth = true
    }
    delete_file_transactions = {
      route_key    = "DELETE /files/{id}/transactions"
      integration  = "file_operations"
      requires_auth = true
    }
    list_files = {
      route_key    = "GET /files"
      integration  = "file_operations"
      requires_auth = true
    }
    get_file = {
      route_key    = "GET /files/{id}"
      integration  = "file_operations"
      requires_auth = true
    }
    list_files_by_account = {
      route_key    = "GET /files/account/{accountId}"
      integration  = "file_operations"
      requires_auth = true
    }
    get_s3_upload_url = {
      route_key    = "POST /files/upload"
      integration  = "file_operations"
      requires_auth = true
    }
    get_download_url = {
      route_key    = "GET /files/{id}/download"
      integration  = "file_operations"
      requires_auth = true
    }
    delete_file = {
      route_key    = "DELETE /files/{id}"
      integration  = "file_operations"
      requires_auth = true
    }
    unassociate_file = {
      route_key    = "PUT /files/{id}/unassociate"
      integration  = "file_operations"
      requires_auth = true
    }
    associate_file = {
      route_key    = "PUT /files/{id}/associate"
      integration  = "file_operations"
      requires_auth = true
    }
    file_balance = {
      route_key    = "PUT /files/{id}/balance"
      integration  = "file_operations"
      requires_auth = true
    }
    file_closing_balance = {
      route_key    = "PUT /files/{id}/closing-balance"
      integration  = "file_operations"
      requires_auth = true
    }
    get_file_metadata = {
      route_key    = "GET /files/{id}/metadata"
      integration  = "file_operations"
      requires_auth = true
    }
    update_file_field_map = {
      route_key    = "PUT /files/{id}/file-map"
      integration  = "file_operations"
      requires_auth = true
    }
    get_file_preview = {
      route_key    = "GET /files/{id}/preview"
      integration  = "file_operations"
      requires_auth = true
    }

    # Workflow Tracking
    get_workflow_status = {
      route_key    = "GET /workflows/{workflowId}/status"
      integration  = "workflow_tracking"
      requires_auth = true
    }
    list_user_workflows = {
      route_key    = "GET /workflows"
      integration  = "workflow_tracking"
      requires_auth = true
    }
    cancel_workflow = {
      route_key    = "POST /workflows/{workflowId}/cancel"
      integration  = "workflow_tracking"
      requires_auth = true
    }

    # Account Operations
    create_account = {
      route_key    = "POST /accounts"
      integration  = "account_operations"
      requires_auth = true
    }
    list_accounts = {
      route_key    = "GET /accounts"
      integration  = "account_operations"
      requires_auth = true
    }
    delete_accounts = {
      route_key    = "DELETE /accounts"
      integration  = "account_operations"
      requires_auth = true
    }
    get_account = {
      route_key    = "GET /accounts/{id}"
      integration  = "account_operations"
      requires_auth = true
    }
    update_account = {
      route_key    = "PUT /accounts/{id}"
      integration  = "account_operations"
      requires_auth = true
    }
    delete_account = {
      route_key    = "DELETE /accounts/{id}"
      integration  = "account_operations"
      requires_auth = true
    }
    account_files = {
      route_key    = "GET /accounts/{id}/files"
      integration  = "account_operations"
      requires_auth = true
    }
    account_file_upload = {
      route_key    = "POST /accounts/{id}/files"
      integration  = "account_operations"
      requires_auth = true
    }
    delete_account_files = {
      route_key    = "DELETE /accounts/{id}/files"
      integration  = "account_operations"
      requires_auth = true
    }
    get_account_transactions = {
      route_key    = "GET /accounts/{id}/transactions"
      integration  = "account_operations"
      requires_auth = true
    }
    account_file_timeline = {
      route_key    = "GET /accounts/{id}/timeline"
      integration  = "account_operations"
      requires_auth = true
    }

    # Transaction Operations
    get_transactions = {
      route_key    = "GET /transactions"
      integration  = "transaction_operations"
      requires_auth = true
    }
    delete_transaction = {
      route_key    = "DELETE /transactions/{id}"
      integration  = "transaction_operations"
      requires_auth = true
    }

    # Transfer Operations
    detect_transfers = {
      route_key    = "GET /transfers/detect"
      integration  = "transfer_operations"
      requires_auth = true
    }
    get_paired_transfers = {
      route_key    = "GET /transfers/paired"
      integration  = "transfer_operations"
      requires_auth = true
    }
    mark_transfer_pair = {
      route_key    = "POST /transfers/mark-pair"
      integration  = "transfer_operations"
      requires_auth = true
    }
    bulk_mark_transfers = {
      route_key    = "POST /transfers/bulk-mark"
      integration  = "transfer_operations"
      requires_auth = true
    }

    # Field Map Operations
    create_field_map = {
      route_key    = "POST /file-maps"
      integration  = "field_map_operations"
      requires_auth = true
    }
    get_field_map = {
      route_key    = "GET /file-maps/{id}"
      integration  = "field_map_operations"
      requires_auth = true
    }
    list_field_maps = {
      route_key    = "GET /file-maps"
      integration  = "field_map_operations"
      requires_auth = true
    }
    update_field_map = {
      route_key    = "PUT /file-maps/{id}"
      integration  = "field_map_operations"
      requires_auth = true
    }
    delete_field_map = {
      route_key    = "DELETE /file-maps/{id}"
      integration  = "field_map_operations"
      requires_auth = true
    }

    # Category Operations
    create_category = {
      route_key    = "POST /categories"
      integration  = "category_operations"
      requires_auth = true
    }
    list_categories = {
      route_key    = "GET /categories"
      integration  = "category_operations"
      requires_auth = true
    }
    get_categories_hierarchy = {
      route_key    = "GET /categories/hierarchy"
      integration  = "category_operations"
      requires_auth = true
    }
    get_category = {
      route_key    = "GET /categories/{categoryId}"
      integration  = "category_operations"
      requires_auth = true
    }
    update_category = {
      route_key    = "PUT /categories/{categoryId}"
      integration  = "category_operations"
      requires_auth = true
    }
    delete_category = {
      route_key    = "DELETE /categories/{categoryId}"
      integration  = "category_operations"
      requires_auth = true
    }
    test_category_rule = {
      route_key    = "POST /categories/test-rule"
      integration  = "category_operations"
      requires_auth = true
    }
    preview_category_matches = {
      route_key    = "GET /categories/{categoryId}/preview-matches"
      integration  = "category_operations"
      requires_auth = true
    }
    validate_regex_pattern = {
      route_key    = "POST /categories/validate-regex"
      integration  = "category_operations"
      requires_auth = true
    }
    generate_pattern = {
      route_key    = "POST /categories/generate-pattern"
      integration  = "category_operations"
      requires_auth = true
    }
    generate_category_suggestions = {
      route_key    = "POST /transactions/{transactionId}/category-suggestions"
      integration  = "category_operations"
      requires_auth = true
    }
    apply_category_rules_bulk = {
      route_key    = "POST /categories/apply-rules-bulk"
      integration  = "category_operations"
      requires_auth = true
    }
    add_rule_to_category = {
      route_key    = "POST /categories/{categoryId}/rules"
      integration  = "category_operations"
      requires_auth = true
    }
    update_category_rule = {
      route_key    = "PUT /categories/{categoryId}/rules/{ruleId}"
      integration  = "category_operations"
      requires_auth = true
    }
    delete_category_rule = {
      route_key    = "DELETE /categories/{categoryId}/rules/{ruleId}"
      integration  = "category_operations"
      requires_auth = true
    }
    suggest_category_from_transaction = {
      route_key    = "POST /categories/suggest-from-transaction"
      integration  = "category_operations"
      requires_auth = true
    }
    extract_patterns = {
      route_key    = "POST /categories/extract-patterns"
      integration  = "category_operations"
      requires_auth = true
    }
    create_category_with_rule = {
      route_key    = "POST /categories/create-with-rule"
      integration  = "category_operations"
      requires_auth = true
    }
    reset_and_reapply_categories = {
      route_key    = "POST /categories/reset-and-reapply"
      integration  = "category_operations"
      requires_auth = true
    }

    # Analytics Operations
    get_analytics = {
      route_key    = "GET /analytics"
      integration  = "analytics_operations"
      requires_auth = true
    }
    refresh_analytics = {
      route_key    = "POST /analytics/refresh"
      integration  = "analytics_operations"
      requires_auth = true
    }
    get_analytics_status = {
      route_key    = "GET /analytics/status"
      integration  = "analytics_operations"
      requires_auth = true
    }

    # Export Operations
    initiate_export = {
      route_key    = "POST /export"
      integration  = "export_operations"
      requires_auth = true
    }
    list_exports = {
      route_key    = "GET /export"
      integration  = "export_operations"
      requires_auth = true
    }
    get_export_status = {
      route_key    = "GET /export/{exportId}/status"
      integration  = "export_operations"
      requires_auth = true
    }
    get_export_download = {
      route_key    = "GET /export/{exportId}/download"
      integration  = "export_operations"
      requires_auth = true
    }
    delete_export = {
      route_key    = "DELETE /export/{exportId}"
      integration  = "export_operations"
      requires_auth = true
    }

    # FZIP Operations
    fzip_initiate_backup = {
      route_key    = "POST /fzip/backup"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_list_backups = {
      route_key    = "GET /fzip/backup"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_get_backup_status = {
      route_key    = "GET /fzip/backup/{jobId}/status"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_get_backup_download = {
      route_key    = "GET /fzip/backup/{jobId}/download"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_delete_backup = {
      route_key    = "DELETE /fzip/backup/{jobId}"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_create_restore = {
      route_key    = "POST /fzip/restore"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_list_restores = {
      route_key    = "GET /fzip/restore"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_get_restore_status = {
      route_key    = "GET /fzip/restore/{jobId}/status"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_delete_restore = {
      route_key    = "DELETE /fzip/restore/{jobId}"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_upload_restore_package = {
      route_key    = "POST /fzip/restore/{jobId}/upload"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_start_restore_processing = {
      route_key    = "POST /fzip/restore/{jobId}/start"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_restore_upload_url = {
      route_key    = "POST /fzip/restore/upload-url"
      integration  = "fzip_operations"
      requires_auth = true
    }
    fzip_cancel_restore = {
      route_key    = "POST /fzip/restore/{jobId}/cancel"
      integration  = "fzip_operations"
      requires_auth = true
    }

    # User Preferences Operations
    get_user_preferences = {
      route_key    = "GET /user-preferences"
      integration  = "user_preferences_operations"
      requires_auth = true
    }
    update_user_preferences = {
      route_key    = "PUT /user-preferences"
      integration  = "user_preferences_operations"
      requires_auth = true
    }
    get_transfer_preferences = {
      route_key    = "GET /user-preferences/transfers"
      integration  = "user_preferences_operations"
      requires_auth = true
    }
    update_transfer_preferences = {
      route_key    = "PUT /user-preferences/transfers"
      integration  = "user_preferences_operations"
      requires_auth = true
    }
    get_account_date_range = {
      route_key    = "GET /user-preferences/account-date-range"
      integration  = "user_preferences_operations"
      requires_auth = true
    }
  }

  # Lambda permission configurations
  lambda_permissions = {
    api_gateway_colors = {
      statement_id  = "AllowAPIGatewayInvokeColors"
      function_name = "getcolors"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/colors"
    }
    api_gateway_files = {
      statement_id  = "AllowAPIGatewayInvokeFiles"
      function_name = "file_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/files*"
    }
    api_gateway_upload = {
      statement_id  = "AllowAPIGatewayInvokeUpload"
      function_name = "file_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/files/upload"
    }
    api_gateway_accounts = {
      statement_id  = "AllowAPIGatewayInvokeAccounts"
      function_name = "account_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/accounts*"
    }
    api_gateway_transactions = {
      statement_id  = "AllowAPIGatewayInvokeTransactions"
      function_name = "transaction_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/transactions*"
    }
    api_gateway_transfers = {
      statement_id  = "AllowAPIGatewayInvokeTransfers"
      function_name = "transfer_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/transfers*"
    }
    getcolors = {
      statement_id  = "AllowAPIGatewayInvoke"
      function_name = "getcolors"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
    }
    api_gateway_field_maps = {
      statement_id  = "AllowAPIGatewayInvokeFieldMapsLambda"
      function_name = "field_map_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
    }
    api_gateway_categories = {
      statement_id  = "AllowAPIGatewayInvokeCategoriesLambda"
      function_name = "category_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
    }
    api_gateway_analytics = {
      statement_id  = "AllowAPIGatewayInvokeAnalyticsLambda"
      function_name = "analytics_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/analytics*"
    }
    api_gateway_workflows = {
      statement_id  = "AllowAPIGatewayInvokeWorkflowsLambda"
      function_name = "workflow_tracking"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/workflows*"
    }
    api_gateway_export = {
      statement_id  = "AllowExecutionFromAPIGateway"
      function_name = "export_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
    }
    api_gateway_fzip = {
      statement_id  = "AllowAPIGatewayInvokeFZIPLambda"
      function_name = "fzip_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/fzip*"
      use_alias     = true
    }
    api_gateway_user_preferences_ops = {
      statement_id  = "AllowAPIGatewayInvokeUserPreferencesLambda"
      function_name = "user_preferences_operations"
      source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
    }
  }
}

# =========================================
# API GATEWAY MAIN CONFIGURATION
# =========================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-${var.environment}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["http://localhost:5173"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
    allow_headers = ["Authorization", "Content-Type", "Origin", "Accept", "Access-Control-Request-Headers", "Access-Control-Request-Method"]
    max_age       = 600
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
  name             = "${var.project_name}-${var.environment}-cognito"

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.main.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

# =========================================
# DYNAMIC INTEGRATIONS
# =========================================

resource "aws_apigatewayv2_integration" "lambda_integrations" {
  for_each = local.integrations

  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = lookup(each.value, "use_alias", false) ? local.fzip_operations_arn : local.lambda_functions[each.value.lambda_key].invoke_arn
  payload_format_version = "2.0"
  description            = each.value.description
}

# =========================================
# DYNAMIC ROUTES
# =========================================

resource "aws_apigatewayv2_route" "api_routes" {
  for_each = local.routes

  api_id             = aws_apigatewayv2_api.main.id
  route_key          = each.value.route_key
  target             = "integrations/${aws_apigatewayv2_integration.lambda_integrations[each.value.integration].id}"
  authorization_type = each.value.requires_auth ? "JWT" : "NONE"
  authorizer_id      = each.value.requires_auth ? aws_apigatewayv2_authorizer.cognito.id : null
}


# =========================================
# STAGE CONFIGURATION
# =========================================


resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = var.environment
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
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

# =========================================
# DYNAMIC LAMBDA PERMISSIONS
# =========================================

resource "aws_lambda_permission" "api_gateway_lambda_permissions" {
  for_each = local.lambda_permissions

  statement_id  = each.value.statement_id
  action        = "lambda:InvokeFunction"
  function_name = lookup(each.value, "use_alias", false) ? local.fzip_operations_function_name : local.lambda_functions[each.value.function_name].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = each.value.source_arn
}

# =========================================
# MOVED BLOCKS FOR REFACTORING
# =========================================

# Integration moves
moved {
  from = aws_apigatewayv2_integration.getcolors
  to   = aws_apigatewayv2_integration.lambda_integrations["getcolors"]
}

moved {
  from = aws_apigatewayv2_integration.file_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["file_operations"]
}

moved {
  from = aws_apigatewayv2_integration.workflow_tracking
  to   = aws_apigatewayv2_integration.lambda_integrations["workflow_tracking"]
}

moved {
  from = aws_apigatewayv2_integration.account_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["account_operations"]
}

moved {
  from = aws_apigatewayv2_integration.transaction_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["transaction_operations"]
}

moved {
  from = aws_apigatewayv2_integration.transfer_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["transfer_operations"]
}

moved {
  from = aws_apigatewayv2_integration.field_map_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["field_map_operations"]
}

moved {
  from = aws_apigatewayv2_integration.category_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["category_operations"]
}

moved {
  from = aws_apigatewayv2_integration.analytics_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["analytics_operations"]
}

moved {
  from = aws_apigatewayv2_integration.export_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["export_operations"]
}

moved {
  from = aws_apigatewayv2_integration.fzip_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["fzip_operations"]
}

moved {
  from = aws_apigatewayv2_integration.user_preferences_operations
  to   = aws_apigatewayv2_integration.lambda_integrations["user_preferences_operations"]
}

# Route moves
moved {
  from = aws_apigatewayv2_route.getcolors
  to   = aws_apigatewayv2_route.api_routes["getcolors"]
}

moved {
  from = aws_apigatewayv2_route.get_file_transactions
  to   = aws_apigatewayv2_route.api_routes["get_file_transactions"]
}

moved {
  from = aws_apigatewayv2_route.delete_file_transactions
  to   = aws_apigatewayv2_route.api_routes["delete_file_transactions"]
}

moved {
  from = aws_apigatewayv2_route.list_files
  to   = aws_apigatewayv2_route.api_routes["list_files"]
}

moved {
  from = aws_apigatewayv2_route.get_file
  to   = aws_apigatewayv2_route.api_routes["get_file"]
}

moved {
  from = aws_apigatewayv2_route.list_files_by_account
  to   = aws_apigatewayv2_route.api_routes["list_files_by_account"]
}

moved {
  from = aws_apigatewayv2_route.get_s3_upload_url
  to   = aws_apigatewayv2_route.api_routes["get_s3_upload_url"]
}

moved {
  from = aws_apigatewayv2_route.get_download_url
  to   = aws_apigatewayv2_route.api_routes["get_download_url"]
}

moved {
  from = aws_apigatewayv2_route.delete_file
  to   = aws_apigatewayv2_route.api_routes["delete_file"]
}

moved {
  from = aws_apigatewayv2_route.unassociate_file
  to   = aws_apigatewayv2_route.api_routes["unassociate_file"]
}

moved {
  from = aws_apigatewayv2_route.associate_file
  to   = aws_apigatewayv2_route.api_routes["associate_file"]
}

moved {
  from = aws_apigatewayv2_route.file_balance
  to   = aws_apigatewayv2_route.api_routes["file_balance"]
}

moved {
  from = aws_apigatewayv2_route.file_closing_balance
  to   = aws_apigatewayv2_route.api_routes["file_closing_balance"]
}

moved {
  from = aws_apigatewayv2_route.get_file_metadata
  to   = aws_apigatewayv2_route.api_routes["get_file_metadata"]
}

moved {
  from = aws_apigatewayv2_route.update_file_field_map
  to   = aws_apigatewayv2_route.api_routes["update_file_field_map"]
}

moved {
  from = aws_apigatewayv2_route.get_file_preview
  to   = aws_apigatewayv2_route.api_routes["get_file_preview"]
}

moved {
  from = aws_apigatewayv2_route.get_workflow_status
  to   = aws_apigatewayv2_route.api_routes["get_workflow_status"]
}

moved {
  from = aws_apigatewayv2_route.list_user_workflows
  to   = aws_apigatewayv2_route.api_routes["list_user_workflows"]
}

moved {
  from = aws_apigatewayv2_route.cancel_workflow
  to   = aws_apigatewayv2_route.api_routes["cancel_workflow"]
}

moved {
  from = aws_apigatewayv2_route.create_account
  to   = aws_apigatewayv2_route.api_routes["create_account"]
}

moved {
  from = aws_apigatewayv2_route.list_accounts
  to   = aws_apigatewayv2_route.api_routes["list_accounts"]
}

moved {
  from = aws_apigatewayv2_route.delete_accounts
  to   = aws_apigatewayv2_route.api_routes["delete_accounts"]
}

moved {
  from = aws_apigatewayv2_route.get_account
  to   = aws_apigatewayv2_route.api_routes["get_account"]
}

moved {
  from = aws_apigatewayv2_route.update_account
  to   = aws_apigatewayv2_route.api_routes["update_account"]
}

moved {
  from = aws_apigatewayv2_route.delete_account
  to   = aws_apigatewayv2_route.api_routes["delete_account"]
}

moved {
  from = aws_apigatewayv2_route.account_files
  to   = aws_apigatewayv2_route.api_routes["account_files"]
}

moved {
  from = aws_apigatewayv2_route.account_file_upload
  to   = aws_apigatewayv2_route.api_routes["account_file_upload"]
}

moved {
  from = aws_apigatewayv2_route.delete_account_files
  to   = aws_apigatewayv2_route.api_routes["delete_account_files"]
}

moved {
  from = aws_apigatewayv2_route.get_account_transactions
  to   = aws_apigatewayv2_route.api_routes["get_account_transactions"]
}

moved {
  from = aws_apigatewayv2_route.account_file_timeline
  to   = aws_apigatewayv2_route.api_routes["account_file_timeline"]
}

moved {
  from = aws_apigatewayv2_route.get_transactions
  to   = aws_apigatewayv2_route.api_routes["get_transactions"]
}

moved {
  from = aws_apigatewayv2_route.delete_transaction
  to   = aws_apigatewayv2_route.api_routes["delete_transaction"]
}

moved {
  from = aws_apigatewayv2_route.detect_transfers
  to   = aws_apigatewayv2_route.api_routes["detect_transfers"]
}

moved {
  from = aws_apigatewayv2_route.get_paired_transfers
  to   = aws_apigatewayv2_route.api_routes["get_paired_transfers"]
}

moved {
  from = aws_apigatewayv2_route.mark_transfer_pair
  to   = aws_apigatewayv2_route.api_routes["mark_transfer_pair"]
}

moved {
  from = aws_apigatewayv2_route.bulk_mark_transfers
  to   = aws_apigatewayv2_route.api_routes["bulk_mark_transfers"]
}

moved {
  from = aws_apigatewayv2_route.create_field_map
  to   = aws_apigatewayv2_route.api_routes["create_field_map"]
}

moved {
  from = aws_apigatewayv2_route.get_field_map
  to   = aws_apigatewayv2_route.api_routes["get_field_map"]
}

moved {
  from = aws_apigatewayv2_route.list_field_maps
  to   = aws_apigatewayv2_route.api_routes["list_field_maps"]
}

moved {
  from = aws_apigatewayv2_route.update_field_map
  to   = aws_apigatewayv2_route.api_routes["update_field_map"]
}

moved {
  from = aws_apigatewayv2_route.delete_field_map
  to   = aws_apigatewayv2_route.api_routes["delete_field_map"]
}

moved {
  from = aws_apigatewayv2_route.create_category
  to   = aws_apigatewayv2_route.api_routes["create_category"]
}

moved {
  from = aws_apigatewayv2_route.list_categories
  to   = aws_apigatewayv2_route.api_routes["list_categories"]
}

moved {
  from = aws_apigatewayv2_route.get_categories_hierarchy
  to   = aws_apigatewayv2_route.api_routes["get_categories_hierarchy"]
}

moved {
  from = aws_apigatewayv2_route.get_category
  to   = aws_apigatewayv2_route.api_routes["get_category"]
}

moved {
  from = aws_apigatewayv2_route.update_category
  to   = aws_apigatewayv2_route.api_routes["update_category"]
}

moved {
  from = aws_apigatewayv2_route.delete_category
  to   = aws_apigatewayv2_route.api_routes["delete_category"]
}

moved {
  from = aws_apigatewayv2_route.test_category_rule
  to   = aws_apigatewayv2_route.api_routes["test_category_rule"]
}

moved {
  from = aws_apigatewayv2_route.preview_category_matches
  to   = aws_apigatewayv2_route.api_routes["preview_category_matches"]
}

moved {
  from = aws_apigatewayv2_route.validate_regex_pattern
  to   = aws_apigatewayv2_route.api_routes["validate_regex_pattern"]
}

moved {
  from = aws_apigatewayv2_route.generate_pattern
  to   = aws_apigatewayv2_route.api_routes["generate_pattern"]
}

moved {
  from = aws_apigatewayv2_route.generate_category_suggestions
  to   = aws_apigatewayv2_route.api_routes["generate_category_suggestions"]
}

moved {
  from = aws_apigatewayv2_route.apply_category_rules_bulk
  to   = aws_apigatewayv2_route.api_routes["apply_category_rules_bulk"]
}

moved {
  from = aws_apigatewayv2_route.add_rule_to_category
  to   = aws_apigatewayv2_route.api_routes["add_rule_to_category"]
}

moved {
  from = aws_apigatewayv2_route.update_category_rule
  to   = aws_apigatewayv2_route.api_routes["update_category_rule"]
}

moved {
  from = aws_apigatewayv2_route.delete_category_rule
  to   = aws_apigatewayv2_route.api_routes["delete_category_rule"]
}

moved {
  from = aws_apigatewayv2_route.suggest_category_from_transaction
  to   = aws_apigatewayv2_route.api_routes["suggest_category_from_transaction"]
}

moved {
  from = aws_apigatewayv2_route.extract_patterns
  to   = aws_apigatewayv2_route.api_routes["extract_patterns"]
}

moved {
  from = aws_apigatewayv2_route.create_category_with_rule
  to   = aws_apigatewayv2_route.api_routes["create_category_with_rule"]
}

moved {
  from = aws_apigatewayv2_route.reset_and_reapply_categories
  to   = aws_apigatewayv2_route.api_routes["reset_and_reapply_categories"]
}

moved {
  from = aws_apigatewayv2_route.get_analytics
  to   = aws_apigatewayv2_route.api_routes["get_analytics"]
}

moved {
  from = aws_apigatewayv2_route.refresh_analytics
  to   = aws_apigatewayv2_route.api_routes["refresh_analytics"]
}

moved {
  from = aws_apigatewayv2_route.get_analytics_status
  to   = aws_apigatewayv2_route.api_routes["get_analytics_status"]
}

moved {
  from = aws_apigatewayv2_route.initiate_export
  to   = aws_apigatewayv2_route.api_routes["initiate_export"]
}

moved {
  from = aws_apigatewayv2_route.list_exports
  to   = aws_apigatewayv2_route.api_routes["list_exports"]
}

moved {
  from = aws_apigatewayv2_route.get_export_status
  to   = aws_apigatewayv2_route.api_routes["get_export_status"]
}

moved {
  from = aws_apigatewayv2_route.get_export_download
  to   = aws_apigatewayv2_route.api_routes["get_export_download"]
}

moved {
  from = aws_apigatewayv2_route.delete_export
  to   = aws_apigatewayv2_route.api_routes["delete_export"]
}

moved {
  from = aws_apigatewayv2_route.fzip_initiate_backup
  to   = aws_apigatewayv2_route.api_routes["fzip_initiate_backup"]
}

moved {
  from = aws_apigatewayv2_route.fzip_list_backups
  to   = aws_apigatewayv2_route.api_routes["fzip_list_backups"]
}

moved {
  from = aws_apigatewayv2_route.fzip_get_backup_status
  to   = aws_apigatewayv2_route.api_routes["fzip_get_backup_status"]
}

moved {
  from = aws_apigatewayv2_route.fzip_get_backup_download
  to   = aws_apigatewayv2_route.api_routes["fzip_get_backup_download"]
}

moved {
  from = aws_apigatewayv2_route.fzip_delete_backup
  to   = aws_apigatewayv2_route.api_routes["fzip_delete_backup"]
}

moved {
  from = aws_apigatewayv2_route.fzip_create_restore
  to   = aws_apigatewayv2_route.api_routes["fzip_create_restore"]
}

moved {
  from = aws_apigatewayv2_route.fzip_list_restores
  to   = aws_apigatewayv2_route.api_routes["fzip_list_restores"]
}

moved {
  from = aws_apigatewayv2_route.fzip_get_restore_status
  to   = aws_apigatewayv2_route.api_routes["fzip_get_restore_status"]
}

moved {
  from = aws_apigatewayv2_route.fzip_delete_restore
  to   = aws_apigatewayv2_route.api_routes["fzip_delete_restore"]
}

moved {
  from = aws_apigatewayv2_route.fzip_upload_restore_package
  to   = aws_apigatewayv2_route.api_routes["fzip_upload_restore_package"]
}

moved {
  from = aws_apigatewayv2_route.fzip_start_restore_processing
  to   = aws_apigatewayv2_route.api_routes["fzip_start_restore_processing"]
}

moved {
  from = aws_apigatewayv2_route.fzip_restore_upload_url
  to   = aws_apigatewayv2_route.api_routes["fzip_restore_upload_url"]
}

moved {
  from = aws_apigatewayv2_route.fzip_cancel_restore
  to   = aws_apigatewayv2_route.api_routes["fzip_cancel_restore"]
}

moved {
  from = aws_apigatewayv2_route.get_user_preferences
  to   = aws_apigatewayv2_route.api_routes["get_user_preferences"]
}

moved {
  from = aws_apigatewayv2_route.update_user_preferences
  to   = aws_apigatewayv2_route.api_routes["update_user_preferences"]
}

moved {
  from = aws_apigatewayv2_route.get_transfer_preferences
  to   = aws_apigatewayv2_route.api_routes["get_transfer_preferences"]
}

moved {
  from = aws_apigatewayv2_route.update_transfer_preferences
  to   = aws_apigatewayv2_route.api_routes["update_transfer_preferences"]
}

moved {
  from = aws_apigatewayv2_route.get_account_date_range
  to   = aws_apigatewayv2_route.api_routes["get_account_date_range"]
}

# Lambda permission moves
moved {
  from = aws_lambda_permission.api_gateway_colors
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_colors"]
}

moved {
  from = aws_lambda_permission.api_gateway_files
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_files"]
}

moved {
  from = aws_lambda_permission.api_gateway_upload
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_upload"]
}

moved {
  from = aws_lambda_permission.api_gateway_accounts
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_accounts"]
}

moved {
  from = aws_lambda_permission.api_gateway_transactions
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_transactions"]
}

moved {
  from = aws_lambda_permission.api_gateway_transfers
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_transfers"]
}

moved {
  from = aws_lambda_permission.getcolors
  to   = aws_lambda_permission.api_gateway_lambda_permissions["getcolors"]
}

moved {
  from = aws_lambda_permission.api_gateway_field_maps
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_field_maps"]
}

moved {
  from = aws_lambda_permission.api_gateway_categories
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_categories"]
}

moved {
  from = aws_lambda_permission.api_gateway_analytics
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_analytics"]
}

moved {
  from = aws_lambda_permission.api_gateway_workflows
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_workflows"]
}

moved {
  from = aws_lambda_permission.api_gateway_export
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_export"]
}

moved {
  from = aws_lambda_permission.api_gateway_fzip
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_fzip"]
}

moved {
  from = aws_lambda_permission.api_gateway_user_preferences_ops
  to   = aws_lambda_permission.api_gateway_lambda_permissions["api_gateway_user_preferences_ops"]
}

# =========================================
# OUTPUTS
# =========================================

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




