# Data Router Migration Guide

## Overview

We've migrated from React Router's `BrowserRouter` to `createBrowserRouter` (data router). This provides significant improvements for data management, authentication, and routing.

## What Changed

### Before (BrowserRouter)
```tsx
// main.tsx
<BrowserRouter>
  <App />
</BrowserRouter>

// App.tsx - conditional rendering based on auth
if (!authenticated) return <Login />;
return <Routes>...</Routes>
```

### After (Data Router)
```tsx
// main.tsx
<RouterProvider router={router} />

// App.tsx - router handles auth via loaders
const router = createAppRouter(queryClient);
return <RouterProvider router={router} />;
```

## Benefits

### 1. **Native `useMatches()` Support**
No need for custom hooks - `useMatches()` works natively with data routers.

```tsx
// In NewUILayout.tsx
const matches = useMatches(); // Now works natively!
```

### 2. **Route Loaders for Data Fetching**
Load data before rendering a route. Great for fetching entity details.

```tsx
// In router.tsx
{
  path: 'accounts/:accountId',
  element: <AccountDetailPage />,
  loader: async ({ params }) => {
    const account = await fetchAccount(params.accountId);
    return { account };
  }
}

// In AccountDetailPage.tsx
import { useLoaderData } from 'react-router-dom';

const AccountDetailPage = () => {
  const { account } = useLoaderData() as { account: Account };
  return <div>{account.name}</div>;
};
```

### 3. **Route Actions for Mutations**
Handle form submissions at the route level.

```tsx
// In router.tsx
{
  path: 'accounts/:accountId',
  element: <AccountDetailPage />,
  action: async ({ request, params }) => {
    const formData = await request.formData();
    const name = formData.get('name') as string;
    await updateAccount(params.accountId, { name });
    return { success: true };
  }
}

// In AccountDetailPage.tsx
import { Form } from 'react-router-dom';

<Form method="post">
  <input name="name" defaultValue={account.name} />
  <button type="submit">Save</button>
</Form>
```

### 4. **Better Authentication Flow**
Auth is now handled at the router level via loaders.

```tsx
// routes/router.tsx
export const protectedLoader = async () => {
  const authStatus = await rootLoader();
  if (!authStatus.authenticated) {
    return redirect('/login');
  }
  return authStatus;
};
```

All protected routes automatically check authentication before rendering.

### 5. **Data Persistence Callbacks**
You can now easily implement callbacks when navigating between routes:

```tsx
// Add to your route config
{
  path: 'accounts/:accountId',
  loader: async ({ params, request }) => {
    // Called BEFORE entering route
    console.log('Loading account:', params.accountId);
    
    // You can check if there's unsaved data
    const hasUnsavedData = checkUnsavedData();
    if (hasUnsavedData) {
      const confirmed = window.confirm('You have unsaved changes. Continue?');
      if (!confirmed) {
        throw new Response('Cancelled', { status: 499 });
      }
    }
    
    // Fetch data
    const account = await fetchAccount(params.accountId);
    return { account };
  }
}
```

For more complex scenarios, use `shouldRevalidate`:

```tsx
{
  path: 'accounts/:accountId',
  loader: accountLoader,
  shouldRevalidate: ({ currentUrl, nextUrl, formData }) => {
    // Only revalidate if the account ID changed
    return currentUrl.pathname !== nextUrl.pathname;
  }
}
```

### 6. **Error Handling**
Route-level error boundaries.

```tsx
{
  path: 'accounts/:accountId',
  element: <AccountDetailPage />,
  errorElement: <ErrorPage />,
  loader: async ({ params }) => {
    const account = await fetchAccount(params.accountId);
    if (!account) {
      throw new Response('Account not found', { status: 404 });
    }
    return { account };
  }
}

// ErrorPage.tsx
import { useRouteError } from 'react-router-dom';

const ErrorPage = () => {
  const error = useRouteError();
  return <div>Error: {error.statusText}</div>;
};
```

## Migration Checklist

