# New UI: Transactions Section - Main Content Area

This document describes the main content area of the modern finance application when the "Transactions" section is selected from the sidebar navigation. This area will utilize a tabbed interface to organize different transaction-related functionalities, ensuring a modern, fresh, and intuitive user experience.

## 1. Overview

The Transactions section is central to managing all financial transactions. It aims to provide a comprehensive yet easy-to-navigate interface for users to view, add, edit, categorize, and analyze their financial activities. It will also include tools for importing transaction data and managing how transactions are categorized automatically.

## 2. Tabbed Navigation

Upon selecting "Transactions" from the sidebar, the main content area will display a set of tabs. The default active tab will be "Transactions List".

*   **Primary Tabs:**
    *   `Transactions List`: View, filter, search, and manage individual transactions.
    *   `Category Management`: Define and manage transaction categories, including setting up rules for auto-categorization.
    *   `Statements & Imports`: Import transaction files (e.g., bank statements) and view import history.
*   **Secondary Action Button (always visible in header, outside tabs):**
    *   `[+ Add Transaction]` button: Opens a modal or a dedicated form for manually adding a new transaction. This is globally accessible within the Transactions section.

## 3. Tab 1: Transactions List

This tab is for day-to-day transaction management.

### 3.1. Filtering and Search Controls

Located prominently at the top of this tab's content area.

*   **Date Range Picker:** Select common ranges (This Month, Last Month, YTD, Custom) or specific dates.
*   **Account Filter:** Multi-select dropdown for accounts.
*   **Category Filter:** Multi-select dropdown or typeahead for categories (including "Uncategorized").
*   **Transaction Type Filter:** Buttons/dropdown for `All | Income | Expenses | Transfers`.
*   **Search Bar:** Free-text search for description, payee, notes, amount.
*   `[Apply Filters]` and `[Clear Filters]` buttons, styled for a modern look (e.g., subtle icons, clear visual hierarchy).

### 3.2. Transaction Table

A responsive table displaying transactions with a clean, modern aesthetic (e.g., good use of whitespace, clear typography, subtle row highlighting on hover).

*   **Columns:** `Checkbox`, `Date`, `Description/Payee`, `Category` (clickable for quick change), `Account`, `Amount` (color-coded for income/expense), `Actions` (e.g., edit icon).
*   **Sorting:** All columns sortable.
*   **Pagination:** Modern pagination controls if many transactions.
*   **Inline Editing (Quick Change Category):** Clicking the category in a row opens a popover/dropdown to quickly change it.
*   **Expandable Rows (Optional):** For notes or split details.

### 3.3. Edit Transaction Dialog (Modal)

Opened by clicking an "Edit" icon on a transaction row.

*   **Modern Design:** Clean layout, clear input fields, intuitive controls.
*   **Fields:** All transaction attributes (Date, Description/Payee, Amount, Currency, Account, Notes).
*   **Category Assignment:** A prominent, easy-to-use dropdown or searchable selector for assigning/changing the category.
    *   Option to `[+ Create New Category]` directly from this dialog if needed (opens a smaller, focused category creation modal).
*   **Split Transaction Interface:** If applicable, a clean way to split one transaction into multiple categories/amounts.
*   **Actions:** `[Save]`, `[Cancel]`, `[Delete]`. Buttons styled for clarity (e.g., primary for save, secondary for cancel).

### 3.4. Bulk Actions Bar

Appears contextually (e.g., subtle bar at top/bottom of table) when transactions are selected via checkbox.

*   `[Categorize Selected]` (opens a category selector modal), `[Delete Selected]`, `[Export Selected]`. Modern, icon-based buttons with tooltips could be used.

## 4. Tab 2: Category Management

This tab allows users to control how their transactions are categorized, including setting up smart rules.

### 4.1. Category List & CRUD

