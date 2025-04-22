# Storage Design Document

## DynamoDB Tables Overview

### 1. Transactions Table
Primary Key: `transactionId` (String)

#### Fields:
| Field Name | Type | Description | Required |
|------------|------|-------------|----------|
| transactionId | S | Unique identifier for the transaction | Yes |
| accountId | S | ID of the account this transaction belongs to | Yes |
| fileId | S | ID of the file this transaction was imported from | Yes |
| userId | S | ID of the user who owns this transaction | Yes |
| date | N | Transaction date in milliseconds since epoch | Yes |
| description | S | Transaction description | Yes |
| amount | N | Transaction amount as Decimal | Yes |
| balance | N | Running balance after this transaction as Decimal | Yes |
| importOrder | N | Order in which this transaction was imported | No |
| transactionHash | N | Numeric hash for duplicate detection | No |
| status | S | Transaction status (e.g., "PENDING", "PROCESSED") | No |
| transactionType | S | Type of transaction (e.g., "DEBIT", "CREDIT") | No |
| memo | S | Additional transaction notes | No |
| checkNumber | S | Check number if applicable | No |
| fitId | S | Financial Institution Transaction ID | No |
| createdAt | S | ISO timestamp of creation | No |
| updatedAt | S | ISO timestamp of last update | No |

#### Global Secondary Indexes:
1. `FileIdIndex`
   - Hash Key: `fileId`
   - Purpose: Query transactions by file

2. `UserIdIndex`
   - Hash Key: `userId`
   - Purpose: Query transactions by user

3. `StatusIndex`
   - Hash Key: `status`
   - Purpose: Query transactions by status

4. `AccountAmountIndex`
   - Hash Key: `accountId`
   - Range Key: `amount`
   - Purpose: Query transactions by account and amount

5. `AccountBalanceIndex`
   - Hash Key: `accountId`
   - Range Key: `balance`
   - Purpose: Query transactions by account and balance

6. `ImportOrderIndex`
   - Hash Key: `fileId`
   - Range Key: `importOrder`
   - Purpose: Sort transactions by import order

7. `AccountDateIndex`
   - Hash Key: `accountId`
   - Range Key: `date`
   - Purpose: Sort transactions by date within account

8. `TransactionHashIndex`
   - Hash Key: `accountId`
   - Range Key: `transactionHash`
   - Purpose: Efficient duplicate detection

### 2. Transaction Files Table
Primary Key: `fileId` (String)

#### Fields:
| Field Name | Type | Description | Required |
|------------|------|-------------|----------|
| fileId | S | Unique identifier for the file | Yes |
| userId | S | ID of the user who uploaded the file | Yes |
| accountId | S | ID of the account this file is associated with | No |
| fileName | S | Original name of the uploaded file | Yes |
| uploadDate | S | ISO timestamp of upload | Yes |
| fileSize | N | Size of the file in bytes | Yes |
| fileFormat | S | Format of the file (e.g., "CSV", "OFX") | Yes |
| s3Key | S | S3 object key for the file | Yes |
| processingStatus | S | Current processing status | Yes |
| fieldMapId | S | ID of the field mapping used | No |
| recordCount | N | Number of records in the file | No |
| dateRangeStart | S | Start date of transactions in the file | No |
| dateRangeEnd | S | End date of transactions in the file | No |
| errorMessage | S | Error message if processing failed | No |
| openingBalance | N | Opening balance from the file | No |

#### Global Secondary Indexes:
1. `UserIdIndex`
   - Hash Key: `userId`
   - Purpose: Query files by user

2. `AccountIdIndex`
   - Hash Key: `accountId`
   - Purpose: Query files by account

3. `S3KeyIndex`
   - Hash Key: `s3Key`
   - Purpose: Query files by S3 key

### 3. Accounts Table
Primary Key: `accountId` (String)

#### Fields:
| Field Name | Type | Description | Required |
|------------|------|-------------|----------|
| accountId | S | Unique identifier for the account | Yes |
| userId | S | ID of the user who owns the account | Yes |
| accountName | S | Name of the account | Yes |
| accountType | S | Type of account (e.g., "CHECKING", "SAVINGS") | Yes |
| institution | S | Name of the financial institution | Yes |
| balance | N | Current account balance | Yes |
| currency | S | Currency code (e.g., "USD") | Yes |
| notes | S | Additional account notes | No |
| isActive | BOOL | Whether the account is active | Yes |
| createdAt | S | ISO timestamp of creation | Yes |
| defaultFieldMapId | S | ID of the default field map | No |

#### Global Secondary Indexes:
1. `UserIdIndex`
   - Hash Key: `userId`
   - Range Key: `createdAt`
   - Purpose: Query accounts by user, sorted by creation date

### 4. Field Maps Table
Primary Key: `fieldMapId` (String)

#### Fields:
| Field Name | Type | Description | Required |
|------------|------|-------------|----------|
| fieldMapId | S | Unique identifier for the field map | Yes |
| userId | S | ID of the user who created the field map | Yes |
| accountId | S | ID of the account this field map is for | No |
| name | S | Name of the field map | Yes |
| mappings | M | Map of source to destination fields | Yes |
| isDefault | BOOL | Whether this is the default field map | No |
| createdAt | S | ISO timestamp of creation | Yes |
| updatedAt | S | ISO timestamp of last update | Yes |

#### Global Secondary Indexes:
1. `UserIdIndex`
   - Hash Key: `userId`
   - Purpose: Query field maps by user

2. `AccountIdIndex`
   - Hash Key: `accountId`
   - Purpose: Query field maps by account

## Data Types
- S: String
- N: Number (Decimal)
- BOOL: Boolean
- M: Map
- L: List

## Notes
1. All timestamps are stored in ISO 8601 format
2. Monetary values are stored as Decimal numbers to maintain precision
3. The `transactionHash` is a 64-bit numeric hash used for duplicate detection
4. The `date` field in transactions is stored as milliseconds since epoch for efficient sorting
5. All tables use on-demand capacity mode (PAY_PER_REQUEST)
6. Point-in-time recovery is enabled for all tables
7. Server-side encryption is enabled for all tables 