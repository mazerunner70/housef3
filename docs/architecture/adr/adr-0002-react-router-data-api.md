# ADR-0002: React Router Data API Migration

**Status:** Accepted  
**Date:** 2025-11-30  
**Deciders:** Frontend Team

## Context

The frontend uses React Router for navigation. We need to decide between continuing with `BrowserRouter` (v6.4+ traditional API) or migrating to `createBrowserRouter` (Data Router API).

### Current Implementation (BrowserRouter)

```tsx
// main.tsx
<BrowserRouter>
  <App />
</BrowserRouter>

// App.tsx - conditional rendering based on auth
if (!authenticated) return <Login />;
return <Routes>...</Routes>
```

### Problems with Current Approach

1. **Custom Hook Workarounds**: `useMatches()` requires custom implementation instead of native support
2. **Mixed Concerns**: Authentication logic mixed with component rendering
3. **Limited Data Management**: No built-in support for route-level data fetching
4. **Manual Loading States**: Need to manage loading states in every component
5. **Form Handling**: No route-level form submission handling
6. **Navigation Blocking**: Complex implementation for unsaved changes warnings

## Decision

We will migrate to **React Router Data API** using `createBrowserRouter`.

### Key Changes

#### 1. Router Provider Pattern
```tsx
// main.tsx
<RouterProvider router={router} />

// App.tsx - router handles auth via loaders
const router = createAppRouter(queryClient);
return <RouterProvider router={router} />;
```

#### 2. Route Loaders for Data Fetching
```tsx
{
  path: 'accounts/:accountId',
  element: <AccountDetailPage />,
  loader: async ({ params }) => {
    const account = await fetchAccount(params.accountId);
    return { account };
  }
}
```

#### 3. Route Actions for Mutations
```tsx
{
  path: 'accounts/:accountId',
  action: async ({ request, params }) => {
    const formData = await request.formData();
    const name = formData.get('name') as string;
    await updateAccount(params.accountId, { name });
    return { success: true };
  }
}
```

#### 4. Loader-Based Authentication
```tsx
export const protectedLoader = async () => {
  const authStatus = await rootLoader();
  if (!authStatus.authenticated) {
    return redirect('/login');
  }
  return authStatus;
};
```

## Consequences

### Positive Consequences

1. **Native Functionality**
   - `useMatches()` works natively without custom hooks
   - Built-in navigation blocking with `useBlocker()`
   - Native form handling with `<Form>` component

2. **Better Data Management**
   - Route-level data fetching with loaders
   - Automatic loading states and error boundaries
   - Data available before component renders
   - Easier data dependencies between routes

3. **Cleaner Architecture**
   - Authentication at router level, not component level
   - Separation of data fetching from component logic
   - Route-level form submission handling
   - Better error boundaries at route level

4. **Improved Developer Experience**
   - Type-safe loaders with `useLoaderData()`
   - Declarative routing configuration
   - Better debugging with React Router DevTools
   - Easier testing with isolated loaders/actions

5. **Performance Benefits**
   - Data prefetching for better UX
   - Parallel data loading for nested routes
   - Optimistic UI updates with actions
   - Better code splitting opportunities

### Negative Consequences

1. **Migration Complexity**
   - Requires updating all route definitions
   - Need to refactor authentication logic
   - Potential breaking changes in existing components
   - Learning curve for team

2. **Breaking Changes**
   - Different API surface than BrowserRouter
   - Components relying on old patterns need updates
   - Custom hooks may need refactoring

3. **Initial Development Time**
   - Time to migrate existing routes
   - Need to implement loaders/actions
   - Testing overhead for new patterns

### Mitigation Strategies

1. **Phased Migration**: Keep BrowserRouter backup during transition
2. **Rollback Plan**: Documented process to revert if needed
3. **Code Examples**: Provide templates for common patterns
4. **Team Training**: Share examples and best practices

## Alternatives Considered

### Alternative 1: Keep BrowserRouter
**Rejected because:**
- Requires custom implementations for standard features
- Missing built-in data fetching patterns
- More boilerplate for common scenarios
- Harder to implement route-level authentication

### Alternative 2: Use TanStack Router
**Rejected because:**
- Additional dependency vs React Router upgrade
- Smaller community and ecosystem
- Team already familiar with React Router
- Migration would be more complex

### Alternative 3: Custom Data Fetching Layer
**Rejected because:**
- Reinventing functionality React Router provides
- More code to maintain
- Less standardized approach
- Harder for new developers to learn

## Implementation Notes

- See `docs/impl-log/data-router-migration.md` for migration steps
- Migration completed with rollback plan in place
- Examples provided for loaders, actions, and navigation blocking

## References

- Implementation log: `docs/impl-log/data-router-migration.md`
- React Router Data Router: https://reactrouter.com/en/main/routers/picking-a-router
- Route Loaders: https://reactrouter.com/en/main/route/loader
- Route Actions: https://reactrouter.com/en/main/route/action
- useBlocker Hook: https://reactrouter.com/en/main/hooks/use-blocker

