# Transaction Import UI Page Design

## Overview
This document describes the design for a new transaction import UI page that displays accounts in a compact list format, ordered by oldest last update, with a contextual sidebar for import-related actions and navigation.

## Page Structure

### Main Content Area
The main content area will be divided into two primary sections:

#### 1. Page Header
- **Title**: "Import Transactions"
- **Subtitle**: "Select an account to import transaction files"
- **Import Status Indicator**: Shows current import progress/status
- **Quick Actions**: 
  - "Upload New File" button (primary action)
  - "View Import History" button (secondary action)

#### 2. Accounts List (Compact View)
A compact, scannable list of all user accounts, optimized for the import workflow.

**Sorting**: Accounts ordered by `updatedAt` timestamp (oldest first) to prioritize accounts that haven't been updated recently.

**Compact List Item Structure**:
```
[Icon] Account Name                    Last Import: Date    [Import Button]
       Institution • Account Type      Balance: $X,XXX.XX   
       Import Range: Start - End       Status: ✓ Active
```

**Data Fields Displayed**:
- **Account Icon**: Based on account type (💳 checking, 💰 savings, 📈 investment, etc.)
- **Account Name**: Primary identifier
- **Institution**: Bank/financial institution name
- **Account Type**: Formatted account type (e.g., "Checking", "Credit Card")
- **Balance**: Current account balance with currency
- **Last Import Date**: `importsEndDate` or "Never" if no imports
- **Import Date Range**: `importsStartDate` to `importsEndDate`
- **Status**: Active/Inactive indicator
- **Import Action**: Prominent "Import" button for quick access

**Visual Design**:
- **Compact rows**: ~60px height per item
- **Alternating row colors**: Light gray/white for better scanning
- **Hover states**: Subtle highlight on row hover
- **Import button**: Primary color, right-aligned
- **Typography**: Account name in medium weight, metadata in lighter weight
- **Icons**: Consistent 20px icons for account types

**Interaction Patterns**:
- **Click account name**: Navigate to account detail view
- **Click "Import" button**: Open file upload dialog for that account
- **Hover row**: Show additional metadata tooltip (last transaction date, file count)

### Contextual Sidebar: Import Navigation

The contextual sidebar will provide import-specific navigation and tools using the established configuration-based approach with `BaseSidebarContent`.

#### Sidebar Configuration Structure

The sidebar will use three main section types following the established conventions:

##### 1. Navigation Section - Import Tools
```typescript
{
  type: 'navigation',
  title: 'Import Tools',
  items: [
    createNavItem('upload-file', 'Upload File', '/import/upload', '📤'),
    createNavItem('import-history', 'Import History', '/import/history', '📊'),
    createNavItem('field-mappings', 'Field Mappings', '/import/mappings', '🗂️'),
    createNavItem('import-settings', 'Import Settings', '/import/settings', '⚙️')
  ]
}
```

##### 2. Context Section - Current Status & Recent Activity
```typescript
{
  type: 'context',
  title: 'Import Status',
  items: [
    // Dynamic content based on current import status
    // If import in progress: show progress indicator
    // Otherwise: show recent imports summary
  ]
}
```

##### 3. Actions Section - Quick Actions
```typescript
{
  type: 'actions',
  title: 'Quick Actions',
  items: [
    createActionItem('add-account', 'Add New Account', () => openAccountDialog(), '🏦'),
    createActionItem('refresh-accounts', 'Refresh Account Data', () => refreshAccounts(), '🔄'),
    createNavItem('view-accounts', 'View All Accounts', '/accounts', '📈')
  ]
}
```

#### Dynamic Content Handling

For dynamic content like import progress and recent imports, the sidebar will use the `dynamicSections` function:

