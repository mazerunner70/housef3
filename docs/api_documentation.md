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

### File Operations

#### POST /upload
Generate a presigned URL for direct S3 file upload.

**Request Body:**
```json
{
  "key": "string",         // S3 key in format: userId/fileId/fileName
  "contentType": "string", // File content type
  "accountId": "string"    // Optional: Account ID to associate the file with
}
```

**Response:**
```json
{
  "url": "string",         // S3 presigned POST URL
  "fields": {             // Form fields required for the POST request
    "key": "string",
    "Content-Type": "string",
    ...additional AWS fields
  },
  "fileId": "string",     // Extracted from the key
  "expires": number       // URL expiration time in seconds
}
```

**Notes:**
- The presigned URL is valid for 1 hour
- The key must start with the authenticated user's ID
- If accountId is provided, it must belong to the authenticated user
- Use multipart form upload with the provided fields and URL
- Add x-amz-meta-accountid field to form data if associating with an account

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

## Transfers

The transfer detection system provides endpoints for identifying and managing inter-account transfers. These endpoints help users automatically detect when money moves between their own accounts and properly categorize these transactions.

### GET /transfers/detect

Detects potential transfer transactions within a specified date range.

**Query Parameters:**
- `startDate` (optional): Start date in milliseconds since epoch or ISO 8601 format
- `endDate` (optional): End date in milliseconds since epoch or ISO 8601 format

**Default Behavior:**
If no dates are provided, defaults to the last 7 days.

**Example Request:**
```
GET /transfers/detect?startDate=1704067200000&endDate=1704758400000
```

**Example Response:**
```json
{
  "transfers": [
    {
      "outgoingTransaction": {
        "transactionId": "tx-123",
        "accountId": "acc-456",
        "amount": -500.00,
        "date": 1704067200000,
        "description": "Transfer to Savings",
        "currency": "USD"
      },
      "incomingTransaction": {
        "transactionId": "tx-124",
        "accountId": "acc-789",
        "amount": 500.00,
        "date": 1704067200000,
        "description": "Transfer from Checking",
        "currency": "USD"
      },
      "amount": 500.00,
      "dateDifference": 0
    }
  ],
  "count": 1,
  "dateRange": {
    "startDate": 1704067200000,
    "endDate": 1704758400000
  }
}
```

**Detection Criteria:**
- Transactions must be from different accounts
- Amounts must be opposite (one negative, one positive) within $0.01 tolerance
- Transactions must occur within 7 days of each other
- Only uncategorized transactions are considered

### GET /transfers/paired

Returns existing transfer pairs that have already been marked as transfers.

**Query Parameters:**
- `startDate` (optional): Start date filter in milliseconds since epoch or ISO 8601 format
- `endDate` (optional): End date filter in milliseconds since epoch or ISO 8601 format

**Default Behavior:**
If no dates are provided, returns all existing transfer pairs.

**Example Request:**
```
GET /transfers/paired?startDate=1704067200000&endDate=1704758400000
```

**Example Response:**
```json
{
  "pairedTransfers": [
    {
      "outgoingTransaction": {
        "transactionId": "tx-123",
        "accountId": "acc-456",
        "amount": -500.00,
        "date": 1704067200000,
        "description": "Transfer to Savings",
        "currency": "USD",
        "categories": [
          {
            "categoryId": "cat-transfer",
            "categoryName": "Transfers"
          }
        ]
      },
      "incomingTransaction": {
        "transactionId": "tx-124",
        "accountId": "acc-789",
        "amount": 500.00,
        "date": 1704067200000,
        "description": "Transfer from Checking",
        "currency": "USD",
        "categories": [
          {
            "categoryId": "cat-transfer",
            "categoryName": "Transfers"
          }
        ]
      },
      "amount": 500.00,
      "dateDifference": 0
    }
  ],
  "count": 1,
  "dateRange": {
    "startDate": 1704067200000,
    "endDate": 1704758400000
  }
}
```

### POST /transfers/mark-pair

Marks two specific transactions as a transfer pair.

**Request Body:**
```json
{
  "outgoingTransactionId": "tx-123",
  "incomingTransactionId": "tx-124"
}
```

**Example Response:**
```json
{
  "message": "Transfer pair marked successfully"
}
```

**Behavior:**
- Creates or assigns a "Transfers" category to both transactions
- Sets the transfer category as the primary category
- Updates both transactions in the database
- Validates that both transactions belong to the authenticated user

### POST /transfers/bulk-mark

Marks multiple detected transfer pairs as transfers in a single operation.

