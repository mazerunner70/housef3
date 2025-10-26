// Re-export the accounts store and hooks from the domain location
// This provides a consistent import path for components that need accounts functionality

export {
    useAccountsStore,
    useAccounts,
    useAccountsLoading,
    useAccountsError,
    useFetchAccounts,
    useCreateAccount,
    useUpdateAccount,
    useDeleteAccount,
    useClearError,
    useAccountsActions,
    useAccountById,
    useInvalidateAccountsCache,
    useAccountsCacheManagement
} from '@/components/domain/accounts/stores/useAccountsStore';

export { default as useAccountsWithStore } from '@/components/domain/accounts/stores/useAccountsStore';