```typescript
dynamicSections: ({ importStatus, recentImports }) => {
  const contextItems = [];
  
  // Add current import progress if active
  if (importStatus?.isImporting) {
    contextItems.push(
      createStatusItem('current-import', `Processing ${importStatus.currentFile?.fileName}`, 
        `${importStatus.currentFile?.progress}% complete`, '📤')
    );
  }
  
  // Add recent imports
  recentImports?.slice(0, 3).forEach(import => {
    contextItems.push(
      createInfoItem(`recent-${import.fileName}`, import.fileName,
        `${import.accountName} • ${formatDate(import.importedAt)} • ${import.transactionCount} transactions`)
    );
  });
  
  return [{
    type: 'context',
    title: importStatus?.isImporting ? 'Current Import' : 'Recent Imports',
    items: contextItems
  }];
}
```

## Responsive Design

### Desktop (1200px+)
- Full sidebar visible (280px width)
- Accounts list in 2-3 columns if space allows
- All metadata visible

### Tablet (768px - 1199px)
- Collapsible sidebar (collapsed by default)
- Single column accounts list
- Reduced metadata (hide import range)

### Mobile (< 768px)
- Sidebar as overlay/drawer
- Stacked account cards
- Minimal metadata (name, balance, import button only)

## Data Requirements

### Account Data Structure
Based on the existing `Account` schema:
```typescript
interface AccountForImport {
  accountId: string;
  accountName: string;
  accountType: AccountType;
  institution?: string;
  balance?: Decimal;
  currency?: Currency;
  isActive: boolean;
  lastTransactionDate?: number; // milliseconds since epoch
  importsStartDate?: number; // milliseconds since epoch
  importsEndDate?: number; // milliseconds since epoch
  updatedAt: number; // for sorting
}
```

### Sorting Logic
```typescript
// Sort by updatedAt ascending (oldest first)
accounts.sort((a, b) => (a.updatedAt || 0) - (b.updatedAt || 0));
```

### Import Status Data
```typescript
interface ImportStatus {
  isImporting: boolean;
  currentFile?: {
    fileName: string;
    accountId: string;
    progress: number; // 0-100
    status: string; // "uploading" | "parsing" | "processing" | "complete"
  };
  recentImports: Array<{
    fileName: string;
    accountName: string;
    importedAt: number;
    transactionCount: number;
    status: "success" | "error" | "partial";
  }>;
}
```

## Component Architecture

### Page Component: `ImportTransactionsPage`
- **Location**: `/frontend/src/new-ui/pages/ImportTransactionsPage.tsx`
- **Responsibilities**: 
  - Route-level container that composes the main view
  - Handle route parameters and navigation
  - Minimal logic - delegates to view component

```typescript
const ImportTransactionsPage: React.FC = () => {
  return <ImportTransactionsView />;
};
```

### View Component: `ImportTransactionsView`
- **Location**: `/frontend/src/new-ui/views/ImportTransactionsView.tsx`
- **Architecture**: Organized into logical sections using composition pattern
- **Structure**:

```typescript
const ImportTransactionsView: React.FC = () => {
  // 1. State Management Section
  const importState = useImportState();
  const accountsData = useAccountsData();
  const fileUpload = useFileUploadLogic();
  
  // 2. Layout Composition
  return (
    <ImportViewLayout>
      <ImportHeader {...importState} />
      <ImportMainContent 
        accounts={accountsData.accounts}
        onImportClick={fileUpload.handleImport}
        isLoading={accountsData.isLoading}
      />
      <ImportModals {...fileUpload.modalState} />
    </ImportViewLayout>
  );
};
```

## View Component Decomposition

The `ImportTransactionsView` is organized into logical sections to improve maintainability and readability:

### 1. Custom Hooks (State Management)
Extract complex state logic into focused custom hooks:

#### `useImportState` Hook
- **Location**: `/frontend/src/new-ui/hooks/useImportState.ts`
- **Purpose**: Manages import workflow state and progress
```typescript
interface ImportState {
  currentStep: number;
  importStatus: ImportStatus;
  errorMessage: string | null;
  successAlert: ImportResult | null;
}

const useImportState = () => {
  // Import workflow state management
  // Progress tracking, error handling, success states
};
```

#### `useAccountsData` Hook  
- **Location**: `/frontend/src/new-ui/hooks/useAccountsData.ts`
- **Purpose**: Handles account data fetching and management
```typescript
const useAccountsData = () => {
  // Account fetching, caching, sorting logic
  // Returns: { accounts, isLoading, error, refetch }
};
```