*   **Display:** A clean table or card list showing existing categories: `Name`, `Type (Income/Expense)`, `Assigned Rules Count`.
*   **Actions per Category:** `Edit`, `Delete` icons.
*   **`[+ Add New Category]` Button:** Opens a modal/form for creating a new category.
    *   **Fields:** Category Name, Category Type (Income, Expense), Parent Category (optional, for sub-categories), Icon (optional), Color (optional).

### 4.2. Category Rules Engine

This is a key feature for a modern experience, allowing users to automate categorization.

*   **Interface:** When adding/editing a category, a section for "Automation Rules".
*   **Rule Definition:**
    *   Users can add one or more rules per category.
    *   Each rule consists of:
        *   `Field to Match`: Dropdown (e.g., "Description/Payee", "Notes", "Amount").
        *   `Condition`: Dropdown (e.g., "Contains", "Starts With", "Ends With", "Equals", "Regex Match", "Greater Than", "Less Than").
        *   `Value`: Text input for the value/pattern (e.g., "AMAZON", "^UBER TRIP", "\d{2}/\d{2}").
    *   Multiple conditions for a rule could be combined with AND/OR logic.
*   **Assisted Rule Generation ('Match Like This'):**
    *   To simplify regex creation, users can initiate rule generation from the "Transactions List" tab.
    *   After filtering transactions (e.g., by a keyword in the description), a button like `[Create Rule from Filter]` or `[Match Like This]` would be available.
    *   Activating this feature would:
        1.  Send the relevant transaction descriptions (from the filtered set) to the backend.
        2.  The backend analyzes these descriptions to generate a candidate regular expression that aims to match similar future transactions.
        3.  The user is then taken to the rule creation interface within "Category Management", with the "Field to Match" (e.g., "Description/Payee"), "Condition" ("Regex Match"), and the generated "Value" (the regex) pre-filled.
    *   This allows users to create powerful rules based on observed patterns without needing to write regex manually from scratch. They can then refine the suggested regex if needed.
    *   (This implies a new backend endpoint, e.g., `POST /api/rules/generate-regex-from-pattern` or similar, to handle the regex generation logic.)
*   **Testing Area (Optional but Recommended):** A small input where a user can paste a sample transaction description to see if it would match the defined rules for the current category.
*   **Priority/Ordering:** If multiple categories have rules that could match a single transaction, a system for prioritizing rules (e.g., order of categories, more specific rules first) might be needed in advanced scenarios.
*   **Feedback:** Clear indication of how many rules are set for each category in the list view.

## 5. Tab 3: Statements & Imports

This tab centralizes file import operations and history.

### 5.1. Import Workflow (Initiated here)

*   **Dedicated Page/Section:** This tab will host the multi-step import process.
*   **Step 1: File Upload & Account Selection**
    *   **Modern UI:** Large, clear drag-and-drop area at the top of the page with an account selected and below it a list of files previously imported and the mapping for each. uploading a new file or selecting existing will enable the button.
    *   Supported formats clearly indicated with icons (OFX, QFX, CSV).
    *   Account selection dropdown.
    *   `[Next/Preview]` button.
*   **Step 2: Preview, Mapping (CSV), & Confirmation**
    *   **Clean Table Preview:** Parsed transactions shown in a clear table.
    *   **Intuitive CSV Mapping:** If CSV, an interactive interface to map columns. Visual cues for matched/unmatched columns. Option to save mapping for the source.
    *   **Clear Duplicate Handling:** Duplicates highlighted, with clear options (`Skip`, `Import`, `Overwrite` - use with caution).
    *   Summary of import (new, duplicates).
    *   `[Complete Import]`, `[Cancel]` buttons.
*   **Step 3: Completion Summary**
    *   Clear success/error message. Link to view imported transactions.

### 5.2. Import History

*   A table listing previously imported files: `Date Imported`, `File Name`, `Source Account`, `Status (Success/Failed)`, `Transactions Imported Count`, `Link to View These Transactions`.

## 6. Other Potential Tabs (Future Considerations)

*   **Recurring Transactions:** Manage scheduled/repeating income and expenses.
*   **Transaction Rules (Advanced):** Beyond category regex, more complex rule creation for tags, flags, or other actions.

