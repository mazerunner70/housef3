import { useEffect } from 'react';
import useAccountsWithStore, { Account } from '@/stores/useAccountsStore';

/**
 * Custom hook for managing account data specifically for the import workflow
 * 
 * Features:
 * - Fetches accounts on mount
 * - Sorts accounts by last import date (oldest first) to prioritize accounts needing imports
 * - Accounts with no imports appear first, followed by oldest imports
 * - Provides loading and error states
 * - Refetch capability for manual refresh
 */
interface UseAccountsDataReturn {
    accounts: Account[];
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
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
        fetchAccounts();
    }, [fetchAccounts]);

    // Sort accounts by last import date (oldest first) for import prioritization
    // Accounts with no imports (null/undefined importsEndDate) should appear first
    const sortedAccounts = [...rawAccounts].sort((a, b) => {
        const aLastImport = a.importsEndDate || 0;
        const bLastImport = b.importsEndDate || 0;

        // If both have no imports, sort by updatedAt as fallback
        if (aLastImport === 0 && bLastImport === 0) {
            return (a.updatedAt || 0) - (b.updatedAt || 0);
        }

        // Accounts with no imports come first (0 is less than any timestamp)
        return aLastImport - bLastImport;
    });

    const refetch = async () => {
        clearError();
        await fetchAccounts(true); // Force refresh
    };

    return {
        accounts: sortedAccounts,
        isLoading,
        error,
        refetch
    };
};

export default useAccountsData;
