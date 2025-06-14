#!/bin/bash
set -e

# Function to handle errors and exit with code 1
handle_error() {
  echo "❌ ERROR: $1"
  exit 1
}

# Get CloudFront domain from Terraform output
cd $(dirname "$0")/../infrastructure/terraform
CLOUDFRONT_DOMAIN=$(terraform output -raw cloudfront_distribution_domain)
cd ../..

LOCAL_URL="http://localhost:5173"
PROD_URL="https://$CLOUDFRONT_DOMAIN"

# Function to test a frontend deployment
test_frontend() {
  local url="$1"
  local env_name="$2"
  
  echo -e "\n======================="
  echo "TESTING $env_name FRONTEND"
  echo "URL: $url"
  echo -e "=======================\n"

  # Test basic connectivity
  echo "1. Testing basic connectivity..."
  FRONTEND_RESPONSE=$(curl -s "$url")
  [ -z "$FRONTEND_RESPONSE" ] && handle_error "No response from $env_name frontend at $url"
  echo "✅ Frontend is accessible"

  # Check for key elements in HTML
  echo -e "\n2. Validating HTML structure..."
  if echo "$FRONTEND_RESPONSE" | grep -q "<div id=\"root\"></div>"; then
    echo "✅ React root element found"
  else
    handle_error "React root element not found in $env_name frontend"
  fi

  # Check for required assets - script patterns differ in development vs production
  echo -e "\n3. Checking for required assets..."
  
  # Different script patterns for dev vs prod
  if [ "$env_name" = "LOCAL" ]; then
    # Development mode typically uses type="module" without crossorigin
    if echo "$FRONTEND_RESPONSE" | grep -q "<script type=\"module\""; then
      echo "✅ JavaScript module is included (dev mode)"
    else
      handle_error "JavaScript module is missing in $env_name frontend"
    fi
    
    # In development, CSS might be injected by JavaScript
    echo "✅ CSS is likely injected by JavaScript (dev mode)"
  else
    # Production typically has bundled assets with crossorigin
    if echo "$FRONTEND_RESPONSE" | grep -q "<script type=\"module\" crossorigin"; then
      SCRIPT_SRC=$(echo "$FRONTEND_RESPONSE" | grep -o 'src="/assets/[^"]*"' | head -1)
      echo "✅ JavaScript is included: $SCRIPT_SRC"
    else
      handle_error "JavaScript is missing in $env_name frontend"
    fi
    
    if echo "$FRONTEND_RESPONSE" | grep -q "<link rel=\"stylesheet\""; then
      CSS_HREF=$(echo "$FRONTEND_RESPONSE" | grep -o 'href="/assets/[^"]*\.css"' | head -1)
      echo "✅ CSS is included: $CSS_HREF"
    else
      handle_error "CSS is missing in $env_name frontend"
    fi
  fi

  # Check app title
  if echo "$FRONTEND_RESPONSE" | grep -q "<title>"; then
    APP_TITLE=$(echo "$FRONTEND_RESPONSE" | grep -o '<title>[^<]*</title>' | head -1)
    echo "✅ Page title found: $APP_TITLE"
  else
    handle_error "Page title missing in $env_name frontend"
  fi

  # Asset verification
  if [ "$env_name" = "PRODUCTION" ]; then
    # Extract JS file path and test it (production only)
    echo -e "\n4. Verifying JavaScript asset..."
    JS_PATH=$(echo "$FRONTEND_RESPONSE" | grep -o 'src="/assets/[^"]*"' | head -1 | sed 's/src="//;s/"$//')
    if [ -n "$JS_PATH" ]; then
      JS_RESPONSE=$(curl -s "$url$JS_PATH" -o /dev/null -w "%{http_code}")
      if [ "$JS_RESPONSE" == "200" ]; then
        echo "✅ JavaScript asset is accessible"
      else
        handle_error "JavaScript asset returned HTTP $JS_RESPONSE in $env_name frontend"
      fi
    else
      handle_error "Could not extract JavaScript path from $env_name frontend"
    fi

    # Extract CSS file path and test it (production only)
    echo -e "\n5. Verifying CSS asset..."
    CSS_PATH=$(echo "$FRONTEND_RESPONSE" | grep -o 'href="/assets/[^"]*\.css"' | head -1 | sed 's/href="//;s/"$//')
    if [ -n "$CSS_PATH" ]; then
      CSS_RESPONSE=$(curl -s "$url$CSS_PATH" -o /dev/null -w "%{http_code}")
      if [ "$CSS_RESPONSE" == "200" ]; then
        echo "✅ CSS asset is accessible"
      else
        handle_error "CSS asset returned HTTP $CSS_RESPONSE in $env_name frontend"
      fi
    else
      handle_error "Could not extract CSS path from $env_name frontend"
    fi
  else
    echo -e "\n4. Skipping individual asset verification in development mode"
    echo "   (Dev server handles assets differently)"
  fi

  echo -e "\n✅ All $env_name frontend tests passed successfully!"
}

# Check if local development server is running
echo "Checking if local development server is running..."
LOCAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $LOCAL_URL || echo "000")

if [ "$LOCAL_STATUS" == "200" ]; then
  # Test local frontend
  test_frontend "$LOCAL_URL" "LOCAL"
else
  echo "⚠️ Local development server is not running at $LOCAL_URL (HTTP $LOCAL_STATUS)"
  echo "Start the server with: cd frontend && npm run dev"
  echo "Skipping local tests."
fi

# Test production frontend
test_frontend "$PROD_URL" "PRODUCTION"

echo -e "\n✅ Frontend testing complete!"
exit 0 