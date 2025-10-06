# Breadcrumb Navigation System Design

## Overview

The breadcrumb navigation system provides hierarchical navigation with persistent state management, supporting complex navigation flows including forward/backward navigation, session persistence, and URL resumability. The system handles both simple linear navigation and complex branching scenarios.

## Core Concepts

### Breadcrumb Structure

Each breadcrumb item contains:
```typescript
interface BreadcrumbItem {
    label: string;           // Display text
    action: () => void;      // Navigation function
    level: number;           // Hierarchical depth (0-based)
    context?: {              // Optional context data
        accountId?: string;
        fileId?: string;
        transactionId?: string;
        categoryId?: string;
        filter?: string;
        viewType?: string;
    };
    timestamp: number;       // When this breadcrumb was created
    sessionId?: string;      // Reference to session state if complex
}
```

### Navigation State Management

The system maintains multiple layers of state:

1. **Current Breadcrumb Chain**: Active navigation path
2. **Navigation History**: Forward/backward navigation stack
3. **Session Store**: Persistent complex states
4. **Context Cache**: Frequently accessed navigation contexts

## Navigation Flow Examples

### Example 1: Linear Account Navigation
```
Accounts → My Bank → Transactions → Transaction #123
Level 0  → Level 1 → Level 2      → Level 3

Breadcrumb Chain:
[
  { label: "Accounts", level: 0, action: goToAccountList() },
  { label: "My Bank", level: 1, context: { accountId: "acc123" } },
  { label: "Transactions", level: 2, context: { accountId: "acc123", viewType: "transactions" } },
  { label: "Transaction #123", level: 3, context: { accountId: "acc123", transactionId: "tx123" } }
]
```

### Example 2: Complex Branching Navigation
```
Accounts → My Bank → Transactions → Transaction #123 → Category: Food → 
All Food Transactions → Different Account → New Transactions

Navigation Path:
Level 0: Accounts
Level 1: My Bank (acc123)
Level 2: Transactions (acc123)
Level 3: Transaction #123 (acc123, tx123)
Level 4: Category: Food (acc123, tx123, category: food)
Level 5: All Food Transactions (filter: category=food)
Level 6: Savings Account (acc456)
Level 7: Savings Transactions (acc456)
```

## Forward and Backward Navigation

### Backward Navigation Behavior

#### 1. Single Step Back
```typescript
// Current: Accounts > My Bank > Transactions > Transaction #123
// User clicks back or presses Alt+←
// Result: Accounts > My Bank > Transactions

breadcrumbChain.pop(); // Remove last item
navigateToLevel(breadcrumbChain.length - 1);
```

#### 2. Multi-Level Back (Breadcrumb Click)
```typescript
// Current: Accounts > My Bank > Transactions > Transaction #123 > Category
// User clicks "My Bank" breadcrumb
// Result: Accounts > My Bank

breadcrumbChain = breadcrumbChain.slice(0, targetLevel + 1);
navigateToLevel(targetLevel);
```

#### 3. Context-Aware Back Navigation
```typescript
// When backing out of complex states, preserve relevant context
// Current: Account > Transactions (filtered by category=food, sorted by date)
// Back to: Account (preserve some context like date range, lose category filter)

const preserveContext = (fromLevel: number, toLevel: number) => {
    const contextToPreserve = ['dateRange', 'sortOrder'];
    const contextToRemove = ['categoryFilter', 'searchQuery'];
    
    return filterContext(currentContext, contextToPreserve);
};
```

### Forward Navigation Behavior

#### 1. Linear Forward Navigation
```typescript
// Current: Accounts > My Bank
// User navigates to Transactions
// Result: Accounts > My Bank > Transactions

breadcrumbChain.push({
    label: "Transactions",
    level: breadcrumbChain.length,
    context: { accountId: "acc123", viewType: "transactions" },
    action: () => navigateToTransactions("acc123"),
    timestamp: Date.now()
});
```

