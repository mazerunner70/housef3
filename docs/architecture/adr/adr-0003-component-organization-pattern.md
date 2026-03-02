# ADR-0003: Four-Layer Component Organization Pattern

**Status:** Accepted  
**Date:** 2025-11-30  
**Deciders:** Frontend Team

## Context

The React frontend needs a clear component organization strategy as the application grows. Without a consistent pattern, components become:
- Difficult to locate and navigate
- Mixed in purpose (UI primitives vs business logic vs feature-specific)
- Hard to reuse across different parts of the application
- Inconsistent in styling and behavior
- Challenging to test in isolation

### Current State

Components are organized in a flat structure with mixed concerns:
- No clear separation between reusable and feature-specific components
- Business logic mixed with presentation logic
- Duplicate implementations of similar patterns
- Inconsistent styling approaches
- Difficult to identify reusable components

### Business Impact

- **Development Velocity**: Developers spend time recreating similar components
- **Consistency**: UI elements look and behave differently across features
- **Maintainability**: Changes require updates in multiple places
- **Testing**: Hard to test components in isolation
- **Onboarding**: New developers struggle to understand component hierarchy

## Decision

We will adopt a **four-layer component organization pattern** with clear separation of concerns:

### Layer 1: UI Components (`components/ui/`)

**Purpose**: Pure, reusable UI primitives with no business logic

**Characteristics**:
- No knowledge of business domain
- Accept all data via props
- Highly configurable through props
- No direct API calls or state management
- Focus on presentation and user interaction

**Examples**: `Button`, `Table`, `Modal`, `Input`, `Spinner`

```tsx
// Generic, domain-agnostic
<Button variant="primary" size="large" onClick={handleClick}>
  Save Changes
</Button>
```

### Layer 2: Business Components (`components/business/`)

**Purpose**: Domain-aware reusable components

**Characteristics**:
- Understand business domain (currencies, categories, accounts)
- Contain domain-specific logic and formatting
- Reusable across different views
- May include validation and business rules
- Still component-focused, not feature-focused

**Examples**: `CategoryDisplay`, `CurrencyAmount`, `AccountBadge`, `TransactionStatus`

```tsx
// Domain-specific but reusable
<CurrencyAmount 
  amount={transaction.amount} 
  currency={transaction.currency}
  showSign={true}
/>
```

### Layer 3: Composite Components (`components/composite/`)

**Purpose**: Complex components combining multiple UI/business components

**Characteristics**:
- Combine multiple smaller components
- Handle complex interactions
- May include local state management
- Reusable across different views
- No direct API calls

**Examples**: `DataTable`, `SearchFilters`, `FileUpload`, `BulkActionsPanel`

```tsx
// Complex but still reusable
<DataTable
  data={transactions}
  columns={columns}
  sortable={true}
  filterable={true}
  pagination={true}
/>
```

### Layer 4: Domain Components (`components/domain/`)

**Purpose**: Feature-specific components tied to business domains

**Characteristics**:
- Tied to specific business features
- May include API calls and complex state management
- Use hooks for data fetching and state management
- Combine multiple composite/business/UI components
- Not intended for reuse outside their domain

**Examples**: `TransactionTable`, `AccountForm`, `CategoryManagement`, `AnalyticsDashboard`

```tsx
// Feature-specific
<TransactionTable
  accountId={accountId}
  showAccountColumn={false}
  onCategoryUpdate={handleCategoryUpdate}
/>
```

### Directory Structure

```
frontend/src/components/
├── ui/                    # Layer 1: Pure UI primitives
│   ├── Button/
│   ├── Table/
│   ├── Modal/
│   └── index.ts          # Export all UI components
├── business/              # Layer 2: Domain-aware reusable
│   ├── Currency/
│   ├── Category/
│   ├── Account/
│   └── index.ts
├── composite/             # Layer 3: Complex reusable
│   ├── DataTable/
│   ├── SearchFilters/
│   └── index.ts
└── domain/                # Layer 4: Feature-specific
    ├── transactions/
    ├── accounts/
    ├── categories/
    └── analytics/
```

### Naming Conventions

- **UI components**: Generic names (`Button`, `Table`, `Modal`)
- **Business components**: Domain-specific names (`CategoryDisplay`, `AccountBadge`)
- **Composite components**: Descriptive names (`DataTable`, `SearchFilters`)
- **Domain components**: Feature-specific names (`TransactionTable`, `AccountForm`)

### Single Responsibility Principle

Each component should have one clear purpose:

```tsx
// Good: Focused on currency display
<CurrencyAmount amount={balance} currency="USD" />

// Bad: Mixed responsibilities
<TransactionRowWithCurrencyAndCategoryAndAccount transaction={tx} />
```

## Consequences

### Positive Consequences

1. **Clear Organization**
   - Easy to locate components by purpose and scope
   - Obvious where new components belong
   - Self-documenting architecture

2. **Better Reusability**
   - UI and business components reusable across features
   - Clear which components are meant for reuse
   - Easier to extract and share common patterns

3. **Improved Maintainability**
   - Single Responsibility Principle enforced
   - Changes localized to appropriate layer
   - Easier to refactor without breaking dependencies

4. **Easier Testing**
   - Smaller, focused components easier to test
   - Can test layers independently
   - Mock dependencies clearly defined by layer

5. **Better Developer Experience**
   - Cleaner code, easier to understand
   - New developers understand structure quickly
   - Natural evolution toward design system

6. **Consistency**
   - UI elements look and behave the same everywhere
   - Standardized patterns across application
   - Easier to enforce design standards

### Negative Consequences

1. **Initial Learning Curve**
   - Team needs to understand four-layer pattern
   - Decisions about which layer for new components
   - May feel over-engineered initially

2. **Migration Complexity**
   - Need to refactor existing components
   - Update imports throughout codebase
   - Potential for inconsistency during transition

3. **More Directories**
   - More navigation to find components
   - Could feel overwhelming initially
   - Need good IDE navigation

### Mitigation Strategies

1. **Clear Documentation**: Implementation guide with examples
2. **Gradual Migration**: Start with most repeated patterns
3. **Index Exports**: Use `index.ts` files for clean imports
4. **Code Reviews**: Ensure components in correct layer
5. **Examples**: Provide templates for each layer

## Alternatives Considered

### Alternative 1: Flat Component Structure
**Rejected because:**
- Doesn't scale as application grows
- No clear separation of concerns
- Difficult to identify reusable components
- Hard to enforce consistency

### Alternative 2: Feature-First Organization
**Rejected because:**
- Duplicates reusable components across features
- Harder to maintain consistency
- Difficult to share components between features
- Doesn't promote reusability

### Alternative 3: Atomic Design (Atoms/Molecules/Organisms)
**Rejected because:**
- Abstract terminology less intuitive for team
- Doesn't map well to business domain concepts
- Harder to determine component classification
- Four-layer pattern more aligned with actual use cases

### Alternative 4: Two-Layer (Shared/Feature)
**Rejected because:**
- Not enough granularity
- "Shared" becomes dumping ground
- Doesn't distinguish UI primitives from business components
- Harder to enforce SRP

## Implementation Notes

- See `docs/impl-log/component-organization-migration.md` for migration steps
- Start with Layer 1 (UI primitives) and Layer 2 (business components)
- Use CurrencyAmount as reference implementation
- Index exports for clean import paths

## References

- Implementation guide: `docs/impl-log/component-organization-migration.md`
- Example: `components/ui/CurrencyAmount.tsx`
- React Component Patterns: https://reactpatterns.com/
- Component-Driven Development: https://www.componentdriven.org/

