import React, { useState, useMemo, useEffect, useRef } from 'react';
import './TransactionTable.css';
import LoadMore from '@/components/Pagination'; // Import LoadMore (renamed from Pagination)
import CategoryQuickSelector from '@/components/domain/categories/CategoryQuickSelector';
import PatternSuggestionModal from '@/components/PatternSuggestionModal';
import { TransactionViewItem, CategoryInfo } from '@/schemas/Transaction'; // IMPORT SERVICE TYPES
import { Account as AccountDetail } from '@/schemas/Account'; // IMPORT ACCOUNT SERVICE
import { Category, CategoryRule } from '@/types/Category';
import { CategoryService } from '@/services/CategoryService';
import { useTransactionViewSort } from '@/hooks/useTransactionViewSort';
import {
  CurrencyAmount,
  DateCell,
  TextWithSubtext,
  LookupCell,
  NumberCell,
  RowActions
} from '@/components/ui';



interface TransactionTableProps {
  transactions: TransactionViewItem[]; // USE TransactionViewItem
  isLoading: boolean;
  error?: string | null;
  categories?: CategoryInfo[]; // USE CategoryInfo
  accountsData: AccountDetail[]; // NEW PROP for accounts from parent
  onEditTransaction: (transactionId: string) => void;
  onQuickCategoryChange: (transactionId: string, newCategoryId: string) => void;
  onCreateNewCategory?: (transactionData: {
    description: string;
    amount?: string;
    suggestedCategory?: {
      name: string;
      type: 'INCOME' | 'EXPENSE';
      confidence: number;
    };
    suggestedPatterns?: Array<{
      pattern: string;
      confidence: number;
      explanation: string;
    }>;
  }) => void;
  onNavigateToCategoryManagement?: (categoryData?: {
    suggestedName?: string;
    suggestedType?: 'INCOME' | 'EXPENSE';
    suggestedPattern?: string;
    transactionDescription?: string;
  }) => void;
  hasMore: boolean;
  onLoadMore: () => void;
  itemsLoaded: number;
  pageSize: number;
  onPageSizeChange: (newPageSize: number) => void;
  showAccountColumn?: boolean; // NEW PROP to control account column visibility
}

