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

echo "Testing frontend deployment at https://$CLOUDFRONT_DOMAIN"

# Test basic connectivity
echo -e "\n1. Testing basic connectivity..."
FRONTEND_RESPONSE=$(curl -s "https://$CLOUDFRONT_DOMAIN")
[ -z "$FRONTEND_RESPONSE" ] && handle_error "No response from frontend deployment"
echo "✅ Frontend is accessible"

# Check for key elements in HTML
echo -e "\n2. Validating HTML structure..."
if echo "$FRONTEND_RESPONSE" | grep -q "<div id=\"root\"></div>"; then
  echo "✅ React root element found"
else
  handle_error "React root element not found"
fi

# Check for required assets
echo -e "\n3. Checking for required assets..."
if echo "$FRONTEND_RESPONSE" | grep -q "<script type=\"module\""; then
  SCRIPT_SRC=$(echo "$FRONTEND_RESPONSE" | grep -o 'src="/assets/[^"]*"' | head -1)
  echo "✅ JavaScript is included: $SCRIPT_SRC"
else
  handle_error "JavaScript is missing"
fi

if echo "$FRONTEND_RESPONSE" | grep -q "<link rel=\"stylesheet\""; then
  CSS_HREF=$(echo "$FRONTEND_RESPONSE" | grep -o 'href="/assets/[^"]*\.css"' | head -1)
  echo "✅ CSS is included: $CSS_HREF"
else
  handle_error "CSS is missing"
fi

# Check app title
if echo "$FRONTEND_RESPONSE" | grep -q "<title>"; then
  APP_TITLE=$(echo "$FRONTEND_RESPONSE" | grep -o '<title>[^<]*</title>' | head -1)
  echo "✅ Page title found: $APP_TITLE"
else
  handle_error "Page title missing"
fi

# Extract JS file path and test it
echo -e "\n4. Verifying JavaScript asset..."
JS_PATH=$(echo "$FRONTEND_RESPONSE" | grep -o 'src="/assets/[^"]*"' | head -1 | sed 's/src="//;s/"$//')
if [ -n "$JS_PATH" ]; then
  JS_RESPONSE=$(curl -s "https://$CLOUDFRONT_DOMAIN$JS_PATH" -o /dev/null -w "%{http_code}")
  if [ "$JS_RESPONSE" == "200" ]; then
    echo "✅ JavaScript asset is accessible"
  else
    handle_error "JavaScript asset returned HTTP $JS_RESPONSE"
  fi
else
  handle_error "Could not extract JavaScript path"
fi

# Extract CSS file path and test it
echo -e "\n5. Verifying CSS asset..."
CSS_PATH=$(echo "$FRONTEND_RESPONSE" | grep -o 'href="/assets/[^"]*\.css"' | head -1 | sed 's/href="//;s/"$//')
if [ -n "$CSS_PATH" ]; then
  CSS_RESPONSE=$(curl -s "https://$CLOUDFRONT_DOMAIN$CSS_PATH" -o /dev/null -w "%{http_code}")
  if [ "$CSS_RESPONSE" == "200" ]; then
    echo "✅ CSS asset is accessible"
  else
    handle_error "CSS asset returned HTTP $CSS_RESPONSE"
  fi
else
  handle_error "Could not extract CSS path"
fi

echo -e "\n✅ All frontend deployment tests passed successfully!"
echo "Frontend is properly deployed at: https://$CLOUDFRONT_DOMAIN"
exit 0 