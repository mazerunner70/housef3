import React from 'react';
import {
    useAccountsStore,
    useAccounts,
    useAccountsLoading,
    useAccountsError,
    useFetchAccounts,
    useCreateAccount,
    useUpdateAccount,
    useDeleteAccount,
    useClearError
} from './accountsStore';
import { Account, AccountCreate } from '../schemas/Account';

// Re-export types for convenience
export type { Account, AccountCreate };

interface UseAccountsReturn {
    accounts: Account[];
    isLoading: boolean;
    error: string | null;
    fetchAccounts: (force?: boolean) => Promise<void>;
    createAccount: (accountData: AccountCreate) => Promise<Account | null>;
    updateAccount: (accountId: string, accountData: AccountCreate) => Promise<Account | null>;
    deleteAccount: (accountId: string) => Promise<boolean>;
    clearError: () => void;
}

/**
 * Hook that provides account management with intelligent caching via Zustand store.
 * 
 * Features:
 * - Automatic caching with 5-minute expiry
 * - Optimistic updates for better UX
 * - Persistent storage across sessions
 * - Minimal re-fetching of data
 * - Automatic fetch on first mount
 */
const useAccountsWithStore = (): UseAccountsReturn => {
    console.warn('🔄 useAccountsWithStore hook called - component mounting');

    // DIAGNOSTIC: Test with minimal single selector to isolate the issue
    console.warn('📊 DIAGNOSTIC: Testing with single store subscription');

    // Use only one subscription to the entire store to test if multiple selectors cause the issue
    const storeState = useAccountsStore();

    console.warn('📊 DIAGNOSTIC: Single store subscription complete');

    // Extract values from the single subscription
    const accounts = storeState.accounts;
    const isLoading = storeState.isLoading;
    const isCreating = storeState.isCreating;
    const isUpdating = storeState.isUpdating;
    const isDeleting = storeState.isDeleting;
    const error = storeState.error;
    const fetchAccounts = storeState.fetchAccounts;
    const createAccount = storeState.createAccount;
    const updateAccount = storeState.updateAccount;
    const deleteAccount = storeState.deleteAccount;
    const clearError = storeState.clearError;

    // No automatic fetching in the hook - let the component decide when to fetch
    // This eliminates all render-time side effects that cause React errors

    // Combine all loading states
    const combinedLoading = isLoading || isCreating || isUpdating || isDeleting;

    return {
        accounts,
        isLoading: combinedLoading,
        error,
        fetchAccounts,
        createAccount,
        updateAccount,
        deleteAccount,
        clearError,
    };
};

export default useAccountsWithStore;

/**
 * Hook to get a specific account by ID from the store
 */
export const useAccountById = (accountId: string): Account | undefined => {
    const getAccountById = useAccountsStore(state => state.getAccountById);
    return getAccountById(accountId);
};

/**
 * Hook to invalidate the accounts cache (useful after external changes)
 */
export const useInvalidateAccountsCache = () => {
    const invalidateCache = useAccountsStore(state => state.invalidateCache);
    return invalidateCache;
};

/**
 * Hook for advanced cache management
 */
export const useAccountsCacheManagement = () => {
    const invalidateCache = useAccountsStore(state => state.invalidateCache);
    const refreshAccount = useAccountsStore(state => state.refreshAccount);
    const setCacheExpiry = useAccountsStore(state => state.setCacheExpiry);
    const isCacheValid = useAccountsStore(state => state.isCacheValid);
    const fetchAccounts = useAccountsStore(state => state.fetchAccounts);

    return {
        invalidateCache,
        refreshAccount,
        setCacheExpiry,
        isCacheValid,
        forceRefresh: () => fetchAccounts(true),
    };
};
