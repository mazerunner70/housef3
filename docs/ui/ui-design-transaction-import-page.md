# Transaction Import UI Page Design

## Overview
This document describes the design for transaction import UI pages, including the main import page that displays accounts in a compact list format and the account file upload page for managing transaction files for a specific account.

## Main Import Page Structure

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

### Main Import Page Contextual Sidebar: Import Navigation

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

### Main Import Page Responsive Design

#### Desktop (1200px+)
- Full sidebar visible (280px width)
- Accounts list in 2-3 columns if space allows
- All metadata visible

#### Tablet (768px - 1199px)
- Collapsible sidebar (collapsed by default)
- Single column accounts list
- Reduced metadata (hide import range)

#### Mobile (< 768px)
- Sidebar as overlay/drawer
- Stacked account cards
- Minimal metadata (name, balance, import button only)

### Main Import Page Data Requirements

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

## Account File Upload Page

### Overview
The account file upload page is accessed when clicking the "Import" button for a specific account from the main import page. This page provides a focused interface for managing transaction files for a single account.

### Page Structure

#### 1. Page Header
- **Title**: "Upload Files for [Account Name]"
- **Subtitle**: "[Institution] • [Account Type]"
- **Breadcrumb**: "Import Transactions > [Account Name]"
- **Back Button**: Return to main import page

#### 2. File Upload Status Section
Located at the top of the main content area, this section provides an overview of uploaded files:

```
Files Uploaded: X files
Total Transactions: X,XXX transactions
Date Range: MM/DD/YYYY - MM/DD/YYYY
```

**Visual Design**:
- **Card-based layout**: Clean white background with subtle border
- **Icon indicators**: 📁 for file count, 📊 for transaction count, 📅 for date range
- **Typography**: Bold numbers for key metrics, regular text for labels

#### 3. Field Mapping Section
Displays the current field mapping configuration and provides management options:

**If mapping exists**:
```
Current Field Mapping: [Mapping Name]
✓ Date Column: Transaction Date
✓ Amount Column: Amount  
✓ Description Column: Description
✓ Category Column: Category (Optional)

[View/Edit Mapping] [Delete Mapping]
```

**If no mapping exists but files uploaded**:
```
⚠️ Field Mapping Required
Transaction files have been uploaded but no field mapping has been configured.
A field mapping tells the system which columns contain transaction data.

[Create Field Mapping]
```

**If no files uploaded**:
```
Field Mapping
Upload at least one transaction file to configure field mappings.
```

**Visual Design**:
- **Status indicators**: Green checkmarks for configured fields, warning icon for missing mapping
- **Action buttons**: Primary button for create/edit, secondary for view, destructive for delete
- **Expandable details**: Click to show/hide detailed mapping configuration

#### 4. Drag and Drop Upload Panel (Central)
The main focal point of the page - a large, prominent drag-and-drop area:

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│              📤                                     │
│         Drag & Drop Files Here                      │
│                                                     │
│        or click to browse files                     │
│                                                     │
│    Supported formats: CSV, Excel, QIF, OFX         │
│         Maximum file size: 10MB                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**States**:
- **Default**: Light gray background with dashed border
- **Drag hover**: Blue background with solid border, slight scale animation
- **Uploading**: Progress bar and percentage, disable interactions
- **Error**: Red border with error message below
- **Success**: Green border with success message, fade to default after 3s

**Visual Design**:
- **Large size**: ~400px wide × 200px tall on desktop
- **Responsive**: Scales down appropriately on mobile
- **Clear typography**: Large, readable text with good contrast
- **Accessibility**: Proper ARIA labels and keyboard support

#### 5. Uploaded Files List (Bottom)
A detailed list of all uploaded files for this account, ordered by upload date (newest first):

**List Item Structure**:
```
📄 transactions_jan_2024.csv                    Jan 15, 2024
    1,247 transactions • 2.3 MB                 [View] [Download] [Delete]
    Date range: 01/01/2024 - 01/31/2024
    Status: ✅ Processed successfully
```

**Data Fields**:
- **File icon**: Based on file type (📄 CSV, 📊 Excel, etc.)
- **File name**: Original uploaded filename
- **Upload date**: When the file was uploaded
- **Transaction count**: Number of transactions in the file
- **File size**: Human-readable file size
- **Date range**: Earliest to latest transaction date in file
- **Processing status**: Success, processing, error with details
- **Actions**: View details, download original file, delete file

