import React from 'react';

// Placeholder type - will be refined with useAccountTransactions hook
export interface UITransaction {
  id: string;
  date: string; // Or Date object
  description: string;
  category?: string;
  amount: string; // Using string if Decimal.js is involved, or number
  type: 'Debit' | 'Credit'; // Or an enum
  status?: string; // e.g., "Cleared", "Pending"
  importOrder?: number; // Import order for sorting
}

interface TransactionListProps {
  transactions: UITransaction[];
}

const TransactionList: React.FC<TransactionListProps> = ({ transactions }) => {
  if (!transactions || transactions.length === 0) {
    return <p>No transactions found for this account.</p>;
  }

  return (
    <div className="transaction-list">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Category</th>
            <th>Amount</th>
            <th>Type</th>
            <th>Status</th>
            <th>Import Order</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <tr key={tx.id}>
              <td>{tx.date}</td>
              <td>{tx.description}</td>
              <td>{tx.category || 'N/A'}</td>
              <td>{tx.amount}</td>
              <td>{tx.type}</td>
              <td>{tx.status || 'N/A'}</td>
              <td className="import-order">{tx.importOrder || 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TransactionList; 