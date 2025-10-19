# Frontend Conventions Alignment Summary

## Changes Made to Ensure Consistency

### ✅ Fixed Inconsistencies

#### 1. Service Architecture Description
**Before (Inconsistent):**
- `frontend-conventions.mdc`: "Service classes for backend API communication"
- `frontend-services-conventions.mdc`: "Prefer named function exports over class-based services"

**After (Aligned):**
- Both now specify: **"Functional exports for backend API communication (not classes)"**

#### 2. Code Colocation for Services
**Before:** 
- No guidance on when services should be domain-specific vs. shared

**After:**
- Added clear decision tree in both files
- Services can live in `components/domain/{feature}/services/` if used by one feature
- Services move to `src/services/` when reused across features
- Follows same "Rule of Three" pattern as other code

#### 3. Cross-References
**Before:**
- Services conventions operated in isolation

**After:**
- Services conventions now references frontend-conventions.mdc
- Explicitly mentions code colocation principle
- References progressive enhancement philosophy
- Clear "See Also" section at top

#### 4. Naming Conventions
**Before:**
- Only covered `src/services/` naming

**After:**
- Added naming for domain-specific services: `{domain}Api.ts` (camelCase)
- Clarified: PascalCase for shared services, camelCase for domain services
- Examples: `TransactionService.ts` (shared) vs. `transfersApi.ts` (domain)

#### 5. Service Characteristics
**Before:**
- Implicit understanding of service behavior

**After:**
- Explicitly stated: Services are **stateless** and **pure API clients**
- No state, no side effects beyond API calls
- Let React Query handle caching

## Aligned Principles

### Code Colocation (Now Consistent)

Both conventions now follow the same pattern:

```
1. Used by ONE feature?
   → components/domain/{feature}/services/

2. Used by MULTIPLE features?
   → src/services/

3. Rule of Three:
   → Abstract after third similar instance
```

### Progressive Enhancement (Now Consistent)

Both conventions reference the same philosophy:
- Start simple and explicit
- Abstract only when patterns emerge
- Prefer duplication over wrong abstraction
- "Rule of Three": Abstract after third similar instance

### Naming Patterns (Now Consistent)

| Location | Pattern | Example | Case |
|----------|---------|---------|------|
| Shared services | `{Domain}Service.ts` | `TransactionService.ts` | PascalCase |
| Domain services | `{domain}Api.ts` | `transfersApi.ts` | camelCase |
| Functions | `{verb}{Noun}` | `getAccount` | camelCase |
| Types | `{Name}` | `AccountResponse` | PascalCase |

## File Structure Alignment

### Frontend Conventions Structure
```
src/
├── components/
│   ├── domain/{feature}/
│   │   ├── {DomainName}Page.tsx
│   │   ├── hooks/
│   │   ├── utils/
│   │   ├── types/
│   │   └── services/          ← NOW DOCUMENTED
│   ├── business/
│   └── ui/
├── services/                   ← Shared across app
├── hooks/                      ← Shared across app
├── utils/                      ← Shared across app
└── types/                      ← Shared across app
```

### Services Location Decision Tree

```
Is API call used by ONE feature?
  ↓
YES → domain/{feature}/services/
  Example: components/domain/transfers/services/transfersApi.ts
  
NO → Is it used by MULTIPLE features?
  ↓
YES → src/services/
  Example: src/services/TransactionService.ts
```

## Cross-Reference Matrix

| Topic | Frontend Conventions | Services Conventions | Status |
|-------|---------------------|---------------------|--------|
| Code Colocation | ✅ Defined | ✅ References | ✅ Aligned |
| Progressive Enhancement | ✅ Defined | ✅ References | ✅ Aligned |
| Functional Architecture | ✅ Mentions | ✅ Detailed | ✅ Aligned |
| Naming Patterns | ✅ General | ✅ Specific | ✅ Aligned |
| Domain Structure | ✅ Defined | ✅ References | ✅ Aligned |
| Service Location | ✅ Added | ✅ Detailed | ✅ Aligned |

## Key Takeaways

### 1. Services Follow Same Colocation Rules
Services are not special - they follow the same colocation principles as hooks, utils, and types:
- Start in domain folders
- Move to shared when reused
- Apply "Rule of Three"

### 2. Two Types of Services
- **Shared Services** (`src/services/`) - Used across multiple features
- **Domain Services** (`domain/{feature}/services/`) - Used by one feature

### 3. Functional, Not Classes
All new services use functional exports, not class-based architecture.

### 4. Stateless API Clients
Services are pure API clients - no state, no caching, no side effects.

### 5. Consistent References
All conventions documents now reference each other for complete understanding.

## Updated Documentation Files

1. **frontend-conventions.mdc**
   - ✅ Corrected service description (functional, not classes)
   - ✅ Added reference to frontend-services-conventions.mdc
   - ✅ Added note about domain-specific services
   - ✅ Clarified services follow colocation principle

2. **frontend-services-conventions.mdc**
   - ✅ Added cross-reference to frontend-conventions.mdc
   - ✅ Added "Service Location Strategy" section
   - ✅ Added code colocation principle
   - ✅ Added progressive enhancement reference
   - ✅ Added naming conventions for domain services
   - ✅ Clarified stateless nature of services

## Validation Checklist

Use this to verify conventions are being followed:

### ✅ Service Location
- [ ] Service used by only one feature? → In domain folder
- [ ] Service used by multiple features? → In `src/services/`
- [ ] Following "Rule of Three" before abstracting

### ✅ Naming
- [ ] Shared services use PascalCase (`TransactionService.ts`)
- [ ] Domain services use camelCase (`transfersApi.ts`)
- [ ] Functions use camelCase (`getAccount`)
- [ ] Types use PascalCase (`AccountResponse`)

### ✅ Architecture
- [ ] Using functional exports (not classes)
- [ ] All API calls go through ApiClient
- [ ] Services are stateless
- [ ] No caching in services (use React Query)

### ✅ Documentation
- [ ] Services reference frontend-conventions.mdc principles
- [ ] Following code colocation principle
- [ ] Following progressive enhancement philosophy

## Conclusion

The frontend conventions are now **fully aligned and consistent**. Both documents:
- Reference each other appropriately
- Follow the same organizational principles
- Use consistent terminology
- Provide clear, actionable guidance

Developers can now confidently follow either document knowing they're consistent with the overall architecture! 🎯