#### `useFileUploadLogic` Hook
- **Location**: `/frontend/src/new-ui/hooks/useFileUploadLogic.ts`
- **Purpose**: Manages file upload workflow and modal states
```typescript
const useFileUploadLogic = () => {
  // File validation, upload, processing logic
  // Modal state management for import dialogs
};
```

### 2. Layout Components (Visual Structure)

#### `ImportViewLayout` Component
- **Location**: `/frontend/src/new-ui/components/business/import/ImportViewLayout.tsx`
- **Purpose**: Provides the overall page structure and responsive layout
```typescript
interface ImportViewLayoutProps {
  children: React.ReactNode;
  className?: string;
}

const ImportViewLayout: React.FC<ImportViewLayoutProps> = ({ children }) => {
  return (
    <div className="import-transactions-container">
      <div className="import-content-wrapper">
        {children}
      </div>
    </div>
  );
};
```

#### `ImportHeader` Component
- **Location**: `/frontend/src/new-ui/components/business/import/ImportHeader.tsx`
- **Purpose**: Page title, status indicators, and quick actions
```typescript
interface ImportHeaderProps {
  importStatus: ImportStatus;
  onUploadClick: () => void;
  onHistoryClick: () => void;
}
```

#### `ImportMainContent` Component
- **Location**: `/frontend/src/new-ui/components/business/import/ImportMainContent.tsx`
- **Purpose**: Main content area with accounts list and status displays
```typescript
interface ImportMainContentProps {
  accounts: AccountForImport[];
  onImportClick: (accountId: string) => void;
  onAccountClick: (accountId: string) => void;
  isLoading: boolean;
  errorMessage?: string;
}
```

### 3. Business Components (Feature-Specific)

#### `CompactAccountsList` Component
- **Location**: `/frontend/src/new-ui/components/business/import/CompactAccountsList.tsx`
- **Purpose**: Renders the compact accounts list optimized for import workflow
- **Implementation**: Uses reusable UI components for consistency and maintainability
```typescript
interface CompactAccountsListProps {
  accounts: AccountForImport[];
  onImportClick: (accountId: string) => void;
  onAccountClick: (accountId: string) => void;
  isLoading?: boolean;
}

// Implementation should leverage existing UI components:
import { 
  SortableTable, 
  CurrencyAmount, 
  DateCell, 
  StatusBadge, 
  TextWithSubtext,
  LoadingState 
} from '@/new-ui/components/ui';
```

#### `CompactAccountItem` Component
- **Location**: `/frontend/src/new-ui/components/business/import/CompactAccountItem.tsx`
- **Purpose**: Individual account row with import-optimized display
```typescript
interface CompactAccountItemProps {
  account: AccountForImport;
  onImportClick: (accountId: string) => void;
  onAccountClick: (accountId: string) => void;
}
```

### 4. Modal Components (Dialog Management)

#### `ImportModals` Component
- **Location**: `/frontend/src/new-ui/components/business/import/ImportModals.tsx`
- **Purpose**: Manages all import-related modals and dialogs
```typescript
interface ImportModalsProps {
  fileUploadModal: {
    isOpen: boolean;
    selectedAccount?: string;
    onClose: () => void;
    onUpload: (file: File) => void;
  };
  mappingModal: {
    isOpen: boolean;
    fileData?: ParsedFileData;
    onClose: () => void;
    onComplete: (mapping: FieldMapping) => void;
  };
}
```

## Organized View Structure

With this decomposition, the `ImportTransactionsView` becomes much cleaner and easier to follow:

