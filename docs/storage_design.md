# Storage Design Document

## Design Decisions

### Transaction Deduplication Strategy

#### Current Implementation
The current implementation uses DynamoDB queries to check for duplicate transactions. For each new transaction, it:
1. Queries the transactions table using the `AccountIdIndex`
2. Filters results by date, description, and amount
3. Marks transactions as duplicates if matches are found

#### Analysis of Approaches

##### In-Memory Approach
**Pros:**
1. Single database query to fetch all transactions
2. Faster comparison operations in memory
3. Better for small accounts with few transactions

**Cons:**
1. Memory usage could be high for large accounts (e.g., 10,000 transactions = 10-20MB)
2. Need to handle pagination for large result sets
3. Could hit Lambda memory limits (128MB-10GB)
4. More expensive in terms of DynamoDB read capacity

##### Current DynamoDB Query Approach
**Pros:**
1. Memory efficient - only loads potential matches
2. Scales well with large datasets
3. Uses indexes effectively
4. No pagination needed

**Cons:**
1. More database queries (one per transaction)
2. More expensive in terms of DynamoDB read operations
3. Slightly slower due to network latency

#### Decision Rationale
The current DynamoDB query approach was chosen because:
1. It's more memory efficient, which is important for Lambda functions
2. It scales better with large accounts
3. The cost of DynamoDB queries is likely less than the cost of increased Lambda memory usage
4. The current implementation already handles the query efficiently using the `AccountIdIndex`

#### Potential Optimizations
1. **Date Range Filtering**
   - Add a date range filter to the query to reduce the number of potential matches
   - This would be particularly effective for accounts with many transactions over long periods

2. **Batch Processing**
   - Batch the duplicate checks (e.g., check 25 transactions at a time)
   - This would reduce the number of database queries while maintaining memory efficiency

3. **Caching Layer**
   - Add a cache layer for frequently accessed accounts
   - This would improve performance for accounts that are frequently updated

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
| categoryId | S | ID of the category this transaction is assigned to | No |
| importOrder | N | Order in which this transaction was imported | No |
| transactionHash | N | Numeric hash for duplicate detection | No |
| status | S | Transaction status (e.g., "PENDING", "PROCESSED") | No |
| transactionType | S | Type of transaction (e.g., "DEBIT", "CREDIT") | No |
| memo | S | Additional transaction notes | No |
| checkNumber | S | Check number if applicable | No |
| fitId | S | Financial Institution Transaction ID | No |
| createdAt | N | Transaction creation timestamp in milliseconds since epoch | No |
| updatedAt | N | Transaction last update timestamp in milliseconds since epoch | No |

Estimated size: 1-2KB per transaction

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

9. `AccountCategoryIndex`
   - Hash Key: `accountId`
   - Range Key: `categoryId`
   - Purpose: Query transactions by account and category

### 2. Transaction Files Table
Primary Key: `fileId` (String)

#### Fields:
| Field Name | Type | Description | Required |
|------------|------|-------------|----------|
| fileId | S | Unique identifier for the file | Yes |
| userId | S | ID of the user who uploaded the file | Yes |
| accountId | S | ID of the account this file is associated with | No |
| fileName | S | Original name of the uploaded file | Yes |
| uploadDate | N | File upload timestamp in milliseconds since epoch | Yes |
| fileSize | N | Size of the file in bytes | Yes |
| fileFormat | S | Format of the file (e.g., "CSV", "OFX") | Yes |
| s3Key | S | S3 object key for the file | Yes |
| processingStatus | S | Current processing status | Yes |
| fieldMapId | S | ID of the field mapping used | No |
| recordCount | N | Number of records in the file | No |
| dateRangeStart | N | Start date of transactions in the file in milliseconds since epoch | No |
| dateRangeEnd | N | End date of transactions in the file in milliseconds since epoch | No |
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
| createdAt | N | Account creation timestamp in milliseconds since epoch | Yes |
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
| createdAt | N | Field map creation timestamp in milliseconds since epoch | Yes |
| updatedAt | N | Field map last update timestamp in milliseconds since epoch | Yes |

