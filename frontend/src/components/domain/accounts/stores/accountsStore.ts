import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Account, AccountCreate } from '@/schemas/Account';
import {
    listAccounts as serviceListAccounts,
    createAccount as serviceCreateAccount,
    updateAccount as serviceUpdateAccount,
    deleteAccount as serviceDeleteAccount
} from '../services/AccountService';

// --- MAPPING FUNCTIONS ---

const mapAccountCreateToServiceInput = (accountData: AccountCreate): Partial<Account> => {
    // AccountCreate and ServiceAccount are compatible types from schemas
    return {
        accountName: accountData.accountName,
        accountType: accountData.accountType,
        institution: accountData.institution,
        currency: accountData.currency,
        balance: accountData.balance,
        notes: accountData.notes,
        isActive: true,
        defaultFileMapId: accountData.defaultFileMapId,
    };
};

interface AccountsState {
    // Data
    accounts: Account[];

    // Loading states
    isLoading: boolean;
    isCreating: boolean;
    isUpdating: boolean;
    isDeleting: boolean;

    // Error handling
    error: string | null;

    // Cache management
    lastFetched: number | null;
    cacheExpiry: number; // milliseconds

    // Actions
    fetchAccounts: (force?: boolean) => Promise<void>;
    createAccount: (accountData: AccountCreate) => Promise<Account | null>;
    updateAccount: (accountId: string, accountData: AccountCreate) => Promise<Account | null>;
    deleteAccount: (accountId: string) => Promise<boolean>;

    // Utility actions
    clearError: () => void;
    invalidateCache: () => void;
    getAccountById: (accountId: string) => Account | undefined;
    refreshAccount: () => Promise<void>;

    // Optimistic updates
    optimisticUpdate: (accountId: string, updates: Partial<Account>) => void;
    revertOptimisticUpdate: (accountId: string, originalAccount: Account) => void;

    // Cache management
    setCacheExpiry: (milliseconds: number) => void;
    isCacheValid: () => boolean;
}

// Cache duration: 2 days (for testing caching behavior)
const CACHE_DURATION = 2 * 24 * 60 * 60 * 1000;