**Visual Design**:
- **Card-based items**: Each file as a distinct card with subtle shadow
- **Status indicators**: Color-coded status badges (green success, yellow processing, red error)
- **Hover states**: Subtle highlight on hover
- **Action buttons**: Small, icon-based buttons aligned to the right
- **Empty state**: "No files uploaded yet" with upload encouragement

**Error States**:
- **Processing errors**: Show error details with retry option
- **Validation errors**: Highlight issues with file format or content
- **Network errors**: Retry upload option

### Data Requirements for Account File Upload Page

#### File Upload Data Structure
```typescript
interface UploadedFile {
  fileId: string;
  fileName: string;
  fileSize: number;
  uploadedAt: number; // milliseconds since epoch
  accountId: string;
  transactionCount: number;
  dateRange: {
    startDate: number;
    endDate: number;
  };
  status: 'processing' | 'success' | 'error';
  errorMessage?: string;
  processingProgress?: number; // 0-100 for processing files
}
```

#### Field Mapping Data Structure
```typescript
interface FieldMapping {
  mappingId: string;
  accountId: string;
  mappingName: string;
  createdAt: number;
  updatedAt: number;
  fieldMappings: {
    dateColumn: string;
    amountColumn: string;
    descriptionColumn: string;
    categoryColumn?: string;
    referenceColumn?: string;
  };
  dateFormat?: string; // e.g., "MM/DD/YYYY", "YYYY-MM-DD"
  csvSettings?: {
    delimiter: string;
    hasHeader: boolean;
    encoding: string;
  };
}
```

### Account File Upload Component Architecture

#### Page Component: `AccountFileUploadPage`
- **Location**: `/frontend/src/new-ui/pages/AccountFileUploadPage.tsx`
- **Route**: `/import/account/:accountId`
- **Responsibilities**: Route-level container, parameter handling

```typescript
const AccountFileUploadPage: React.FC = () => {
  const { accountId } = useParams();
  return <AccountFileUploadView accountId={accountId} />;
};
```

#### View Component: `AccountFileUploadView`
- **Location**: `/frontend/src/new-ui/views/AccountFileUploadView.tsx`
- **Structure**:

```typescript
const AccountFileUploadView: React.FC<{ accountId: string }> = ({ accountId }) => {
  // State management
  const account = useAccountData(accountId);
  const uploadedFiles = useUploadedFiles(accountId);
  const fieldMapping = useFieldMapping(accountId);
  const fileUpload = useFileUploadLogic(accountId);
  
  return (
    <AccountUploadLayout>
      <AccountUploadHeader account={account} />
      <FileUploadStatus 
        fileCount={uploadedFiles.length}
        totalTransactions={uploadedFiles.reduce((sum, f) => sum + f.transactionCount, 0)}
        dateRange={calculateDateRange(uploadedFiles)}
      />
      <FieldMappingSection 
        mapping={fieldMapping}
        hasFiles={uploadedFiles.length > 0}
        onCreateMapping={() => fileUpload.openMappingDialog()}
        onEditMapping={() => fileUpload.editMapping(fieldMapping)}
      />
      <DragDropUploadPanel 
        onFileSelect={fileUpload.handleFileUpload}
        isUploading={fileUpload.isUploading}
        uploadProgress={fileUpload.uploadProgress}
      />
      <UploadedFilesList 
        files={uploadedFiles}
        onViewFile={fileUpload.viewFile}
        onDownloadFile={fileUpload.downloadFile}
        onDeleteFile={fileUpload.deleteFile}
      />
    </AccountUploadLayout>
  );
};
```

#### Business Components for Account File Upload

##### `DragDropUploadPanel` Component
- **Location**: `/frontend/src/new-ui/components/business/import/DragDropUploadPanel.tsx`
- **Features**:
  - Drag and drop file handling
  - Click to browse files
  - File validation (type, size)
  - Upload progress indication
  - Error state management

```typescript
interface DragDropUploadPanelProps {
  onFileSelect: (files: FileList) => void;
  isUploading: boolean;
  uploadProgress?: number;
  acceptedTypes?: string[];
  maxFileSize?: number;
  disabled?: boolean;
}
```

