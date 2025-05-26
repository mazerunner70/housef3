import React, { useState, useMemo, useEffect, useRef } from 'react';
import './TransactionTable.css';
import Pagination from './Pagination'; // Import Pagination
import { TransactionViewItem, CategoryInfo, AccountInfo } from '../../services/TransactionService'; // IMPORT SERVICE TYPES

// REMOVE LOCAL TYPE DEFINITIONS
// interface Category {
//   id: string;
//   name: string;
// }
// 
// interface Account {
//   id: string;
//   name: string;
// }
// 
// export interface Transaction {
//   id: string;
//   date: string; // "2023-10-26"
//   description: string;
//   payee?: string;
//   category: Category; // Changed to CategoryInfo
//   account: Account;   // Changed to AccountInfo
//   amount: number;
//   currency: string;
//   type: 'income' | 'expense' | 'transfer';
//   notes?: string;
//   isSplit?: boolean;
// }

export interface SortConfig {
  key: keyof TransactionViewItem | null; // USE TransactionViewItem
  direction: 'ascending' | 'descending';
}

interface TransactionTableProps {
  transactions: TransactionViewItem[]; // USE TransactionViewItem
  isLoading: boolean;
  error?: string | null;
  categories?: CategoryInfo[]; // USE CategoryInfo
  onEditTransaction: (transactionId: string) => void;
  onQuickCategoryChange: (transactionId: string, newCategoryId: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  itemsPerPage: number;
  totalItems: number;
}

const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  isLoading,
  error,
  categories, // This is now CategoryInfo[]
  onEditTransaction,
  onQuickCategoryChange,
  currentPage,
  totalPages,
  onPageChange,
  itemsPerPage,
  totalItems,
}) => {
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'date', direction: 'descending' });
  const [selectedTransactionIds, setSelectedTransactionIds] = useState<Set<string>>(new Set());
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // Dummy categories for inline editing example - ensure it conforms to CategoryInfo[]
  const DUMMY_CATEGORIES: CategoryInfo[] = [ // USE CategoryInfo
    { id: 'cat_food', name: 'Food & Drink' },
    { id: 'cat_transport', name: 'Transport' },
    { id: 'cat_bills', name: 'Bills' },
    { id: 'cat_entertainment', name: 'Entertainment' },
    { id: 'cat_uncategorized', name: 'Uncategorized' },
  ];
  
  const availableCategories = useMemo(() => {
    // categories prop is already CategoryInfo[] or undefined
    return categories && categories.length > 0 ? categories : DUMMY_CATEGORIES;
  }, [categories]);

  const handleSort = (key: keyof TransactionViewItem) => { // USE TransactionViewItem
    let direction: 'ascending' | 'descending' = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  const sortedTransactionsOnPage = useMemo(() => {
    const sortableItems = [...transactions]; // transactions is TransactionViewItem[]
    if (sortConfig.key) {
      sortableItems.sort((a, b) => {
        const aValue = a[sortConfig.key!];
        const bValue = b[sortConfig.key!];

        if (aValue === undefined || bValue === undefined) return 0;

        // Accessing category.name or account.name from TransactionViewItem
        if (sortConfig.key === 'category') { 
          const aCatName = (aValue as CategoryInfo).name;
          const bCatName = (bValue as CategoryInfo).name;
          return sortConfig.direction === 'ascending' ? aCatName.localeCompare(bCatName) : bCatName.localeCompare(aCatName);
        }
        if (sortConfig.key === 'account') {
          const aAccName = (aValue as AccountInfo).name;
          const bAccName = (bValue as AccountInfo).name;
          return sortConfig.direction === 'ascending' ? aAccName.localeCompare(bAccName) : bAccName.localeCompare(aAccName);
        }

        if (typeof aValue === 'number' && typeof bValue === 'number') {
          return sortConfig.direction === 'ascending' ? aValue - bValue : bValue - aValue;
        }
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          return sortConfig.direction === 'ascending' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
        }
        return 0;
      });
    }
    return sortableItems;
  }, [transactions, sortConfig]);
  
  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      const numSelected = selectedTransactionIds.size;
      const numItemsOnPage = sortedTransactionsOnPage.length;
      selectAllCheckboxRef.current.indeterminate = numSelected > 0 && numSelected < numItemsOnPage;
      selectAllCheckboxRef.current.checked = numSelected > 0 && numSelected === numItemsOnPage;
    }
  }, [selectedTransactionIds, sortedTransactionsOnPage.length]);

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    const isChecked = event.target.checked;
    if (isChecked) {
      const allIdsOnPage = new Set(sortedTransactionsOnPage.map(t => t.id));
      setSelectedTransactionIds(allIdsOnPage);
    } else {
      setSelectedTransactionIds(new Set());
    }
  };

  const handleSelectSingle = (transactionId: string, isSelected: boolean) => {
    const newSelectedIds = new Set(selectedTransactionIds);
    if (isSelected) {
      newSelectedIds.add(transactionId);
    } else {
      newSelectedIds.delete(transactionId);
    }
    setSelectedTransactionIds(newSelectedIds);
  };

  const getSortIndicator = (key: keyof TransactionViewItem) => { // USE TransactionViewItem
    if (sortConfig.key === key) {
      return sortConfig.direction === 'ascending' ? ' ↑' : ' ↓';
    }
    return '';
  };

  if (isLoading) {
    return <div className="transaction-table-loading">Loading transactions...</div>;
  }

  if (error) {
    return <div className="transaction-table-error">Error loading transactions: {error}</div>;
  }

  if (!isLoading && transactions.length === 0 && totalItems === 0) {
    return <div className="transaction-table-empty">No transactions found.</div>;
  } 

  return (
    <div className="transaction-table-container">
      <table>
        <thead>
          <tr>
            <th>
              <input 
                type="checkbox" 
                ref={selectAllCheckboxRef}
                onChange={handleSelectAll}
                disabled={sortedTransactionsOnPage.length === 0}
              />
            </th>
            {/* Ensure these keys are valid for TransactionViewItem */}
            <th onClick={() => handleSort('date')}>Date{getSortIndicator('date')}</th>
            <th onClick={() => handleSort('description')}>Description/Payee{getSortIndicator('description')}</th>
            <th onClick={() => handleSort('category')}>Category{getSortIndicator('category')}</th>
            <th onClick={() => handleSort('account')}>Account{getSortIndicator('account')}</th>
            <th onClick={() => handleSort('amount')}>Amount{getSortIndicator('amount')}</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sortedTransactionsOnPage.length === 0 && (
            <tr>
              <td colSpan={7} style={{ textAlign: 'center', padding: '20px' }}>
                No transactions for the current page or filters.
              </td>
            </tr>
          )}
          {sortedTransactionsOnPage.map((transaction) => ( // transaction is TransactionViewItem
            <tr key={transaction.id} className={selectedTransactionIds.has(transaction.id) ? 'selected' : ''}>
              <td>
                <input 
                  type="checkbox" 
                  checked={selectedTransactionIds.has(transaction.id)}
                  onChange={(e) => handleSelectSingle(transaction.id, e.target.checked)}
                />
              </td>
              {/* Assuming transaction.date is "YYYY-MM-DD" string as per TransactionViewItem */}
              <td>{new Date(transaction.date + 'T00:00:00').toLocaleDateString()}</td> 
              <td>
                {transaction.description}
                {transaction.payee && <span className="payee-details"> ({transaction.payee})</span>}
              </td>
              <td>
                <select 
                  value={transaction.category.id} // transaction.category is CategoryInfo
                  onChange={(e) => onQuickCategoryChange(transaction.id, e.target.value)}
                  className="category-quick-select"
                  onClick={(e) => e.stopPropagation()} 
                >
                  {availableCategories.map(cat => ( // cat is CategoryInfo
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                  {/* Ensure the currently selected category is in the list */}
                  {!availableCategories.find(c => c.id === transaction.category.id) && (
                    <option key={transaction.category.id} value={transaction.category.id} disabled>
                      {transaction.category.name} (Current)
                    </option>
                  )}
                </select>
              </td>
              <td>{transaction.account.name}</td> {/* transaction.account is AccountInfo */}
              <td className={transaction.amount >= 0 ? 'amount-income' : 'amount-expense'}>
                {transaction.currency}{transaction.amount.toFixed(2)}
              </td>
              <td>
                <button onClick={() => onEditTransaction(transaction.id)} className="action-button edit-button" title="Edit transaction">
                  ✎
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {totalPages > 0 && (
        <Pagination 
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
};

export default TransactionTable; 