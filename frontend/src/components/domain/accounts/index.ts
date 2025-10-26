// Barrel exports for the accounts domain
export { default as AccountsPage } from './AccountsPage';
export { default as AccountsDashboard } from './AccountsDashboard';

// Re-export stores and hooks for convenience
export { default as useAccountsWithStore } from './stores/useAccountsStore';
export { useAccountsStore } from './stores/accountsStore';

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