## 7. General UI/UX Principles

*   **Modern & Fresh Aesthetic:** Clean lines, ample whitespace, intuitive iconography, smooth transitions, and a cohesive color palette.
*   **Responsiveness:** Ensure the entire section and its tabs work flawlessly on various screen sizes.
*   **Performance:** Fast loading times, especially for the transaction list and filtering.
*   **Feedback:** Clear visual feedback for user actions (e.g., loading states, success/error messages).

This revised structure should provide a more organized and powerful experience for managing transactions. Wireframes and prototypes for each tab and modal would be the next logical step.

## 8. API Endpoint Analysis (for Tab 1: Transactions List)

This section outlines the backend API endpoints required to support the "Transactions List" tab, specifically its filtering controls (3.1) and transaction table (3.2).

### 8.1. Data for Filtering Controls

*   **Account Filter:**
    *   **Endpoint:** `GET /api/accounts`
    *   **Purpose:** Fetch a list of the user's financial accounts (ID and name).
    *   **Example Response:** `[{ "id": "acc_123", "name": "Checking Account" }, ...]`
*   **Category Filter:**
    *   **Endpoint:** `GET /api/categories`
    *   **Purpose:** Fetch a list of all available transaction categories (ID and name).
    *   **Example Response:** `[{ "id": "cat_abc", "name": "Groceries" }, ...]`

### 8.2. Main Transaction Data & Operations

*   **Fetching Transactions (with Filtering, Sorting, Pagination):**
    *   **Endpoint:** `GET /api/transactions_for_user` (or `/api/transactions`)
    *   **Purpose:** Fetch the list of transactions based on user-selected criteria.
    *   **Key Parameters:**
        *   `page` (integer, e.g., 1)
        *   `pageSize` (integer, e.g., 25)
        *   `startDate` (date string, e.g., "2023-01-01")
        *   `endDate` (date string, e.g., "2023-01-31")
        *   `accountIds` (comma-separated string, e.g., "acc_123,acc_456")
        *   `categoryIds` (comma-separated string, e.g., "cat_abc,cat_xyz")
        *   `transactionType` (string, e.g., "income", "expense", "transfer", "all")
        *   `searchTerm` (string, e.g., "coffee shop")
        *   `sortBy` fixed to date
        *   `sortOrder` (string, e.g., "asc", "desc")
    *   **Example Response Structure:**
        ```json
        {
          "transactions": [
            {
              "id": "txn_789",
              "date": "2023-10-26",
              "description": "Starbucks",
              "payee": "Starbucks #123",
              "category": { "id": "cat_food", "name": "Food & Drink" },
              "account": { "id": "acc_123", "name": "Checking Account" },
              "amount": -5.75,
              "currency": "USD",
              "type": "expense",
              "notes": "Morning coffee",
              "isSplit": false
            },
            // ... more transactions
          ],
          "pagination": {
            "currentPage": 1,
            "pageSize": 25,
            "totalItems": 150,
            "totalPages": 6
          }
        }
        ```

*   **Quick Category Update (Inline Edit):**
    *   **Endpoint:** `PUT /api/transactions/{transactionId}/category`
    *   **Purpose:** Update the category of a single transaction.
    *   **Request Body:** `{ "categoryId": "new_cat_id" }`
    *   **Response:** The updated transaction object or a success status.

### 8.3. Related Endpoints (for Add/Edit/Delete Modals via Table Actions)

While the full "Edit Transaction Dialog" (3.3) and "Add Transaction" functionality are separate, actions from the transaction table will invoke these:

*   **Fetch Full Transaction Details (for Edit Modal):**
    *   **Endpoint:** `GET /api/transactions/{transactionId}`
*   **Add New Transaction:**
    *   **Endpoint:** `POST /api/transactions`
*   **Update Full Transaction (from Edit Modal):**
    *   **Endpoint:** `PUT /api/transactions/{transactionId}`
*   **Delete Transaction:**
    *   **Endpoint:** `DELETE /api/transactions/{transactionId}` 