#### 2. Branching Navigation
```typescript
// Current: Accounts > My Bank > Transaction #123
// User navigates to Category view
// Result: Accounts > My Bank > Transaction #123 > Category: Food

// This creates a new branch in the navigation tree
breadcrumbChain.push({
    label: "Category: Food",
    level: breadcrumbChain.length,
    context: { 
        accountId: "acc123", 
        transactionId: "tx123", 
        categoryId: "food",
        viewType: "category"
    },
    action: () => navigateToCategoryView("acc123", "tx123", "food"),
    timestamp: Date.now()
});
```

#### 3. Cross-Context Navigation
```typescript
// Current: Account A > Transactions > Category: Food
// User navigates to Account B from category view
// Result: Account A > Transactions > Category: Food > Account B

// This preserves the path that led to the cross-navigation
breadcrumbChain.push({
    label: "Savings Account",
    level: breadcrumbChain.length,
    context: { 
        accountId: "acc456",
        previousContext: { 
            fromAccountId: "acc123", 
            fromCategory: "food" 
        }
    },
    action: () => navigateToAccount("acc456"),
    timestamp: Date.now()
});
```

## Breadcrumb Storage and Persistence

### 1. Session-Based Storage

#### Short-Term State (Navigation Store)
```typescript
interface NavigationState {
    currentBreadcrumb: BreadcrumbItem[];
    navigationHistory: BreadcrumbItem[][];  // Stack of previous breadcrumb states
    forwardHistory: BreadcrumbItem[][];     // Stack for forward navigation
    maxHistorySize: number;                 // Default: 50
}
```

#### Long-Term Persistence (Session Store)
```typescript
interface BreadcrumbSession {
    sessionId: string;
    breadcrumbChain: BreadcrumbItem[];
    navigationHistory: BreadcrumbItem[][];
    createdAt: number;
    lastAccessed: number;
    accessCount: number;
    metadata: {
        totalLevels: number;
        maxDepth: number;
        branchPoints: number[];  // Levels where branching occurred
        crossContextNavigations: number;
    };
}
```

### 2. URL Generation Strategy

#### Simple Breadcrumbs (Traditional URLs)
```typescript
// Linear navigation with ≤ 4 levels
// Accounts > My Bank > Transactions > Transaction #123
URL: /accounts/acc123/transactions/tx123

Breadcrumb reconstruction from URL:
[
    { label: "Accounts", level: 0, action: () => navigate("/accounts") },
    { label: "My Bank", level: 1, action: () => navigate("/accounts/acc123") },
    { label: "Transactions", level: 2, action: () => navigate("/accounts/acc123/transactions") },
    { label: "Transaction #123", level: 3, action: () => navigate("/accounts/acc123/transactions/tx123") }
]
```

#### Complex Breadcrumbs (Session URLs)
```typescript
// Complex navigation with > 4 levels or branching
// Accounts > My Bank > Transactions > Transaction #123 > Category: Food > All Food Transactions
URL: /accounts?s=ABC123XY

Session ABC123XY contains:
{
    breadcrumbChain: [
        { label: "Accounts", level: 0, ... },
        { label: "My Bank", level: 1, context: { accountId: "acc123" } },
        { label: "Transactions", level: 2, context: { accountId: "acc123" } },
        { label: "Transaction #123", level: 3, context: { accountId: "acc123", transactionId: "tx123" } },
        { label: "Category: Food", level: 4, context: { categoryId: "food", fromTransaction: "tx123" } },
        { label: "All Food Transactions", level: 5, context: { filter: "category=food" } }
    ],
    navigationHistory: [...],
    currentState: { ... }
}
```

### 3. Session Resumability

#### URL Sharing and Bookmarking
```typescript
// User shares: /accounts?s=ABC123XY
// Recipient opens URL:

const resumeSession = (sessionId: string) => {
    const session = sessionStore.getSession(sessionId);
    if (!session) {
        // Graceful fallback to root
        return navigateToAccountList();
    }
    
    // Restore complete navigation state
    restoreBreadcrumbChain(session.breadcrumbChain);
    restoreNavigationHistory(session.navigationHistory);
    applyCurrentState(session.currentState);
    
    // Update session access tracking
    sessionStore.updateAccess(sessionId);
};
```

