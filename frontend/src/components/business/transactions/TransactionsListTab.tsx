import React, { useEffect, useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getUserTransactions,
  getCategories,
  quickUpdateTransactionCategory,
} from '@/services/TransactionService';
import { listAccounts } from '@/components/domain/accounts/services/AccountService';
import { TransactionViewItem, CategoryInfo, TransactionRequestParams } from '@/schemas/Transaction';
import { Account } from '@/schemas/Account';
import TransactionFilters, { FilterValues as ComponentFilterValues } from './TransactionFilters';
import TransactionTable from './TransactionTable';
import '@/pages/TransactionsPage.css';
import { useTransactionsUIStore } from '@/stores/transactionsStore';

// Helper functions
const parseDateString = (dateStr: string | undefined): Date | null => {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  return Number.isNaN(date.getTime()) ? null : date;
};

const TransactionsListTab: React.FC = () => {
  const queryClient = useQueryClient();
  const { filters, pageSize, applyNewFilters, setPageSize } = useTransactionsUIStore();

  // Simple state
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [allTransactions, setAllTransactions] = useState<TransactionViewItem[]>([]);
  const [lastEvaluatedKey, setLastEvaluatedKey] = useState<any>(undefined);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

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
  const buildParams = (useLastKey = false): TransactionRequestParams => {
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
      lastEvaluatedKey: useLastKey ? lastEvaluatedKey : undefined,
      ignoreDup: true,
    };
  };

  // Load transactions (initial load)
  const { isLoading, error } = useQuery({
    queryKey: ['transactions', filters, pageSize],
    queryFn: async () => {
      const response = await getUserTransactions(buildParams(false));
      setAllTransactions(response.transactions);
      setLastEvaluatedKey(response.loadMore.lastEvaluatedKey);
      return response;
    },
    staleTime: 120000,
  });

  // Load more function
  const handleLoadMore = async () => {
    if (!lastEvaluatedKey || isLoadingMore) return;

    setIsLoadingMore(true);
    try {
      const response = await getUserTransactions(buildParams(true));
      setAllTransactions(prev => [...prev, ...response.transactions]);
      setLastEvaluatedKey(response.loadMore.lastEvaluatedKey);
    } catch (error) {
      console.error('Error loading more:', error);
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Handle filter changes
  const handleApplyFilters = (newFilters: ComponentFilterValues) => {
    setAllTransactions([]);
    setLastEvaluatedKey(undefined);

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
    setAllTransactions([]);
    setLastEvaluatedKey(undefined);
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
    <>
      <TransactionFilters
        accounts={accounts}
        categories={categories}
        initialFilters={filters}
        onApplyFilters={handleApplyFilters}
      />

      <TransactionTable
        transactions={transformedTransactions}
        isLoading={isLoading || isQuickUpdating}
        error={null}
        categories={categories}
        accountsData={accounts}
        onEditTransaction={handleEditTransaction}
        onQuickCategoryChange={handleQuickCategoryChange}
        hasMore={!!lastEvaluatedKey}
        onLoadMore={handleLoadMore}
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
    </>
  );
};

export default TransactionsListTab; 