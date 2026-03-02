# Breadcrumb Fix for Data Router

## Issue

After migrating to `createBrowserRouter`, breadcrumbs were not showing.

## Root Cause

The Breadcrumb component only displays when there are **2 or more** breadcrumb items (see `Breadcrumb.tsx` line 205-207):

```tsx
if (breadcrumbMatches.length <= 1) {
    return null; // Don't show breadcrumb for single item
}
```

With the data router structure, when navigating to a route like `/transactions`:
- `useMatches()` returned only 1 match: the current route
- The parent layout route at `/` had no breadcrumb handle
- Result: Only 1 breadcrumb → component returns null

## Solution

Added a Home breadcrumb to the root layout route in `routes/router.tsx`:

```tsx
{
    path: '/',
    element: <NewUILayout />,
    handle: {
        breadcrumb: () => <Link to="/">Home</Link>
    },
    children: appRoutes.map(route => ({ ... }))
}
```

## How It Works Now

When navigating to `/transactions`:
1. `useMatches()` returns 2 matches:
   - Parent route `/` with "Home" breadcrumb
   - Child route `/transactions` with "Transactions" breadcrumb
2. Breadcrumb component receives 2 items
3. Since 2 > 1, breadcrumbs display: **Home / Transactions** ✅

## Why This Differs from BrowserRouter

### Old Implementation (BrowserRouter + Custom Hook)
The custom `useRouteMatches` hook **artificially constructed** breadcrumb trails by:
- Splitting the pathname into segments
- Progressively matching each segment
- Building a hierarchy even for flat routes

```tsx
// Custom hook would create:
// /transactions → ["/", "/transactions"]
```

### New Implementation (Data Router)
The native `useMatches()` hook returns **only actually matched routes** from the router configuration:
- No artificial construction
- Only returns routes that were matched in the router tree
- More accurate but requires proper route nesting

```tsx
// useMatches() returns:
// /transactions → [parent route, child route]
```

## Benefits

The new approach is:
- ✅ More accurate (reflects actual route structure)
- ✅ Simpler (no custom logic needed)
- ✅ Standard React Router pattern
- ✅ Works with route loaders and actions

## Future Considerations

If you want different breadcrumb behavior for certain routes:

### Option 1: Custom breadcrumb for root
```tsx
handle: {
    breadcrumb: (match) => {
        // Hide Home breadcrumb on home page
        if (match.pathname === '/') return null;
        return <Link to="/">Home</Link>;
    }
}
```

### Option 2: Nested route structure
```tsx
{
    path: 'admin',
    handle: {
        breadcrumb: () => <Link to="/admin">Admin</Link>
    },
    children: [
        {
            path: 'users',
            handle: {
                breadcrumb: () => <Link to="/admin/users">Users</Link>
            }
        }
    ]
}
// Result: Home / Admin / Users
```

### Option 3: Dynamic breadcrumbs with loaders
```tsx
{
    path: 'accounts/:accountId',
    loader: async ({ params }) => {
        const account = await fetchAccount(params.accountId);
        return { account };
    },
    handle: {
        breadcrumb: (match) => {
            const { account } = match.data || {};
            return <Link to={`/accounts/${match.params.accountId}`}>
                {account?.name || 'Loading...'}
            </Link>;
        }
    }
}
// Result: Home / Accounts / [Account Name]
```

## Files Changed

- `frontend/src/routes/router.tsx` - Added Home breadcrumb to root route
- `frontend/src/layouts/NewUILayout.tsx` - Cleaned up debug logging

## Testing

1. Navigate to any route (e.g., `/transactions`)
2. Verify breadcrumbs show: **Home / [Page Name]**
3. Click "Home" breadcrumb → should navigate to `/`
4. Test nested routes (e.g., `/categories/:id`) → should show trail

