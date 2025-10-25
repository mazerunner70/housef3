# Frontend Conventions Updates Summary

## Changes Made

### 1. Removed Non-Existent "new-ui" Folder Structure
**Before**: Conventions referenced `new-ui/` as a folder that doesn't exist  
**After**: Updated to reflect actual structure with folders directly under `src/`

**Updated paths**:
- `new-ui/layouts/` → `layouts/`
- `new-ui/pages/` → `pages/`
- `new-ui/components/` → `components/`
- `new-ui/hooks/` → `hooks/`
- `new-ui/views/` → `views/`
- `new-ui/styles/` → `styles/`

### 2. Clarified Component Organization Hierarchy
**New hierarchy**:
```
App.tsx
├── layouts/NewUILayout
    └── pages/ (Route containers)
        └── views/ or components/domain/ (Feature implementations)
            └── components/business/ (Shared business logic)
                └── components/ui/ (Reusable UI)
```

### 3. Added Code Colocation Principles
**New "Organization Principles" section** with clear decision tree:

1. **Feature-specific code** → `components/domain/{feature}/`
   - Use when code is only used by ONE feature
   - Keep hooks, utilities, types, sidebar content together
   - Example: `components/domain/transfers/hooks/`

2. **Shared business code** → `components/business/{domain}/`
   - Use when code is shared across MULTIPLE features
   - Example: Category selector used by transactions and rules

3. **App-wide code** → Top-level folders (`hooks/`, `utils/`, `types/`, `services/`)
   - Use only when code is truly used across entire app
   - Examples: `useLocale`, `dateUtils`, `AccountService`

**Key anti-pattern identified**: Don't prematurely create "shared" code. Start in domain folder and only promote when actual reuse occurs.

### 4. Introduced Domain Components Category
**New component type**: `components/domain/{feature}/`
- Self-contained feature folders
- Include all feature-specific code (components, hooks, utils, types, sidebar)
- Principle: "If it's only used by one feature, keep it in that feature's domain folder"

### 5. Updated Component Rules
**Clarified three distinct component types**:

1. **Domain Components** (`components/domain/{feature}/`)
   - Feature-specific, no reuse elsewhere
   - Self-contained with own hooks/utils/types

2. **Business Components** (`components/business/{domain}/`)
   - Shared across multiple features
   - Domain-specific logic

3. **UI Components** (`components/ui/`)
   - Reusable, domain-agnostic
   - Pure presentation

### 6. Updated Import Examples
**Before**: `import { Button } from '@/new-ui/components/ui/Button'`  
**After**:
- `import { Button } from '@/components/ui/Button'`
- `import { TransfersDashboard } from '@/components/domain/transfers/TransfersDashboard'`
- `import { useLocale } from '@/hooks/useLocale'`

### 7. Clarified Hooks Organization
**Updated guidance**:
- `src/hooks/` → Only for hooks shared across multiple features
- `components/domain/{feature}/hooks/` → For feature-specific hooks
- **Anti-pattern**: Creating hooks in top-level `hooks/` when only used by one feature

### 8. Updated UI Standards Section
**Before**: Referenced `new-ui/styles/` and `new-ui components`  
**After**: 
- Use `styles/theme.ts` for theme system
- Use `styles/global.css` for app-wide styling
- Removed "new-ui" terminology

## Migration Notes

### Legacy Structure
The conventions now acknowledge:
- **Legacy folders at root**: `components/accounts/`, `components/fzip/`
- **Status**: Being migrated to `components/domain/` structure
- This documents the transition state without claiming it's complete

### Practical Examples

**Good - Domain-specific code colocation**:
```
components/domain/transfers/
  ├── TransfersDashboard.tsx
  ├── TransfersDashboard.css
  ├── hooks/
  │   └── useTransferState.ts
  ├── utils/
  │   └── transferCalculations.ts
  └── types/
      └── TransferTypes.ts
```

**Good - Shared hooks in top-level**:
```
hooks/
  ├── useLocale.ts          # Used across entire app
  ├── useTableSort.ts       # Used by multiple features
  └── useSessionRouting.ts  # Used app-wide
```

**Bad - Premature abstraction**:
```
❌ hooks/useTransferState.ts  # Only used by transfers feature
✅ components/domain/transfers/hooks/useTransferState.ts
```

## Key Takeaways

1. **No "new-ui" folder** - All folders are directly under `src/`
2. **Colocation over abstraction** - Keep code near where it's used
3. **Three component types** - Domain (feature-specific), Business (shared domain logic), UI (reusable generic)
4. **Domain folders are self-contained** - Include hooks, utils, types when not reused
5. **Promote to shared only when needed** - Start local, move up only with actual reuse

## Alignment with Actual Codebase

These updates bring the conventions in line with the actual project structure, particularly:
- The transfers feature in `components/domain/transfers/`
- Shared hooks like `useLocale`, `useTableSort` in `src/hooks/`
- Business components in `components/business/`
- UI components in `components/ui/`
- Pages in `src/pages/`
- Views in `src/views/`
- Layouts in `src/layouts/`

