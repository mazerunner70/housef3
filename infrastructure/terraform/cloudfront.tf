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

# CloudFront function to rewrite API paths
resource "aws_cloudfront_function" "rewrite_api_path" {
  name    = "${var.project_name}-${var.environment}-rewrite-api-path"
  runtime = "cloudfront-js-1.0"
  publish = true
  code    = <<-EOT
    function handler(event) {
      var request = event.request;
      var uri = request.uri;
      
      // Only modify API requests
      if (uri.startsWith('/api/')) {
        // Remove /api prefix (origin_path will add /dev)
        request.uri = uri.replace(/^\/api/, '');
      }
      
      return request;
    }
  EOT
}

resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = local.s3_origin_id
    
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend.id
  }
  
  # API Gateway Origin
  origin {
    domain_name = replace(aws_apigatewayv2_api.main.api_endpoint, "https://", "")
    origin_id   = local.api_origin_id
    origin_path = "/dev"  # This appends the stage name
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_read_timeout    = 30
      origin_keepalive_timeout = 5
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.project_name} ${var.environment}"
  default_root_object = "index.html"
  
  # API Gateway behavior for all API routes
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.api_origin_id

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]

      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.rewrite_api_path.arn
    }
  }

  # Default behavior for S3 bucket (frontend)
  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.s3_origin_id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
    compress               = true
    viewer_protocol_policy = "redirect-to-https"
  }

  # Only apply SPA routing (serving index.html) for frontend routes
  # These won't affect /api/* routes due to the ordered_cache_behavior above
  # which takes precedence for /api/* paths
  custom_error_response {
    error_code         = 403
    response_code      = 403
    response_page_path = "/index.html"
    error_caching_min_ttl = 0
  }
  
  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/index.html"
    error_caching_min_ttl = 0
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

output "cloudfront_distribution_domain" {
  description = "Domain name of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution"
  value       = aws_cloudfront_distribution.frontend.id
} 