##### `UploadedFilesList` Component
- **Location**: `/frontend/src/new-ui/components/business/import/UploadedFilesList.tsx`
- **Features**:
  - File list display with metadata
  - Status indicators
  - Action buttons (view, download, delete)
  - Empty state handling

```typescript
interface UploadedFilesListProps {
  files: UploadedFile[];
  onViewFile: (fileId: string) => void;
  onDownloadFile: (fileId: string) => void;
  onDeleteFile: (fileId: string) => void;
  isLoading?: boolean;
}
```

##### `FieldMappingSection` Component
- **Location**: `/frontend/src/new-ui/components/business/import/FieldMappingSection.tsx`
- **Features**:
  - Display current mapping configuration
  - Create/edit/delete mapping actions
  - Status indicators for mapping completeness

```typescript
interface FieldMappingSectionProps {
  mapping?: FieldMapping;
  hasFiles: boolean;
  onCreateMapping: () => void;
  onEditMapping: (mapping: FieldMapping) => void;
  onDeleteMapping: (mappingId: string) => void;
  onViewMapping: (mapping: FieldMapping) => void;
}
```

#### Custom Hooks for Account File Upload

##### `useFileUploadLogic` Hook
- **Location**: `/frontend/src/new-ui/hooks/useFileUploadLogic.ts`
- **Purpose**: Manages file upload workflow, validation, and progress

```typescript
const useFileUploadLogic = (accountId: string) => {
  // File upload, validation, progress tracking
  // Modal state management for mapping dialogs
  // Error handling and retry logic
};
```

##### `useUploadedFiles` Hook
- **Location**: `/frontend/src/new-ui/hooks/useUploadedFiles.ts`
- **Purpose**: Manages uploaded files data and operations

```typescript
const useUploadedFiles = (accountId: string) => {
  // Fetch uploaded files for account
  // Real-time updates for processing status
  // File operations (view, download, delete)
};
```

##### `useFieldMapping` Hook
- **Location**: `/frontend/src/new-ui/hooks/useFieldMapping.ts`
- **Purpose**: Manages field mapping configuration

```typescript
const useFieldMapping = (accountId: string) => {
  // Fetch current field mapping
  // Create/update/delete operations
  // Validation and error handling
};
```

### Routing Integration for Account File Upload

#### Route Definition
```typescript
// Add to router configuration
{
  path: "/import/account/:accountId",
  element: <AccountFileUploadPage />
}
```

#### Navigation Flow
1. **From main import page**: Click "Import" button on account → navigate to `/import/account/{accountId}`
2. **Back navigation**: Breadcrumb or back button → return to `/import`
3. **Deep linking**: Direct access via URL with account ID

### Account File Upload Page Responsive Design

#### Desktop (1200px+)
- Full-width drag-and-drop panel (400px × 200px)
- Files list in single column with full metadata
- Side-by-side mapping section and upload status

#### Tablet (768px - 1199px)
- Slightly smaller drag-and-drop panel (350px × 180px)
- Stacked layout for status and mapping sections
- Condensed file list items

#### Mobile (< 768px)
- Full-width drag-and-drop panel (fills container, ~150px height)
- Vertical stack layout for all sections
- Minimal file list (name, date, status only)
- Collapsible file details

### Account File Upload Page Accessibility

#### Drag and Drop Accessibility
- **Keyboard support**: Tab to panel, Enter/Space to open file browser
- **Screen reader**: Clear instructions and status announcements
- **ARIA labels**: Proper labeling for upload states
- **Focus management**: Clear focus indicators and logical tab order

#### File List Accessibility
- **Table semantics**: Use proper table structure for file list
- **Action buttons**: Clear labels and keyboard access
- **Status announcements**: Live regions for upload progress and errors

### Account File Upload Page Error Handling

#### Upload Errors
- **File validation**: Clear messages for unsupported formats or oversized files
- **Network errors**: Retry mechanism with exponential backoff
- **Processing errors**: Detailed error messages with support links

#### Mapping Errors
- **Missing mapping**: Clear call-to-action to create mapping
- **Invalid mapping**: Validation errors with specific field guidance
- **Mapping conflicts**: Handle changes to file structure

### Account File Upload Page Performance

#### File Upload
- **Chunked uploads**: For files larger than 5MB
- **Progress tracking**: Real-time upload progress
- **Background processing**: Non-blocking file processing
- **Retry logic**: Automatic retry for failed uploads

