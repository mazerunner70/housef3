#!/bin/bash
set -e

echo "🔧 Fixing Cognito User Pool - Importing Original Pool"

cd infrastructure/terraform

# Remove the new pool from Terraform state
echo "Removing new User Pool from state..."
terraform state rm aws_cognito_user_pool.main
terraform state rm aws_cognito_user_pool_client.main  
terraform state rm aws_cognito_resource_server.api

# Import the original User Pool
echo "Importing original User Pool..."
terraform import aws_cognito_user_pool.main eu-west-2_sLSn4biAC

# Get the client ID from the original pool
ORIGINAL_CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id eu-west-2_sLSn4biAC --query 'UserPoolClients[0].ClientId' --output text)
echo "Original Client ID: $ORIGINAL_CLIENT_ID"

# Import the original client and resource server
terraform import aws_cognito_user_pool_client.main eu-west-2_sLSn4biAC/$ORIGINAL_CLIENT_ID
terraform import aws_cognito_resource_server.api eu-west-2_sLSn4biAC/https://api.localhost:3000

echo "✅ Original User Pool imported successfully!"
echo "Your existing users are preserved:"
aws cognito-idp list-users --user-pool-id eu-west-2_sLSn4biAC --query 'Users[].Attributes[?Name==`email`].Value' --output text

# Delete the orphaned new pool
echo "🗑️ Deleting the new orphaned User Pool..."
aws cognito-idp delete-user-pool --user-pool-id eu-west-2_OLL20U1qx

echo "✅ Cognito User Pool fix complete!"
echo "Original pool (eu-west-2_sLSn4biAC) is now managed by Terraform"
echo "Your existing users can continue to login normally"