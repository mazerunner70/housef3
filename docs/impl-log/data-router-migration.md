# Data Router Migration - Implementation Log

**Feature:** React Router Data API Migration  
**Status:** Completed  
**Owner:** Frontend Team  
**ADR:** [ADR-0002: React Router Data API Migration](../architecture/adr/adr-0002-react-router-data-api.md)

## Implementation Timeline

### 2025-11-30: Migration Completed ✅
- Created `routes/router.tsx` with `createBrowserRouter`
- Added auth loaders (`protectedLoader`, `loginLoader`)
- Updated `main.tsx` to pass `queryClient` to App
- Updated `App.tsx` to use `RouterProvider`
- Updated `NewUILayout.tsx` to use native `useMatches()`
- Backed up old App as `App-BrowserRouter.tsx`

---

## Migration Checklist

### Phase 1: Core Infrastructure ✅
- [x] Created `routes/router.tsx` with `createBrowserRouter`
- [x] Added auth loaders (`protectedLoader`, `loginLoader`)
- [x] Updated `main.tsx` to pass `queryClient` to App
- [x] Updated `App.tsx` to use `RouterProvider`
- [x] Updated `NewUILayout.tsx` to use native `useMatches()`
- [x] Backed up old App as `App-BrowserRouter.tsx`

### Phase 2: Route Enhancement (As Needed)
- [ ] Add loaders to individual routes (as needed)
- [ ] Add actions to routes with forms (as needed)
- [ ] Implement unsaved data warnings (as needed)

---

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

---

## Implementation Examples

### Adding a Loader to a Route

Example: Add loader to transactions page to fetch data before rendering

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
  const url = new URL(request.url);
  const startDate = url.searchParams.get('startDate');
  const endDate = url.searchParams.get('endDate');
  
  const transactions = await fetchTransactions({
    startDate: startDate || undefined,
    endDate: endDate || undefined
  });
  
  return { transactions, filters: { startDate, endDate } };
};

// routes/router.tsx
import { transactionsLoader } from './loaders/transactionLoaders';

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

### Implementing Unsaved Data Warning

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

### Implementing Route Actions

```tsx
// In router.tsx
{
  path: 'accounts/:accountId',
  element: <AccountDetailPage />,
  loader: async ({ params }) => {
    const account = await fetchAccount(params.accountId);
    return { account };
  },
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

---

## Benefits Realized

### 1. Native `useMatches()` Support ✅
No need for custom hooks - `useMatches()` works natively with data routers.

```tsx
// In NewUILayout.tsx
const matches = useMatches(); // Now works natively!
```

### 2. Route Loaders for Data Fetching ✅
Load data before rendering a route - great for entity details.

### 3. Better Authentication Flow ✅
Auth handled at router level via loaders instead of component-level checks.

```tsx
export const protectedLoader = async () => {
  const authStatus = await rootLoader();
  if (!authStatus.authenticated) {
    return redirect('/login');
  }
  return authStatus;
};
```

### 4. Built-in Error Boundaries ✅
Route-level error handling with `errorElement`.

### 5. Data Persistence Callbacks ✅
Easy implementation of navigation guards and unsaved data warnings.

---

## Resources

- [React Router Data Router Documentation](https://reactrouter.com/en/main/routers/picking-a-router)
- [Route Loaders](https://reactrouter.com/en/main/route/loader)
- [Route Actions](https://reactrouter.com/en/main/route/action)
- [useBlocker Hook](https://reactrouter.com/en/main/hooks/use-blocker)

