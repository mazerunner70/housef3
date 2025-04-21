# File Association Process

This document describes the process when a user associates a file with an account.

## Overview

When a user associates a file with an account, the system:
1. Validates the file and account ownership
2. Updates the file record with the account ID
3. Reprocesses the file's transactions with the account context
4. Updates the file's status and transaction count

## Detailed Process

### 1. Initial Request
- User selects a file and an account to associate
- Frontend sends a POST request to `/files/{fileId}/associate`
- Request body includes:
  ```json
  {
    "accountId": "account-123"
  }
  ```

### 2. Validation
The system performs several validations:
- Verifies the file exists and belongs to the user
- Checks the account exists and belongs to the user
- Ensures the file isn't already associated with an account
- Validates the user has permission to access both resources

### 3. File Record Update
- Updates the file record in DynamoDB with the account ID
- Sets the processing status to "pending"
- Updates the file's metadata to include the account association

### 4. Transaction Reprocessing
The system then reprocesses the file's transactions:
1. Retrieves the file content from S3
2. Gets the file's format and opening balance
3. Processes transactions with account-specific logic:
   - Applies account-specific field mapping if available
   - Checks for duplicate transactions within the account (see [Deduplication Process](#deduplication-process))
   - Associates each transaction with the account
   - Updates transaction statuses (new/duplicate)

### 5. Final Updates
After processing:
- Updates the file's processing status to "processed"
- Records the number of transactions processed
- Updates the file's metadata with processing results
- Returns success response with transaction count

## Deduplication Process

When processing transactions, the system checks for duplicates within the account. A transaction is considered a duplicate if it matches an existing transaction on:
- Date
- Description
- Amount

The deduplication process:
0. delete all transactions relating to the file if any are present
1. For each new transaction, queries existing transactions in the account
2. Compares the transaction's date (string equality), description(string equality), and amount (as Decimal)
3. If a match is found:
   - Marks the new transaction as status "duplicate"
   - Increments the duplicate count
   - Stores the transaction
4. If no match is found:
   - Marks the transaction as "new"
   - Stores it as a status "new" transaction

This process helps prevent duplicate entries while maintaining a record of all transactions, including duplicates.

## Error Handling

The system handles various error cases:
- File not found
- Account not found
- Permission denied
- File already associated
- Processing errors
- S3 access issues

Each error case returns an appropriate HTTP status code and error message.

## API Response

Successful response:
```json
{
  "message": "File successfully associated with account and transactions reprocessed",
  "fileId": "file-123",
  "accountId": "account-123",
  "accountName": "Checking Account",
  "transactionCount": 50
}
```

Error response:
```json
{
  "message": "Error message describing the issue"
}
```

## Frontend Integration

The frontend:
1. Shows available files and accounts for association
2. Handles the association request
3. Updates the UI to reflect the new association
4. Shows processing status and results
5. Displays any errors that occur

## Security Considerations

- All operations verify user ownership of both file and account
- File content is only accessed during processing
- Account association can only be done once per file
- Processing errors don't affect the account association
- All operations are logged for audit purposes 