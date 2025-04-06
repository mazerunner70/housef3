# API Documentation for Housef3

## Overview

This document provides details about the API endpoints available in the Housef3 application. The API is organized around RESTful principles and uses standard HTTP methods.

All endpoints require authentication using a JWT token provided by Amazon Cognito. This token must be included in the `Authorization` header of all requests.

## Base URL

```
https://ypa8h438hl.execute-api.eu-west-2.amazonaws.com/dev
```

## Authentication

All API requests require a valid JWT token from Amazon Cognito. Include this token in the `Authorization` header:

```
Authorization: <your-jwt-token>
```

## Endpoints

### Colors

#### GET /colors

Returns a list of available colors.

**Example Response:**
```json
{
  "colors": ["Cerulean", "Crimson", "Sage", "Amber"]
}
```

### Files

#### GET /files

Returns a list of all files for the authenticated user.

**Example Response:**
```json
{
  "files": [
    {
      "fileId": "558f142f-1ec5-4792-a25c-60bcce976ecf",
      "fileName": "data.csv",
      "contentType": "text/csv",
      "fileSize": 6854,
      "uploadDate": "2025-04-05T19:00:48.070106",
      "lastModified": "2025-04-05T19:00:48.070106"
    }
  ],
  "user": {
    "id": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
    "email": "testuser@example.com",
    "auth_time": "1743939419"
  },
  "metadata": {
    "totalFiles": 1,
    "timestamp": "2025-04-06T11:37:02.979802"
  }
}
```

#### POST /files/upload

Generates a pre-signed URL for file upload.

**Request Body:**
```json
{
  "fileName": "example.csv",
  "contentType": "text/csv",
  "fileSize": 1024
}
```

**Example Response:**
```json
{
  "fileId": "c2920fef-23ce-400c-926e-76a6884aabd9",
  "uploadUrl": "https://housef3-dev-file-storage.s3.amazonaws.com/...",
  "fileName": "example.csv",
  "contentType": "text/csv",
  "expires": 3600,
  "processingStatus": "pending",
  "fileFormat": "csv"
}
```

#### GET /files/{id}/download

Generates a pre-signed URL for file download.

**Example Response:**
```json
{
  "downloadUrl": "https://housef3-dev-file-storage.s3.amazonaws.com/...",
  "fileName": "example.csv",
  "contentType": "text/csv",
  "expires": 3600
}
```

#### DELETE /files/{id}

Deletes a file.

**Example Response:**
```json
{
  "message": "File deleted successfully",
  "fileId": "c2920fef-23ce-400c-926e-76a6884aabd9"
}
```

### Accounts

#### GET /accounts

Returns a list of all accounts for the authenticated user.

**Example Response:**
```json
{
  "accounts": [
    {
      "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
      "userId": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
      "accountName": "Test Account",
      "accountType": "checking",
      "institution": "Test Bank",
      "balance": "1500.0",
      "currency": "USD",
      "lastUpdated": "2025-04-05T21:10:29.269040",
      "createdAt": "2025-04-05T21:10:28.724511",
      "notes": "Test account created via API",
      "isActive": true
    }
  ],
  "user": {
    "id": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
    "email": "testuser@example.com",
    "auth_time": "1743939419"
  },
  "metadata": {
    "totalAccounts": 1
  }
}
```

#### POST /accounts

Creates a new account.

**Request Body:**
```json
{
  "accountName": "New Account",
  "accountType": "checking",
  "institution": "Test Bank",
  "balance": "1000.0",
  "currency": "USD",
  "notes": "New account"
}
```

**Example Response:**
```json
{
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
  "userId": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
  "accountName": "New Account",
  "accountType": "checking",
  "institution": "Test Bank",
  "balance": "1000.0",
  "currency": "USD",
  "lastUpdated": "2025-04-06T11:00:00.000000",
  "createdAt": "2025-04-06T11:00:00.000000",
  "notes": "New account",
  "isActive": true
}
```

#### GET /accounts/{id}

Returns details for a specific account.

**Example Response:**
```json
{
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
  "userId": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
  "accountName": "Test Account",
  "accountType": "checking",
  "institution": "Test Bank",
  "balance": "1500.0",
  "currency": "USD",
  "lastUpdated": "2025-04-05T21:10:29.269040",
  "createdAt": "2025-04-05T21:10:28.724511",
  "notes": "Test account created via API",
  "isActive": true
}
```

#### PUT /accounts/{id}

Updates an account.

**Request Body:**
```json
{
  "accountName": "Updated Account",
  "balance": "2000.0",
  "notes": "Updated notes"
}
```

