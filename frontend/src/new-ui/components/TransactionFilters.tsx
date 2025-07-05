import React, { useState, useEffect } from 'react';
import './TransactionFilters.css';
import { CategoryInfo } from '../../services/TransactionService'; // Keep CategoryInfo
import { Account } from '../../services/AccountService'; // Import Account from AccountService

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

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleMultiSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const { name, options } = e.target;
    const selectedValues = Array.from(options)
      .filter(option => option.selected)
      .map(option => option.value);
    setFilters(prev => ({ ...prev, [name]: selectedValues }));
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
          <select 
            id="accountIds" 
            name="accountIds" 
            multiple 
            value={filters.accountIds || []} 
            onChange={handleMultiSelectChange} 
            className="filter-select multi-select"
          >
            {accounts.map(account => (
              <option key={account.accountId} value={account.accountId}>{account.accountName}</option>
            ))}
          </select>
        </div>

        {/* Category Filter */}
        <div className="filter-group">
          <label htmlFor="categoryIds">Categories:</label>
          <select 
            id="categoryIds" 
            name="categoryIds" 
            multiple 
            value={filters.categoryIds || []} 
            onChange={handleMultiSelectChange} 
            className="filter-select multi-select"
          >
            {categories.map(category => (
              <option key={category.categoryId} value={category.categoryId}>{category.name}</option>
            ))}
          </select>
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