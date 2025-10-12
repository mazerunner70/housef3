import { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getAccountTransactions,
  getCategories,
  quickUpdateTransactionCategory,
} from '../services/TransactionService';
import {
  Transaction,
  TransactionViewItem,
  CategoryInfo,
  TransactionListResponse,
} from '../schemas/Transaction';

// Transform the response to match TransactionViewItem format
const transformAccountTransactions = (response: TransactionListResponse, categories: CategoryInfo[]): TransactionViewItem[] => {
  if (!response.transactions || categories.length === 0) {
    return response.transactions?.map((tx: Transaction) => ({
      ...tx,
      id: tx.transactionId,
      account: tx.accountId || '',
      type: (tx.debitOrCredit === 'DEBIT' ? 'expense' : 'income') as 'income' | 'expense' | 'transfer',
    } as TransactionViewItem)) || [];
  }

  // Transform transactions to include category ID
  return response.transactions.map((tx: Transaction) => {
    return {
      ...tx,
      id: tx.transactionId,
      account: tx.accountId || '',
      type: (tx.debitOrCredit === 'DEBIT' ? 'expense' : 'income') as 'income' | 'expense' | 'transfer',
    } as TransactionViewItem;
  });
};

const useAccountTransactions = (accountId: string | null) => {
  const queryClient = useQueryClient();
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);

  // Fetch categories for transformation
  const fetchCategories = useCallback(async () => {
    setCategoriesLoading(true);
    setCategoriesError(null);
    try {
      const categoriesResponse = await getCategories();
      setCategories(categoriesResponse);
    } catch (err) {
      console.error("Error fetching categories:", err);
      setCategoriesError("Failed to load categories.");
    } finally {
      setCategoriesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // Fetch transactions for the account
  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsError,
    refetch: refetchTransactions,
  } = useQuery({
    queryKey: ['account-transactions', accountId],
    queryFn: async () => {
      if (!accountId) return null;
      return getAccountTransactions(accountId, 100); // Fetch up to 100 transactions
    },
    enabled: !!accountId,
    staleTime: 60000, // 1 minute
  });

  // Transform transactions
  const transformedTransactions = useMemo(() => {
    if (!transactionsData || categories.length === 0) {
      return [];
    }
    return transformAccountTransactions(transactionsData as unknown as TransactionListResponse, categories);
  }, [transactionsData, categories]);

  // Quick category update
  const handleQuickCategoryChange = async (transactionId: string, newCategoryId: string) => {
    try {
      quickUpdateTransactionCategory(transactionId, newCategoryId);
      queryClient.invalidateQueries({ queryKey: ['account-transactions', accountId] });
    } catch (err) {
      console.error("Error updating category:", err);
      throw err;
    }
  };

  return {
    transactions: transformedTransactions,
    loading: transactionsLoading || categoriesLoading,
    error: transactionsError?.message || categoriesError,
    categories,
    refetch: refetchTransactions,
    handleQuickCategoryChange,
  };
};

export default useAccountTransactions; 