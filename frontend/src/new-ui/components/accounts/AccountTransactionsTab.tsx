import React from 'react';
// import TransactionList from './TransactionList'; // To be created
// import useAccountTransactions from '../../hooks/useAccountTransactions'; // To be created

interface AccountTransactionsTabProps {
  accountId: string;
}

const AccountTransactionsTab: React.FC<AccountTransactionsTabProps> = ({ accountId }) => {
  // const { transactions, loading, error, fetchTransactions } = useAccountTransactions(accountId);

  // if (loading) return <p>Loading transactions...</p>;
  // if (error) return <p>Error loading transactions: {error}</p>;

  return (
    <div className="account-transactions-tab">
      <h3>Transactions for Account: {accountId}</h3>
      {/* <TransactionList transactions={transactions} /> */}
      <p>Transaction list will appear here.</p>
    </div>
  );
};

export default AccountTransactionsTab; 