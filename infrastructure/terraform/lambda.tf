data "archive_file" "lambda_colors" {
  type        = "zip"
  source_dir  = "../../backend/src/handlers"
  output_path = "../../backend/lambda.zip"
}

resource "aws_lambda_function" "colors" {
  filename         = "../../backend/lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-colors"
  role            = aws_iam_role.lambda_exec.arn
  handler         = "list_imports.handler"
  runtime         = "python3.9"
  source_code_hash = data.archive_file.lambda_colors.output_base64sha256
  
  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_exec.name
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.colors.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs
output "lambda_function_name" {
  value = aws_lambda_function.colors.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.colors.arn
} 