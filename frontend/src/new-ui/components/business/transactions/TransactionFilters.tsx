import React, { useState, useEffect } from 'react';
import './TransactionFilters.css';
import { CategoryInfo } from '@/schemas/Transaction'; // Keep CategoryInfo
import { Account } from '@/schemas/Account'; // Import Account from AccountService
import CustomMultiSelect from '@/new-ui/components/CustomMultiSelect';

export interface FilterValues {
  startDate?: string;
  endDate?: string;
  accountIds?: string[];
  categoryIds?: string[];
  transactionType?: 'all' | 'income' | 'expense' | 'transfer';
  searchTerm?: string;
}

interface TransactionFiltersProps {
  accounts: Account[]; // Changed from AccountInfo[]
  categories: CategoryInfo[];
  initialFilters?: FilterValues;
  onApplyFilters: (filters: FilterValues) => void;
  // onClearFilters might be handled by onApplyFilters with empty values
}

const DEFAULT_FILTERS: FilterValues = {
  startDate: '',
  endDate: '',
  accountIds: [],
  categoryIds: [],
  transactionType: 'all',
  searchTerm: '',
};

const TransactionFilters: React.FC<TransactionFiltersProps> = ({
  accounts,
  categories,
  initialFilters = DEFAULT_FILTERS,
  onApplyFilters,
}) => {
  const [filters, setFilters] = useState<FilterValues>(initialFilters);

  useEffect(() => {
    setFilters(initialFilters);
  }, [initialFilters]);

  // Clean up orphaned category IDs when categories list changes - just for display
  useEffect(() => {
    if (categories.length > 0 && filters.categoryIds && filters.categoryIds.length > 0) {
      const validCategoryIds = categories.map(cat => cat.categoryId);
      const filteredCategoryIds = filters.categoryIds.filter(id => validCategoryIds.includes(id));

      // Only update local display state if we found orphaned IDs
      if (filteredCategoryIds.length !== filters.categoryIds.length) {
        setFilters(prev => ({ ...prev, categoryIds: filteredCategoryIds }));
      }
    }
  }, [categories]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleAccountSelectionChange = (selectedValues: string[]) => {
    setFilters(prev => ({ ...prev, accountIds: selectedValues }));
  };

  const handleCategorySelectionChange = (selectedValues: string[]) => {
    // Filter out any category IDs that don't exist in available categories
    const validCategoryIds = categories.map(cat => cat.categoryId);
    const filteredValues = selectedValues.filter(id => validCategoryIds.includes(id));
    setFilters(prev => ({ ...prev, categoryIds: filteredValues }));
  };

  const handleTransactionTypeChange = (type: FilterValues['transactionType']) => {
    setFilters(prev => ({ ...prev, transactionType: type }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onApplyFilters(filters);
  };

  const handleClearFilters = () => {
    setFilters(DEFAULT_FILTERS);
    onApplyFilters(DEFAULT_FILTERS); // Also immediately apply cleared filters
  };

  return (
    <form className="transaction-filters-form" onSubmit={handleSubmit}>
      <div className="filter-grid">
        {/* Date Range Picker */}
        <div className="filter-group date-range-group">
          <label htmlFor="startDate">From:</label>
          <input
            type="date"
            id="startDate"
            name="startDate"
            value={filters.startDate || ''}
            onChange={handleChange}
            className="filter-input"
          />
          <label htmlFor="endDate">To:</label>
          <input
            type="date"
            id="endDate"
            name="endDate"
            value={filters.endDate || ''}
            onChange={handleChange}
            className="filter-input"
          />
        </div>

        {/* Account Filter */}
        <div className="filter-group">
          <label htmlFor="accountIds">Accounts:</label>
          <CustomMultiSelect
            options={accounts.map(account => ({
              value: account.accountId,
              label: account.accountName
            }))}
            selectedValues={filters.accountIds || []}
            onSelectionChange={handleAccountSelectionChange}
            placeholder="Select accounts..."
            className="filter-select"
          />
        </div>

        {/* Category Filter */}
        <div className="filter-group">
          <label htmlFor="categoryIds">Categories:</label>
          <CustomMultiSelect
            options={categories.map(category => ({
              value: category.categoryId,
              label: category.name
            }))}
            selectedValues={filters.categoryIds || []}
            onSelectionChange={handleCategorySelectionChange}
            placeholder="Select categories..."
            className="filter-select"
          />
        </div>

        {/* Transaction Type Filter */}
        <div className="filter-group transaction-type-group">
          <label>Type:</label>
          <div className="button-group">
            {(['all', 'income', 'expense', 'transfer'] as const).map(type => (
              <button
                key={type}
                type="button"
                className={`filter-button type-button ${filters.transactionType === type ? 'active' : ''}`}
                onClick={() => handleTransactionTypeChange(type)}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Search Bar */}
        <div className="filter-group search-group">
          <label htmlFor="searchTerm">Search:</label>
          <input
            type="text"
            id="searchTerm"
            name="searchTerm"
            placeholder="Description, payee, notes..."
            value={filters.searchTerm || ''}
            onChange={handleChange}
            className="filter-input search-input"
          />
        </div>
      </div>

      <div className="filter-actions">
        <button type="submit" className="filter-button apply-button">Apply Filters</button>
        <button type="button" onClick={handleClearFilters} className="filter-button clear-button">Clear Filters</button>
      </div>
    </form>
  );
};

export default TransactionFilters; 