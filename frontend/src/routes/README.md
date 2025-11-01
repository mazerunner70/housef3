# Routes and Sidebar Configuration

## Overview

Routes and their sidebars are now explicitly connected through the route's `handle` property. This creates a clear, maintainable relationship between pages and their navigation context.

## How It Works

### 1. Route Definition with Sidebar

Each route can specify which sidebar to display using the `handle.sidebar` property:

```typescript
{
    path: 'transactions',
    element: <TransactionsPage />,
    handle: {
        breadcrumb: () => <Link to="/transactions">Transactions</Link>,
        sidebar: 'transactions'  // ← Explicitly specify sidebar
    } as RouteHandle
}
```

### 2. Sidebar Selection Logic

When a route is rendered, `ContextualSidebar` uses this logic:

1. **First Priority**: Check if route specifies `handle.sidebar`
   - Looks through matched routes (most specific first)
   - Uses the first sidebar key found
   
2. **Fallback**: Use first path segment
   - Example: `/accounts/123` → looks for 'accounts' sidebar
   
3. **Default**: Use 'default' sidebar if nothing matches

### 3. Sidebar Registry

Sidebars are registered at app startup in `registerSidebars.ts`:

```typescript
export function registerAllSidebars(): void {
    sidebarRegistry.register('accounts', AccountsSidebarContent);
    sidebarRegistry.register('transactions', TransactionsSidebarContent);
    // ... more registrations
}
```

## Route Handle Interface

```typescript
interface RouteHandle {
    /**
     * Function to render breadcrumb for this route
     */
    breadcrumb?: (match: UIMatch) => React.ReactNode;
    
    /**
     * Sidebar key - identifies which sidebar to display
     * Examples: 'accounts', 'transactions', 'categories', 'import', etc.
     */
    sidebar?: string;
}
```

## Benefits

### ✅ **Explicit Connection**
Routes explicitly declare their sidebar - no implicit string matching needed.

### ✅ **Type Safety**
TypeScript ensures sidebar keys are consistent across routes and registrations.

### ✅ **Maintainability**
Easy to see which sidebar a route uses and change it if needed.

### ✅ **Flexibility**
- Child routes can override parent sidebar
- Routes can share sidebars
- Easy to add new sidebars without changing base code

### ✅ **Graceful Fallback**
If `sidebar` is not specified, falls back to path-based lookup for backward compatibility.

## Example: Domain Organization

All routes for a domain can use the same sidebar:

```typescript
// Categories domain routes
{
    path: 'categories',
    handle: {
        breadcrumb: () => <Link to="/categories">Categories</Link>,
        sidebar: 'categories'
    }
},
{
    path: 'categories/:categoryId',
    handle: {
        breadcrumb: (match) => <Link>Category {match.params.categoryId}</Link>,
        sidebar: 'categories'  // Same sidebar for detail view
    }
},
{
    path: 'categories/:categoryId/transactions',
    handle: {
        breadcrumb: () => <Link>Transactions</Link>,
        sidebar: 'categories'  // Same sidebar for sub-views
    }
}
```

## Example: Overriding Sidebars

Child routes can specify different sidebars:

```typescript
{
    path: 'admin',
    handle: {
        sidebar: 'admin'  // Parent uses admin sidebar
    },
    children: [
        {
            path: 'users',
            handle: {
                sidebar: 'users'  // Child overrides with users sidebar
            }
        }
    ]
}
```

## Adding a New Route with Sidebar

1. **Define the route** in `appRoutes.tsx`:
```typescript
{
    path: 'myfeature',
    element: <MyFeaturePage />,
    handle: {
        breadcrumb: () => <Link to="/myfeature">My Feature</Link>,
        sidebar: 'myfeature'
    } as RouteHandle
}
```

2. **Create the sidebar** in `components/domain/myfeature/sidebar/`:
```typescript
// MyFeatureSidebarContent.tsx
const MyFeatureSidebarContent = ({ sidebarCollapsed }) => {
    return <BaseSidebarContent config={myFeatureConfig} sidebarCollapsed={sidebarCollapsed} />;
};
```

3. **Register the sidebar** in `registerSidebars.ts`:
```typescript
import MyFeatureSidebarContent from '@/components/domain/myfeature/sidebar/MyFeatureSidebarContent';

export function registerAllSidebars(): void {
    // ... existing registrations
    sidebarRegistry.register('myfeature', MyFeatureSidebarContent);
}
```

4. **Done!** The route and sidebar are now connected.

## Architecture Diagram

```
Route Definition (appRoutes.tsx)
    ↓
    handle.sidebar: 'transactions'
    ↓
ContextualSidebar (reads route matches)
    ↓
    looks up 'transactions' key
    ↓
Sidebar Registry (registerSidebars.ts)
    ↓
    returns TransactionsSidebarContent
    ↓
TransactionsSidebarContent (renders)
```

## Files Involved

- **`routes/types.ts`** - TypeScript interfaces for RouteHandle
- **`routes/appRoutes.tsx`** - Route definitions with sidebar keys
- **`components/navigation/ContextualSidebar.tsx`** - Reads sidebar from route matches
- **`components/navigation/sidebar-content/sidebarRegistry.ts`** - Registry pattern
- **`components/navigation/sidebar-content/registerSidebars.ts`** - Sidebar registrations
- **`components/domain/{feature}/sidebar/`** - Domain-specific sidebars

