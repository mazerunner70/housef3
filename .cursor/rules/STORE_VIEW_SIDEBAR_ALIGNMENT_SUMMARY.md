# Store, View, and Sidebar Conventions Alignment Summary

## Overview
This document summarizes the alignment work done to ensure the store, view, and sidebar conventions are consistent with the main frontend conventions and follow the same organizational principles.

## Changes Made

### ✅ Store Conventions (frontend-store-conventions.mdc)

#### 1. Added Cross-Reference
**Before:** No reference to main conventions
**After:** Added "See Also" section linking to frontend-conventions.mdc

#### 2. Added Code Colocation Principles
**Before:** Only mentioned shared `src/stores/` location
**After:** Added complete colocation strategy:
```
Used by ONE feature → components/domain/{feature}/stores/
Used by MULTIPLE features → src/stores/
```

#### 3. Added Progressive Enhancement
**Before:** No guidance on when to share stores
**After:** Added "Rule of Three" - start domain-specific, share when reused

#### 4. Enhanced File Organization
**Before:** Only showed `src/stores/` structure
**After:** Shows both shared and domain-specific store locations

#### 5. Added Integration Context
**Before:** Stores described in isolation
**After:** Explicitly notes stores follow same colocation principles as other code

---

### ✅ Sidebar Conventions (frontend-sidebar-conventions.mdc)

#### 1. Added Cross-Reference
**Before:** No reference to main conventions
**After:** Added "See Also" section linking to frontend-conventions.mdc

#### 2. Removed "new-ui" References
**Before:** All paths referenced non-existent `new-ui/` folder
**After:** Updated to actual structure (`components/navigation/`)

#### 3. Added Domain-Specific Sidebar Section
**Before:** Only showed shared sidebar location
**After:** Added explicit section for domain-specific sidebars:
```
components/domain/{feature}/sidebar/
├── {Feature}SidebarContent.tsx
└── {feature}SidebarConfig.ts
```

#### 4. Added Decision Guide
**Before:** No guidance on when to use shared vs domain sidebars
**After:** Clear rules:
- Shared (`components/navigation/`): Used by multiple features
- Domain (`components/domain/{feature}/sidebar/`): Used by one feature only

#### 5. Added Integration Context
**Before:** Sidebars described in isolation
**After:** Explicitly states sidebars follow code colocation principle

---

### ✅ View Conventions (frontend-view-conventions.mdc)

#### 1. Added Cross-Reference
**Before:** No reference to main conventions
**After:** Added "See Also" section linking to frontend-conventions.mdc

#### 2. Removed "new-ui" References
**Before:** All paths referenced non-existent `new-ui/` folder
**After:** Updated to actual structure:
- `hooks/` or `components/domain/{feature}/hooks/`
- `components/business/{feature}/` or `components/domain/{feature}/`

#### 3. Added Colocation Guidance for Each Layer
**Before:** Fixed locations for all view components
**After:** Each layer now has colocation guidance:

**Hooks Layer:**
```
Location: hooks/ (if shared) or components/domain/{feature}/hooks/ (if domain-specific)
Colocation: Follow frontend-conventions.mdc - start in domain folder, move to shared when reused
```

**Layout Layer:**
```
Location: components/business/{feature}/ (if shared) or components/domain/{feature}/ (if domain-specific)
Colocation: Follow frontend-conventions.mdc - domain-specific layout components stay in domain folder
```

**Business Components Layer:**
```
Location: components/business/{feature}/ (if shared) or components/domain/{feature}/ (if feature-specific)
Colocation: Follow frontend-conventions.mdc - start in domain folder, promote to business/ when reused
```

**Modal Layer:**
```
Location: components/domain/{feature}/ or components/business/{feature}/
Colocation: Follow frontend-conventions.mdc - domain-specific modals stay in domain folder
```

#### 4. Added Two Organization Options
**Before:** Only showed one way to organize views
**After:** Shows two patterns:

**Option A: Feature-Specific (Colocation Pattern)**
```
components/domain/import/
├── ImportPage.tsx
├── ImportView.tsx
├── hooks/
├── ImportViewLayout.tsx
├── ImportHeader.tsx
└── ImportModals.tsx
```

**Option B: Shared Components (When Reused)**
```
views/ImportTransactionsView.tsx
hooks/ (shared)
components/business/import/ (shared)
```

