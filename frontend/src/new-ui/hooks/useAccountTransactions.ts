import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getAccountTransactions,
  getCategories,
  quickUpdateTransactionCategory,
  TransactionViewItem,
  CategoryInfo,
  TransactionListResponse,
} from '../../services/TransactionService';
import { listAccounts, Account } from '../../services/AccountService';
import { Decimal } from 'decimal.js';

// Transform the response to match TransactionViewItem format
const transformAccountTransactions = (response: TransactionListResponse, categories: CategoryInfo[]): TransactionViewItem[] => {
  if (!response.transactions || categories.length === 0) {
    return response.transactions?.map(tx => ({
      ...tx,
      id: tx.transactionId,
      account: tx.accountId || '',
      category: undefined,
      type: (tx.debitOrCredit === 'DEBIT' ? 'expense' : 'income') as 'income' | 'expense' | 'transfer',
    })) || [];
  }
  
  // Create a map of category IDs to category info
  const categoriesMap = new Map<string, CategoryInfo>();
  categories.forEach(cat => {
    categoriesMap.set(cat.categoryId, cat);
  });
  
  // Transform transactions to include full category info
  return response.transactions.map(tx => {
    let category: CategoryInfo | undefined = undefined;
    if (tx.category) {
      category = categoriesMap.get(tx.category);
    }
    
    return {
      ...tx,
      id: tx.transactionId,
      account: tx.accountId || '',
      category,
      primaryCategoryId: tx.category,
      type: (tx.debitOrCredit === 'DEBIT' ? 'expense' : 'income') as 'income' | 'expense' | 'transfer',
    };
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
      return await getAccountTransactions(accountId, 100); // Fetch up to 100 transactions
    },
    enabled: !!accountId,
    staleTime: 60000, // 1 minute
  });

  // Transform transactions
  const transformedTransactions = useMemo(() => {
    if (!transactionsData || categories.length === 0) {
      return [];
    }
    return transformAccountTransactions(transactionsData, categories);
  }, [transactionsData, categories]);

  // Quick category update
  const handleQuickCategoryChange = async (transactionId: string, newCategoryId: string) => {
    try {
      await quickUpdateTransactionCategory(transactionId, newCategoryId);
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