# Zustand Stores Documentation

This directory contains Zustand stores for global state management with intelligent caching and optimistic updates.

## Accounts Store (`accountsStore.ts`)

The accounts store provides centralized account management with the following features:

### Key Features

1. **Intelligent Caching**: 5-minute cache expiry with automatic refresh logic
2. **Optimistic Updates**: Immediate UI updates with rollback on failure
3. **Persistent Storage**: Accounts cached in localStorage across sessions
4. **Minimal Re-fetching**: Only fetches when cache is expired or forced
5. **Loading States**: Separate loading states for different operations
6. **Error Handling**: Comprehensive error handling with user-friendly messages

### Usage

#### Basic Usage

```typescript
import useAccountsWithStore from '../stores/useAccountsStore';

const MyComponent = () => {
    const {
        accounts,
        isLoading,
        error,
        createAccount,
        updateAccount,
        deleteAccount,
        clearError
    } = useAccountsWithStore();

    // Accounts are automatically fetched on first mount
    // Subsequent mounts use cached data if still valid
    
    return (
        <div>
            {isLoading && <p>Loading accounts...</p>}
            {error && <p>Error: {error}</p>}
            {accounts.map(account => (
                <div key={account.id}>{account.name}</div>
            ))}
        </div>
    );
};
```

#### Advanced Cache Management

```typescript
import { useAccountsCacheManagement } from '../stores/useAccountsStore';

const AdminComponent = () => {
    const {
        invalidateCache,
        refreshAccount,
        setCacheExpiry,
        isCacheValid,
        forceRefresh
    } = useAccountsCacheManagement();

    const handleFileUpload = async () => {
        // After uploading files that might affect accounts
        await uploadFiles();
        invalidateCache(); // Next access will fetch fresh data
    };

    const handleUserPreference = () => {
        // User wants longer cache for slower connections
        setCacheExpiry(15 * 60 * 1000); // 15 minutes
    };

    const handleRefreshButton = async () => {
        // User explicitly wants fresh data
        await forceRefresh();
    };

    return (
        <div>
            <button onClick={handleRefreshButton}>
                Refresh Accounts
            </button>
            <p>Cache is {isCacheValid() ? 'valid' : 'expired'}</p>
        </div>
    );
};
```

#### Getting Specific Account

```typescript
import { useAccountById } from '../stores/useAccountsStore';

const AccountDetail = ({ accountId }: { accountId: string }) => {
    const account = useAccountById(accountId);
    
    if (!account) {
        return <p>Account not found</p>;
    }
    
    return <div>{account.name}</div>;
};
```

### Cache Strategies

#### When Cache is Used
- **First Mount**: Fetches fresh data and caches it
- **Subsequent Mounts**: Uses cached data if less than 5 minutes old
- **Component Re-renders**: Always uses cached data (no re-fetch)

#### When Fresh Data is Fetched
- Cache is older than 5 minutes
- `forceRefresh()` is called
- `invalidateCache()` is called and data is accessed
- No cached data exists

#### Cache Invalidation Strategies

1. **After External Changes**
   ```typescript
   // After file uploads, imports, or external account modifications
   invalidateCache();
   ```

2. **User-Requested Refresh**
   ```typescript
   // When user clicks refresh button
   await forceRefresh();
   ```

3. **After Account Operations**
   ```typescript
   // After creating/updating/deleting accounts
   // (Handled automatically by the store)
   ```

### Optimistic Updates

The store implements optimistic updates for better UX:

#### Create Account
- Immediately adds account to UI
- Rollback if API call fails

#### Update Account
- Immediately updates account in UI
- Reverts to original if API call fails

#### Delete Account
- Immediately removes account from UI
- Restores account if API call fails

### Error Handling

```typescript
const { error, clearError } = useAccountsWithStore();

useEffect(() => {
    if (error) {
        // Show error to user
        showNotification(error);
        clearError(); // Clear after showing
    }
}, [error, clearError]);
```

### Performance Considerations

1. **Selector Hooks**: Use specific selector hooks for better performance
   ```typescript
   // Instead of destructuring everything
   const { accounts } = useAccountsWithStore();
   
   // Use specific selectors
   const accounts = useAccounts();
   const { isLoading } = useAccountsLoading();
   ```

2. **Cache Management**: Don't invalidate cache unnecessarily
   ```typescript
   // Good: Only invalidate when external changes occur
   if (externalChangeOccurred) {
       invalidateCache();
   }
   
   // Bad: Invalidating on every render
   useEffect(() => {
       invalidateCache(); // This will cause infinite re-renders
   });
   ```

### Usage in Components

The store provides a clean, familiar API:

```typescript
import useAccountsWithStore from '../stores/useAccountsStore';

const MyComponent = () => {
    const { accounts, isLoading, error, createAccount } = useAccountsWithStore();
    
    // Benefits you get automatically:
    // - Intelligent caching across components
    // - Reduced API calls
    // - Persistent storage across sessions
    // - Better performance with optimistic updates
    
    return (
        <div>
            {isLoading && <p>Loading...</p>}
            {accounts.map(account => <div key={account.id}>{account.name}</div>)}
        </div>
    );
};
```

### Store Structure

```typescript
interface AccountsState {
    // Data
    accounts: UIAccount[];
    
    // Loading states
    isLoading: boolean;
    isCreating: boolean;
    isUpdating: boolean;
    isDeleting: boolean;
    
    // Error handling
    error: string | null;
    
    // Cache management
    lastFetched: number | null;
    cacheExpiry: number;
    
    // Actions
    fetchAccounts: (force?: boolean) => Promise<void>;
    createAccount: (data: UIAccountInputData) => Promise<UIAccount | null>;
    updateAccount: (id: string, data: UIAccountInputData) => Promise<UIAccount | null>;
    deleteAccount: (id: string) => Promise<boolean>;
    
    // Utilities
    clearError: () => void;
    invalidateCache: () => void;
    getAccountById: (id: string) => UIAccount | undefined;
    // ... other utility methods
}
```

### Best Practices

1. **Use the hook, not the store directly**
   ```typescript
   // Good
   import useAccountsWithStore from '../stores/useAccountsStore';
   
   // Avoid (unless you need direct store access)
   import { useAccountsStore } from '../stores/accountsStore';
   ```

2. **Handle loading states appropriately**
   ```typescript
   const { accounts, isLoading } = useAccountsWithStore();
   
   if (isLoading && accounts.length === 0) {
       return <LoadingSpinner />;
   }
   
   // Show cached data while refreshing
   return (
       <div>
           {isLoading && <RefreshIndicator />}
           <AccountList accounts={accounts} />
       </div>
   );
   ```

3. **Clear errors after handling**
   ```typescript
   useEffect(() => {
       if (error) {
           showErrorNotification(error);
           clearError(); // Important: clear after handling
       }
   }, [error, clearError]);
   ```

4. **Use cache invalidation strategically**
   ```typescript
   // Good: Invalidate after external changes
   const handleFileUpload = async () => {
       await uploadFile();
       invalidateCache(); // Accounts might have changed
   };
   
   // Good: Force refresh on user request
   const handleRefreshClick = () => {
       forceRefresh();
   };
   ```

This store provides a robust foundation for account management with minimal API calls and excellent user experience through caching and optimistic updates.