```typescript
// ImportTransactionsView.tsx - Clean and organized
const ImportTransactionsView: React.FC = () => {
  // === 1. STATE MANAGEMENT SECTION ===
  const importState = useImportState();
  const accountsData = useAccountsData();
  const fileUpload = useFileUploadLogic();
  
  // === 2. EVENT HANDLERS SECTION ===
  const handleImportClick = useCallback((accountId: string) => {
    fileUpload.startImport(accountId);
  }, [fileUpload]);
  
  const handleAccountClick = useCallback((accountId: string) => {
    // Navigate to account detail
  }, []);
  
  // === 3. LAYOUT COMPOSITION SECTION ===
  return (
    <ImportViewLayout>
      <ImportHeader 
        importStatus={importState.importStatus}
        onUploadClick={fileUpload.openUploadDialog}
        onHistoryClick={importState.showHistory}
      />
      
      <ImportMainContent
        accounts={accountsData.accounts}
        onImportClick={handleImportClick}
        onAccountClick={handleAccountClick}
        isLoading={accountsData.isLoading}
        errorMessage={importState.errorMessage}
      />
      
      <ImportModals
        fileUploadModal={fileUpload.modalState.upload}
        mappingModal={fileUpload.modalState.mapping}
      />
    </ImportViewLayout>
  );
};
```

## UI Component Reusability Guidelines

### Leverage Existing UI Components
The application has a comprehensive set of reusable UI components in `/frontend/src/new-ui/components/ui/`. **Always check for existing components before creating new ones.**

#### Available UI Components for Tables and Data Display:
- **`SortableTable`**: Automatic sorting, type detection, accessibility features
- **`CurrencyAmount`**: Consistent currency formatting with locale support
- **`DateCell`**: Standardized date display and formatting
- **`StatusBadge`**: Consistent status indicators with color coding
- **`TextWithSubtext`**: Primary text with secondary information
- **`LoadingState`**: Standardized loading indicators
- **`EditableCell`**: In-line editing with validation
- **`RowActions`**: Consistent action buttons for table rows

#### Implementation Example for Accounts List:
```typescript
// CompactAccountsList.tsx - Using reusable UI components
import { 
  SortableTable, 
  CurrencyAmount, 
  DateCell, 
  StatusBadge, 
  TextWithSubtext,
  LoadingState,
  RowActions 
} from '@/new-ui/components/ui';

const CompactAccountsList: React.FC<CompactAccountsListProps> = ({ 
  accounts, 
  onImportClick, 
  onAccountClick, 
  isLoading 
}) => {
  if (isLoading) return <LoadingState message="Loading accounts..." />;

  const columns = [
    {
      key: 'accountName' as keyof AccountForImport,
      label: 'Account',
      render: (value: string, account: AccountForImport) => (
        <TextWithSubtext
          primary={account.accountName}
          secondary={`${account.institution} • ${account.accountType}`}
          onClick={() => onAccountClick(account.accountId)}
          className="clickable-account"
        />
      )
    },
    {
      key: 'balance' as keyof AccountForImport,
      label: 'Balance',
      render: (value: Decimal, account: AccountForImport) => (
        <CurrencyAmount 
          amount={value} 
          currency={account.currency} 
        />
      )
    },
    {
      key: 'importsEndDate' as keyof AccountForImport,
      label: 'Last Import',
      render: (value: number) => (
        <DateCell 
          timestamp={value} 
          fallback="Never" 
        />
      )
    },
    {
      key: 'isActive' as keyof AccountForImport,
      label: 'Status',
      render: (value: boolean) => (
        <StatusBadge 
          status={value ? 'active' : 'inactive'} 
          variant={value ? 'success' : 'warning'} 
        />
      )
    },
    {
      key: 'actions' as keyof AccountForImport,
      label: 'Actions',
      render: (_, account: AccountForImport) => (
        <RowActions
          actions={[
            {
              label: 'Import',
              onClick: () => onImportClick(account.accountId),
              variant: 'primary',
              icon: '📤'
            }
          ]}
        />
      )
    }
  ];

  return (
    <SortableTable
      data={accounts}
      columns={columns}
      defaultSortKey="updatedAt"
      defaultSortDirection="ascending"
      fieldsConfig={{
        updatedAt: { type: 'date' },
        balance: { type: 'decimal' },
        importsEndDate: { type: 'date' }
      }}
    />
  );
};
```

### Proposed New UI Component: `CompactListTable`