**With Decision Rule:**
- Start with Option A (colocation)
- Move to Option B when reused
- Apply "Rule of Three"

#### 5. Added Integration Context
**Before:** Views described in isolation
**After:** Explicitly states "Views sit between Pages and Domain/Business Components in the hierarchy defined in frontend-conventions.mdc"

---

## Alignment Summary

### Common Principles Now Applied to All Conventions

| Principle | Services | Stores | Views | Sidebars | Status |
|-----------|----------|--------|-------|----------|--------|
| **Code Colocation** | ✅ | ✅ | ✅ | ✅ | Aligned |
| **Progressive Enhancement** | ✅ | ✅ | ✅ | ✅ | Aligned |
| **Cross-References** | ✅ | ✅ | ✅ | ✅ | Aligned |
| **Domain vs Shared** | ✅ | ✅ | ✅ | ✅ | Aligned |
| **Rule of Three** | ✅ | ✅ | ✅ | ✅ | Aligned |
| **No "new-ui" folder** | N/A | N/A | ✅ | ✅ | Aligned |

### Decision Trees (Now Consistent Across All)

All conventions now follow the same decision pattern:

```
Is it used by ONLY ONE feature?
  → YES: Place in components/domain/{feature}/{type}/
  → NO: Continue...

Is it used by MULTIPLE features?
  → YES: Place in src/{type}/ or components/business/{feature}/
  → NO: Continue...

Is it used across ENTIRE app?
  → YES: Place in src/{type}/
```

**Where {type} is:**
- `services/` for API clients
- `stores/` for state management
- `hooks/` for React hooks
- `sidebar/` for sidebar content
- Component files for views/layouts/modals

### File Organization Consistency

All conventions now use the same structure terminology:

```
src/
├── stores/               ← Shared state
├── services/             ← Shared API clients
├── hooks/                ← Shared hooks
├── components/
│   ├── domain/{feature}/
│   │   ├── {Feature}Page.tsx
│   │   ├── stores/       ← Domain-specific state
│   │   ├── services/     ← Domain-specific API calls
│   │   ├── hooks/        ← Domain-specific hooks
│   │   └── sidebar/      ← Domain-specific sidebar
│   ├── business/         ← Shared business components
│   ├── ui/               ← Generic reusable components
│   └── navigation/       ← Shared navigation/sidebar
└── views/                ← Shared complex views
```

---

## Cross-Reference Matrix

| Document | References | Referenced By |
|----------|------------|---------------|
| **frontend-conventions.mdc** | - | All other conventions |
| **frontend-services-conventions.mdc** | frontend-conventions.mdc | frontend-conventions.mdc |
| **frontend-store-conventions.mdc** | frontend-conventions.mdc | frontend-conventions.mdc |
| **frontend-sidebar-conventions.mdc** | frontend-conventions.mdc | frontend-conventions.mdc |
| **frontend-view-conventions.mdc** | frontend-conventions.mdc | frontend-conventions.mdc |

All specific conventions now reference the main conventions document for:
- Overall architecture principles
- Code colocation decision tree
- Progressive enhancement philosophy
- Domain vs shared placement rules

---

## Benefits of Alignment

### 1. Consistency
- Same organizational principles across all code types
- Same decision-making process for placement
- Same terminology throughout

### 2. Predictability
Developers can now predict where code should go:
- "If it's only used by transfers → in domain/transfers/"
- "If it's used by multiple features → promote to shared"
- Works for stores, services, hooks, views, sidebars, everything!

### 3. Reduced Cognitive Load
- One set of rules to learn
- No special cases for different code types
- Clear decision tree applies universally

### 4. Better Collaboration
- Team members understand where to find things
- Clear ownership boundaries
- Easier code reviews

### 5. Scalability
- Clear path from domain-specific to shared
- "Rule of Three" prevents premature abstraction
- Easy to refactor as needs evolve

---

## Validation Checklist

Use this to verify all conventions are being followed:

### ✅ Services
- [ ] Domain-specific API calls in `domain/{feature}/services/`?
- [ ] Shared services in `src/services/`?
- [ ] Following "Rule of Three" before abstracting?
- [ ] Using functional exports (not classes)?

### ✅ Stores
- [ ] Domain-specific state in `domain/{feature}/stores/`?
- [ ] Shared stores in `src/stores/`?
- [ ] Following single subscription pattern?
- [ ] Using explicit TypeScript types?

