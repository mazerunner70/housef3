import React, { useEffect, useCallback, useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getUserTransactions,
  getCategories,
  quickUpdateTransactionCategory,
  TransactionViewItem,
  CategoryInfo,
  TransactionRequestParams,
  PaginationInfo as BackendPaginationInfo,
  TransactionsViewResponse,
} from '../../services/TransactionService';
import { listAccounts, Account } from '../../services/AccountService';
import TransactionFilters, { FilterValues as ComponentFilterValues } from '../components/TransactionFilters';
import TransactionTable from '../components/TransactionTable';
import './TransactionsView.css';
import { useTransactionsUIStore, FilterValues as StoreFilterValues } from '../../stores/transactionsStore';

// Placeholder for a potential future Modal component
// For now, we can use alerts or simple divs
const ModalPlaceholder: React.FC<{ title: string; onClose: () => void; children: React.ReactNode }> = ({ title, onClose, children }) => {
  return (
    <div className="modal-backdrop-placeholder">
      <div className="modal-content-placeholder">
        <h2>{title}</h2>
        {children}
        <button onClick={onClose} className="modal-close-button">
          <span role="img" aria-label="close">❌</span> Close
        </button>
      </div>
    </div>
  );
};

// type TransactionTab = 'TRANSACTIONS_LIST' | 'CATEGORY_MANAGEMENT' | 'STATEMENTS_IMPORTS'; // This type might be managed by the shell if needed there

const DEFAULT_PAGE_SIZE = 25;

// API Response type for getUserTransactions -- This can be removed if TransactionsViewResponse is used directly
// interface TransactionsApiResponse {
//   transactions: TransactionViewItem[];
//   pagination: BackendPaginationInfo;
// }

// Helper to convert YYYY-MM-DD string to Date or null
const parseDateString = (dateStr: string | undefined): Date | null => {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  return isNaN(date.getTime()) ? null : date;
};

// Helper to format Date to YYYY-MM-DD string or empty string
const formatDateToString = (date: Date | null): string => {
  if (!date) return '';
  // Adjust for timezone offset to get YYYY-MM-DD in local time
  const pad = (num: number) => num.toString().padStart(2, '0');
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  return `${year}-${month}-${day}`;
};