#### Cross-Device Continuity
```typescript
// Sessions persist across devices via localStorage/sessionStorage
const persistSession = (session: BreadcrumbSession) => {
    // Store in localStorage for cross-session persistence
    localStorage.setItem(`breadcrumb_session_${session.sessionId}`, JSON.stringify(session));
    
    // Store in sessionStorage for current session
    sessionStorage.setItem('current_breadcrumb_session', session.sessionId);
};
```

## Entity-Based Branching Strategy

### Dedicated Entity Endpoints

When branching to entity views (categories, transactions, files), the system switches to **entity-based endpoints** that provide full entity context and navigation options, regardless of the originating context.

This applies to:
- **Categories**: `/categories/:categoryId`
- **Transactions**: `/transactions/:transactionId` 
- **Transaction Files**: `/files/:fileId`

#### **Why Entity-Based Endpoints?**

Instead of keeping entity views within their originating context:

**Categories:**
```typescript
// ❌ AVOID: Category view tied to specific transaction
/accounts/acc123/transactions/tx456?view=category&categoryId=food

// ✅ PREFER: Dedicated category endpoint with context
/categories/food?fromAccount=acc123&fromTransaction=tx456
```

**Transactions:**
```typescript
// ❌ AVOID: Transaction view tied to specific account/file
/accounts/acc123/transactions/tx456
/files/file789/transactions/tx456

// ✅ PREFER: Dedicated transaction endpoint with context
/transactions/tx456?fromAccount=acc123
/transactions/tx456?fromFile=file789
```

**Transaction Files:**
```typescript
// ❌ AVOID: File view tied to specific account
/accounts/acc123/files/file789

// ✅ PREFER: Dedicated file endpoint with context
/files/file789?fromAccount=acc123
```

**Benefits:**
- **Unified entity experience**: Same interface regardless of entry point
- **Full navigation options**: Access to all entity-related actions
- **Consistent URL structure**: Entities always at their dedicated endpoints
- **Better SEO**: Entity content has dedicated URLs
- **Reduced complexity**: No entity views scattered across different endpoints
- **Cross-entity navigation**: Easy to navigate between related entities

#### **Entity Branch Implementation**

**Category Branching:**
```typescript
// User navigates from transaction to category
// FROM: /accounts/acc123/transactions/tx456
// TO:   /categories/food?fromAccount=acc123&fromTransaction=tx456

const branchToCategory = (categoryId: string, originContext: NavigationContext) => {
    const categoryUrl = `/categories/${categoryId}`;
    const contextParams = new URLSearchParams();
    
    // Preserve origin context for breadcrumb and back navigation
    if (originContext.accountId) contextParams.set('fromAccount', originContext.accountId);
    if (originContext.transactionId) contextParams.set('fromTransaction', originContext.transactionId);
    if (originContext.fileId) contextParams.set('fromFile', originContext.fileId);
    
    navigate(`${categoryUrl}?${contextParams.toString()}`);
};
```

**Transaction Branching:**
```typescript
// User navigates to transaction from different contexts
// FROM: /accounts/acc123/transactions (account context)
// FROM: /files/file789/transactions (file context)  
// FROM: /categories/food/transactions (category context)
// TO:   /transactions/tx456?fromAccount=acc123 | ?fromFile=file789 | ?fromCategory=food

const branchToTransaction = (transactionId: string, originContext: NavigationContext) => {
    const transactionUrl = `/transactions/${transactionId}`;
    const contextParams = new URLSearchParams();
    
    // Preserve origin context
    if (originContext.accountId) contextParams.set('fromAccount', originContext.accountId);
    if (originContext.fileId) contextParams.set('fromFile', originContext.fileId);
    if (originContext.categoryId) contextParams.set('fromCategory', originContext.categoryId);
    if (originContext.searchQuery) contextParams.set('fromSearch', originContext.searchQuery);
    
    navigate(`${transactionUrl}?${contextParams.toString()}`);
};
```