Since the import page uses a "compact list" format that differs from standard tables, consider creating a new reusable UI component:

#### `CompactListTable` Component
- **Location**: `/frontend/src/new-ui/components/ui/CompactListTable.tsx`
- **Purpose**: Specialized table for compact, scannable lists with prominent actions
- **Features**:
  - Optimized for mobile/responsive design
  - Built-in action buttons per row
  - Compact row height (~60px)
  - Alternating row colors
  - Hover states and tooltips
  - Keyboard navigation support

```typescript
interface CompactListTableProps<T> {
  data: T[];
  columns: Array<{
    key: keyof T;
    label: string;
    render?: (value: any, item: T) => React.ReactNode;
    width?: string; // e.g., '200px', '30%', 'auto'
    hideOnMobile?: boolean;
  }>;
  primaryAction?: {
    label: string;
    onClick: (item: T) => void;
    variant?: 'primary' | 'secondary';
    icon?: string;
  };
  onRowClick?: (item: T) => void;
  isLoading?: boolean;
  emptyMessage?: string;
  className?: string;
}
```

## Benefits of This Structure

### 1. **Separation of Concerns**
- **Hooks**: Handle state and business logic
- **Layout Components**: Handle visual structure
- **Business Components**: Handle feature-specific UI
- **Modal Components**: Handle dialog management

### 2. **Improved Readability**
- Each section has a clear, single responsibility
- Easy to locate specific functionality
- Logical flow from state → handlers → layout

### 3. **Better Testability**
- Hooks can be tested independently
- Components have focused, testable interfaces
- Mock dependencies are clearly defined

### 4. **Enhanced Maintainability**
- Changes to state logic only affect hooks
- UI changes only affect layout/business components
- New features can be added by composing existing pieces

### 5. **UI Consistency**
- Reusing UI components ensures consistent look and behavior
- Centralized styling and accessibility features
- Easier to maintain design system compliance

### Import Sidebar Content: `ImportSidebarContent`
- **Location**: `/frontend/src/new-ui/components/navigation/sidebar-content/ImportSidebarContent.tsx`
- **Integration**: Add to `ContextualSidebar.tsx` routing logic
- **Implementation**: Uses `BaseSidebarContent` with configuration-based approach
- **Props**:
  ```typescript
  interface ImportSidebarContentProps {
    sidebarCollapsed: boolean;
  }
  ```

### Import Sidebar Configuration: `importConfig`
- **Location**: `/frontend/src/new-ui/components/navigation/sidebar-content/configs/importConfig.ts`
- **Structure**:
  ```typescript
  export const importConfig: SidebarContentConfig = {
    sections: [
      {
        type: 'navigation',
        title: 'Import Tools',
        items: [
          createNavItem('upload-file', 'Upload File', '/import/upload', '📤'),
          createNavItem('import-history', 'Import History', '/import/history', '📊'),
          createNavItem('field-mappings', 'Field Mappings', '/import/mappings', '🗂️'),
          createNavItem('import-settings', 'Import Settings', '/import/settings', '⚙️')
        ]
      },
      {
        type: 'actions',
        title: 'Quick Actions',
        items: [
          createActionItem('add-account', 'Add New Account', () => openAccountDialog(), '🏦'),
          createActionItem('refresh-accounts', 'Refresh Account Data', () => refreshAccounts(), '🔄'),
          createNavItem('view-accounts', 'View All Accounts', '/accounts', '📈')
        ]
      }
    ],
    dynamicSections: ({ importStatus, recentImports }) => {
      // Dynamic context section for import status and recent imports
      return generateImportContextSections(importStatus, recentImports);
    }
  };
  ```

## Routing Integration

### Route Definition
```typescript
// Add to router configuration
{
  path: "/import",
  element: <ImportTransactionsPage />
}
```

### Sidebar Integration
```typescript
// In ContextualSidebar.tsx, add case:
case 'import':
  return <ImportSidebarContent sidebarCollapsed={sidebarCollapsed} />;
```

### Factory Function Usage
The sidebar configuration uses the established factory functions from `SidebarConfigFactory.ts`:

