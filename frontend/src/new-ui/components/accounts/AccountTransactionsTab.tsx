import React, { useState } from 'react';
import useAccountTransactions from '../../hooks/useAccountTransactions';
import TransactionTable from '../TransactionTable';
import { Account } from '../../../services/AccountService';

interface AccountTransactionsTabProps {
  accountId: string;
}

const AccountTransactionsTab: React.FC<AccountTransactionsTabProps> = ({ accountId }) => {
  const { transactions, loading, error, categories, handleQuickCategoryChange } = useAccountTransactions(accountId);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const handleEditTransaction = (transactionId: string) => {
    console.log("Edit transaction (placeholder):", transactionId);
    alert('Edit functionality to be implemented for account transactions.');
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  // Calculate pagination for client-side pagination
  const totalItems = transactions.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedTransactions = transactions.slice(startIndex, endIndex);

  if (loading) {
    return <div className="loading-spinner">Loading transactions...</div>;
  }

  if (error) {
    return <div className="error-message">Error loading transactions: {error}</div>;
  }

  return (
    <div className="account-transactions-tab">
      <h3>Account Transactions</h3>
      <p>Showing {transactions.length} transactions for this account</p>
      <TransactionTable
        transactions={paginatedTransactions}
        isLoading={loading}
        error={error}
        categories={categories}
        accountsData={[]} // Empty array since we're not showing account column
        onEditTransaction={handleEditTransaction}
        onQuickCategoryChange={handleQuickCategoryChange}
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
        itemsPerPage={pageSize}
        totalItems={totalItems}
        onPageSizeChange={handlePageSizeChange}
        showAccountColumn={false} // Hide the account column since we're already in account context
      />
    </div>
  );
};

export default AccountTransactionsTab; 