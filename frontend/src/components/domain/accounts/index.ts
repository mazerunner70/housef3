// Barrel exports for the accounts domain
export { default as AccountsPage } from './AccountsPage';
export { default as AccountFileUploadPage } from './AccountFileUploadPage';
export { default as AccountsDashboard } from './AccountsDashboard';
export { default as AccountFileUploadView } from './views/AccountFileUploadView';

// Re-export stores and hooks for convenience
export { default as useAccountsWithStore } from './stores/useAccountsStore';
export { useAccountsStore } from './stores/accountsStore';
export { useAccountsData } from './stores/useAccountsStore';

// Re-export commonly used types from schemas for convenience
export type {
    Account,
    AccountCreate,
    AccountUpdate,
    AccountListResponse,
    AccountSummary,
    AccountStats,
    AccountFilters
} from '@/schemas/Account';