```typescript
import { createNavItem, createActionItem, createFilterItem } from '../SidebarConfigFactory';

// Navigation items for routing
createNavItem(id, label, path, icon?, customActiveCheck?)

// Action items for functions
createActionItem(id, label, clickHandler, icon?)

// Filter items for search/filtering
createFilterItem(id, label, basePath, searchParams, icon?)
```

## Accessibility Considerations

### Keyboard Navigation
- **Tab order**: Header actions → account list → sidebar
- **Arrow keys**: Navigate within account list
- **Enter/Space**: Activate import buttons
- **Escape**: Close any open dialogs

### Screen Reader Support
- **Semantic HTML**: Use proper heading hierarchy (h1 → h2 → h3)
- **ARIA labels**: Descriptive labels for import buttons
- **Live regions**: Announce import progress updates
- **Table semantics**: Consider using table structure for account list

### Visual Accessibility
- **Color contrast**: Ensure 4.5:1 contrast ratio minimum
- **Focus indicators**: Clear focus outlines on all interactive elements
- **Text scaling**: Support up to 200% zoom
- **Reduced motion**: Respect `prefers-reduced-motion` for animations

## Error Handling

### Account Loading Errors
- **Empty state**: "No accounts found. Create an account to start importing."
- **Network errors**: "Unable to load accounts. Please try again."
- **Retry mechanism**: Automatic retry with exponential backoff

### Import Errors
- **File validation errors**: Clear messaging about supported formats
- **Upload failures**: Retry options and error details
- **Processing errors**: Link to support documentation

## Performance Considerations

### Data Loading
- **Lazy loading**: Load account details on demand
- **Caching**: Cache account list with appropriate TTL
- **Pagination**: If account list grows large (>100 accounts)

### File Upload
- **Progress indicators**: Real-time upload progress
- **Background processing**: Don't block UI during file processing
- **Chunked uploads**: For large files (>10MB)

## Future Enhancements

### Phase 2 Features
- **Bulk import**: Select multiple accounts for batch import
- **Scheduled imports**: Recurring import schedules
- **Import templates**: Save common field mappings
- **Account grouping**: Group accounts by institution

### Advanced Features
- **Drag & drop**: Drag files directly onto account items
- **Import preview**: Preview transactions before final import
- **Conflict resolution**: Handle duplicate transaction scenarios
- **Import analytics**: Track import success rates and patterns

## Implementation Notes

### State Management
- Use existing `useAccountsStore` for account data
- Create new `useImportStore` for import-specific state
- Integrate with `useNavigationStore` for sidebar state

### Sidebar Implementation Pattern
Following the established sidebar conventions:

1. **Configuration-Based Approach**: Use `BaseSidebarContent` with `importConfig`
2. **Section Types**: Properly categorize content into `navigation`, `context`, and `actions`
3. **Factory Functions**: Use `createNavItem`, `createActionItem` for consistent item creation
4. **Dynamic Content**: Handle real-time import status via `dynamicSections` function
5. **Integration**: Register in `ContextualSidebar.tsx` route switching logic

### UI Component Usage
- **Prioritize reusable UI components** from `/frontend/src/new-ui/components/ui/`
- **Check existing components first** before creating new ones
- **Use `SortableTable`** for data tables with sorting requirements
- **Use specialized cells** (`CurrencyAmount`, `DateCell`, `StatusBadge`) for consistent formatting
- **Consider creating `CompactListTable`** if the compact list pattern is reused elsewhere

### Styling
- Follow existing CSS conventions in `/frontend/src/new-ui/`
- Use CSS modules for component-specific styles
- Leverage existing design tokens and color schemes
- Extend UI component styles through CSS classes rather than inline styles

### Testing Strategy
- **Unit tests**: Component rendering and interaction logic
- **Integration tests**: Account loading and import flow
- **E2E tests**: Complete import workflow
- **Accessibility tests**: Screen reader and keyboard navigation

This design provides a focused, efficient interface for transaction imports while maintaining consistency with the existing application architecture and design patterns.