**File Branching:**
```typescript
// User navigates to file from different contexts
// FROM: /accounts/acc123/files (account context)
// FROM: /transactions/tx456 (transaction context)
// TO:   /files/file789?fromAccount=acc123 | ?fromTransaction=tx456

const branchToFile = (fileId: string, originContext: NavigationContext) => {
    const fileUrl = `/files/${fileId}`;
    const contextParams = new URLSearchParams();
    
    // Preserve origin context
    if (originContext.accountId) contextParams.set('fromAccount', originContext.accountId);
    if (originContext.transactionId) contextParams.set('fromTransaction', originContext.transactionId);
    if (originContext.categoryId) contextParams.set('fromCategory', originContext.categoryId);
    
    navigate(`${fileUrl}?${contextParams.toString()}`);
};
```

#### **Entity Navigation Options**

**Category Navigation** at `/categories/food`:
```typescript
const CategoryPage = () => {
    const { categoryId } = useParams();
    const originContext = useOriginContext();
    
    return (
        <CategoryView 
            categoryId={categoryId}
            navigationOptions={{
                // Category-specific actions
                viewAllTransactions: () => navigate(`/categories/${categoryId}/transactions`),
                viewByAccount: () => navigate(`/categories/${categoryId}/accounts`),
                viewTrends: () => navigate(`/categories/${categoryId}/analytics`),
                compareCategories: () => navigate(`/categories/compare?include=${categoryId}`),
                relatedCategories: () => navigate(`/categories/${categoryId}/related`),
                
                // Back to origin context
                backToOrigin: () => navigateToOriginContext(originContext)
            }}
        />
    );
};
```

**Transaction Navigation** at `/transactions/tx456`:
```typescript
const TransactionPage = () => {
    const { transactionId } = useParams();
    const originContext = useOriginContext();
    
    return (
        <TransactionView 
            transactionId={transactionId}
            navigationOptions={{
                // Transaction-specific actions
                viewCategory: (categoryId) => navigate(`/categories/${categoryId}?fromTransaction=${transactionId}`),
                viewAccount: (accountId) => navigate(`/accounts/${accountId}?fromTransaction=${transactionId}`),
                viewFile: (fileId) => navigate(`/files/${fileId}?fromTransaction=${transactionId}`),
                viewSimilarTransactions: () => navigate(`/transactions?similar=${transactionId}`),
                editTransaction: () => navigate(`/transactions/${transactionId}/edit`),
                
                // Cross-transaction navigation
                nextTransaction: () => navigate(`/transactions/${getNextTransactionId()}`),
                previousTransaction: () => navigate(`/transactions/${getPreviousTransactionId()}`),
                
                // Back to origin context
                backToOrigin: () => navigateToOriginContext(originContext)
            }}
        />
    );
};
```

**File Navigation** at `/files/file789`:
```typescript
const FilePage = () => {
    const { fileId } = useParams();
    const originContext = useOriginContext();
    
    return (
        <FileView 
            fileId={fileId}
            navigationOptions={{
                // File-specific actions
                viewTransactions: () => navigate(`/files/${fileId}/transactions`),
                viewAccounts: () => navigate(`/files/${fileId}/accounts`),
                viewCategories: () => navigate(`/files/${fileId}/categories`),
                downloadFile: () => downloadFile(fileId),
                reprocessFile: () => reprocessFile(fileId),
                
                // File analysis
                viewImportSummary: () => navigate(`/files/${fileId}/summary`),
                viewProcessingLog: () => navigate(`/files/${fileId}/log`),
                compareFiles: () => navigate(`/files/compare?include=${fileId}`),
                
                // Back to origin context
                backToOrigin: () => navigateToOriginContext(originContext)
            }}
        />
    );
};
```

#### **React Router Structure for All Entities**