#### Global Secondary Indexes:
1. `UserIdIndex`
   - Hash Key: `userId`
   - Purpose: Query field maps by user

2. `AccountIdIndex`
   - Hash Key: `accountId`
   - Purpose: Query field maps by account

### 5. Categories Table
Primary Key: `categoryId` (String)

#### Purpose:
Stores user-defined categories for classifying transactions. Supports hierarchical categories (parent-child relationships) and rules for auto-categorization as described in `docs/new_ui_transactions_view.md`.

#### Fields:
| Field Name      | Type   | Description                                                                 | Required |
|-----------------|--------|-----------------------------------------------------------------------------|----------|
| categoryId      | S      | Unique identifier for the category (e.g., "cat_ groceries_123")               | Yes      |
| userId          | S      | ID of the user who owns this category                                         | Yes      |
| name            | S      | Display name of the category (e.g., "Groceries", "Salary")                  | Yes      |
| type            | S      | Type of category ("INCOME", "EXPENSE")                                      | Yes      |
| parentCategoryId| S      | ID of the parent category for sub-categories (optional)                     | No       |
| icon            | S      | Optional icon identifier for the category (e.g., "cart", "briefcase")       | No       |
| color           | S      | Optional color code for the category (e.g., "#FF5733")                       | No       |
| createdAt       | N      | Category creation timestamp in milliseconds since epoch                     | Yes      |
| updatedAt       | N      | Category last update timestamp in milliseconds since epoch                  | Yes      |
| rules           | L of M | List of rules for auto-categorization. Each rule is a map:                | No       |
|                 |        | - `fieldToMatch` (S): "Description/Payee", "Notes", "Amount"                |          |
|                 |        | - `condition` (S): "Contains", "StartsWith", "Equals", "Regex", "GT", "LT"  |          |
|                 |        | - `value` (S or N): Value/pattern to match                                  |          |
|                 |        | - `ruleLogic` (S): "AND", "OR" (if multiple conditions in one rule object)  | No       |


#### Global Secondary Indexes:
1.  `UserIdIndex`
    *   Hash Key: `userId`
    *   Range Key: `name` (to sort categories by name for a user)
    *   Purpose: Query categories by user, optionally sort/filter by name.

2.  `UserIdParentCategoryIdIndex`
    *   Hash Key: `userId`
    *   Range Key: `parentCategoryId`
    *   Purpose: Efficiently query for sub-categories of a given parent category for a user. Allows fetching top-level categories by querying where `parentCategoryId` is null or not present.

#### Notes:
*   The `rules` attribute stores an array of rule objects. Each object defines a condition (or set of conditions if `ruleLogic` is used) that, if met by a transaction's details, will assign this category to that transaction.
*   When a transaction is created or updated, these rules can be evaluated by the backend to suggest or automatically assign a category.
*   The `Transactions` table should be updated to include a `categoryId` field (String, optional) to link transactions to a category. If a transaction is categorized, this field will store the `categoryId`. This allows for efficient filtering of transactions by category.

## Technical Details

### Data Types
- S: String
- N: Number (Decimal)
- BOOL: Boolean
- M: Map
- L: List

### Batch Processing Limits
- DynamoDB has a batch limit of 25 items
- This is used in the `delete_transactions_for_file` function
- Could be leveraged for batch duplicate checking

### Notes
1. All timestamps are stored as milliseconds since epoch.
2. Monetary values are stored as Money objects to maintain precision
3. The `transactionHash` is a 64-bit numeric hash used for duplicate detection
4. The `date` field in transactions is stored as milliseconds since epoch for efficient sorting
5. All tables use on-demand capacity mode (PAY_PER_REQUEST)
6. Point-in-time recovery is enabled for all tables
7. Server-side encryption is enabled for all tables

## Future Considerations

### 1. Scaling
- Monitor DynamoDB read capacity as the number of transactions grows
- Consider implementing batch processing if query costs become significant

### 2. Performance
- Track processing times for different account sizes
- Consider implementing caching if certain accounts show high latency

### 3. Cost Optimization
- Monitor DynamoDB costs
- Consider implementing batch processing if query costs become significant
- Evaluate the trade-off between Lambda memory usage and DynamoDB query costs 