**Request Body:**
```json
{
  "transferPairs": [
    {
      "outgoingTransactionId": "tx-123",
      "incomingTransactionId": "tx-124"
    },
    {
      "outgoingTransactionId": "tx-125",
      "incomingTransactionId": "tx-126"
    }
  ]
}
```

**Example Response:**
```json
{
  "successful": [
    {
      "outgoingTransactionId": "tx-123",
      "incomingTransactionId": "tx-124"
    }
  ],
  "failed": [
    {
      "pair": {
        "outgoingTransactionId": "tx-125",
        "incomingTransactionId": "tx-126"
      },
      "error": "One or both transactions not found"
    }
  ],
  "successCount": 1,
  "failureCount": 1
}
```

**Behavior:**
- Processes each transfer pair individually
- Returns detailed success/failure information
- Continues processing even if some pairs fail
- Validates user ownership for all transactions

## Transfer Detection Algorithm

The system uses a sophisticated sliding window algorithm to efficiently detect transfers:

### Sliding Window Processing
- **Window Size**: 14 days with 3-day overlap
- **Memory Efficient**: Uses minimal transaction objects during processing
- **Scalable**: Handles large datasets without memory issues

### Matching Logic
1. **Account Validation**: Transactions must be from different accounts
2. **Amount Matching**: Absolute amounts must match within $0.01 tolerance
3. **Sign Validation**: One transaction must be negative (outgoing), one positive (incoming)
4. **Date Proximity**: Transactions must be within 7 days of each other
5. **Availability**: Only uncategorized transactions are considered

### Performance Optimizations
- **Amount Sorting**: Enables early termination when amount differences are too large
- **Batch Processing**: Processes transactions in manageable chunks
- **Pagination Handling**: Prevents infinite loops in database pagination

## Transfer Category Management

### Automatic Category Creation
When transfers are marked, the system automatically:
1. Creates a "Transfers" category if none exists
2. Assigns the transfer category to both transactions
3. Sets the category as the primary category
4. Uses category type `TRANSFER` for proper reporting exclusion

### Category Properties
```json
{
  "name": "Transfers",
  "type": "TRANSFER",
  "icon": "transfer",
  "color": "#6B7280"
}
```

### Impact on Financial Reporting
- Transfer transactions are excluded from income/expense calculations
- Account balances remain accurate (transfers don't affect net worth)
- Transfers appear in their own category for reporting purposes

## Error Handling

### Common Error Responses

**400 Bad Request - Invalid Date Format:**
```json
{
  "error": "Invalid date format. Expected milliseconds since epoch"
}
```

**404 Not Found - Transaction Not Found:**
```json
{
  "error": "One or both transactions not found"
}
```

**401 Unauthorized - Access Denied:**
```json
{
  "error": "Unauthorized access to transactions"
}
```

**500 Internal Server Error - Processing Failed:**
```json
{
  "error": "Failed to mark transfer pair"
}
```

## Usage Examples

### Detecting Transfers for Last 30 Days
```javascript
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
const now = new Date();

const response = await fetch(`/transfers/detect?startDate=${thirtyDaysAgo.getTime()}&endDate=${now.getTime()}`, {
  headers: {
    'Authorization': 'your-jwt-token'
  }
});
```

### Bulk Marking Detected Transfers
```javascript
const transferPairs = [
  { outgoingTransactionId: 'tx-1', incomingTransactionId: 'tx-2' },
  { outgoingTransactionId: 'tx-3', incomingTransactionId: 'tx-4' }
];

const response = await fetch('/transfers/bulk-mark', {
  method: 'POST',
  headers: {
    'Authorization': 'your-jwt-token',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ transferPairs })
});
```

### Getting Existing Transfer Pairs
```javascript
const response = await fetch('/transfers/paired', {
  headers: {
    'Authorization': 'your-jwt-token'
  }
});
```

## Best Practices

### For API Consumers
1. **Use Appropriate Date Ranges**: Start with 7-30 days for better performance
2. **Review Before Marking**: Always review detected transfers before bulk marking
3. **Handle Partial Failures**: Check both success and failure arrays in bulk operations
4. **Progressive Processing**: Use systematic date ranges to cover all data

### For Performance
1. **Limit Date Ranges**: Smaller ranges (7-30 days) perform better than large ranges
2. **Batch Operations**: Use bulk-mark for multiple transfers
3. **Monitor Progress**: Track which date ranges have been processed
4. **Handle Timeouts**: Be prepared for longer processing times with large datasets 