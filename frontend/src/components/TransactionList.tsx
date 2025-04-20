import React, { useState, useEffect } from 'react';
import { Transaction, getFileTransactions } from '../services/TransactionService';
import './TransactionList.css';

interface TransactionListProps {
  fileId: string;
  fileName?: string;
  openingBalance?: number;
  onClose: () => void;
}

const TransactionList: React.FC<TransactionListProps> = ({ 
  fileId, 
  fileName, 
  openingBalance, 
  onClose 
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<keyof Transaction>('importOrder');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [isCustomSorted, setIsCustomSorted] = useState(false);

  // Load transactions when component mounts
  useEffect(() => {
    const loadTransactions = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await getFileTransactions(fileId);
        setTransactions(data.transactions || []);
      } catch (error) {
        console.error('Error loading transactions:', error);
        setError(error instanceof Error ? error.message : 'Failed to load transactions');
        setTransactions([]);
      } finally {
        setLoading(false);
      }
    };
    
    loadTransactions();
  }, [fileId]);

  // Format amount as currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Handle sort change
  const handleSortChange = (field: keyof Transaction) => {
    setIsCustomSorted(true);
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Reset to import order
  const resetToImportOrder = () => {
    setIsCustomSorted(false);
    setSortField('importOrder');
    setSortDirection('asc');
  };

  // Get sorted transactions
  const getSortedTransactions = () => {
    if (!isCustomSorted) {
      // Use importOrder when no custom sorting is applied
      return [...transactions].sort((a, b) => a.importOrder - b.importOrder);
    }

    return [...transactions].sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];
      
      // Handle date comparison
      if (sortField === 'date') {
        aValue = new Date(a.date).getTime();
        bValue = new Date(b.date).getTime();
      }
      
      // Handle numeric comparison
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      // Handle string comparison
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return 0;
    });
  };

  // Get sort indicator
  const getSortIndicator = (field: keyof Transaction) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  return (
    <div className="transaction-list-container">
      <div className="transaction-list-header">
        <h2>{fileName ? `Transactions - ${fileName}` : 'Transactions'}</h2>
        <div className="header-actions">
          {isCustomSorted && (
            <button 
              className="reset-order-button" 
              onClick={resetToImportOrder}
              title="Reset to original import order"
            >
              Reset Order
            </button>
          )}
          <button className="close-button" onClick={onClose}>×</button>
        </div>
      </div>

      {/* Opening balance */}
      {openingBalance !== undefined && (
        <div className="opening-balance">
          Opening Balance: {formatCurrency(openingBalance)}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="transaction-list-error">
          <span className="error-icon">⚠️</span> {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="loading-transactions">Loading transactions...</div>
      ) : transactions.length === 0 ? (
        <div className="no-transactions">No transactions found.</div>
      ) : (
        <div className="transaction-table-container">
          <table className="transaction-table">
            <thead>
              <tr>
                <th onClick={() => handleSortChange('date')} className="sortable">
                  Date {getSortIndicator('date')}
                </th>
                <th onClick={() => handleSortChange('description')} className="sortable">
                  Description {getSortIndicator('description')}
                </th>
                <th onClick={() => handleSortChange('amount')} className="sortable">
                  Amount {getSortIndicator('amount')}
                </th>
                <th onClick={() => handleSortChange('runningTotal')} className="sortable">
                  Balance {getSortIndicator('runningTotal')}
                </th>
                <th>Type</th>
                <th>Category</th>
                <th>Reference</th>
              </tr>
            </thead>
            <tbody>
              {getSortedTransactions().map(transaction => (
                <tr key={transaction.transactionId}>
                  <td>{formatDate(transaction.date)}</td>
                  <td className="description-cell">
                    {transaction.description}
                    {transaction.memo && (
                      <div className="memo">{transaction.memo}</div>
                    )}
                  </td>
                  <td className={`amount-cell ${transaction.amount >= 0 ? 'positive' : 'negative'}`}>
                    {formatCurrency(transaction.amount)}
                  </td>
                  <td className="balance-cell">
                    {formatCurrency(transaction.runningTotal)}
                  </td>
                  <td>{transaction.transactionType}</td>
                  <td>{transaction.category}</td>
                  <td>{transaction.reference || transaction.checkNumber}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TransactionList; 