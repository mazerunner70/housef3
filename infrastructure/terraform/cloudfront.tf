locals {
  s3_origin_id = "${var.project_name}-${var.environment}-frontend-origin"
  api_origin_id = "${var.project_name}-${var.environment}-api-origin"
}

resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "${var.project_name}-${var.environment}-frontend-oac"
  description                       = "Origin Access Control for Frontend S3 Bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Cache policy for API Gateway
resource "aws_cloudfront_cache_policy" "api_gateway" {
  name        = "${var.project_name}-${var.environment}-api-gateway-cache"
  comment     = "Cache policy for API Gateway"
  default_ttl = 60
  min_ttl     = 0
  max_ttl     = 300

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "all"
    }
  }
}

# Response headers policy for CORS
resource "aws_cloudfront_response_headers_policy" "cors_policy" {
  name    = "${var.project_name}-${var.environment}-cors-policy"
  comment = "CORS policy for API Gateway and frontend integration"

  cors_config {
    access_control_allow_credentials = true
    
    access_control_allow_headers {
      items = ["Authorization", "Content-Type", "Origin", "Accept"]
    }
    
    access_control_allow_methods {
      items = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "DELETE", "PATCH"]
    }
    
    access_control_allow_origins {
      items = ["http://localhost:5173"]
    }
    
    access_control_max_age_sec = 600
    origin_override            = true
  }
}

resource "aws_cloudfront_distribution" "frontend" {
  enabled             = true
  is_ipv6_enabled    = true
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    domain_name = aws_s3_bucket_website_configuration.frontend.website_endpoint
    origin_id   = local.s3_origin_id
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # API Gateway Origin
  origin {
    domain_name = replace(aws_apigatewayv2_api.main.api_endpoint, "https://", "")
    origin_id   = local.api_origin_id
    origin_path = "/dev"  # This appends the stage name

    custom_origin_config {
      http_port              = 80
      https_port            = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 30
      origin_keepalive_timeout = 5
    }
  }

  # Enable detailed logging to S3
  logging_config {
    include_cookies = false
    bucket          = "${aws_s3_bucket.frontend.bucket}.s3.amazonaws.com"
    prefix          = "cloudfront-logs/"
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = local.s3_origin_id
    viewer_protocol_policy = "redirect-to-https"
    compress              = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # API Gateway behavior - direct pass-through
  ordered_cache_behavior {
    path_pattern     = "/colors"  # Simple path pattern matching the example
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.api_origin_id
    
    response_headers_policy_id = aws_cloudfront_response_headers_policy.cors_policy.id

    compress               = true
    viewer_protocol_policy = "https-only"

    forwarded_values {
      query_string = true
      headers = [
        "Authorization",
        "Origin",
        "Access-Control-Request-Headers",
        "Access-Control-Request-Method",
        "Content-Type"
      ]
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  # This special behavior handles routing SPA routes back to index.html
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = var.tags
}

output "cloudfront_distribution_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.id
} 