export const useAccountsStore = create<AccountsState>()(
    persist(
        (set, get) => {
            return {
                // Initial state
                accounts: [],
                isLoading: false,
                isCreating: false,
                isUpdating: false,
                isDeleting: false,
                error: null,
                lastFetched: null,
                cacheExpiry: CACHE_DURATION,

                // Fetch accounts with intelligent caching
                fetchAccounts: async (force = false) => {
                    const state = get();
                    const now = Date.now();

                    // Debug localStorage persistence
                    const storedData = localStorage.getItem('accounts-storage');
                    console.warn('📦 LOCALSTORAGE DEBUG:', {
                        storedData: storedData ? JSON.parse(storedData) : null,
                        currentState: {
                            accounts: state.accounts.length,
                            lastFetched: state.lastFetched,
                            cacheExpiry: state.cacheExpiry
                        }
                    });

                    // Debug cache state
                    console.warn('🔍 ACCOUNTS CACHE DEBUG:', {
                        force,
                        lastFetched: state.lastFetched,
                        lastFetchedDate: state.lastFetched ? new Date(state.lastFetched).toISOString() : 'never',
                        cacheExpiry: state.cacheExpiry,
                        accountsLength: state.accounts.length,
                        timeSinceLastFetch: state.lastFetched ? now - state.lastFetched : 'never',
                        cacheAge: state.lastFetched ? `${Math.round((now - state.lastFetched) / 1000)}s` : 'never',
                        shouldFetchReasons: {
                            forced: force,
                            noLastFetched: !state.lastFetched,
                            cacheExpired: state.lastFetched ? (now - state.lastFetched) > state.cacheExpiry : false,
                            noAccounts: state.accounts.length === 0
                        }
                    });

                    // Check if we need to fetch (cache expired or forced)
                    const shouldFetch = force ||
                        !state.lastFetched ||
                        (now - state.lastFetched) > state.cacheExpiry ||
                        state.accounts.length === 0;

                    if (!shouldFetch) {
                        return;
                    }

                    set({ isLoading: true, error: null });

                    try {
                        const response = await serviceListAccounts();

                        // Use accounts directly - no mapping needed since we use the same type
                        const accounts = response.accounts;

                        set({
                            accounts: accounts,
                            isLoading: false,
                            lastFetched: now,
                            error: null
                        });
                    } catch (err: any) {
                        console.error("Error fetching accounts:", err);
                        set({
                            error: err.message || 'Failed to fetch accounts',
                            isLoading: false
                        });
                    }
                },

                // Create account with optimistic updates
                createAccount: async (accountData: AccountCreate) => {
                    set({ isCreating: true, error: null });

                    try {
                        // Map AccountCreate to service input
                        const serviceInput = mapAccountCreateToServiceInput(accountData);

                        const response = await serviceCreateAccount(serviceInput);

                        // Use account directly - no mapping needed
                        const newAccount = response.account;

                        set(state => ({
                            accounts: [...state.accounts, newAccount],
                            isCreating: false,
                            error: null
                        }));

                        return newAccount;
                    } catch (err: any) {
                        console.error("Error creating account:", err);
                        set({
                            error: err.message || 'Failed to create account',
                            isCreating: false
                        });
                        return null;
                    }
                },

                // Update account with optimistic updates
                updateAccount: async (accountId: string, accountData: AccountCreate) => {
                    const state = get();
                    const originalAccount = state.accounts.find(acc => acc.accountId === accountId);

                    if (!originalAccount) {
                        set({ error: 'Account not found' });
                        return null;
                    }

                    // Optimistic update
                    const optimisticAccount: Account = {
                        ...originalAccount,
                        accountName: accountData.accountName,
                        accountType: accountData.accountType,
                        currency: accountData.currency,
                        institution: accountData.institution,
                        balance: accountData.balance,
                        notes: accountData.notes,
                        // Keep other fields from original
                    };

                    set(state => ({
                        accounts: state.accounts.map(acc =>
                            acc.accountId === accountId ? optimisticAccount : acc
                        ),
                        isUpdating: true,
                        error: null
                    }));

                    try {
                        // Map AccountCreate to service input
                        const serviceInput = mapAccountCreateToServiceInput(accountData);

                        const response = await serviceUpdateAccount(accountId, serviceInput)();

                        // Use account directly - no mapping needed
                        const updatedAccount = response.account;

                        set(state => ({
                            accounts: state.accounts.map(acc =>
                                acc.accountId === accountId ? updatedAccount : acc
                            ),
                            isUpdating: false,
                            error: null
                        }));

                        return updatedAccount;
                    } catch (err: any) {
                        console.error("Error updating account:", err);

                        // Revert optimistic update
                        set(state => ({
                            accounts: state.accounts.map(acc =>
                                acc.accountId === accountId ? originalAccount : acc
                            ),
                            error: err.message || 'Failed to update account',
                            isUpdating: false
                        }));
                        return null;
                    }
                },

                // Delete account with optimistic updates
                deleteAccount: async (accountId: string) => {
                    const state = get();
                    const originalAccounts = [...state.accounts];

                    // Optimistic delete
                    set(state => ({
                        accounts: state.accounts.filter(acc => acc.accountId !== accountId),
                        isDeleting: true,
                        error: null
                    }));

                    try {
                        await serviceDeleteAccount(accountId);
                        set({ isDeleting: false, error: null });
                        return true;
                    } catch (err: any) {
                        console.error("Error deleting account:", err);

                        // Revert optimistic delete
                        set({
                            accounts: originalAccounts,
                            error: err.message || 'Failed to delete account',
                            isDeleting: false
                        });
                        return false;
                    }
                },

                // Utility actions
                clearError: () => set({ error: null }),

                invalidateCache: () => set({ lastFetched: null }),

                getAccountById: (accountId: string) => {
                    const state = get();
                    return state.accounts.find(acc => acc.accountId === accountId);
                },

                refreshAccount: async () => {
                    // Force refresh of all accounts by invalidating cache and fetching
                    set({ lastFetched: null });
                    await get().fetchAccounts(true);
                },

                // Optimistic update helpers
                optimisticUpdate: (accountId: string, updates: Partial<Account>) => {
                    set(state => ({
                        accounts: state.accounts.map(acc =>
                            acc.accountId === accountId ? { ...acc, ...updates } : acc
                        )
                    }));
                },

                revertOptimisticUpdate: (accountId: string, originalAccount: Account) => {
                    set(state => ({
                        accounts: state.accounts.map(acc =>
                            acc.accountId === accountId ? originalAccount : acc
                        )
                    }));
                },

                // Cache management
                setCacheExpiry: (milliseconds: number) => {
                    set({ cacheExpiry: milliseconds });
                },

                isCacheValid: () => {
                    const state = get();
                    const now = Date.now();
                    return state.lastFetched !== null &&
                        (now - state.lastFetched) < state.cacheExpiry;
                },
            };
        },
        {
            name: 'accounts-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                accounts: state.accounts,
                lastFetched: state.lastFetched,
                cacheExpiry: state.cacheExpiry,
            }),
        }
    )
);

// Selector hooks for better performance with explicit types
export const useAccounts = (): Account[] => useAccountsStore(state => state.accounts);

export const useAccountsLoading = (): {
    isLoading: boolean;
    isCreating: boolean;
    isUpdating: boolean;
    isDeleting: boolean;
} => useAccountsStore(state => ({
    isLoading: state.isLoading,
    isCreating: state.isCreating,
    isUpdating: state.isUpdating,
    isDeleting: state.isDeleting,
}));

export const useAccountsError = (): string | null => useAccountsStore(state => state.error);

// Individual action selectors for stable references
export const useFetchAccounts = (): ((force?: boolean) => Promise<void>) =>
    useAccountsStore(state => state.fetchAccounts);

export const useCreateAccount = (): ((accountData: AccountCreate) => Promise<Account | null>) =>
    useAccountsStore(state => state.createAccount);

export const useUpdateAccount = (): ((accountId: string, accountData: AccountCreate) => Promise<Account | null>) =>
    useAccountsStore(state => state.updateAccount);

export const useDeleteAccount = (): ((accountId: string) => Promise<boolean>) =>
    useAccountsStore(state => state.deleteAccount);

export const useClearError = (): (() => void) =>
    useAccountsStore(state => state.clearError);

// Combined actions hook with explicit return type (creates new object each time)
export const useAccountsActions = (): {
    fetchAccounts: (force?: boolean) => Promise<void>;
    createAccount: (accountData: AccountCreate) => Promise<Account | null>;
    updateAccount: (accountId: string, accountData: AccountCreate) => Promise<Account | null>;
    deleteAccount: (accountId: string) => Promise<boolean>;
    clearError: () => void;
    invalidateCache: () => void;
    getAccountById: (accountId: string) => Account | undefined;
} => useAccountsStore(state => ({
    fetchAccounts: state.fetchAccounts,
    createAccount: state.createAccount,
    updateAccount: state.updateAccount,
    deleteAccount: state.deleteAccount,
    clearError: state.clearError,
    invalidateCache: state.invalidateCache,
    getAccountById: state.getAccountById,
}));
