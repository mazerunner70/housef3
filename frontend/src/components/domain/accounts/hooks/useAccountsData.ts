import { useEffect } from 'react';
import useAccountsWithStore, { Account } from '../stores/useAccountsStore';

/**
 * Enhanced custom hook for managing account data specifically for the import workflow
 * 
 * Stage 1 Features:
 * - Fetches accounts on mount with comprehensive error handling
 * - Sorts accounts by updatedAt (oldest first) to prioritize accounts needing attention
 * - Accounts that haven't been updated recently appear first for import workflow
 * - Provides loading and error states with retry capability
 * - Enhanced metadata for import workflow optimization
 */

export type AccountForImport = Account;

interface UseAccountsDataReturn {
    accounts: AccountForImport[];
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
    accountCount: number;
    activeAccountCount: number;
    lastUpdated: number | null;
}

const useAccountsData = (): UseAccountsDataReturn => {
    const {
        accounts: rawAccounts,
        isLoading,
        error,
        fetchAccounts,
        clearError
    } = useAccountsWithStore();

    // Fetch accounts on component mount
    useEffect(() => {
        console.log('useAccountsData: Fetching accounts for import workflow...');
        fetchAccounts();
    }, [fetchAccounts]);

    // Sort accounts by updatedAt (oldest first) for import workflow priority
    // Accounts that haven't been updated recently should be prioritized for imports
    const sortedAccounts: AccountForImport[] = [...rawAccounts].sort((a, b) => {
        // Primary sort: updatedAt (oldest first)
        const aUpdated = a.updatedAt || 0;
        const bUpdated = b.updatedAt || 0;

        if (aUpdated !== bUpdated) {
            return aUpdated - bUpdated;
        }

        // Secondary sort: accounts with no imports first
        const aLastImport = a.importsEndDate || 0;
        const bLastImport = b.importsEndDate || 0;

        if (aLastImport !== bLastImport) {
            return aLastImport - bLastImport;
        }

        // Tertiary sort: by account name for consistency
        return a.accountName.localeCompare(b.accountName);
    });

    // Calculate metadata for import workflow
    const accountCount = sortedAccounts.length;
    const activeAccountCount = sortedAccounts.filter(account => account.isActive).length;

    const refetch = async () => {
        console.log('useAccountsData: Manual refetch requested');
        clearError();
        await fetchAccounts(true); // Force refresh
    };

    return {
        accounts: sortedAccounts,
        isLoading,
        error,
        refetch,
        accountCount,
        activeAccountCount,
        lastUpdated: Date.now() // Placeholder - will be enhanced in future versions
    };
};

export default useAccountsData;
