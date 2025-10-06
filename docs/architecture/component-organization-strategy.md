# Component Organization Strategy

## Overview

This document outlines a recommended approach for organizing React components to separate reusable UI components from business-specific ones. The goal is to create a maintainable, scalable component architecture that promotes reusability and consistency across the application.

## Directory Structure

```
frontend/src/new-ui/
├── components/
│   ├── ui/                    # Pure, reusable UI components
│   │   ├── Button/
│   │   │   ├── Button.tsx
│   │   │   └── Button.css
│   │   ├── Table/
│   │   │   ├── Table.tsx
│   │   │   ├── TableHeader.tsx
│   │   │   ├── TableRow.tsx
│   │   │   └── Table.css
│   │   ├── Modal/
│   │   │   ├── Modal.tsx
│   │   │   ├── ModalHeader.tsx
│   │   │   ├── ModalBody.tsx
│   │   │   ├── ModalFooter.tsx
│   │   │   └── Modal.css
│   │   ├── Form/
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Checkbox.tsx
│   │   │   └── Form.css
│   │   ├── Loading/
│   │   │   ├── Spinner.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── Loading.css
│   │   ├── Pagination/
│   │   │   ├── Pagination.tsx
│   │   │   └── Pagination.css
│   │   ├── CurrencyAmount.tsx     # Example: Already implemented
│   │   ├── CategoryDisplay.tsx    # Example: Created earlier
│   │   ├── ui-components.css      # Global UI component styles
│   │   └── index.ts              # Export all UI components
│   │
│   ├── business/              # Business-specific reusable components
│   │   ├── Currency/
│   │   │   ├── CurrencyDisplay.tsx
│   │   │   ├── CurrencyInput.tsx
│   │   │   └── CurrencyConverter.tsx
│   │   ├── Category/
│   │   │   ├── CategoryBadge.tsx
│   │   │   ├── CategorySelector.tsx
│   │   │   ├── CategoryHierarchy.tsx
│   │   │   └── CategoryIcon.tsx
│   │   ├── Account/
│   │   │   ├── AccountDisplay.tsx
│   │   │   ├── AccountBadge.tsx
│   │   │   ├── AccountTypeIcon.tsx
│   │   │   └── AccountBalance.tsx
│   │   ├── Transaction/
│   │   │   ├── TransactionAmount.tsx
│   │   │   ├── TransactionDate.tsx
│   │   │   ├── TransactionStatus.tsx
│   │   │   ├── TransactionType.tsx
│   │   │   └── TransactionDescription.tsx
│   │   ├── Analytics/
│   │   │   ├── MetricCard.tsx
│   │   │   ├── TrendIndicator.tsx
│   │   │   └── PercentageDisplay.tsx
│   │   └── index.ts
│   │
│   ├── composite/             # Complex reusable components
│   │   ├── DataTable/
│   │   │   ├── DataTable.tsx
│   │   │   ├── DataTableHeader.tsx
│   │   │   ├── DataTableRow.tsx
│   │   │   ├── DataTableCell.tsx
│   │   │   ├── DataTablePagination.tsx
│   │   │   └── DataTable.css
│   │   ├── SearchFilters/
│   │   │   ├── SearchFilters.tsx
│   │   │   ├── DateRangeFilter.tsx
│   │   │   ├── MultiSelectFilter.tsx
│   │   │   └── SearchFilters.css
│   │   ├── BulkActions/
│   │   │   ├── BulkActionsPanel.tsx
│   │   │   ├── BulkActionButton.tsx
│   │   │   └── BulkActions.css
│   │   ├── FileUpload/
│   │   │   ├── FileUploadArea.tsx
│   │   │   ├── FilePreview.tsx
│   │   │   └── FileUpload.css
│   │   └── index.ts
│   │
│   └── domain/                # Domain-specific components
│       ├── transactions/
│       │   ├── TransactionTable.tsx
│       │   ├── TransactionFilters.tsx
│       │   ├── TransactionBulkActions.tsx
│       │   ├── TransactionImport.tsx
│       │   └── TransactionAnalytics.tsx
│       ├── accounts/
│       │   ├── AccountList.tsx
│       │   ├── AccountForm.tsx
│       │   ├── AccountTransactionsTab.tsx
│       │   ├── AccountFilesTab.tsx
│       │   └── AccountAnalytics.tsx
│       ├── categories/
│       │   ├── CategoryManagement.tsx
│       │   ├── CategoryRuleBuilder.tsx
│       │   └── CategorySuggestions.tsx
│       ├── analytics/
│       │   ├── AnalyticsDashboard.tsx
│       │   ├── CashFlowChart.tsx
│       │   └── SpendingBreakdown.tsx
│       └── files/
│           ├── FileManager.tsx
│           ├── FileProcessor.tsx
│           └── FileMapping.tsx
```

