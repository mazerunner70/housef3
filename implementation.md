# Accounts Functionality Implementation Plan

## Overview
This document outlines the implementation plan for the accounts functionality, including CRUD operations for account metadata, transaction deduplication, and UI components.

## Backend Implementation

### 1. Account CRUD Operations
- Create new Lambda handler `account_operations.py` with the following endpoints:
  - `POST /accounts` - Create new account
  - `GET /accounts` - List all accounts
  - `GET /accounts/{id}` - Get account details
  - `GET /accounts/{id}/transactions` - Get paginated account transactions (ignoring records marked as duplicate)
  - `PUT /accounts/{id}` - Update account metadata
  - `DELETE /accounts/{id}` - Delete account

### 2. Account Metadata Schema
```typescript
interface Account {
  accountId: string;
  name: string;
  description?: string;
  type: 'checking' | 'savings' | 'credit' | 'investment';
  currency: string;
  createdAt: string;
  updatedAt: string;
}
```

### 3. Transaction Deduplication Logic
When a file is associated with an account:
1. Fetch all transactions for the account
2. For each new transaction:
   - Compare with existing transactions using precise matching on:
     - Date 
     - Amount
     - Description 
   - If match found:
     - update a 'duplication' field in the associating file transaction as true


When a file is unassociated:
1. update all transactions from the file with duplicated status to not duplicated


### 4. API Gateway Configuration
Add new routes in `api_gateway.tf`:
```hcl
resource "aws_apigatewayv2_route" "create_account" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /accounts"
  target    = "integrations/${aws_apigatewayv2_integration.account_operations.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

# Similar routes for other operations
```

## Frontend Implementation

### 1. Account Service
Create `AccountService.ts`:
```typescript
class AccountService {
  static async createAccount(data: AccountCreateData): Promise<Account>;
  static async getAccounts(): Promise<Account[]>;
  static async getAccount(id: string): Promise<Account>;
  static async updateAccount(id: string, data: AccountUpdateData): Promise<Account>;
  static async deleteAccount(id: string): Promise<void>;
}
```

### 2. Account List Component
Create `AccountList.tsx`:
- Display list of accounts with basic metadata
- Search/filter functionality
- Link to account details

### 3. Account Details Component
Create `AccountDetails.tsx`:
- Display account metadata
- Edit account information
- List of associated files
- Paginated transaction view with:
  - Transaction details
  - Duplicate status indicators
  - Filtering options

### 4. Transaction List Component
Create `TransactionList.tsx`:
- Paginated view of transactions (ignoring duplicates)
- Filter by date range, amount, status

## Database Schema Updates

### 1. Accounts Table
```hcl
resource "aws_dynamodb_table" "accounts" {
  name           = "${var.project_name}-${var.environment}-accounts"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "accountId"

  attribute {
    name = "accountId"
    type = "S"
  }
}
```

### 2. Transactions Table Updates
Add new attributes:
- `duplicateStatus`: 'unique' | 'duplicated'
- `duplicateOf`: reference to duplicate transaction ID

## Testing Plan

### 1. Backend Tests
- Account CRUD operations
- Transaction deduplication logic
- File association/unassociation effects

### 2. Frontend Tests
- Account list rendering
- Account details view
- Transaction list with duplicates
- Pagination and filtering

### 3. Integration Tests
- End-to-end account creation
- File association with deduplication
- Transaction status updates

## Deployment Steps

1. Create DynamoDB tables
2. Deploy Lambda functions
3. Update API Gateway configuration
4. Deploy frontend components
5. Run database migrations
6. Verify functionality

## Future Enhancements

1. Batch processing for large transaction sets
2. Machine learning for improved duplicate detection
3. Account reconciliation features
4. Export functionality for account data
5. Account analytics and reporting
