import React, { useState, useEffect, useCallback } from 'react';
import {
  getUserTransactions,
  getCategories,
  quickUpdateTransactionCategory,
  TransactionViewItem,
  CategoryInfo,
  PaginationInfo,
  TransactionRequestParams,
} from '../../services/TransactionService';
import { listAccounts, Account } from '../../services/AccountService';
import TransactionFilters, { FilterValues } from '../components/TransactionFilters';
import TransactionTable from '../components/TransactionTable';
import './TransactionsView.css'; // Assuming this CSS can be shared or adjusted

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

const TransactionsListTab: React.FC = () => { // Renamed component
  const [transactions, setTransactions] = useState<TransactionViewItem[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<CategoryInfo[]>([]);
  
  const [filters, setFilters] = useState<FilterValues>({
    startDate: '',
    endDate: '',
    accountIds: [],
    categoryIds: [],
    transactionType: 'all',
    searchTerm: '',
  });
  
  const [pagination, setPagination] = useState<PaginationInfo>({
    currentPage: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalItems: 0,
    totalPages: 0,
    lastEvaluatedKey: undefined,
  });
  const [currentRequestLastEvaluatedKey, setCurrentRequestLastEvaluatedKey] = useState<Record<string, any> | undefined>(undefined);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInitialData = useCallback(async () => {
    setIsLoading(true);
    try {
      const accountsResponse = await listAccounts();
      setAccounts(accountsResponse.accounts);

      const categoriesResponse = await getCategories();
      setCategories(categoriesResponse);

    } catch (err) {
      console.error("Error fetching initial data:", err);
      setError("Failed to load accounts or categories.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  const fetchTransactions = useCallback(async (
    currentFilters: FilterValues,
    currentPage: number,
    pageSize: number,
    keyForNextPage?: Record<string, any> 
  ) => {
    setIsLoading(true);
    setError(null);

    const startDateMs = currentFilters.startDate ? parseDateString(currentFilters.startDate)?.getTime() : undefined;
    const endDateSourceDate = parseDateString(currentFilters.endDate);
    let endDateMs = endDateSourceDate ? endDateSourceDate.getTime() : undefined;

    if (endDateMs && endDateSourceDate) {
        // Ensure endDateMs represents the end of the selected day if it's just a date string
        const endOfDay = new Date(endDateSourceDate);
        endOfDay.setHours(23, 59, 59, 999);
        endDateMs = endOfDay.getTime();
    }

    const params: TransactionRequestParams = {
      page: currentPage,
      pageSize: pageSize,
      transactionType: currentFilters.transactionType === 'all' ? undefined : currentFilters.transactionType,
      searchTerm: currentFilters.searchTerm || undefined,
      accountIds: currentFilters.accountIds && currentFilters.accountIds.length > 0 ? currentFilters.accountIds : undefined,
      categoryIds: currentFilters.categoryIds && currentFilters.categoryIds.length > 0 ? currentFilters.categoryIds : undefined,
      startDate: startDateMs,
      endDate: endDateMs,
      sortBy: 'date', 
      sortOrder: 'desc',
      lastEvaluatedKey: keyForNextPage,
      ignoreDup: true,
    };

    try {
      const response = await getUserTransactions(params);
      setTransactions(response.transactions);
      setPagination(response.pagination);
      setCurrentRequestLastEvaluatedKey(response.pagination.lastEvaluatedKey);
    } catch (err) {
      console.error("Error fetching transactions:", err);
      setError("Failed to load transactions.");
      setTransactions([]);
      setPagination(prev => ({ ...prev, totalItems: 0, totalPages: 0, lastEvaluatedKey: undefined }));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTransactions(filters, 1, pagination.pageSize);
    setCurrentRequestLastEvaluatedKey(undefined); 
  }, [filters, fetchTransactions, pagination.pageSize]); // Added pagination.pageSize to dependencies

  const handleApplyFilters = (newFilters: FilterValues) => {
    setFilters(newFilters);
    setPagination(prev => ({ ...prev, currentPage: 1, lastEvaluatedKey: undefined }));
  };
  
  const handlePageChange = (newPage: number) => {
    let keyForPageFetch = newPage === 1 ? undefined : currentRequestLastEvaluatedKey;
    
    if (newPage <= pagination.currentPage && newPage !== 1) {
        keyForPageFetch = undefined; 
        if (pagination.currentPage > 1 && newPage < pagination.currentPage) {
             console.warn("Navigating to a previous page without a stored LEK history; fetching from the start of the filtered set for page:", newPage);
        }
    }
    fetchTransactions(filters, newPage, pagination.pageSize, keyForPageFetch);
    setPagination(prev => ({ ...prev, currentPage: newPage })); 
  };

  const handlePageSizeChange = (newPageSize: number) => {
    if (newPageSize === pagination.pageSize) return; // No change

    console.log(`Changing page size from ${pagination.pageSize} to ${newPageSize}`);
    // When page size changes, reset to page 1 and clear LEK
    setPagination(prev => ({
      ...prev,
      pageSize: newPageSize,
      currentPage: 1, // Reset to page 1
      lastEvaluatedKey: undefined, // Clear LEK for a fresh fetch from page 1
    }));
    setCurrentRequestLastEvaluatedKey(undefined); // Also clear the component's LEK state
    // Fetch transactions with new page size, from page 1
    fetchTransactions(filters, 1, newPageSize, undefined);
  };

  const handleEditTransaction = (transactionId: string) => {
    console.log("Edit transaction:", transactionId);
  };

  const handleQuickCategoryChange = async (transactionId: string, newCategoryId: string) => {
    setIsLoading(true);
    try {
      await quickUpdateTransactionCategory(transactionId, newCategoryId);
      const updatedCategoryInfo = categories.find(c => c.id === newCategoryId);

      if (updatedCategoryInfo) {
        setTransactions(prevTransactions =>
          prevTransactions.map(t =>
            t.id === transactionId ? { ...t, category: updatedCategoryInfo } : t
          )
        );
      } else {
        // If category info not found locally (should be rare if `categories` state is up-to-date),
        // or if quickUpdateTransactionCategory returned a complex object needing full refresh.
        fetchTransactions(filters, pagination.currentPage, pagination.pageSize, pagination.currentPage === 1 ? undefined : currentRequestLastEvaluatedKey);
      }
    } catch (err) {
      console.error("Error updating category:", err);
      setError("Failed to update category.");
      // Refetch on error to ensure data consistency
      fetchTransactions(filters, pagination.currentPage, pagination.pageSize, pagination.currentPage === 1 ? undefined : currentRequestLastEvaluatedKey);
    } finally {
      setIsLoading(false);
    }
  };
  
  const initialFilterValuesProvided = accounts.length > 0 ;

  // This component now only renders its specific content, not the overall page shell or tabs
  return (
    <>
      {initialFilterValuesProvided ? (
          <TransactionFilters
            accounts={accounts}
            categories={categories}
            initialFilters={filters}
            onApplyFilters={handleApplyFilters}
          />
      ) : (
        <div>Loading filters...</div> // Or some other placeholder
      )}
      {error && <div className="error-message">Error: {error}</div>}
      <TransactionTable
        transactions={transactions}
        isLoading={isLoading}
        error={error}
        categories={categories}
        accountsData={accounts}
        onEditTransaction={handleEditTransaction}
        onQuickCategoryChange={handleQuickCategoryChange}
        currentPage={pagination.currentPage}
        totalPages={pagination.totalPages}
        onPageChange={handlePageChange}
        itemsPerPage={pagination.pageSize}
        totalItems={pagination.totalItems}
        onPageSizeChange={handlePageSizeChange}
      />
      {isLoading && transactions.length === 0 && <div className="loading-spinner">Loading transactions...</div>}
    </>
  );
};

export default TransactionsListTab; // Export with new name 