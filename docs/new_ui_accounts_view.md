# New UI - Accounts Section Design

## 1. Overview

The Accounts section in the new UI will provide users with a comprehensive interface to manage their financial accounts. Users will be able to view a list of their accounts, add new accounts, edit existing ones, and delete accounts. For each account, users will see relevant details, including the number of associated transaction files. 

The UI will also offer a detailed view for each account, allowing users to:
- Manage associated transaction files: View currently linked files and associate files that are not yet linked to any account.
- View all transactions: See a list of all transactions belonging to the selected account.

## 2. Main Accounts View (`AccountsView.tsx`)

This will be the primary page for managing accounts.

**Layout:**
- A clear title: "My Accounts".
- An "Add New Account" button.
- A list or grid of account cards/rows.

**Each Account Item in the List will display:**
- Account Name (e.g., "Chase Checking", "Amex Gold")
- Account Type (e.g., "Checking", "Credit Card", "Savings")
- Account Number (masked, e.g., "****1234")
- Current Balance (if applicable and available)
- Currency
- Number of associated Transaction Files (e.g., "5 files")
- Actions:
    - "Edit" button/icon
    - "Delete" button/icon
    - Clicking the account item itself (or a "View Details" button) will navigate to/open the Account Detail View.

**Functionality:**
- **List Accounts:** Fetch and display all accounts for the logged-in user.
- **Add Account:**
    - Clicking "Add New Account" will open a modal or navigate to a form (`AccountForm.tsx` - potentially a new version or reuse/refactor existing).
    - Form fields: Account Name, Account Type, Account Number, Opening Balance, Currency, Bank Name (optional).
- **Edit Account:**
    - Clicking "Edit" will open a modal/form pre-filled with the account's current details.
    - Allow modification of editable fields.
- **Delete Account:**
    - Clicking "Delete" will prompt for confirmation.
    - Upon confirmation, the account and its associations (handle with care, backend should manage cascading deletes or disassociations) will be removed.

## 3. Account Detail View

This view will be accessed by selecting an account from the main `AccountsView`. It could be a separate page or a master-detail layout within `AccountsView`. A tabbed interface is recommended for clarity.

**Layout:**
- Account Header: Displaying key details of the selected account (Name, Type, Number).
- Tabs:
    - Tab 1: Files
    - Tab 2: Transactions

### 3.1. Files Tab

**Purpose:** Manage transaction files associated with the selected account.

**Content:**
- **Associated Files List:**
    - Displays files currently linked to this account.
    - Each file item shows: File Name, Upload Date, Status (e.g., "Processed", "Pending"), Number of Transactions in the file.
    - Option to "Unlink" a file (disassociate from this account, does not delete the file itself).
- **Available Unlinked Files List:**
    - Displays transaction files uploaded by the user that are *not* currently associated with *any* account.
    - Each file item shows: File Name, Upload Date.
    - Option to "Link to [Account Name]" for each file.

**Functionality:**
- **List Associated Files:** Fetch files linked to the current `accountId`.
- **List Unlinked Files:** Fetch files belonging to the user that have `accountId` as null or empty.
- **Link File:** Associate an unlinked file with the current account.
- **Unlink File:** Disassociate a file from the current account (set its `accountId` to null).

### 3.2. Transactions Tab

**Purpose:** View all transactions belonging to the selected account.

**Content:**
- A filterable and sortable table/list of transactions.
- Columns: Date, Description, Category (if assigned), Amount, Type (Debit/Credit), Status (e.g., "Cleared", "Pending", "Duplicate").
- Filters: Date range, Transaction Type, Category, Search by description.
- Sorting: By Date, Amount, Description.
- Pagination for large numbers of transactions.

**Functionality:**
- **List Transactions:** Fetch all transactions where `accountId` matches the selected account.
- Implement filtering and sorting client-side or server-side depending on data volume and performance considerations.
- Clicking a transaction could open a `TransactionDetailModal.tsx` for more actions (e.g., edit category, split transaction - future enhancements).

## 4. Proposed New/Updated React Components

**Located in `frontend/src/new-ui/`:**

