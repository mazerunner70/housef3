# Component Organization Migration - Implementation Log

**Feature:** Four-Layer Component Organization  
**Status:** In Progress  
**Owner:** Frontend Team  
**ADR:** [ADR-0003: Four-Layer Component Organization Pattern](../architecture/adr/adr-0003-component-organization-pattern.md)

## Implementation Timeline

### 2025-11-30: Planning Phase
- Documented four-layer organization pattern in ADR-0003
- Created implementation guide
- Identified initial migration candidates

---

## Migration Strategy

### Phase 1: Extract Common UI Patterns ⏳

Start by identifying repeated patterns in existing code:

**Tasks:**
- [ ] **Currency Display**: Extract all currency formatting logic → `CurrencyAmount` ✅ (Already done)
- [ ] **Date Formatting**: Consistent date display across components
- [ ] **Status Indicators**: Common status/badge displays
- [ ] **Loading States**: Standardized loading indicators

### Phase 2: Create Business Components

Extract domain-specific display logic:

**Tasks:**
- [ ] **Category Components**: Category badges, selectors, hierarchies
- [ ] **Account Components**: Account displays, type indicators
- [ ] **Transaction Components**: Amount displays, status indicators
- [ ] **Analytics Components**: Metric cards, trend indicators

### Phase 3: Build Composite Components

Create reusable complex components:

**Tasks:**
- [ ] **Data Table**: Generic table with sorting, filtering, pagination
- [ ] **Form Components**: Reusable form layouts and validation
- [ ] **Search/Filter Components**: Standardized filtering interfaces
- [ ] **Modal Components**: Consistent modal patterns

### Phase 4: Refactor Domain Components

Update existing domain components to use new reusable components:

**Tasks:**
- [ ] **Transaction Views**: Use new table and form components
- [ ] **Account Views**: Use new display and form components
- [ ] **Analytics Views**: Use new chart and metric components

---

## Directory Structure Implementation

```
frontend/src/components/
├── ui/                    # Pure, reusable UI components
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── Button.css
│   ├── Table/
│   │   ├── Table.tsx
│   │   ├── TableHeader.tsx
│   │   ├── TableRow.tsx
│   │   └── Table.css
│   ├── Modal/
│   │   ├── Modal.tsx
│   │   ├── ModalHeader.tsx
│   │   ├── ModalBody.tsx
│   │   ├── ModalFooter.tsx
│   │   └── Modal.css
│   ├── Form/
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Checkbox.tsx
│   │   └── Form.css
│   ├── Loading/
│   │   ├── Spinner.tsx
│   │   ├── Skeleton.tsx
│   │   └── Loading.css
│   ├── Pagination/
│   │   ├── Pagination.tsx
│   │   └── Pagination.css
│   ├── CurrencyAmount.tsx     # ✅ Already implemented
│   ├── CategoryDisplay.tsx    # ✅ Already created
│   ├── ui-components.css      # Global UI component styles
│   └── index.ts              # Export all UI components
│
├── business/              # Business-specific reusable components
│   ├── Currency/
│   │   ├── CurrencyDisplay.tsx
│   │   ├── CurrencyInput.tsx
│   │   └── CurrencyConverter.tsx
│   ├── Category/
│   │   ├── CategoryBadge.tsx
│   │   ├── CategorySelector.tsx
│   │   ├── CategoryHierarchy.tsx
│   │   └── CategoryIcon.tsx
│   ├── Account/
│   │   ├── AccountDisplay.tsx
│   │   ├── AccountBadge.tsx
│   │   ├── AccountTypeIcon.tsx
│   │   └── AccountBalance.tsx
│   ├── Transaction/
│   │   ├── TransactionAmount.tsx
│   │   ├── TransactionDate.tsx
│   │   ├── TransactionStatus.tsx
│   │   ├── TransactionType.tsx
│   │   └── TransactionDescription.tsx
│   ├── Analytics/
│   │   ├── MetricCard.tsx
│   │   ├── TrendIndicator.tsx
│   │   └── PercentageDisplay.tsx
│   └── index.ts
│
├── composite/             # Complex reusable components
│   ├── DataTable/
│   │   ├── DataTable.tsx
│   │   ├── DataTableHeader.tsx
│   │   ├── DataTableRow.tsx
│   │   ├── DataTableCell.tsx
│   │   ├── DataTablePagination.tsx
│   │   └── DataTable.css
│   ├── SearchFilters/
│   │   ├── SearchFilters.tsx
│   │   ├── DateRangeFilter.tsx
│   │   ├── MultiSelectFilter.tsx
│   │   └── SearchFilters.css
│   ├── BulkActions/
│   │   ├── BulkActionsPanel.tsx
│   │   ├── BulkActionButton.tsx
│   │   └── BulkActions.css
│   ├── FileUpload/
│   │   ├── FileUploadArea.tsx
│   │   ├── FilePreview.tsx
│   │   └── FileUpload.css
│   └── index.ts
│
└── domain/                # Domain-specific components
    ├── transactions/
    │   ├── TransactionTable.tsx
    │   ├── TransactionFilters.tsx
    │   ├── TransactionBulkActions.tsx
    │   ├── TransactionImport.tsx
    │   └── TransactionAnalytics.tsx
    ├── accounts/
    │   ├── AccountList.tsx
    │   ├── AccountForm.tsx
    │   ├── AccountTransactionsTab.tsx
    │   ├── AccountFilesTab.tsx
    │   └── AccountAnalytics.tsx
    ├── categories/
    │   ├── CategoryManagement.tsx
    │   ├── CategoryRuleBuilder.tsx
    │   └── CategorySuggestions.tsx
    ├── analytics/
    │   ├── AnalyticsDashboard.tsx
    │   ├── CashFlowChart.tsx
    │   └── SpendingBreakdown.tsx
    └── files/
        ├── FileManager.tsx
        ├── FileProcessor.tsx
        └── FileMapping.tsx
```