const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  isLoading: isLoadingTransactions, // Prop renamed for clarity if needed, or keep as isLoading
  error: transactionsError, // Prop renamed for clarity
  categories, // This is now CategoryInfo[]
  accountsData, // Destructure new prop
  onEditTransaction,
  onQuickCategoryChange,
  onCreateNewCategory,
  onNavigateToCategoryManagement,
  hasMore,
  onLoadMore,
  itemsLoaded,
  pageSize,
  onPageSizeChange, // Destructure new prop
  showAccountColumn = true, // Default to true for backward compatibility
}) => {
  const [selectedTransactionIds, setSelectedTransactionIds] = useState<Set<string>>(new Set());
  const selectAllCheckboxRef = useRef<HTMLInputElement>(null);

  // Pattern suggestion modal state
  const [isPatternModalOpen, setIsPatternModalOpen] = useState(false);
  const [patternModalTransaction, setPatternModalTransaction] = useState<{
    id: string;
    description: string;
    amount?: string;
  } | null>(null);
  const [patternModalCategory, setPatternModalCategory] = useState<Category | null>(null);

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

  // Use the sorting hook
  const { sortedData: sortedTransactionsOnPage, handleSort, getSortIndicator } = useTransactionViewSort(
    transactions,
    accountsMap
  );

  const availableCategories = useMemo(() => {
    // Only return real categories, no dummy fallbacks
    return categories || [];
  }, [categories]);

  // Convert CategoryInfo to Category format for CategoryQuickSelector
  const convertedCategories = useMemo(() => {
    return availableCategories.map(cat => ({
      categoryId: cat.categoryId,
      userId: cat.userId, // Use the actual userId from CategoryInfo
      name: cat.name,
      type: cat.type as 'EXPENSE' | 'INCOME', // Use the actual type from CategoryInfo
      icon: '📁', // Default icon
      color: '#6c757d', // Default color
      rules: [], // Empty rules array
      parentCategoryId: cat.parentCategoryId,
      inheritParentRules: false,
      ruleInheritanceMode: 'additive' as const,
      createdAt: Date.now(),
      updatedAt: Date.now()
    } as Category));
  }, [availableCategories]);

  // Handle new category creation
  const handleCreateNewCategory = (transactionData: {
    description: string;
    amount?: string;
    suggestedCategory?: {
      name: string;
      type: 'INCOME' | 'EXPENSE';
      confidence: number;
    };
    suggestedPatterns?: Array<{
      pattern: string;
      confidence: number;
      explanation: string;
    }>;
  }) => {
    if (onCreateNewCategory) {
      onCreateNewCategory(transactionData);
    } else if (onNavigateToCategoryManagement) {
      // Fallback to navigation with pre-populated data
      onNavigateToCategoryManagement({
        suggestedName: transactionData.suggestedCategory?.name,
        suggestedType: transactionData.suggestedCategory?.type,
        suggestedPattern: transactionData.suggestedPatterns?.[0]?.pattern,
        transactionDescription: transactionData.description
      });
    }
  };

  // Handle pattern confirmation from modal
  const handlePatternConfirm = async (_pattern: string, rule: Partial<CategoryRule>) => {
    if (!patternModalTransaction || !patternModalCategory) return;

    try {
      // Add rule to category - Type assertion needed until PatternSuggestionModal provides complete rule
      await CategoryService.addRuleToCategory(patternModalCategory.categoryId, rule as Omit<CategoryRule, 'ruleId'>);

      // Apply category to transaction
      onQuickCategoryChange(patternModalTransaction.id, patternModalCategory.categoryId);

      // Close modal
      setIsPatternModalOpen(false);
      setPatternModalTransaction(null);
      setPatternModalCategory(null);
    } catch (error) {
      console.error('Error creating rule and applying category:', error);
    }
  };

  // Handle new category creation from pattern modal
  const handlePatternModalCreateCategory = async (
    categoryName: string,
    categoryType: 'INCOME' | 'EXPENSE',
    pattern: string,
    fieldToMatch: string,
    condition: string
  ) => {
    if (!patternModalTransaction) return;

    try {
      // Create category with rule using the new API
      const response = await CategoryService.createWithRule(
        categoryName,
        categoryType,
        pattern,
        fieldToMatch,
        condition
      );

      // Apply the new category to the transaction
      onQuickCategoryChange(patternModalTransaction.id, response.category.categoryId);

      // Close modal
      setIsPatternModalOpen(false);
      setPatternModalTransaction(null);
      setPatternModalCategory(null);
    } catch (error) {
      console.error('Error creating category with rule:', error);
    }
  };



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



  if (isLoadingTransactions) {
    return <div className="transaction-table-loading">Loading transactions...</div>;
  }

  if (transactionsError) {
    return <div className="transaction-table-error">Error loading transactions: {transactionsError}</div>;
  }

  if (!isLoadingTransactions && transactions.length === 0 && itemsLoaded === 0) {
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
            <th
              onClick={() => handleSort('date')}
              onKeyDown={(e) => e.key === 'Enter' && handleSort('date')}
              tabIndex={0}
              role="button"
              aria-label="Sort by date"
            >
              Date{getSortIndicator('date')}
            </th>
            <th
              onClick={() => handleSort('description')}
              onKeyDown={(e) => e.key === 'Enter' && handleSort('description')}
              tabIndex={0}
              role="button"
              aria-label="Sort by description"
            >
              Description/Payee{getSortIndicator('description')}
            </th>
            <th
              onClick={() => handleSort('category')}
              onKeyDown={(e) => e.key === 'Enter' && handleSort('category')}
              tabIndex={0}
              role="button"
              aria-label="Sort by category"
            >
              Category{getSortIndicator('category')}
            </th>
            {showAccountColumn && (
              <th
                onClick={() => handleSort('account')}
                onKeyDown={(e) => e.key === 'Enter' && handleSort('account')}
                tabIndex={0}
                role="button"
                aria-label="Sort by account"
              >
                Account{getSortIndicator('account')}
              </th>
            )}
            <th
              onClick={() => handleSort('amount')}
              onKeyDown={(e) => e.key === 'Enter' && handleSort('amount')}
              tabIndex={0}
              role="button"
              aria-label="Sort by amount"
            >
              Amount{getSortIndicator('amount')}
            </th>
            <th
              onClick={() => handleSort('balance')}
              onKeyDown={(e) => e.key === 'Enter' && handleSort('balance')}
              tabIndex={0}
              role="button"
              aria-label="Sort by balance"
            >
              Balance{getSortIndicator('balance')}
            </th>
            <th
              onClick={() => handleSort('importOrder')}
              onKeyDown={(e) => e.key === 'Enter' && handleSort('importOrder')}
              tabIndex={0}
              role="button"
              aria-label="Sort by import order"
            >
              Import Order{getSortIndicator('importOrder')}
            </th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sortedTransactionsOnPage.length === 0 && (
            <tr>
              <td colSpan={showAccountColumn ? 9 : 8} style={{ textAlign: 'center', padding: '20px' }}>
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
                <DateCell date={transaction.date} />
              </td>
              <td>
                <TextWithSubtext
                  primaryText={transaction.description}
                  secondaryText={transaction.payee}
                />
              </td>
              <td>
                <div className="category-cell">
                  <CategoryQuickSelector
                    transactionId={transaction.id}
                    transactionDescription={transaction.description}
                    transactionAmount={transaction.amount?.toString()}
                    availableCategories={convertedCategories}
                    currentCategoryId={transaction.category}
                    onCategorySelect={onQuickCategoryChange}
                    onCreateNewCategory={handleCreateNewCategory}
                    disabled={isLoadingTransactions}
                  />
                  {/* Add Category Icon - shows for uncategorized transactions */}
                  {!transaction.category && (
                    <button
                      className="add-category-button"
                      onClick={() => {
                        if (onNavigateToCategoryManagement) {
                          onNavigateToCategoryManagement({
                            transactionDescription: transaction.description,
                            suggestedName: '', // Will be suggested by backend
                            suggestedPattern: '' // Will be suggested by backend
                          });
                        } else {
                          // Fallback: trigger pattern modal for new category creation
                          setPatternModalTransaction({
                            id: transaction.id,
                            description: transaction.description,
                            amount: transaction.amount?.toString()
                          });
                          setPatternModalCategory(null); // No selected category for new creation
                          setIsPatternModalOpen(true);
                        }
                      }}
                      title="Create new category for this transaction"
                      disabled={isLoadingTransactions}
                    >
                      +
                    </button>
                  )}
                </div>
              </td>
              {/* Updated to use accountsMap */}
              {showAccountColumn && (
                <td>
                  <LookupCell
                    id={transaction.accountId}
                    lookupMap={accountsMap}
                  />
                </td>
              )}
              <td>
                <CurrencyAmount
                  amount={transaction.amount}
                  currency={transaction.currency as string}
                />
              </td>
              <td>
                <CurrencyAmount
                  amount={transaction.balance}
                  currency={transaction.currency as string}
                  className="balance-cell"
                />
              </td>
              <td>
                <NumberCell value={transaction.importOrder} />
              </td>
              <td>
                <RowActions
                  itemId={transaction.id}
                  actions={[
                    {
                      key: 'edit',
                      icon: '✎',
                      label: 'Edit transaction',
                      onClick: onEditTransaction
                    }
                  ]}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <LoadMore
        hasMore={hasMore}
        isLoading={isLoadingTransactions}
        onLoadMore={onLoadMore}
        itemsLoaded={itemsLoaded}
        pageSize={pageSize}
        onPageSizeChange={onPageSizeChange}
      />

      {/* Pattern Suggestion Modal */}
      <PatternSuggestionModal
        isOpen={isPatternModalOpen}
        onClose={() => {
          setIsPatternModalOpen(false);
          setPatternModalTransaction(null);
          setPatternModalCategory(null);
        }}
        transactionDescription={patternModalTransaction?.description || ''}
        selectedCategory={patternModalCategory!}
        onConfirmPattern={handlePatternConfirm}
        onCreateCategory={handlePatternModalCreateCategory}
      />
    </div>
  );
};

export default TransactionTable; 