- **Views:**
    - `views/AccountsView.tsx`: Main page for listing and managing accounts.
    - `views/AccountDetailView.tsx`: (If a separate page approach is chosen) Page for showing detailed information about a single account with tabs for files and transactions. Alternatively, this logic can be part of `AccountsView.tsx` using modals or an expanding section.

- **Components (in `components/accounts/` or similar subdirectory):**
    - `AccountList.tsx`: Renders the list of accounts in `AccountsView`.
    - `AccountListItem.tsx`: Renders a single account item.
    - `AccountForm.tsx`: Form for creating/editing accounts (could be a new component or an enhanced version of an existing one).
    - `AccountFilesTab.tsx`: Component for the "Files" tab in the detail view.
        - `AssociatedFilesList.tsx`
        - `UnlinkedFilesList.tsx`
    - `AccountTransactionsTab.tsx`: Component for the "Transactions" tab in the detail view.
        - `TransactionTable.tsx` (could be a generic, reusable table component).
    - `ConfirmationModal.tsx`: Reusable modal for delete confirmations.

- **Layouts (if needed):**
    - `layouts/AccountDetailLayout.tsx`: If a dedicated layout is needed for the detail view.

- **Hooks (in `hooks/`):**
    - `useAccounts.ts`: Custom hook to manage fetching, adding, updating, deleting accounts.
    - `useAccountFiles.ts`: Custom hook for managing files associated with an account and unlinked files.
    - `useAccountTransactions.ts`: Custom hook for fetching and managing transactions for an account.

## 5. Backend API Endpoints (Illustrative)

The following API endpoints (or GraphQL queries/mutations) would be needed. These are illustrative and actual implementation will depend on the backend structure (`db_utils.py` and API handlers).

**Accounts:**
- `GET /api/accounts`: List all accounts for the user.
    - `db_utils.list_user_accounts(user_id)`
- `POST /api/accounts`: Create a new account.
    - `db_utils.create_account(account_data)`
- `GET /api/accounts/{accountId}`: Get details for a specific account.
    - `db_utils.get_account(account_id)`
- `PUT /api/accounts/{accountId}`: Update an account.
    - `db_utils.update_account(account_id, user_id, update_data)`
- `DELETE /api/accounts/{accountId}`: Delete an account.
    - `db_utils.delete_account(account_id, user_id)`

**Transaction Files:**
- `GET /api/files?accountId={accountId}`: List files associated with a specific account.
    - `db_utils.list_account_files(account_id)` (ensure it checks user ownership if not already)
- `GET /api/files?unlinked=true`: List files uploaded by the user not linked to any account.
    - Needs a new `db_utils` function, e.g., `list_user_unlinked_files(user_id)` which queries for files where `userId` matches and `accountId` is null.
- `PUT /api/files/{fileId}/link`: Link a file to an account (body: `{ "accountId": "uuid" }`).
    - `db_utils.update_transaction_file(file_id, user_id, {"accountId": account_id})` or a more specific `db_utils.update_file_account_id(file_id, account_id)`.
- `PUT /api/files/{fileId}/unlink`: Unlink a file from an account (set `accountId` to null).
    - `db_utils.update_transaction_file(file_id, user_id, {"accountId": null})` or `db_utils.update_file_account_id(file_id, null)`.

**Transactions:**
- `GET /api/transactions?accountId={accountId}`: List all transactions for a specific account.
    - `db_utils.list_account_transactions(account_id, limit, last_evaluated_key)` (already exists, may need adjustments for filtering/sorting if done server-side).
    - Consider adding filters: `startDate`, `endDate`, `type`, `searchTerm`. `db_utils.list_user_transactions` is more feature-rich and could be adapted or a new function `list_account_transactions_filtered` could be made.

**Considerations from `db_utils.py`:**
- `checked_mandatory_account` and `checked_optional_account` will be useful for authorization.
- `list_account_files` exists but might need user authorization check for each file if not implicitly handled.
- A new function like `list_user_unlinked_files(user_id: str) -> List[TransactionFile]` will be needed. This would query the files table for items where `userId == user_id` and `accountId` is not set or is `None`.
- The `update_file_account_id` function can be used for linking/unlinking files.
- `list_account_transactions` exists for fetching transactions for an account.

This document provides a foundational design. Further details and refinements will occur during development. 