#### File List
- **Pagination**: For accounts with many files (>50)
- **Lazy loading**: Load file details on demand
- **Caching**: Cache file metadata with appropriate TTL

## Main Import Page Component Architecture

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

### Main Import Page View Component Decomposition

The `ImportTransactionsView` is organized into logical sections to improve maintainability and readability:

#### 1. Custom Hooks (State Management)
Extract complex state logic into focused custom hooks:

##### `useImportState` Hook
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

##### `useAccountsData` Hook  
- **Location**: `/frontend/src/new-ui/hooks/useAccountsData.ts`
- **Purpose**: Handles account data fetching and management
```typescript
const useAccountsData = () => {
  // Account fetching, caching, sorting logic
  // Returns: { accounts, isLoading, error, refetch }
};
```

##### `useFileUploadLogic` Hook
- **Location**: `/frontend/src/new-ui/hooks/useFileUploadLogic.ts`
- **Purpose**: Manages file upload workflow and modal states
```typescript
const useFileUploadLogic = () => {
  // File validation, upload, processing logic
  // Modal state management for import dialogs
};
```

#### 2. Layout Components (Visual Structure)

##### `ImportViewLayout` Component
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

##### `ImportHeader` Component
- **Location**: `/frontend/src/new-ui/components/business/import/ImportHeader.tsx`
- **Purpose**: Page title, status indicators, and quick actions
```typescript
interface ImportHeaderProps {
  importStatus: ImportStatus;
  onUploadClick: () => void;
  onHistoryClick: () => void;
}
```

##### `ImportMainContent` Component
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

#### 3. Business Components (Feature-Specific)

##### `CompactAccountsList` Component
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

##### `CompactAccountItem` Component
- **Location**: `/frontend/src/new-ui/components/business/import/CompactAccountItem.tsx`
- **Purpose**: Individual account row with import-optimized display
```typescript
interface CompactAccountItemProps {
  account: AccountForImport;
  onImportClick: (accountId: string) => void;
  onAccountClick: (accountId: string) => void;
}
```

#### 4. Modal Components (Dialog Management)

##### `ImportModals` Component
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

### Main Import Page Organized View Structure

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

### Benefits of Main Import Page Structure

#### 1. **Separation of Concerns**
- **Hooks**: Handle state and business logic
- **Layout Components**: Handle visual structure
- **Business Components**: Handle feature-specific UI
- **Modal Components**: Handle dialog management

#### 2. **Improved Readability**
- Each section has a clear, single responsibility
- Easy to locate specific functionality
- Logical flow from state → handlers → layout

#### 3. **Better Testability**
- Hooks can be tested independently
- Components have focused, testable interfaces
- Mock dependencies are clearly defined

#### 4. **Enhanced Maintainability**
- Changes to state logic only affect hooks
- UI changes only affect layout/business components
- New features can be added by composing existing pieces

#### 5. **UI Consistency**
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

### Main Import Page Routing Integration

#### Route Definition
```typescript
// Add to router configuration
{
  path: "/import",
  element: <ImportTransactionsPage />
}
```

#### Sidebar Integration
```typescript
// In ContextualSidebar.tsx, add case:
case 'import':
  return <ImportSidebarContent sidebarCollapsed={sidebarCollapsed} />;
```

#### Factory Function Usage
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

### Main Import Page Accessibility Considerations

#### Keyboard Navigation
- **Tab order**: Header actions → account list → sidebar
- **Arrow keys**: Navigate within account list
- **Enter/Space**: Activate import buttons
- **Escape**: Close any open dialogs

#### Screen Reader Support
- **Semantic HTML**: Use proper heading hierarchy (h1 → h2 → h3)
- **ARIA labels**: Descriptive labels for import buttons
- **Live regions**: Announce import progress updates
- **Table semantics**: Consider using table structure for account list

#### Visual Accessibility
- **Color contrast**: Ensure 4.5:1 contrast ratio minimum
- **Focus indicators**: Clear focus outlines on all interactive elements
- **Text scaling**: Support up to 200% zoom
- **Reduced motion**: Respect `prefers-reduced-motion` for animations

### Main Import Page Error Handling

#### Account Loading Errors
- **Empty state**: "No accounts found. Create an account to start importing."
- **Network errors**: "Unable to load accounts. Please try again."
- **Retry mechanism**: Automatic retry with exponential backoff

