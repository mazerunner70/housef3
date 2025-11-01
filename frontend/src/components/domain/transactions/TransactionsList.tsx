import React, { useEffect, useState, useMemo } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import {
    getUserTransactions,
    getCategories,
    quickUpdateTransactionCategory,
} from '@/services/TransactionService';
import { listAccounts } from '@/components/domain/accounts/services/AccountService';
import { CategoryInfo, TransactionRequestParams } from '@/schemas/Transaction';
import { Account } from '@/schemas/Account';
import TransactionFilters, { FilterValues as ComponentFilterValues } from './TransactionFilters';
import TransactionTable from '@/components/business/transactions/TransactionTable';
import './TransactionsList.css';
import { useTransactionsUIStore } from '@/stores/transactionsStore';

// Helper functions
const parseDateString = (dateStr: string | undefined): Date | null => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return Number.isNaN(date.getTime()) ? null : date;
};

const TransactionsList: React.FC = () => {
    const queryClient = useQueryClient();
    const { filters, pageSize, applyNewFilters, setPageSize } = useTransactionsUIStore();

    // Simple state
    const [accounts, setAccounts] = useState<Account[]>([]);
    const [categories, setCategories] = useState<CategoryInfo[]>([]);

    // Load initial data (accounts + categories)
    useEffect(() => {
        const loadInitialData = async () => {
            try {
                const [accountsRes, categoriesRes] = await Promise.all([
                    listAccounts(),
                    getCategories()
                ]);
                setAccounts(accountsRes.accounts);
                setCategories(categoriesRes);
            } catch (error) {
                console.error('Error loading initial data:', error);
            }
        };
        loadInitialData();
    }, []);

    // Build request params
    const buildParams = (pageParam?: any): TransactionRequestParams => {
        const startDateMs = filters.startDate ? parseDateString(filters.startDate)?.getTime() : undefined;
        const endDateSourceDate = parseDateString(filters.endDate);
        let endDateMs = endDateSourceDate ? endDateSourceDate.getTime() : undefined;
        if (endDateMs && endDateSourceDate) {
            const endOfDay = new Date(endDateSourceDate);
            endOfDay.setHours(23, 59, 59, 999);
            endDateMs = endOfDay.getTime();
        }

        return {
            pageSize,
            transactionType: filters.transactionType === 'all' ? undefined : filters.transactionType,
            searchTerm: filters.searchTerm || undefined,
            accountIds: filters.accountIds?.length ? filters.accountIds : undefined,
            categoryIds: filters.categoryIds?.length ? filters.categoryIds : undefined,
            startDate: startDateMs,
            endDate: endDateMs,
            sortBy: 'date',
            sortOrder: 'desc',
            lastEvaluatedKey: pageParam,
            ignoreDup: true,
        };
    };

    // Load transactions with pagination
    const {
        data,
        isLoading,
        error,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
    } = useInfiniteQuery({
        queryKey: ['transactions', filters, pageSize],
        queryFn: async ({ pageParam }: { pageParam: Record<string, any> | undefined }) => {
            const response = await getUserTransactions(buildParams(pageParam));
            return response;
        },
        getNextPageParam: (lastPage) => {
            return lastPage.loadMore.lastEvaluatedKey || undefined;
        },
        initialPageParam: undefined as Record<string, any> | undefined,
        staleTime: 120000,
    });

    // Derive combined transactions list from all pages
    const allTransactions = useMemo(() => {
        if (!data?.pages) return [];
        return data.pages.flatMap(page => page.transactions);
    }, [data]);

    // Handle filter changes
    const handleApplyFilters = (newFilters: ComponentFilterValues) => {
        // React Query will automatically reset when the query key changes
        applyNewFilters({
            startDate: newFilters.startDate,
            endDate: newFilters.endDate,
            accountIds: newFilters.accountIds || [],
            categoryIds: newFilters.categoryIds || [],
            transactionType: newFilters.transactionType || 'all',
            searchTerm: newFilters.searchTerm || '',
        });
    };

    // Handle page size change
    const handlePageSizeChange = (newPageSize: number) => {
        // React Query will automatically reset when the query key changes
        setPageSize(newPageSize);
    };

    // Handle category updates
    const [isQuickUpdating, setIsQuickUpdating] = useState(false);
    const handleQuickCategoryChange = async (transactionId: string, newCategoryId: string) => {
        setIsQuickUpdating(true);
        try {
            await (quickUpdateTransactionCategory as (transactionId: string, categoryId: string) => Promise<any>)(transactionId, newCategoryId);
            queryClient.invalidateQueries({ queryKey: ['transactions'] });
        } catch (err) {
            console.error("Error updating category:", err);
        } finally {
            setIsQuickUpdating(false);
        }
    };

    // Transform transactions with category info
    const transformedTransactions = useMemo(() => {
        if (!allTransactions.length || !categories.length) return allTransactions;

        const categoriesMap = new Map(categories.map(cat => [cat.categoryId, cat]));

        return allTransactions.map(transaction => ({
            ...transaction,
            // Keep category as the category ID string for compatibility
            category: transaction.primaryCategoryId || undefined,
            // Add category object as a separate field for display purposes
            categoryInfo: transaction.primaryCategoryId ? categoriesMap.get(transaction.primaryCategoryId) : undefined
        }));
    }, [allTransactions, categories]);

    const handleEditTransaction = (transactionId: string) => {
        console.log("Edit transaction:", transactionId);
        alert('Edit functionality to be implemented');
    };

    if (error) {
        return <div className="error-message">Error loading transactions: {error.message}</div>;
    }

    return (
        <div className="transactions-list-container">
            <div className="transactions-list-header">
                <h1>Transactions</h1>
                <button
                    className="add-transaction-button"
                    onClick={() => alert('Add Transaction Clicked!')}
                    aria-label="Add new transaction"
                >
                    ➕ Add Transaction
                </button>
            </div>

            <TransactionFilters
                accounts={accounts}
                categories={categories}
                initialFilters={filters}
                onApplyFilters={handleApplyFilters}
            />

            <TransactionTable
                transactions={transformedTransactions}
                isLoading={isLoading || isQuickUpdating || isFetchingNextPage}
                error={null}
                categories={categories}
                accountsData={accounts}
                onEditTransaction={handleEditTransaction}
                onQuickCategoryChange={handleQuickCategoryChange}
                hasMore={!!hasNextPage}
                onLoadMore={fetchNextPage}
                itemsLoaded={transformedTransactions.length}
                pageSize={pageSize}
                onPageSizeChange={handlePageSizeChange}
            />

            {isLoading && !transformedTransactions.length &&
                <div className="loading-spinner">Loading transactions...</div>
            }

            {!isLoading && !transformedTransactions.length &&
                <div className="transaction-table-empty">No transactions found.</div>
            }
        </div>
    );
};

export default TransactionsList;

