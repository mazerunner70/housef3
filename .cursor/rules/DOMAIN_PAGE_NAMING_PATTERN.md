# Domain Page Naming Pattern: `{DomainName}Page.tsx`

## The Pattern

Every routable domain folder should have a standardized entry point using the naming pattern:

```
{DomainName}Page.tsx
```

## Example Structure

```
components/domain/transfers/
├── TransfersPage.tsx           ← ENTRY POINT (routing jump off)
├── TransfersDashboard.tsx      ← Main feature component
├── TransferFilters.tsx         ← Supporting components
├── TransferList.tsx
├── hooks/
│   ├── useTransferDetection.ts
│   └── useTransferState.ts
├── utils/
│   └── transferCalculations.ts
├── types/
│   └── TransferTypes.ts
└── sidebar/
    └── TransfersSidebarContent.tsx
```

## Purpose of the Page File

The `{DomainName}Page.tsx` file serves as the **routing jump off point** for that domain:

1. **Sets up routing context** (breadcrumbs, navigation state)
2. **Renders the main domain component(s)**
3. **Provides a consistent entry point** for maintainers

## Benefits

### 1. 🎯 Predictable Location
When you open any domain folder, you immediately know:
- Is this domain routable? → Check for `{DomainName}Page.tsx`
- Where does routing start? → `{DomainName}Page.tsx`
- What gets rendered first? → Look inside `{DomainName}Page.tsx`

### 2. 🧭 Clear Orientation
Maintainers can quickly orient themselves:
```
"I need to understand the transfers feature"
  ↓
Open components/domain/transfers/
  ↓
See TransfersPage.tsx → This is the entry point
  ↓
Read TransfersPage → Renders TransfersDashboard
  ↓
Open TransfersDashboard.tsx → Main feature logic
```

### 3. 🔀 Separation of Concerns
```
TransfersPage.tsx          ← Routing concerns (breadcrumbs, context)
TransfersDashboard.tsx     ← Business logic (the actual feature)
```

Clear separation between:
- **What** gets routed (Page)
- **How** it works (Dashboard/main component)

### 4. 📝 Standardized Pattern
Every domain follows the same structure:
- `components/domain/accounts/AccountsPage.tsx`
- `components/domain/transfers/TransfersPage.tsx`
- `components/domain/portfolios/PortfoliosPage.tsx`
- `components/domain/analytics/AnalyticsPage.tsx`

No guessing, no inconsistency.

### 5. 🚀 Future-Proof
Easy to add routing concerns later:
```typescript
// Start simple
const TransfersPage = () => <TransfersDashboard />;

// Later: Add breadcrumbs
const TransfersPage = () => {
  useEffect(() => { goToTransfers(); }, []);
  return <TransfersDashboard />;
};

// Later: Add page header
const TransfersPage = () => {
  useEffect(() => { goToTransfers(); }, []);
  return (
    <>
      <PageHeader title="Transfers" />
      <TransfersDashboard />
    </>
  );
};
```

No route refactoring needed!

## Template

Use this template when creating a new routable domain:

```typescript
// components/domain/{feature}/{DomainName}Page.tsx
import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import {DomainName}Dashboard from './{DomainName}Dashboard';
import './{DomainName}Page.css';

/**
 * {DomainName}Page - Entry point for the {feature} domain
 * 
 * Role: Routing jump off point that sets up context and renders main component
 * Route: /{feature}
 */
const {DomainName}Page: React.FC = () => {
    const { goTo{DomainName} } = useNavigationStore();

    // Set up breadcrumbs/navigation context
    useEffect(() => {
        goTo{DomainName}();
    }, [goTo{DomainName}]);

    return (
        <div className="{feature}-page">
            <{DomainName}Dashboard />
        </div>
    );
};

export default {DomainName}Page;
```

## Routing Configuration

```typescript
// App.tsx
import TransfersPage from '@/components/domain/transfers/TransfersPage';

<Route path="/transfers" element={<TransfersPage />} />
```

## Two Page Patterns

### Pattern A: Multi-Feature Page (in `pages/`)
When grouping multiple related features under tabs:

```typescript
// pages/TransactionsPage.tsx
// Manages tabs for List, Categories, Imports, Transfers
<Route path="/transactions" element={<TransactionsPage />} />
```

### Pattern B: Single-Feature Page (in `components/domain/{feature}/`)
When deep linking to a single domain:

```typescript
// components/domain/transfers/TransfersPage.tsx
// Entry point for transfers domain
<Route path="/transfers" element={<TransfersPage />} />
```

**Both patterns can coexist!** The same `TransfersDashboard` can be rendered by:
1. `TransactionsPage` (as a tab)
2. `TransfersPage` (direct route)

## Comparison with Alternatives

### ❌ No Naming Standard
```
components/domain/transfers/
├── index.tsx              ← Is this the entry point? Or just exports?
├── Transfers.tsx          ← Is this the page or the dashboard?
├── TransfersMain.tsx      ← Main what?
├── Container.tsx          ← Container for what?
```
Result: Confusion, inconsistency, hard to navigate.

### ✅ With `{DomainName}Page.tsx` Standard
```
components/domain/transfers/
├── TransfersPage.tsx      ← 👈 Clear: This is the entry point
├── TransfersDashboard.tsx ← Clear: This is the main feature
├── TransferFilters.tsx    ← Clear: Supporting component
```
Result: Clarity, consistency, easy navigation.

## Decision Rules

### When to Create `{DomainName}Page.tsx`

✅ **Always create it when the domain is routable**
- Even if it's just 5 lines
- Provides predictable entry point
- Makes routing intent explicit
- Easy to extend later

❌ **Don't create it when:**
- Domain is not directly routable
- Components are only used by other pages
- Example: Small utility components that don't warrant their own route

## Examples from the Codebase

### Current: Transfers Domain
```
components/domain/transfers/
├── TransfersPage.tsx           ← Entry point ✅
├── TransfersDashboard.tsx      ← Main feature ✅
├── TransferService.ts
└── hooks/
```

**Routing:**
```typescript
<Route path="/transfers" element={<TransfersPage />} />
```

**Usage in TransfersPage:**
```typescript
const TransfersPage = () => {
  useEffect(() => { goToTransfers(); }, []);
  return <TransfersDashboard />;
};
```

Perfect example of the pattern! 🎯

## Migration Guide

If you have domains without standardized entry points:

### Step 1: Identify Routable Domains
Look in `App.tsx` for routes pointing to domain components:
```typescript
<Route path="/analytics" element={<AnalyticsComponent />} />
```

### Step 2: Create `{DomainName}Page.tsx`
```typescript
// components/domain/analytics/AnalyticsPage.tsx
const AnalyticsPage = () => {
  useEffect(() => { goToAnalytics(); }, []);
  return <AnalyticsComponent />;
};
```

### Step 3: Update Route
```typescript
// App.tsx
<Route path="/analytics" element={<AnalyticsPage />} />
```

### Step 4: Rename Main Component (Optional)
For clarity, rename main component to `{DomainName}Dashboard.tsx`:
```
AnalyticsComponent.tsx → AnalyticsDashboard.tsx
```

## Key Takeaway

**The `{DomainName}Page.tsx` naming pattern creates a predictable, maintainable structure where every routable domain has a clear entry point.**

When you see a domain folder, you instantly know:
- `{DomainName}Page.tsx` = where routing starts
- Everything else = feature implementation

This is the "jump off" pattern in action! 🚀