#### Import Errors
- **File validation errors**: Clear messaging about supported formats
- **Upload failures**: Retry options and error details
- **Processing errors**: Link to support documentation

### Main Import Page Performance Considerations

#### Data Loading
- **Lazy loading**: Load account details on demand
- **Caching**: Cache account list with appropriate TTL
- **Pagination**: If account list grows large (>100 accounts)

#### File Upload
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

## Revised Implementation Plan

Based on the analysis of existing functionality, this implementation plan leverages the sophisticated infrastructure already in place and focuses on creating new UI paradigms that enhance the user experience.

### Stage 1: Enhanced Main Import Page (UI Modernization)
**Duration**: 1-2 weeks  
**Goal**: Create modern, intuitive main import page using existing backend infrastructure

#### Frontend Components (New/Enhanced)
- **Enhanced `ImportTransactionsView`**: 
  - Integrate with existing `useImportState` hook
  - Add contextual sidebar integration
  - Improve error handling and loading states
- **Refined `CompactAccountsList`**:
  - Leverage existing account data APIs
  - Enhanced sorting by `updatedAt` (oldest first)
  - Rich metadata display with import history
  - Improved accessibility and keyboard navigation
- **New `ImportSidebarContent`**:
  - Configuration-based sidebar using existing patterns
  - Dynamic sections for import status and recent activity
  - Integration with existing navigation system

#### Backend Integration
- **Existing APIs**: Use current account and file listing endpoints
- **Enhanced Account Data**: Extend existing account queries to include import metadata
- **No New Endpoints**: Leverage existing `/api/accounts` and `/api/files` structure

#### Deliverables
- ✅ Modern main import page with enhanced UX
- ✅ Contextual sidebar with import navigation
- ✅ Account list with rich import metadata
- ✅ Improved responsive design and accessibility
- ✅ Integration with existing state management

#### Success Criteria
- Users can efficiently browse accounts sorted by import priority
- Import status and recent activity are clearly visible
- Navigation between import workflows is intuitive
- All existing functionality is preserved and enhanced

---

### Stage 2: Account File Upload Page (Component Adaptation)
**Duration**: 2-3 weeks  
**Goal**: Create dedicated account upload page by adapting existing components

#### Component Adaptations
- **Adapt `TransactionFileUpload`** → **`DragDropUploadPanel`**:
  - Maintain existing validation and upload logic
  - Enhance visual design for central prominence
  - Improve progress indication and error states
- **Adapt `ImportHistoryTable`** → **`UploadedFilesList`**:
  - Filter for account-specific files using existing APIs
  - Enhance metadata display and file operations
  - Improve mobile responsiveness
- **Adapt `ImportStep2Preview`** → **`FieldMappingSection`**:
  - Streamline field mapping interface
  - Maintain existing mapping logic and validation
  - Add status indicators and quick actions

#### New Components
- **`AccountFileUploadView`**: Main view orchestrating adapted components
- **`FileUploadStatus`**: Summary statistics using existing file metadata
- **`AccountUploadHeader`**: Breadcrumb navigation and account context

#### Backend Integration
- **Existing File APIs**: Use current upload, processing, and metadata endpoints
- **Existing Field Mapping**: Leverage current `FileMapService` functionality
- **Account-Specific Filtering**: Use existing `/api/accounts/{id}/files` endpoint

#### Enhanced Hooks
- **`useUploadedFiles`**: Wrapper around existing file listing with account filtering
- **`useFileUploadLogic`**: Enhanced version of existing upload workflow
- **`useFieldMapping`**: Wrapper around existing field mapping operations

#### Deliverables
- ✅ Dedicated account file upload page
- ✅ Enhanced drag-and-drop interface
- ✅ Account-specific file management
- ✅ Streamlined field mapping workflow
- ✅ Comprehensive file metadata display
- ✅ Mobile-optimized responsive design

#### Success Criteria
- Users can efficiently upload files for specific accounts
- File management operations are intuitive and accessible
- Field mapping workflow is streamlined but comprehensive
- All existing upload and processing functionality is preserved

---

### Stage 3: Advanced UX and Polish (Experience Enhancement)
**Duration**: 1-2 weeks  
**Goal**: Add advanced UX features and production polish

