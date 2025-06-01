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

## 5. Backend API Endpoints (Refined based on Handler Review)

The following API endpoints are based on a review of the Lambda handlers (`account_operations.py` and `file_operations.py`). The `/api` prefix is typically managed by API Gateway.

**Accounts (`account_operations.py`):**
- `GET /accounts`: List all accounts for the user.
    - Maps to `list_user_accounts(user_id)`
- `POST /accounts`: Create a new account.
    - Maps to `create_account(account_data)`
- `GET /accounts/{id}`: Get details for a specific account (path parameter `id` is `accountId`).
    - Maps to `get_account(account_id)`
- `PUT /accounts/{id}`: Update an account (path parameter `id` is `accountId`).
    - Maps to `update_account(account_id, user_id, update_data)`
- `DELETE /accounts/{id}`: Delete an account (path parameter `id` is `accountId`).
    - Maps to `delete_account(account_id, user_id)`
- **(New)** `DELETE /accounts`: Deletes all accounts for the authenticated user.
- **(New)** `GET /accounts/{id}/timeline`: Retrieves a file timeline for a specific account.

**Transaction Files (Relevant endpoints from `account_operations.py` and `file_operations.py`):**
- `GET /accounts/{id}/files`: List files associated with a specific account (path parameter `id` is `accountId`).
    - Handled by `account_files_handler` in `account_operations.py`.
    - This is the chosen endpoint for listing files linked to a specific account.
- `GET /files`: List files for the user. When `accountId` query parameter is NOT provided, this is expected to list unlinked files.
    - Handled by `list_files_handler` in `file_operations.py`.
    - *Note: Confirmation needed that `get_files_for_user(user_id, None)` correctly fetches only files where `accountId` is null or not set.*
- `PUT /files/{fileId}/associate`: Link a file to an account (path parameter `fileId`). Expects `accountId` in the request body.
    - Handled by `associate_file_handler` in `file_operations.py`.
    - Maps to `update_transaction_file(file_id, user_id, {"accountId": account_id})` or similar.
- `PUT /files/{fileId}/unassociate`: Unlink a file from an account (path parameter `fileId`). Sets `accountId` to null.
    - Handled by `unassociate_file_handler` in `file_operations.py`.
    - Maps to `update_transaction_file(file_id, user_id, {"accountId": null})` or similar.
- **(New/Different context)** `POST /accounts/{id}/files`: This endpoint in `account_operations.py` is for initiating a new file upload process and associating it with an account, not for linking an *existing, unlinked* file.
- **(New/Different context)** `DELETE /accounts/{id}/files`: This endpoint in `account_operations.py` deletes *all* files associated with an account.

**Transactions (`account_operations.py`):**
- `GET /accounts/{id}/transactions`: List all transactions for a specific account (path parameter `id` is `accountId`).
    - Maps to `list_account_transactions(account_id, limit, last_evaluated_key)`.
    - Design doc notes potential for filters; this seems to be the primary endpoint.


**Original Design Considerations from `db_utils.py` (Still Relevant but map to updated endpoints):**
- `checked_mandatory_account` and `checked_optional_account` will be useful for authorization.
- `list_account_files` in `db_utils` is likely used by `GET /accounts/{id}/files` or `GET /files?accountId=...`.
- `list_user_unlinked_files(user_id: str)`: The functionality for this is likely within `get_files_for_user(user_id, None)` if the `GET /files` (no `accountId`) endpoint is used as inferred.
- `update_file_account_id` function: Likely used by `associate_file_handler` and `unassociate_file_handler`.
- `list_account_transactions` in `db_utils` is used by `GET /accounts/{id}/transactions`.

This document provides a foundational design. Further details and refinements will occur during development. 