**Example Response:**
```json
{
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
  "userId": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
  "accountName": "Updated Account",
  "accountType": "checking",
  "institution": "Test Bank",
  "balance": "2000.0",
  "currency": "USD",
  "lastUpdated": "2025-04-06T11:15:00.000000",
  "createdAt": "2025-04-05T21:10:28.724511",
  "notes": "Updated notes",
  "isActive": true
}
```

#### DELETE /accounts/{id}

Deletes an account.

**Example Response:**
```json
{
  "message": "Account deleted successfully",
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd"
}
```

### Account-File Associations

The API supports associating files with specific accounts. This is an optional feature that allows you to organize files by account.

#### GET /accounts/{id}/files

Returns a list of all files associated with a specific account.

**Example Response:**
```json
{
  "files": [
    {
      "fileId": "d31b6f5a-6ab1-4d89-89c0-c405cfe1124c",
      "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
      "userId": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
      "fileName": "account_test_file.txt",
      "uploadDate": "2025-04-06T11:33:34.341693",
      "fileSize": "52",
      "fileFormat": "other",
      "s3Key": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce/3aa57029-692d-439a-8f55-3e89b54704b5/account_test_file.txt",
      "processingStatus": "pending"
    }
  ],
  "user": {
    "id": "d6c2f244-a0a1-706e-36eb-80d0d0b506ce",
    "email": "testuser@example.com",
    "auth_time": "1743939419"
  },
  "metadata": {
    "totalFiles": 1,
    "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
    "accountName": "Test Account"
  }
}
```

#### POST /accounts/{id}/files

Generates a pre-signed URL for file upload and associates the file with the specified account.

**Request Body:**
```json
{
  "fileName": "account_test_file.txt",
  "contentType": "text/plain",
  "fileSize": 52
}
```

**Example Response:**
```json
{
  "fileId": "c2920fef-23ce-400c-926e-76a6884aabd9",
  "uploadUrl": "https://housef3-dev-file-storage.s3.amazonaws.com/...",
  "fileName": "account_test_file.txt",
  "contentType": "text/plain",
  "expires": 3600,
  "processingStatus": "pending",
  "fileFormat": "other",
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd"
}
```

#### DELETE /accounts/{id}/files/{fileId}

Deletes a file from a specific account.

**Response:**
```json
{
  "message": "File successfully unassociated from account",
  "fileId": "d31b6f5a-6ab1-4d89-89c0-c405cfe1124c",
  "previousAccountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd"
}
```

#### POST /files/{id}/associate

Associates a file with an account. This endpoint allows you to link an existing file to an account.

**Request Parameters:**
- `id` (path parameter): ID of the file to associate with an account

**Request Body:**
```json
{
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd"
}
```

**Response:**
```json
{
  "message": "File successfully associated with account",
  "fileId": "d31b6f5a-6ab1-4d89-89c0-c405cfe1124c",
  "accountId": "6286d8bc-1cb7-4715-95c2-8c5a57d40cfd",
  "accountName": "Test Account"
}
```

## Account-File Association Usage Recommendations

### When to Associate Files with Accounts

1. **Bank Statements**: Associate monthly bank statements with the corresponding bank account.
2. **Transaction Exports**: Link transaction export files (CSV, OFX, etc.) with the account they were exported from.
3. **Credit Card Statements**: Associate credit card statements with the appropriate credit card account.
4. **Account-specific Documents**: Link documents like account opening forms or terms & conditions with the relevant account.

### When to Use Standalone Files

1. **Aggregated Reports**: Reports that span multiple accounts.
2. **Tax Documents**: Documents that apply to your overall financial situation.
3. **General Financial Documents**: Documents that aren't specific to any one account.
4. **Temporary Files**: Files you're working with that don't need a permanent association.

### Benefits of Account-File Associations

1. **Organization**: Keep files organized by account for easier retrieval.
2. **Context**: Maintain the relationship between files and their source accounts.
3. **Filtering**: Filter files by account for more focused analysis.
4. **Reporting**: Generate reports that include files related to specific accounts.

### Accessing Files

* All files, whether associated with an account or not, can be accessed through the main `/files` endpoint.
* Files associated with specific accounts can also be accessed through the `/accounts/{id}/files` endpoint.
* When a file is associated with an account, it will include the `accountId` field in its metadata.

### Management Considerations

* Deleting an account does not automatically delete associated files. Files must be deleted separately.
* Files can be associated with only one account at a time.
* Existing standalone files can be associated with accounts using the `/files/{id}/associate` endpoint.
* Files can be unassociated from accounts using the `/files/{id}/unassociate` endpoint without deleting the file. 