const TransactionsListTab: React.FC = () => {
  const queryClient = useQueryClient();
  const {
    filters,
    currentPage,
    pageSize,
    applyNewFilters,
    setCurrentPage,
    setPageSize,
  } = useTransactionsUIStore();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  const [initialDataLoading, setInitialDataLoading] = useState(true);
  const [initialDataError, setInitialDataError] = useState<string | null>(null);
  const [currentAPILastEvaluatedKey, setCurrentAPILastEvaluatedKey] = useState<Record<string, any> | undefined>();

  const fetchInitialFilterData = useCallback(async () => {
    setInitialDataLoading(true);
    setInitialDataError(null);
    try {
      const accountsResponse = await listAccounts();
      setAccounts(accountsResponse.accounts);
      
      const categoriesResponse = await getCategories();
      setCategories(categoriesResponse);
    } catch (err) {
      console.error("Error fetching initial filter data:", err);
      setInitialDataError("Failed to load account or category data for filters.");
    } finally {
      setInitialDataLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialFilterData();
  }, [fetchInitialFilterData]);

  // Clean up orphaned category IDs from localStorage when categories are loaded
  useEffect(() => {
    if (categories.length > 0 && filters.categoryIds.length > 0) {
      const validCategoryIds = categories.map(cat => cat.categoryId);
      const filteredCategoryIds = filters.categoryIds.filter(id => validCategoryIds.includes(id));
      
      // If we found orphaned IDs, clean them from localStorage immediately
      if (filteredCategoryIds.length !== filters.categoryIds.length) {
        const orphanedCount = filters.categoryIds.length - filteredCategoryIds.length;
        const orphanedIds = filters.categoryIds.filter(id => !validCategoryIds.includes(id));
        
        console.log(`🧹 Cleaning up ${orphanedCount} orphaned category IDs from localStorage:`, orphanedIds);
        
        // Update the store (which persists to localStorage)
        applyNewFilters({ ...filters, categoryIds: filteredCategoryIds });
      }
    }
  }, [categories]); // Only run when categories change to avoid loops

  // Construct queryKey. LEK is part of it to ensure new data fetch when it changes.
  const queryKey = ['transactions', filters, currentPage, pageSize];
  
  const fetchTransactionsQueryFn = useCallback(async (): Promise<TransactionsViewResponse> => {
    const startDateMs = filters.startDate ? parseDateString(filters.startDate)?.getTime() : undefined;
    const endDateSourceDate = parseDateString(filters.endDate);
    let endDateMs = endDateSourceDate ? endDateSourceDate.getTime() : undefined;
    if (endDateMs && endDateSourceDate) {
      const endOfDay = new Date(endDateSourceDate);
      endOfDay.setHours(23, 59, 59, 999);
      endDateMs = endOfDay.getTime();
    }

    const params: TransactionRequestParams = {
      page: currentPage,
      pageSize: pageSize,
      transactionType: filters.transactionType === 'all' ? undefined : filters.transactionType,
      searchTerm: filters.searchTerm || undefined,
      accountIds: filters.accountIds && filters.accountIds.length > 0 ? filters.accountIds : undefined,
      categoryIds: filters.categoryIds && filters.categoryIds.length > 0 ? filters.categoryIds : undefined,
      startDate: startDateMs,
      endDate: endDateMs,
      sortBy: 'date', 
      sortOrder: 'desc',
      lastEvaluatedKey: currentAPILastEvaluatedKey,
      ignoreDup: true,
    };
    return getUserTransactions(params);
  }, [filters, currentPage, pageSize, currentAPILastEvaluatedKey]);

  const {
    data: transactionsData,
    isLoading: transactionsLoading,
    error: transactionsErrorObj,
    isFetching: transactionsIsFetching,
  } = useQuery<TransactionsViewResponse, Error>({
    queryKey,
    queryFn: fetchTransactionsQueryFn,
    placeholderData: (previousData) => previousData,
    staleTime: 120000, // 2 minutes
  });

  useEffect(() => {
    if (transactionsData) {
      setCurrentAPILastEvaluatedKey(transactionsData.pagination?.lastEvaluatedKey);
    }
  }, [transactionsData]);

  const handleApplyFilters = (newFiltersFromComponent: ComponentFilterValues) => {
    setCurrentAPILastEvaluatedKey(undefined);
    const filtersForStore: StoreFilterValues = {
      startDate: newFiltersFromComponent.startDate,
      endDate: newFiltersFromComponent.endDate,
      accountIds: newFiltersFromComponent.accountIds || [],
      categoryIds: newFiltersFromComponent.categoryIds || [],
      transactionType: newFiltersFromComponent.transactionType || 'all',
      searchTerm: newFiltersFromComponent.searchTerm || '',
    };
    applyNewFilters(filtersForStore);
  };
  
  const handlePageChange = (newPage: number) => {
    if (newPage === 1 || newPage < currentPage) {
      setCurrentAPILastEvaluatedKey(undefined);
    }
    setCurrentPage(newPage);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setCurrentAPILastEvaluatedKey(undefined);
    setPageSize(newPageSize);
  };

  const [isQuickUpdating, setIsQuickUpdating] = useState(false);
  const handleQuickCategoryChange = async (transactionId: string, newCategoryId: string) => {
    setIsQuickUpdating(true);
    try {
      await quickUpdateTransactionCategory(transactionId, newCategoryId);
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    } catch (err) {
      console.error("Error updating category:", err);
    } finally {
      setIsQuickUpdating(false);
    }
  };
  
  // Transform transactions to include full category info
  const transformedTransactions = useMemo(() => {
    if (!transactionsData?.transactions || categories.length === 0) {
      return transactionsData?.transactions || [];
    }
    
    // Create a map of category IDs to category info
    const categoriesMap = new Map<string, CategoryInfo>();
    categories.forEach(cat => {
      categoriesMap.set(cat.categoryId, cat);
    });
    
    // Transform transactions to include full category info
    return transactionsData.transactions.map(transaction => {
      let category: CategoryInfo | undefined = undefined;
      if (transaction.primaryCategoryId) {
        category = categoriesMap.get(transaction.primaryCategoryId);
      }
      
      return {
        ...transaction,
        category
      };
    });
  }, [transactionsData?.transactions, categories]);
  
  const initialFilterValuesProvided = !initialDataLoading && accounts.length > 0;
  const apiError = transactionsErrorObj;

  const handleEditTransaction = (transactionId: string) => {
    console.log("Edit transaction (placeholder):", transactionId);
    alert('Edit functionality to be implemented, typically involves a modal and a mutation followed by query invalidation.');
  };

  return (
    <>
      {initialDataLoading && <div className="loading-spinner">Loading filter options...</div>}
      {initialDataError && <div className="error-message">{initialDataError}</div>}
      
      {initialFilterValuesProvided ? (
          <TransactionFilters
            accounts={accounts}
            categories={categories}
            initialFilters={filters}
            onApplyFilters={handleApplyFilters}
          />
      ) : (
        !initialDataLoading && <div>Filter options could not be loaded or are empty.</div>
      )}

      {apiError && <div className="error-message">Error loading transactions: {apiError.message || 'Unknown error'}</div>}
      
      <TransactionTable
        transactions={transformedTransactions}
        isLoading={transactionsLoading || transactionsIsFetching || isQuickUpdating || initialDataLoading}
        error={null}
        categories={categories}
        accountsData={accounts}
        onEditTransaction={handleEditTransaction}
        onQuickCategoryChange={handleQuickCategoryChange}
        currentPage={currentPage}
        totalPages={transactionsData?.pagination?.totalPages || 0}
        onPageChange={handlePageChange}
        itemsPerPage={pageSize}
        totalItems={transactionsData?.pagination?.totalItems || 0}
        onPageSizeChange={handlePageSizeChange}
      />
      {(transactionsLoading || transactionsIsFetching) && (!transformedTransactions || transformedTransactions.length === 0) && 
        <div className="loading-spinner">Loading transactions...</div>
      }
      {!transactionsLoading && !transactionsIsFetching && !initialDataLoading && (!transformedTransactions || transformedTransactions.length === 0) && 
        <div className="transaction-table-empty">No transactions found for the current filters.</div>
      }
    </>
  );
};

export default TransactionsListTab; 