```typescript
<Routes>
    {/* Account-based routes (for account-centric navigation) */}
    <Route path="accounts" element={<AccountsPage />} />
    <Route path="accounts/:accountId" element={<AccountsPage />} />
    
    {/* Entity-based branching routes */}
    
    {/* Categories */}
    <Route path="categories" element={<CategoriesPage />} />
    <Route path="categories/:categoryId" element={<CategoryDetailPage />} />
    <Route path="categories/:categoryId/transactions" element={<CategoryTransactionsPage />} />
    <Route path="categories/:categoryId/accounts" element={<CategoryAccountsPage />} />
    <Route path="categories/:categoryId/analytics" element={<CategoryAnalyticsPage />} />
    <Route path="categories/compare" element={<CategoryComparePage />} />
    
    {/* Transactions */}
    <Route path="transactions" element={<TransactionsPage />} />
    <Route path="transactions/:transactionId" element={<TransactionDetailPage />} />
    <Route path="transactions/:transactionId/edit" element={<TransactionEditPage />} />
    <Route path="transactions/compare" element={<TransactionComparePage />} />
    
    {/* Files */}
    <Route path="files" element={<FilesPage />} />
    <Route path="files/:fileId" element={<FileDetailPage />} />
    <Route path="files/:fileId/transactions" element={<FileTransactionsPage />} />
    <Route path="files/:fileId/accounts" element={<FileAccountsPage />} />
    <Route path="files/:fileId/categories" element={<FileCategoriesPage />} />
    <Route path="files/:fileId/summary" element={<FileSummaryPage />} />
    <Route path="files/:fileId/log" element={<FileProcessingLogPage />} />
    <Route path="files/compare" element={<FileComparePage />} />
    
    {/* Other routes */}
    <Route path="analytics" element={<AnalyticsView />} />
    <Route path="backup" element={<FZIPManagementView />} />
</Routes>
```

#### **Breadcrumb Representation**

```typescript
// Navigation: Accounts > My Bank > Transaction #456 > Category: Food
// URL: /categories/food?fromAccount=acc123&fromTransaction=tx456

Breadcrumb Chain:
[
    { label: "Accounts", level: 0, action: () => navigate("/accounts") },
    { label: "My Bank", level: 1, action: () => navigate("/accounts/acc123") },
    { label: "Transaction #456", level: 2, action: () => navigate("/accounts/acc123/transactions/tx456") },
    { label: "Category: Food", level: 3, action: () => navigate("/categories/food") }
]

// The category level provides full category navigation context
// while preserving the path that led to it
```

#### **Session URL Handling for Complex Category Branches**

```typescript
// For complex category navigation that exceeds URL limits:
// Categories > Food > Related Categories > Dining > Compare with Entertainment > Analytics

URL: /categories?s=CAT123XY

Session CAT123XY contains:
{
    breadcrumbChain: [
        { label: "Categories", level: 0, context: { viewType: "categories" } },
        { label: "Food", level: 1, context: { categoryId: "food" } },
        { label: "Related Categories", level: 2, context: { categoryId: "food", view: "related" } },
        { label: "Dining", level: 3, context: { categoryId: "dining", parentCategory: "food" } },
        { label: "Compare with Entertainment", level: 4, context: { compare: ["dining", "entertainment"] } },
        { label: "Analytics", level: 5, context: { view: "analytics", categories: ["dining", "entertainment"] } }
    ],
    originContext: { fromAccount: "acc123", fromTransaction: "tx456" }
}
```

## Advanced Navigation Scenarios

### 1. Circular Navigation Detection
```typescript
// Detect when user navigates in circles
// Accounts > My Bank > Transactions > My Bank > Transactions
const detectCircularNavigation = (newBreadcrumb: BreadcrumbItem) => {
    const recentItems = breadcrumbChain.slice(-5); // Check last 5 items
    const duplicates = recentItems.filter(item => 
        item.context?.accountId === newBreadcrumb.context?.accountId &&
        item.level === newBreadcrumb.level
    );
    
    if (duplicates.length > 0) {
        // Offer to shortcut or show warning
        showCircularNavigationWarning();
    }
};
```

### 2. Smart Breadcrumb Truncation
```typescript
// For very long breadcrumb chains
const truncateBreadcrumbs = (breadcrumbs: BreadcrumbItem[], maxVisible: number = 5) => {
    if (breadcrumbs.length <= maxVisible) {
        return breadcrumbs;
    }
    
    // Always show: Root + ... + Last 3 items
    return [
        breadcrumbs[0],                                    // Root
        { label: "...", level: -1, action: expandBreadcrumbs }, // Expand button
        ...breadcrumbs.slice(-3)                           // Last 3 items
    ];
};
```