### ✅ Views
- [ ] Domain-specific views in `domain/{feature}/`?
- [ ] Shared views in `views/`?
- [ ] Using four-layer decomposition for complex views?
- [ ] Hooks/layouts/modals colocated appropriately?

### ✅ Sidebars
- [ ] Domain-specific sidebars in `domain/{feature}/sidebar/`?
- [ ] Shared sidebars in `components/navigation/`?
- [ ] Using configuration-driven approach?
- [ ] Following naming conventions?

### ✅ General
- [ ] All new code starts in domain folder?
- [ ] Only promotes to shared when reused?
- [ ] Applies "Rule of Three" principle?
- [ ] References appropriate conventions doc?

---

## Migration Path

### From Inconsistent to Aligned Organization

#### Step 1: Identify Code Type
Determine if it's a service, store, view, or sidebar component.

#### Step 2: Check Current Usage
Count how many features use this code:
- 1 feature → Should be in domain folder
- 2 features → Tolerate duplication (might be coincidence)
- 3+ features → Move to shared location

#### Step 3: Move if Needed
```
# Domain-specific (1 feature)
components/domain/transfers/
├── stores/transfersStore.ts
├── services/transfersApi.ts
├── hooks/useTransferLogic.ts
└── sidebar/TransfersSidebarContent.tsx

# Shared (3+ features)
src/stores/transactionsStore.ts
src/services/TransactionService.ts
src/hooks/useTransaction.ts
components/navigation/sidebar-content/TransactionsSidebarContent.tsx
```

#### Step 4: Update Imports
Update imports to reflect new location.

#### Step 5: Document Decision
If moving to shared, document which features use it and why it's shared.

---

## Updated File Paths

### Before (Inconsistent)
```
frontend/src/new-ui/views/                        ❌ Doesn't exist
frontend/src/new-ui/hooks/                        ❌ Doesn't exist
frontend/src/new-ui/components/business/          ❌ Doesn't exist
frontend/src/new-ui/components/navigation/        ❌ Doesn't exist
```

### After (Aligned)
```
frontend/src/views/                               ✅ Shared views
frontend/src/hooks/                               ✅ Shared hooks
frontend/src/stores/                              ✅ Shared stores
frontend/src/services/                            ✅ Shared services
frontend/src/components/
├── domain/{feature}/                             ✅ Domain-specific everything
│   ├── stores/
│   ├── services/
│   ├── hooks/
│   └── sidebar/
├── business/                                     ✅ Shared business components
├── ui/                                           ✅ Generic reusable
└── navigation/                                   ✅ Shared navigation/sidebar
```

---

## Key Takeaways

### 1. Universal Colocation Principle
All code follows the same placement rules:
- Start domain-specific
- Share when actually reused
- Apply "Rule of Three"

### 2. No Special Cases
Stores, services, views, sidebars - all follow the same rules. No exceptions, no special cases.

### 3. Progressive Enhancement
Don't abstract prematurely. Let patterns emerge naturally.

### 4. Cross-Referenced Documentation
All conventions reference each other appropriately, forming a cohesive whole.

### 5. Consistent Terminology
Same terms used across all documents:
- "Domain-specific" vs "Shared"
- "Code colocation"
- "Progressive enhancement"
- "Rule of Three"

---

## Files Updated

1. ✅ **frontend-store-conventions.mdc**
   - Added cross-reference
   - Added store location strategy
   - Added colocation principles
   - Enhanced file organization

2. ✅ **frontend-sidebar-conventions.mdc**
   - Added cross-reference
   - Removed "new-ui" references
   - Added domain-specific sidebar section
   - Added decision guide

3. ✅ **frontend-view-conventions.mdc**
   - Added cross-reference
   - Removed "new-ui" references
   - Added colocation guidance for all layers
   - Added two organization options
   - Added decision rules

4. ✅ **frontend-conventions.mdc** (previously updated)
   - Already had proper references
   - Already had colocation principles
   - Already had domain structure

---

## Conclusion

All frontend conventions are now **fully aligned and consistent**. The same organizational principles apply universally:

- **Code Colocation**: Place code as close to where it's used as possible
- **Progressive Enhancement**: Start simple, abstract when patterns emerge
- **Rule of Three**: Abstract after third similar instance
- **Domain First**: Start in domain folders, promote to shared when reused

Developers can now follow a single, consistent mental model across all code types! 🎯