- [x] Created `routes/router.tsx` with `createBrowserRouter`
- [x] Added auth loaders (`protectedLoader`, `loginLoader`)
- [x] Updated `main.tsx` to pass `queryClient` to App
- [x] Updated `App.tsx` to use `RouterProvider`
- [x] Updated `NewUILayout.tsx` to use native `useMatches()`
- [x] Backed up old App as `App-BrowserRouter.tsx`
- [ ] Add loaders to individual routes (as needed)
- [ ] Add actions to routes with forms (as needed)
- [ ] Implement unsaved data warnings (as needed)

## Rollback Plan

If you need to rollback to BrowserRouter:

1. Rename `App.tsx` to `App-DataRouter.tsx`
2. Rename `App-BrowserRouter.tsx` to `App.tsx`
3. Update `main.tsx`:
```tsx
import { BrowserRouter } from 'react-router-dom';

<BrowserRouter>
  <App />
</BrowserRouter>
```
4. Update `NewUILayout.tsx` to import `useRouteMatches` from hooks

## Example: Adding a Loader to a Route

Let's add a loader to the transactions page to fetch transactions before rendering:

```tsx
// services/TransactionService.ts
export const fetchTransactions = async (filters?: TransactionFilters) => {
  const queryParams = new URLSearchParams();
  if (filters?.startDate) queryParams.set('startDate', filters.startDate);
  if (filters?.endDate) queryParams.set('endDate', filters.endDate);
  
  const response = await apiClient.get(`/transactions?${queryParams}`);
  return response.data;
};

// routes/loaders/transactionLoaders.ts
import { LoaderFunctionArgs } from 'react-router-dom';
import { fetchTransactions } from '@/services/TransactionService';

export const transactionsLoader = async ({ request }: LoaderFunctionArgs) => {
  // Parse query params from URL
  const url = new URL(request.url);
  const startDate = url.searchParams.get('startDate');
  const endDate = url.searchParams.get('endDate');
  
  // Fetch transactions
  const transactions = await fetchTransactions({
    startDate: startDate || undefined,
    endDate: endDate || undefined
  });
  
  return { transactions, filters: { startDate, endDate } };
};

// routes/router.tsx
import { transactionsLoader } from './loaders/transactionLoaders';

// In your routes array:
{
  path: 'transactions',
  element: <TransactionsPage />,
  loader: transactionsLoader,
  handle: {
    breadcrumb: () => <Link to="/transactions">Transactions</Link>
  }
}

// pages/TransactionsPage.tsx
import { useLoaderData } from 'react-router-dom';

const TransactionsPage = () => {
  const { transactions, filters } = useLoaderData() as {
    transactions: Transaction[];
    filters: TransactionFilters;
  };
  
  return <TransactionsDashboard 
    initialTransactions={transactions}
    initialFilters={filters}
  />;
};
```

## Example: Implementing Unsaved Data Warning

```tsx
// hooks/useUnsavedChanges.ts
import { useEffect } from 'react';
import { useBlocker } from 'react-router-dom';

export const useUnsavedChanges = (hasUnsavedChanges: boolean) => {
  // Block navigation if there are unsaved changes
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasUnsavedChanges &&
      currentLocation.pathname !== nextLocation.pathname
  );

  // Handle browser refresh/close
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges]);

  return blocker;
};

// In your component:
const TransactionEditPage = () => {
  const [hasChanges, setHasChanges] = useState(false);
  const blocker = useUnsavedChanges(hasChanges);

  // Show confirmation dialog when navigation is blocked
  useEffect(() => {
    if (blocker.state === 'blocked') {
      const confirmed = window.confirm(
        'You have unsaved changes. Are you sure you want to leave?'
      );
      if (confirmed) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker]);

  // ... rest of component
};
```

## Resources

- [React Router Data Router Documentation](https://reactrouter.com/en/main/routers/picking-a-router)
- [Route Loaders](https://reactrouter.com/en/main/route/loader)
- [Route Actions](https://reactrouter.com/en/main/route/action)
- [useBlocker Hook](https://reactrouter.com/en/main/hooks/use-blocker)

