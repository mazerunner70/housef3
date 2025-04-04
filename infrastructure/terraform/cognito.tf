resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-${var.environment}-user-pool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject       = "Your verification code"
    email_message       = "Your verification code is {####}"
  }

  # Add JWT token configuration
  user_pool_add_ons {
    advanced_security_mode = "OFF"
  }

  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable            = true

    string_attribute_constraints {
      min_length = 7
      max_length = 256
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_cognito_user_pool_client" "main" {
  name = "${var.project_name}-${var.environment}-client"

  user_pool_id = aws_cognito_user_pool.main.id
  
  # No client secret for public clients
  generate_secret = false
  
  # Auth flows for token generation
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Token configuration
  refresh_token_validity = 30

  prevent_user_existence_errors = "ENABLED"
  
  # Enable token revocation
  enable_token_revocation = true

  # Allow all scopes needed for API access
  allowed_oauth_flows                  = ["implicit"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  # Required for OAuth flows
  callback_urls = ["http://localhost:3000"]
  logout_urls   = ["http://localhost:3000"]
}

# Resource server for API access
resource "aws_cognito_resource_server" "api" {
  identifier = "https://api.${var.domain_name}"
  name       = "${var.project_name}-${var.environment}-api"

  user_pool_id = aws_cognito_user_pool.main.id

  scope {
    scope_name        = "colors.read"
    scope_description = "Read access to colors API"
  }
}

# Outputs for use in other parts of the infrastructure
output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.main.id
}

output "cognito_user_pool_endpoint" {
  value = aws_cognito_user_pool.main.endpoint
}

output "cognito_resource_server_identifier" {
  value = aws_cognito_resource_server.api.identifier
} 