### 3. Context-Aware Navigation Suggestions
```typescript
// Suggest related navigation based on current breadcrumb
const getNavigationSuggestions = (currentBreadcrumb: BreadcrumbItem[]) => {
    const currentContext = currentBreadcrumb[currentBreadcrumb.length - 1].context;
    
    if (currentContext?.transactionId) {
        return [
            { label: "Similar Transactions", action: () => findSimilarTransactions() },
            { label: "Same Category", action: () => filterByCategory() },
            { label: "Same Date Range", action: () => filterByDateRange() }
        ];
    }
    
    if (currentContext?.accountId) {
        return [
            { label: "Account Analytics", action: () => showAccountAnalytics() },
            { label: "Recent Activity", action: () => showRecentActivity() },
            { label: "Compare Accounts", action: () => showAccountComparison() }
        ];
    }
};
```

## Implementation Details

### 1. Breadcrumb Component Integration
```typescript
const Breadcrumb: React.FC = () => {
    const { breadcrumb, navigationHistory } = useNavigationStore();
    const { createSessionUrl, isSessionUrl } = useSessionRouting();
    
    // Handle breadcrumb click
    const handleBreadcrumbClick = (item: BreadcrumbItem, index: number) => {
        // Save current state to history before navigating
        saveToNavigationHistory(breadcrumb);
        
        // Truncate breadcrumb to clicked level
        const newBreadcrumb = breadcrumb.slice(0, index + 1);
        setBreadcrumb(newBreadcrumb);
        
        // Execute navigation
        item.action();
    };
    
    // Handle forward/back navigation
    const handleBackNavigation = () => {
        if (navigationHistory.length > 0) {
            const previousState = navigationHistory.pop();
            forwardHistory.push(breadcrumb);
            setBreadcrumb(previousState);
        }
    };
};
```

### 2. Session Management
```typescript
const BreadcrumbSessionManager = {
    // Create session when breadcrumb becomes complex
    createSession: (breadcrumb: BreadcrumbItem[]) => {
        const sessionId = generateSessionId();
        const session: BreadcrumbSession = {
            sessionId,
            breadcrumbChain: breadcrumb,
            navigationHistory: getNavigationHistory(),
            createdAt: Date.now(),
            lastAccessed: Date.now(),
            accessCount: 1,
            metadata: analyzeBreadcrumbComplexity(breadcrumb)
        };
        
        sessionStore.saveSession(session);
        return sessionId;
    },
    
    // Update session on navigation
    updateSession: (sessionId: string, newBreadcrumb: BreadcrumbItem[]) => {
        const session = sessionStore.getSession(sessionId);
        if (session) {
            session.breadcrumbChain = newBreadcrumb;
            session.navigationHistory = getNavigationHistory();
            session.lastAccessed = Date.now();
            session.accessCount++;
            sessionStore.saveSession(session);
        }
    }
};
```

## Benefits and Use Cases

### 1. Long Session Continuity
- Users can navigate deeply through complex data relationships
- Sessions persist across browser refreshes and device switches
- Navigation state is fully recoverable from URLs

### 2. Collaborative Navigation
- Team members can share complex navigation states via URLs
- Bookmarkable deep-dive analysis paths
- Reproducible navigation flows for support and training

### 3. Performance Optimization
- LRU cache keeps frequently accessed navigation states in memory
- Session compression reduces URL length and complexity
- Smart truncation maintains usability with deep navigation

### 4. User Experience Enhancement
- Visual breadcrumb trail shows navigation context
- Multiple ways to navigate backward (click, keyboard, buttons)
- Context-aware suggestions for related navigation

## Entity List Views with Scoped Filtering

### Scoped Entity Lists

Entity list views need to handle different scopes and filter criteria, providing context-aware filtering while maintaining the entity-centric approach.

#### **Transaction List Scoping**

**Global Transactions:**
```typescript
// All transactions across all accounts
URL: /transactions
Breadcrumb: [{ label: "All Transactions", level: 0 }]
```

