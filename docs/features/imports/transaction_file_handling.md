# Transaction File Handling

This document describes the lifecycle of transaction files in the system and how they interact with transaction records.

## Transaction File Lifecycle

### 1. Creation

When a transaction file is uploaded to the system, the following process occurs:

- A transaction file metadata record is created in DynamoDB
- The file is stored in S3 with a key format of `user_id/file_id/filename`
- Initial status is set to `PENDING` (unprocessed)
- If both account ID and field mapping are known at upload time:
  - The `process_file_with_account` function is automatically triggered
  - File format is detected (CSV, OFX, QFX, etc.)
  - File content is parsed into individual transaction records
  - Each transaction is assigned a hash based on account ID, date, amount, and description
  - File status is updated to `PROCESSED` after successful processing

During processing, duplicate detection works as follows:
- Each transaction is checked against existing records in the account using its hash
- Transactions with matching hashes are marked with status `duplicate`
- Unique transactions are marked with status `new`
- All transactions (both new and duplicates) are stored in DynamoDB with references to their source file
- If the first or last transaction is a duplicate this means the file overlaps with existing transactions. Find the original transaction that causes the duplicate and use it to set the opening balance for this file and trigger an update with the new opening balance

### 2. Reading

Transaction files and their associated transactions can be read in various scenarios:

- When viewing transaction history in the UI
- When generating reports or analytics
- During reconciliation processes
- For audit purposes

Reading operations do not modify any transaction data or file metadata.

### 3. Updates

There are three primary scenarios when a transaction file is updated:

#### Account ID Changes
- Updates file metadata to associate with a different account
- Does not delete or recreate transaction records
- Transactions maintain their original file association
- May affect duplicate detection for future file uploads

#### Opening Balance Changes
- Updates file metadata with new opening balance
- Recalculates running balances for transactions
- Does not delete or recreate transaction records
- All existing transaction records are preserved

#### Field Mapping Changes
- Updates how file fields are interpreted
- If reprocessing with new content occurs:
  1. Existing transactions for this specific file are deleted
  2. New transactions are created according to the updated mapping
  3. Duplicate detection is performed against remaining transactions

### 4. Deletion

When a transaction file is deleted:

- Transaction file metadata is removed from DynamoDB
- The associated file is removed from S3
- All transactions associated with this specific file ID are deleted
- Transactions from other files remain untouched
- Deletion is permanent and cannot be undone

## Transaction Management Principles

1. **File-Transaction Relationship**
   - Transactions are always tied to their source file via `file_id`
   - This enables proper cleanup when files are deleted

2. **Cross-File Duplicate Detection**
   - Duplicate detection works across all files for a given account
   - This prevents duplicate transactions from appearing in account history

3. **Isolation**
   - Only transactions from a specific file are affected when that file is modified or deleted
   - Transactions from other files remain untouched

4. **Metadata Efficiency**
   - Simple metadata changes (like updating opening balance) do not trigger transaction recreation
   - This preserves performance and prevents unnecessary database operations

## Implementation Details

### Key Database Tables

- **Files Table**: Stores metadata about transaction files
  - Primary key: `fileId`
  - GSI: `AccountIdIndex` (partition key: `accountId`)
  - GSI: `UserIdIndex` (partition key: `userId`)

- **Transactions Table**: Stores individual transaction records
  - Primary key: `transactionId`
  - GSI: `FileIdIndex` (partition key: `fileId`)
  - GSI: `AccountDateIndex` (partition key: `accountId`, sort key: `date`)
  - GSI: `TransactionHashIndex` (partition key: `accountId`, sort key: `transactionHash`)

### Key Functions

- `process_file_with_account`: Main function for processing file content into transactions
- `delete_transactions_for_file`: Removes all transactions associated with a specific file
- `check_duplicate_transaction`: Determines if a transaction already exists in the account
- `calculate_opening_balance_from_duplicates`: Calculates opening balance from matching transactions

## Best Practices

1. Always check for account ID and field mapping before processing files
2. Use transaction hashes for reliable duplicate detection
3. Handle reprocessing carefully to avoid data loss
4. Maintain proper transaction-to-file relationships for clean deletion
5. Log all file operations for troubleshooting and audit purposes 