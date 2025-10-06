import { useMemo } from 'react';
import { TransactionViewItem } from '@/schemas/Transaction';
import { useTableSort } from './useTableSort';
import { SortFieldsConfig } from '@/utils/sortUtils';

/**
 * Specialized hook for TransactionViewItem sorting with predefined field configurations
 * and transaction-specific default sorting behavior.
 */
export function useTransactionViewSort(
    transactions: TransactionViewItem[],
    accountsMap: Map<string, string>
) {
    // Define field configurations for TransactionViewItem
    const fieldsConfig: SortFieldsConfig<TransactionViewItem> = {
        date: { type: 'date' },
        description: { type: 'string' },
        payee: { type: 'string' },
        category: { type: 'string' }, // categoryId as string
        accountId: { type: 'lookup' }, // Will use accountsMap for display names
        amount: { type: 'decimal' },
        balance: { type: 'decimal' },
        importOrder: { type: 'number' },
        transactionType: { type: 'string' },
        memo: { type: 'string' },
        checkNumber: { type: 'string' },
        reference: { type: 'string' },
        status: { type: 'string' },
        debitOrCredit: { type: 'string' }
    };

    // Define lookup maps for fields that need them
    const lookupMaps = {
        accountId: accountsMap,
        account: accountsMap // Support both field names
    };

    const sortHook = useTableSort({
        data: transactions,
        defaultSortKey: 'date',
        defaultSortDirection: 'descending',
        fieldsConfig,
        lookupMaps
    });

    // Apply default sorting when no sort is configured
    const sortedTransactions = useMemo(() => {
        if (sortHook.sortConfig.key) {
            return sortHook.sortedData;
        }

        // Default sorting: date + import order
        const defaultSorted = [...transactions].sort((a, b) => {
            const aOrder = a.importOrder ?? 0;
            const bOrder = b.importOrder ?? 0;
            const aSortKey = `${a.date.toString().padStart(15, '0')}_${aOrder.toString().padStart(10, '0')}`;
            const bSortKey = `${b.date.toString().padStart(15, '0')}_${bOrder.toString().padStart(10, '0')}`;
            return aSortKey.localeCompare(bSortKey);
        });

        return defaultSorted;
    }, [transactions, sortHook.sortedData, sortHook.sortConfig.key]);

    return {
        ...sortHook,
        sortedData: sortedTransactions
    };
}
