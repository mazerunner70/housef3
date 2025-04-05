#!/bin/bash

API_ENDPOINT="https://ypa8h438hl.execute-api.eu-west-2.amazonaws.com/dev"
CLIENT_ID="38rp4vcbq0um6795t81sgogflk"
USERNAME="testuser@example.com"
PASSWORD="Test123!@3"

# Function to get authentication token
get_auth_token() {
  echo "Getting authentication token..."
  aws --no-cli-pager cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id $CLIENT_ID \
    --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD > /tmp/auth.json

  TOKEN=$(cat /tmp/auth.json | jq -r '.AuthenticationResult.IdToken')
  echo "Token received: ${TOKEN:0:20}..."
  echo $TOKEN
}

# Test GET /files
test_list_files() {
  local token=$1
  
  echo -e "\nCalling API Gateway: GET /files"
  curl -s "$API_ENDPOINT/files" \
    -H "Authorization: $token" | jq .

  echo -e "\nAPI call completed successfully! ✅"
}

# Test POST /files/upload
test_get_upload_url() {
  local token=$1
  local filename=$2
  local contentType=$3
  local fileSize=$4
  
  echo -e "\nCalling API Gateway: POST /files/upload"
  curl -s -X POST "$API_ENDPOINT/files/upload" \
    -H "Authorization: $token" \
    -H "Content-Type: application/json" \
    -d "{\"fileName\":\"$filename\", \"contentType\":\"$contentType\", \"fileSize\": $fileSize}" | jq .

  echo -e "\nAPI call completed successfully! ✅"
}

# Test GET /files/{fileId}/download
test_get_download_url() {
  local token=$1
  local fileId=$2
  
  echo -e "\nCalling API Gateway: GET /files/$fileId/download"
  curl -s "$API_ENDPOINT/files/$fileId/download" \
    -H "Authorization: $token" | jq .

  echo -e "\nAPI call completed successfully! ✅"
}

# Test DELETE /files/{fileId}
test_delete_file() {
  local token=$1
  local fileId=$2
  
  echo -e "\nCalling API Gateway: DELETE /files/$fileId"
  curl -s -X DELETE "$API_ENDPOINT/files/$fileId" \
    -H "Authorization: $token" | jq .

  echo -e "\nAPI call completed successfully! ✅"
}

# Show menu and handle user selection
show_menu() {
  echo -e "\n===== API Test Menu ====="
  echo "1) List files"
  echo "2) Get upload URL"
  echo "3) Get download URL"
  echo "4) Delete file"
  echo "5) Exit"
  
  read -p "Select option (1-5): " choice
  
  TOKEN=$(get_auth_token)
  
  case $choice in
    1)
      test_list_files "$TOKEN"
      ;;
    2)
      read -p "Enter filename: " filename
      read -p "Enter content type (e.g., text/plain): " contentType
      read -p "Enter file size in bytes: " fileSize
      test_get_upload_url "$TOKEN" "$filename" "$contentType" "$fileSize"
      ;;
    3)
      read -p "Enter file ID: " fileId
      test_get_download_url "$TOKEN" "$fileId"
      ;;
    4)
      read -p "Enter file ID: " fileId
      test_delete_file "$TOKEN" "$fileId"
      ;;
    5)
      echo "Exiting..."
      exit 0
      ;;
    *)
      echo "Invalid option, please try again."
      ;;
  esac
  
  # Return to menu after operation
  show_menu
}

# Start the script
echo "API Test Script - Testing API Gateway endpoints"
show_menu 