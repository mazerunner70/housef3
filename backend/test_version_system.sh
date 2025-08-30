#!/bin/bash

set -e

echo "=== Testing Auto-Incrementing Build Number System ==="

# Test with default base version
echo "🧪 Test 1: Default base version (v1.0.0)"
SEMVER_BASE="v1.0.0" ./build_lambda_package.sh

echo ""
echo "📋 Current build files:"
echo "Build number: $(cat .build_number 2>/dev/null || echo 'Not found')"
echo "Current version: $(cat .current_version 2>/dev/null || echo 'Not found')"

echo ""
echo "🧪 Test 2: Running build again (should increment)"
SEMVER_BASE="v1.0.0" ./build_lambda_package.sh

echo ""
echo "📋 After second build:"
echo "Build number: $(cat .build_number 2>/dev/null || echo 'Not found')"
echo "Current version: $(cat .current_version 2>/dev/null || echo 'Not found')"

echo ""
echo "🧪 Test 3: Different base version"
SEMVER_BASE="v2.1.5" ./build_lambda_package.sh

echo ""
echo "📋 After version change:"
echo "Build number: $(cat .build_number 2>/dev/null || echo 'Not found')"
echo "Current version: $(cat .current_version 2>/dev/null || echo 'Not found')"

echo ""
echo "✅ Version system test completed!"
echo ""
echo "💡 Now you can deploy with Terraform:"
echo "   cd ../infrastructure/terraform"
echo "   terraform plan"
echo "   terraform apply"
echo ""
echo "🔍 The version will appear in CloudWatch log streams like:"
CURRENT_VERSION=$(cat .current_version)
ALIAS_VERSION=$(echo "$CURRENT_VERSION" | sed 's/\./_/g')
echo "   Raw version: $CURRENT_VERSION"
echo "   Alias version: $ALIAS_VERSION"
echo "   Log stream: 2025/08/02/[${ALIAS_VERSION}]6dba91dbc0074bf79eb6bba6726daac0"