## Component Categories

### 1. UI Components (`components/ui/`)

**Purpose**: Pure, reusable UI components with no business logic
**Characteristics**:
- No knowledge of business domain
- Accept all data via props
- Highly configurable through props
- No direct API calls or state management
- Focus on presentation and user interaction

**Examples**:
```tsx
// Button component
<Button variant="primary" size="large" onClick={handleClick}>
  Save Changes
</Button>

// Table component
<Table>
  <TableHeader>
    <TableRow>
      <TableCell>Name</TableCell>
      <TableCell>Amount</TableCell>
    </TableRow>
  </TableHeader>
</Table>
```

### 2. Business Components (`components/business/`)

**Purpose**: Business-specific reusable components that understand domain concepts
**Characteristics**:
- Understand business domain (currencies, categories, accounts, etc.)
- Contain domain-specific logic and formatting
- Reusable across different views
- May include validation and business rules

**Examples**:
```tsx
// Category display with business logic
<CategoryDisplay 
  category={category} 
  showIcon={true} 
  variant="badge" 
  showParent={true} 
/>

// Currency with domain-specific formatting
<CurrencyAmount 
  amount={transaction.amount} 
  currency={transaction.currency}
  showSign={true}
/>
```

### 3. Composite Components (`components/composite/`)

**Purpose**: Complex components that combine multiple UI/business components
**Characteristics**:
- Combine multiple smaller components
- Handle complex interactions
- May include local state management
- Reusable across different views

**Examples**:
```tsx
// Data table with sorting, filtering, pagination
<DataTable
  data={transactions}
  columns={columns}
  sortable={true}
  filterable={true}
  pagination={true}
/>

// File upload with preview and validation
<FileUpload
  accept=".csv,.ofx,.qif"
  onUpload={handleUpload}
  showPreview={true}
  validateFile={validateTransactionFile}
/>
```

### 4. Domain Components (`components/domain/`)

**Purpose**: Feature-specific components for particular domain areas
**Characteristics**:
- Tied to specific business features
- May include API calls and complex state management
- Use hooks for data fetching and state management
- Combine multiple composite/business/UI components

**Examples**:
```tsx
// Transaction table specific to transaction management
<TransactionTable
  accountId={accountId}
  showAccountColumn={false}
  onCategoryUpdate={handleCategoryUpdate}
/>

// Account form for account management
<AccountForm
  account={account}
  onSave={handleSave}
  onCancel={handleCancel}
/>
```

## Implementation Strategy

### Phase 1: Extract Common UI Patterns

Start by identifying repeated patterns in your existing code:

1. **Currency Display**: Extract all currency formatting logic
2. **Date Formatting**: Consistent date display across components
3. **Status Indicators**: Common status/badge displays
4. **Loading States**: Standardized loading indicators

### Phase 2: Create Business Components

Extract domain-specific display logic:

1. **Category Components**: Category badges, selectors, hierarchies
2. **Account Components**: Account displays, type indicators
3. **Transaction Components**: Amount displays, status indicators
4. **Analytics Components**: Metric cards, trend indicators

### Phase 3: Build Composite Components

Create reusable complex components:

1. **Data Table**: Generic table with sorting, filtering, pagination
2. **Form Components**: Reusable form layouts and validation
3. **Search/Filter Components**: Standardized filtering interfaces
4. **Modal Components**: Consistent modal patterns

### Phase 4: Refactor Domain Components

Update existing domain components to use the new reusable components:

1. **Transaction Views**: Use new table and form components
2. **Account Views**: Use new display and form components
3. **Analytics Views**: Use new chart and metric components

