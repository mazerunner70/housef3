import React, { useState, useMemo, useEffect, useRef } from 'react';
import './TransactionTable.css';
import Pagination from './Pagination'; // Import Pagination
import { TransactionViewItem, CategoryInfo } from '../../services/TransactionService'; // IMPORT SERVICE TYPES
import { Account as AccountDetail } from '../../services/AccountService'; // IMPORT ACCOUNT SERVICE
import { Decimal } from 'decimal.js';

export interface SortConfig {
  key: keyof TransactionViewItem | null; // USE TransactionViewItem
  direction: 'ascending' | 'descending';
}

interface TransactionTableProps {
  transactions: TransactionViewItem[]; // USE TransactionViewItem
  isLoading: boolean;
  error?: string | null;
  categories?: CategoryInfo[]; // USE CategoryInfo
  accountsData: AccountDetail[]; // NEW PROP for accounts from parent
  onEditTransaction: (transactionId: string) => void;
  onQuickCategoryChange: (transactionId: string, newCategoryId: string) => void;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  itemsPerPage: number;
  totalItems: number;
  onPageSizeChange: (newPageSize: number) => void; // New prop
}

const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  isLoading: isLoadingTransactions, // Prop renamed for clarity if needed, or keep as isLoading
  error: transactionsError, // Prop renamed for clarity
  categories, // This is now CategoryInfo[]
  accountsData, // Destructure new prop
  onEditTransaction,
  onQuickCategoryChange,
  currentPage,
  totalPages,
  onPageChange,
  itemsPerPage,
  totalItems,
  onPageSizeChange, // Destructure new prop
}) => {
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'date', direction: 'descending' });
  const [selectedTransactionIds, setSelectedTransactionIds] = useState<Set<string>>(new Set());
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // Create accountsMap from the accountsData prop using useMemo
  const accountsMap = useMemo(() => {
    const newMap = new Map<string, string>();
    if (accountsData) {
      accountsData.forEach(acc => {
        newMap.set(acc.accountId, acc.accountName);
      });
    }
    // console.log("TransactionTable: accountsMap created from prop:", newMap); // Optional: for debugging
    return newMap;
  }, [accountsData]);

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
        // Updated sorting for account ID to use names from accountsMap
        if (sortConfig.key === 'account') {
          const aAccName = accountsMap.get(aValue as string) || 'N/A';
          const bAccName = accountsMap.get(bValue as string) || 'N/A';
          return sortConfig.direction === 'ascending' ? aAccName.localeCompare(bAccName) : bAccName.localeCompare(aAccName);
        }

        // Add support for sorting by balance
        if (sortConfig.key === 'balance') {
          const aBalance = aValue instanceof Decimal ? aValue : new Decimal(0);
          const bBalance = bValue instanceof Decimal ? bValue : new Decimal(0);
          return sortConfig.direction === 'ascending' ? aBalance.comparedTo(bBalance) : bBalance.comparedTo(aBalance);
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
  }, [transactions, sortConfig, accountsMap]); // Added accountsMap dependency
  
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

  if (isLoadingTransactions) { 
    return <div className="transaction-table-loading">Loading transactions...</div>;
  }

  if (transactionsError) {
    return <div className="transaction-table-error">Error loading transactions: {transactionsError}</div>;
  }

  if (!isLoadingTransactions && transactions.length === 0 && totalItems === 0) {
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
            <th onClick={() => handleSort('balance')}>Balance{getSortIndicator('balance')}</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sortedTransactionsOnPage.length === 0 && (
            <tr>
              <td colSpan={8} style={{ textAlign: 'center', padding: '20px' }}>
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
              <td>
                {/* transaction.date is a number (milliseconds since epoch) as per TransactionViewItem */}
                {new Date(transaction.date).toLocaleDateString()}
              </td>
              <td>
                {transaction.description}
                {transaction.payee && <span className="payee-details"> ({transaction.payee})</span>}
              </td>
              <td>
                <select 
                  value={transaction.category?.id || ''} // Safely access and provide fallback
                  onChange={(e) => onQuickCategoryChange(transaction.id, e.target.value)}
                  className="category-quick-select"
                  onClick={(e) => e.stopPropagation()} 
                >
                  {availableCategories.map(cat => ( // cat is CategoryInfo
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                  {/* Ensure the currently selected category is in the list */}
                  {transaction.category && !availableCategories.find(c => c.id === transaction.category!.id) && (
                    <option key={transaction.category.id} value={transaction.category.id} disabled>
                      {transaction.category.name} (Current)
                    </option>
                  )}
                  {!transaction.category && (
                     <option key="uncategorized-current" value="" disabled>
                       Uncategorized (Current)
                     </option>
                  )}
                </select>
              </td>
              {/* Updated to use accountsMap */}
              <td>{accountsMap.get(transaction.accountId || '') || 'N/A'}</td>
              {(() => {
                // Default values for safety
                let displayAmount = "0.00";
                let currencySymbol = "";
                let amountClass = 'amount-expense'; // Default to expense or neutral

                // transaction.amount is expected to be a Decimal instance due to processing in TransactionService.ts
                if (transaction.amount instanceof Decimal) {
                  const numericAmount = transaction.amount; // It's already a Decimal
                  displayAmount = numericAmount.toFixed(2);
                  if (transaction.currency) {
                    currencySymbol = transaction.currency as string; // Assuming Currency is string-compatible
                  }
                  amountClass = numericAmount.greaterThanOrEqualTo(new Decimal(0)) ? 'amount-income' : 'amount-expense';
                } else {
                  // This path is taken if transaction.amount is not a Decimal instance.
                  // This could be because it's undefined, null, or if the service layer conversion somehow failed.
                  if (transaction.amount !== undefined && transaction.amount !== null) {
                    // Only log a warning if amount is present but not a Decimal, as this is unexpected.
                    console.warn(
                      "TransactionTable: transaction.amount was expected to be a Decimal instance but was not. Value type:", 
                      typeof transaction.amount, 
                      "Value:", transaction.amount, 
                      "Transaction ID:", transaction.id
                    );
                  }
                  // displayAmount, currencySymbol, amountClass will retain their default values.
                }
                // This console.log was present in the original code provided
                console.log("Transaction:", transaction);
                return (
                  <td className={amountClass}>
                    {currencySymbol}{displayAmount}
                  </td>
                );
              })()}
              {(() => {
                // Display balance
                let displayBalance = "0.00";
                let currencySymbol = "";
                let balanceClass = 'balance-cell';

                // transaction.balance is expected to be a Decimal instance
                if (transaction.balance instanceof Decimal) {
                  const numericBalance = transaction.balance;
                  displayBalance = numericBalance.toFixed(2);
                  if (transaction.currency) {
                    currencySymbol = transaction.currency as string;
                  }
                  balanceClass = numericBalance.greaterThanOrEqualTo(new Decimal(0)) ? 'balance-positive' : 'balance-negative';
                } else {
                  if (transaction.balance !== undefined && transaction.balance !== null) {
                    console.warn(
                      "TransactionTable: transaction.balance was expected to be a Decimal instance but was not. Value type:", 
                      typeof transaction.balance, 
                      "Value:", transaction.balance, 
                      "Transaction ID:", transaction.id
                    );
                  }
                }

                return (
                  <td className={balanceClass}>
                    {currencySymbol}{displayBalance}
                  </td>
                );
              })()}
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
          itemsPerPage={itemsPerPage}
          onPageSizeChange={onPageSizeChange}
          totalItems={totalItems}
        />
      )}
    </div>
  );
};

export default TransactionTable; 