---

## Implementation Guide

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

---

## Component Design Patterns

### Props Interface Design

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

### CSS Organization

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

### Export Strategy

```tsx
// components/ui/index.ts
export { default as Button } from './Button/Button';
export { default as Table } from './Table/Table';
export { default as CurrencyAmount } from './CurrencyAmount';

// components/business/index.ts
export { default as CategoryDisplay } from './Category/CategoryDisplay';
export { default as AccountBadge } from './Account/AccountBadge';
```

---

## Reference Implementation: CurrencyAmount

This is already implemented as an example:

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
  const amountClass = amount.greaterThanOrEqualTo(new Decimal(0)) 
    ? 'amount-income' 
    : 'amount-expense';

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

**Impact**: Transformed 29 lines of complex inline logic into a simple, reusable component.

---

## Layer Decision Guide

When creating a new component, use this guide to determine the correct layer:

### Choose UI Layer if:
- Component has no business domain knowledge
- Accepts all data via props
- Could be used in any application
- Examples: Button, Input, Modal, Table

### Choose Business Layer if:
- Component understands domain concepts (Currency, Category, Account)
- Reusable across multiple features
- Contains domain-specific logic/formatting
- Examples: CurrencyAmount, CategoryBadge, AccountTypeIcon

### Choose Composite Layer if:
- Component combines multiple UI/business components
- Handles complex interactions
- Has local state management
- Still reusable across features
- Examples: DataTable, SearchFilters, FileUpload

### Choose Domain Layer if:
- Component tied to specific feature
- May include API calls
- Uses hooks for data fetching
- Not intended for reuse outside domain
- Examples: TransactionTable, AccountForm, AnalyticsDashboard

---

## Benefits Realized

1. **Consistency**: UI elements look and behave the same everywhere
2. **Maintainability**: Change logic in one place, update everywhere
3. **Reusability**: Components can be used across different features
4. **Testability**: Smaller components are easier to test
5. **Developer Experience**: Cleaner code, easier to understand
6. **Design System**: Natural evolution toward a design system

---

## Next Steps

1. Complete Phase 1 (Extract common UI patterns)
2. Document each extracted component
3. Create component catalog/storybook
4. Establish code review guidelines for component placement
5. Continue gradual migration through Phase 4