**Account-Scoped Transactions:**
```typescript
// All transactions for a specific account
URL: /transactions?account=acc123
Breadcrumb: [
    { label: "All Transactions", level: 0, action: () => navigate("/transactions") },
    { label: "My Bank Transactions", level: 1 }
]
```

**Category-Scoped Transactions:**
```typescript
// All transactions in a specific category
URL: /transactions?category=food
Breadcrumb: [
    { label: "All Transactions", level: 0, action: () => navigate("/transactions") },
    { label: "Food Transactions", level: 1 }
]
```

**File-Scoped Transactions:**
```typescript
// All transactions from a specific file
URL: /transactions?file=file789
Breadcrumb: [
    { label: "All Transactions", level: 0, action: () => navigate("/transactions") },
    { label: "File_Jan2024.csv Transactions", level: 1 }
]
```

**Multi-Scoped Transactions:**
```typescript
// Transactions for specific account AND category
URL: /transactions?account=acc123&category=food
// OR if URL gets too long: /transactions?s=ABC123

Breadcrumb: [
    { label: "All Transactions", level: 0, action: () => navigate("/transactions") },
    { label: "My Bank", level: 1, action: () => navigate("/transactions?account=acc123") },
    { label: "Food Transactions", level: 2 }
]
```

#### **File List Scoping**

**Global Files:**
```typescript
// All files across all accounts
URL: /files
Breadcrumb: [{ label: "All Files", level: 0 }]
```

**Account-Scoped Files:**
```typescript
// All files for a specific account
URL: /files?account=acc123
Breadcrumb: [
    { label: "All Files", level: 0, action: () => navigate("/files") },
    { label: "My Bank Files", level: 1 }
]
```

**Date-Range Scoped Files:**
```typescript
// Files within a specific date range
URL: /files?dateRange=2024-01-01,2024-01-31
Breadcrumb: [
    { label: "All Files", level: 0, action: () => navigate("/files") },
    { label: "January 2024 Files", level: 1 }
]
```

#### **Category List Scoping**

**Global Categories:**
```typescript
// All categories across all accounts
URL: /categories
Breadcrumb: [{ label: "All Categories", level: 0 }]
```

**Account-Scoped Categories:**
```typescript
// Categories used by a specific account
URL: /categories?account=acc123
Breadcrumb: [
    { label: "All Categories", level: 0, action: () => navigate("/categories") },
    { label: "My Bank Categories", level: 1 }
]
```

### Implementation Strategy

#### **Scoped List Component Pattern**

```typescript
const TransactionsPage: React.FC = () => {
    const location = useLocation();
    const searchParams = new URLSearchParams(location.search);
    
    // Extract scope parameters
    const scope = {
        accountId: searchParams.get('account'),
        categoryId: searchParams.get('category'),
        fileId: searchParams.get('file'),
        dateRange: searchParams.get('dateRange'),
        searchQuery: searchParams.get('search')
    };
    
    // Generate breadcrumb based on scope
    const breadcrumb = generateScopedBreadcrumb('transactions', scope);
    
    // Generate page title and filters
    const pageTitle = generateScopedTitle('transactions', scope);
    const activeFilters = generateActiveFilters(scope);
    
    return (
        <TransactionsListView
            scope={scope}
            breadcrumb={breadcrumb}
            title={pageTitle}
            activeFilters={activeFilters}
            onScopeChange={(newScope) => updateUrlScope(newScope)}
        />
    );
};
```

#### **Breadcrumb Generation for Scoped Lists**