#### UX Enhancements
- **Batch Operations**: Multi-file selection and bulk actions
- **Enhanced Progress Tracking**: Real-time status updates with WebSocket integration
- **Smart Defaults**: Auto-suggest field mappings based on file patterns
- **Keyboard Shortcuts**: Power-user navigation and actions
- **Advanced Search/Filtering**: Quick file and account discovery

#### Performance Optimizations
- **Optimistic Updates**: Immediate UI feedback for user actions
- **Background Processing**: Non-blocking file operations
- **Caching Strategy**: Smart caching of account and file metadata
- **Lazy Loading**: Progressive loading of file lists and metadata

#### Accessibility & Polish
- **Screen Reader Optimization**: Enhanced ARIA labels and live regions
- **High Contrast Mode**: Support for accessibility preferences
- **Animation Preferences**: Respect `prefers-reduced-motion`
- **Loading States**: Skeleton screens and progressive disclosure
- **Error Recovery**: Intelligent retry mechanisms and user guidance

#### Analytics Integration
- **Usage Tracking**: Import workflow analytics using existing patterns
- **Performance Monitoring**: Client-side performance metrics
- **Error Reporting**: Enhanced error tracking and user feedback

#### Deliverables
- ✅ Batch file operations and multi-selection
- ✅ Real-time progress tracking and notifications
- ✅ Advanced accessibility features
- ✅ Performance optimizations and caching
- ✅ Comprehensive error handling and recovery
- ✅ Analytics and monitoring integration

#### Success Criteria
- Import workflow is highly efficient for power users
- Performance is optimized for large-scale operations
- Accessibility meets WCAG 2.1 AA standards
- Error recovery is intelligent and user-friendly
- System provides actionable insights through analytics

---

### Implementation Strategy

#### Leverage Existing Infrastructure
- **Backend APIs**: No new endpoints required - enhance existing ones only
- **Component Library**: Adapt existing components rather than rebuild
- **State Management**: Extend existing hooks and stores
- **Validation Logic**: Reuse existing file and field validation

#### Progressive Enhancement Approach
- **Stage 1**: Enhance existing main page with new UI paradigms
- **Stage 2**: Create dedicated upload page using adapted components  
- **Stage 3**: Add advanced features and polish on solid foundation

#### Technical Considerations

##### Component Reusability
- **Maintain API Compatibility**: All existing service calls remain unchanged
- **Enhance, Don't Replace**: Adapt existing components to new UI patterns
- **Preserve Business Logic**: Keep existing validation, processing, and state management

##### Performance Strategy
- **Incremental Loading**: Load account and file data progressively
- **Smart Caching**: Cache frequently accessed data with appropriate TTL
- **Background Updates**: Use existing polling mechanisms for status updates

##### Testing Strategy
- **Component Adaptation Testing**: Ensure adapted components maintain functionality
- **Integration Testing**: Verify new UI flows work with existing backend
- **Accessibility Testing**: Comprehensive a11y testing for new interfaces
- **Performance Testing**: Validate optimizations don't impact existing functionality

### Migration and Deployment

#### Feature Flag Strategy
- **Stage 1**: Feature flag for enhanced main import page
- **Stage 2**: Gradual rollout of account upload pages
- **Stage 3**: Full feature release with advanced capabilities

#### Backward Compatibility
- **Preserve Existing Workflows**: Ensure existing import processes continue to work
- **Graceful Degradation**: New features degrade gracefully on older browsers
- **API Versioning**: Maintain compatibility with existing API contracts

#### Risk Mitigation
- **Component Testing**: Thorough testing of adapted components
- **Incremental Rollout**: Gradual deployment with monitoring
- **Rollback Strategy**: Ability to quickly revert to previous UI if needed

This revised approach leverages the sophisticated existing infrastructure while creating modern, intuitive user interfaces that enhance the import workflow experience.

## Analysis of Existing Transaction Import Functionality

### Current Implementation Overview

The existing codebase contains a comprehensive transaction file upload and import system with the following key components:

#### 1. File Upload Components

##### `TransactionFileUpload` Component
- **Location**: `/frontend/src/new-ui/components/business/transactions/TransactionFileUpload.tsx`
- **Features**:
  - Drag-and-drop file upload with visual feedback
  - File validation (size, type, content structure)
  - Support for CSV, QIF, OFX, QFX formats
  - Real-time file validation with detailed error messages
  - File preview with format-specific information
  - Accessibility features (keyboard navigation, ARIA labels)