## Best Practices

### 1. Single Responsibility Principle
Each component should have one clear purpose:
```tsx
// Good: Focused on currency display
<CurrencyAmount amount={balance} currency="USD" />

// Bad: Mixed responsibilities
<TransactionRowWithCurrencyAndCategoryAndAccount transaction={tx} />
```

### 2. Props Interface Design
Design props to be flexible but typed:
```tsx
interface CurrencyAmountProps {
  amount: Decimal;
  currency?: string;
  precision?: number;
  showSign?: boolean;
  variant?: 'default' | 'compact' | 'large';
  className?: string;
}
```

### 3. Consistent Naming Convention
- UI components: Generic names (`Button`, `Table`, `Modal`)
- Business components: Domain-specific names (`CategoryDisplay`, `AccountBadge`)
- Composite components: Descriptive names (`DataTable`, `SearchFilters`)
- Domain components: Feature-specific names (`TransactionTable`, `AccountForm`)

### 4. CSS Organization
```
components/
├── ui/
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── Button.css          # Component-specific styles
│   └── ui-components.css       # Shared UI styles
├── business/
│   └── business-components.css # Shared business styles
└── composite/
    └── composite-components.css # Shared composite styles
```

### 5. Export Strategy
```tsx
// components/ui/index.ts
export { default as Button } from './Button/Button';
export { default as Table } from './Table/Table';
export { default as CurrencyAmount } from './CurrencyAmount';

// components/business/index.ts
export { default as CategoryDisplay } from './Category/CategoryDisplay';
export { default as AccountBadge } from './Account/AccountBadge';
```

## Migration Guide

### Step 1: Identify Candidates
Look for code that is:
- Repeated across multiple components
- Contains complex inline logic
- Handles domain-specific formatting
- Could benefit from consistency

### Step 2: Extract Gradually
Start with the smallest, most isolated pieces:
1. Extract inline formatting logic (like CurrencyAmount example)
2. Extract repeated JSX patterns
3. Extract complex conditional rendering
4. Extract form validation logic

### Step 3: Update Imports
As you extract components, update imports throughout the codebase:
```tsx
// Before
import { formatCurrency } from '../utils/formatters';

// After
import { CurrencyAmount } from '../components/ui';
```

### Step 4: Test and Validate
- Ensure visual consistency
- Test all component variants
- Verify no regressions in functionality
- Update any relevant tests

## Example: Current CurrencyAmount Implementation

This is already implemented in your codebase as an example:

```tsx
// components/ui/CurrencyAmount.tsx
import React from 'react';
import { Decimal } from 'decimal.js';

interface CurrencyAmountProps {
  amount: Decimal;
  currency?: string;
  className?: string;
}

const CurrencyAmount: React.FC<CurrencyAmountProps> = ({ 
  amount, 
  currency = 'USD', 
  className = '' 
}) => {
  const displayAmount = amount.toFixed(2);
  const currencySymbol = currency === 'USD' ? '$' : currency;
  const amountClass = amount.greaterThanOrEqualTo(new Decimal(0)) ? 'amount-income' : 'amount-expense';

  return (
    <span className={`${amountClass} ${className}`}>
      {currencySymbol}{displayAmount}
    </span>
  );
};

export default CurrencyAmount;
```

**Usage**:
```tsx
// In TransactionTable.tsx
<CurrencyAmount 
  amount={transaction.amount} 
  currency={transaction.currency} 
/>
```

This approach transformed 29 lines of complex inline logic into a simple, reusable component that can be used consistently throughout the application.

## Benefits

1. **Consistency**: UI elements look and behave the same everywhere
2. **Maintainability**: Change logic in one place, update everywhere
3. **Reusability**: Components can be used across different features
4. **Testability**: Smaller components are easier to test
5. **Developer Experience**: Cleaner code, easier to understand
6. **Design System**: Natural evolution toward a design system

## Conclusion

This organization strategy provides a clear path for building a maintainable, scalable component architecture. Start small with focused extractions like the CurrencyAmount example, and gradually build up your library of reusable components. The key is to be consistent and patient - this is an iterative process that will pay dividends over time. 