```typescript
const generateScopedBreadcrumb = (entityType: string, scope: EntityScope): BreadcrumbItem[] => {
    const breadcrumb: BreadcrumbItem[] = [
        { 
            label: `All ${capitalize(entityType)}`, 
            level: 0, 
            action: () => navigate(`/${entityType}`) 
        }
    ];
    
    let currentLevel = 1;
    
    // Add account scope
    if (scope.accountId) {
        const account = getAccount(scope.accountId);
        breadcrumb.push({
            label: `${account.name} ${capitalize(entityType)}`,
            level: currentLevel++,
            action: () => navigate(`/${entityType}?account=${scope.accountId}`)
        });
    }
    
    // Add category scope
    if (scope.categoryId) {
        const category = getCategory(scope.categoryId);
        breadcrumb.push({
            label: `${category.name} ${capitalize(entityType)}`,
            level: currentLevel++,
            action: () => navigate(`/${entityType}?category=${scope.categoryId}`)
        });
    }
    
    // Add file scope
    if (scope.fileId) {
        const file = getFile(scope.fileId);
        breadcrumb.push({
            label: `${file.name} ${capitalize(entityType)}`,
            level: currentLevel++,
            action: () => navigate(`/${entityType}?file=${scope.fileId}`)
        });
    }
    
    // Add search scope
    if (scope.searchQuery) {
        breadcrumb.push({
            label: `Search: "${scope.searchQuery}"`,
            level: currentLevel++,
            action: () => navigate(`/${entityType}?search=${scope.searchQuery}`)
        });
    }
    
    return breadcrumb;
};
```

#### **Navigation Flow Examples**

**Example 1: Account → Transactions List**
```typescript
User Journey:
1. /accounts/acc123 → Account detail
2. Click "View All Transactions" → /transactions?account=acc123
3. Apply category filter → /transactions?account=acc123&category=food
4. Click specific transaction → /transactions/tx456?fromAccount=acc123&fromCategory=food

Breadcrumb Evolution:
Step 2: All Transactions > My Bank Transactions
Step 3: All Transactions > My Bank Transactions > Food Transactions  
Step 4: All Transactions > My Bank Transactions > Food Transactions > Transaction #456
```

**Example 2: Category → Files List**
```typescript
User Journey:
1. /categories/food → Category detail
2. Click "View Files with Food Transactions" → /files?category=food
3. Apply account filter → /files?category=food&account=acc123
4. Click specific file → /files/file789?fromCategory=food&fromAccount=acc123

Breadcrumb Evolution:
Step 2: All Files > Food Files
Step 3: All Files > Food Files > My Bank Food Files
Step 4: All Files > Food Files > My Bank Food Files > File_Jan2024.csv
```

#### **Filter Management**

```typescript
const ScopedEntityList: React.FC = ({ entityType, scope, onScopeChange }) => {
    const availableFilters = getAvailableFilters(entityType, scope);
    const activeFilters = getActiveFilters(scope);
    
    const handleFilterChange = (filterType: string, value: string | null) => {
        const newScope = { ...scope };
        
        if (value) {
            newScope[filterType] = value;
        } else {
            delete newScope[filterType];
        }
        
        onScopeChange(newScope);
    };
    
    const handleFilterClear = (filterType: string) => {
        handleFilterChange(filterType, null);
    };
    
    const handleClearAllFilters = () => {
        onScopeChange({});
    };
    
    return (
        <div className="scoped-entity-list">
            <FilterBar
                availableFilters={availableFilters}
                activeFilters={activeFilters}
                onFilterChange={handleFilterChange}
                onFilterClear={handleFilterClear}
                onClearAll={handleClearAllFilters}
            />
            
            <EntityList
                entityType={entityType}
                scope={scope}
                onEntityClick={(entity) => navigateToEntity(entity, scope)}
            />
        </div>
    );
};
```

### Benefits of Scoped Entity Lists

#### **1. Contextual Filtering**
- Users can progressively narrow down entity lists
- Filters are preserved in URLs for shareability
- Clear visual indication of active scope

#### **2. Flexible Navigation**
- Can reach the same entity list from multiple paths
- Breadcrumbs show the logical filtering path
- Easy to remove individual filters or clear all

#### **3. Performance Optimization**
- Scoped queries are more efficient than global searches
- Progressive loading based on scope
- Cached results for common scope combinations

#### **4. User Experience**
- Intuitive filtering that matches user mental models
- Clear indication of current scope and active filters
- Easy navigation between related scoped views

This design enables sophisticated navigation flows while maintaining URL shareability, session persistence, and optimal user experience across simple and complex navigation scenarios.