**File Validation Logic**:
```typescript
// File size limit: 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// Supported formats
const ALLOWED_FILE_EXTENSIONS = ['.csv', '.qif', '.ofx', '.qfx'];

// Content validation for each format
- CSV: Delimiter detection, column consistency checking
- OFX: Header validation, XML structure checking  
- QIF: Format markers validation (!Type:, !Account)
- QFX: Similar to OFX validation
```

#### 2. Import History and Management

##### `ImportHistoryTable` Component
- **Location**: `/frontend/src/new-ui/components/ImportHistoryTable.tsx`
- **Features**:
  - Sortable table of uploaded files with metadata
  - Inline editing of account associations and field mappings
  - File status tracking (PENDING, PROCESSING, COMPLETED, ERROR)
  - Balance management (opening/closing balances)
  - Integration with field mapping dialog
  - File operations (view, download, delete)

**Key Data Structure**:
```typescript
interface FileMetadata {
  fileId: string;
  fileName: string;
  accountId?: string;
  accountName?: string;
  uploadDate: string;
  fieldMap?: { fileMapId?: string; name?: string; };
  fileFormat?: string;
  processingStatus?: string;
  openingBalance?: Decimal;
  closingBalance?: Decimal;
}
```

#### 3. Field Mapping System

##### `ImportStep2Preview` Component
- **Location**: `/frontend/src/new-ui/components/ImportStep2Preview.tsx`
- **Features**:
  - Interactive field mapping interface
  - Real-time validation of mapped columns
  - Field mapping profiles (save/load/update)
  - Transaction amount reversal option
  - Preview table with validation indicators
  - Support for required vs optional field mappings

**Field Mapping Process**:
```typescript
interface ColumnMapping {
  csvColumn: string | null;
  targetField: string;
  isValid?: boolean;
}

// Target fields for transaction mapping
const TARGET_TRANSACTION_FIELDS = [
  { field: 'date', label: 'Date', required: true },
  { field: 'amount', label: 'Amount', required: true },
  { field: 'description', label: 'Description', required: true },
  { field: 'category', label: 'Category', required: false },
  { field: 'account', label: 'Account', required: false },
];
```

#### 4. Service Layer Architecture

##### `FileService` - File Operations
- **Location**: `/frontend/src/services/FileService.ts`
- **Key API Calls**:

**File Upload Workflow**:
```typescript
// 1. Get presigned upload URL
getUploadUrl(fileName, contentType, fileSize, userId, accountId?) 
  → POST /api/files/upload
  → Returns: { fileId, url, fields, expires }

// 2. Upload to S3 directly
uploadFileToS3(presignedData, file, accountId?)
  → POST to S3 presigned URL
  → Direct S3 upload with FormData

// 3. Wait for processing
waitForFileProcessing(fileId, maxWaitTime, pollInterval)
  → GET /api/files/{fileId}/metadata (polling)
  → Returns: FileMetadata with processingStatus

// 4. Parse/preview file
parseFile(fileId)
  → GET /api/files/{fileId}/preview
  → Returns: { data, headers, file_format, error }
```

**File Management Operations**:
```typescript
// List files
listFiles() → GET /api/files
associateFileWithAccount(fileId, accountId) → PUT /api/files/{fileId}/associate
updateFileBalance(fileId, balance) → PUT /api/files/{fileId}/balance
updateFileClosingBalance(fileId, balance) → PUT /api/files/{fileId}/closing-balance
deleteFile(fileId) → DELETE /api/files/{fileId}
```

##### `FileMapService` - Field Mapping Operations
- **Location**: `/frontend/src/services/FileMapService.ts`
- **Key API Calls**:

```typescript
// Field mapping CRUD operations
listFieldMaps() → GET /file-maps
getFieldMap(fileMapId) → GET /file-maps/{fileMapId}
createFieldMap(fieldMap) → POST /file-maps
updateFieldMap(fileMapId, updates) → PUT /file-maps/{fileMapId}
deleteFieldMap(fileMapId) → DELETE /file-maps/{fileMapId}

// Field map structure
interface FieldMap {
  fileMapId: string;
  name: string;
  description?: string;
  accountId?: string;
  mappings: Array<{
    sourceField: string;    // CSV column name
    targetField: string;    // Target transaction field
  }>;
  reverseAmounts?: boolean;
  createdAt: string;
  updatedAt: string;
}
```

#### 5. Current Import Workflow

The existing system implements a comprehensive 3-step import process:

**Step 1: File Upload**
1. User selects file via drag-and-drop or file picker
2. Client-side validation (size, format, content structure)
3. Get presigned S3 upload URL from backend
4. Direct upload to S3 with metadata
5. Backend Lambda processes file asynchronously
6. Client polls for processing completion

**Step 2: Field Mapping & Preview**
1. Parse uploaded file to extract headers/structure
2. Load existing field mappings or create new mapping
3. Interactive mapping of CSV columns to transaction fields
4. Real-time validation of mapped data
5. Preview table showing mapped transactions
6. Save/update field mapping profiles

**Step 3: Import Completion**
1. Associate field mapping with file
2. Trigger final transaction processing
3. Update file metadata and status
4. Display import results and statistics

#### 6. State Management

##### `useImportState` Hook
- **Location**: `/frontend/src/new-ui/hooks/useImportState.ts`
- **Features**:
  - Import workflow state tracking
  - Progress monitoring (0-100%)
  - Step management (1-3)
  - Error and success state handling
  - Recent imports history

**Import Status Structure**:
```typescript
interface ImportStatus {
  isImporting: boolean;
  currentStep: number;
  totalSteps: number;
  currentFile?: {
    fileName: string;
    accountId: string;
    progress: number;
    status: 'uploading' | 'parsing' | 'processing' | 'complete' | 'error';
  };
  recentImports: Array<{
    fileName: string;
    accountName: string;
    importedAt: number;
    transactionCount: number;
    status: 'success' | 'error' | 'partial';
  }>;
}
```

#### 7. Integration Points

##### Current Import View
- **Location**: `/frontend/src/new-ui/views/ImportTransactionsView.tsx`
- **Current State**: Stage 1 implementation with placeholder functionality
- **Features**: Account list display, basic import state management, error handling

##### Statements/Imports Tab Integration
- **Location**: `/frontend/src/new-ui/components/business/transactions/StatementsImportsTab.tsx`
- **Integration**: Renders `ImportTransactionsView` directly

### API Endpoints Summary

The existing system uses the following API structure:

#### File Operations
```
POST   /api/files/upload              # Get presigned S3 URL
GET    /api/files                     # List user files
GET    /api/files/{id}                # Get file details
GET    /api/files/{id}/metadata       # Get file metadata
GET    /api/files/{id}/preview        # Parse and preview file
GET    /api/files/{id}/download       # Get download URL
DELETE /api/files/{id}                # Delete file
PUT    /api/files/{id}/associate      # Associate with account
PUT    /api/files/{id}/unassociate    # Remove account association
PUT    /api/files/{id}/balance        # Update opening balance
PUT    /api/files/{id}/closing-balance # Update closing balance
PUT    /api/files/{id}/file-map       # Associate field mapping
```

#### Field Mapping Operations
```
GET    /file-maps                     # List field mappings
GET    /file-maps/{id}                # Get specific mapping
POST   /file-maps                     # Create new mapping
PUT    /file-maps/{id}                # Update mapping
DELETE /file-maps/{id}                # Delete mapping
```

#### Account Integration
```
GET    /api/accounts/{id}/files       # List files for account
```

### Key Insights for Design Implementation

1. **Comprehensive System**: The existing implementation is already quite sophisticated with full file upload, processing, and mapping capabilities.

2. **Async Processing**: The system uses S3 direct upload with Lambda-based async processing, requiring polling for completion status.

3. **Rich Validation**: Multiple layers of validation (client-side format checking, server-side processing, field mapping validation).

4. **State Management**: Well-structured state management with progress tracking and error handling.

5. **Reusable Components**: Modular component architecture that can be adapted for the new design.

6. **API Maturity**: Comprehensive REST API with proper error handling and status tracking.

### Recommendations for New Design Implementation

1. **Leverage Existing Services**: The `FileService` and `FileMapService` can be used as-is for the new design.

2. **Adapt Components**: `TransactionFileUpload` and `ImportStep2Preview` can be adapted for the account-specific upload page.

3. **Enhance State Management**: The `useImportState` hook provides a solid foundation that can be extended.

4. **Maintain API Compatibility**: The existing API structure supports the new design requirements.

5. **Progressive Enhancement**: The new design can be implemented as an enhancement to the existing system rather than a replacement.
