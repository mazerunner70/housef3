import React, { useState } from 'react';
// import { useParams } from 'react-router-dom'; // Assuming routing will provide accountId
import AccountFilesTab from '../components/accounts/AccountFilesTab';
import AccountTransactionsTab from '../components/accounts/AccountTransactionsTab'; // Import the new tab
// import AccountTransactionsTab from '../components/accounts/AccountTransactionsTab'; // To be added later
import { UIAccount } from '../hooks/useAccounts'; // Import UIAccount type
import './AccountDetailView.css'; // Import the CSS file

interface AccountDetailViewProps {
  account: UIAccount; // Changed from accountId: string to account: UIAccount
}

const AccountDetailView: React.FC<AccountDetailViewProps> = ({ account }) => {
  const [activeTab, setActiveTab] = useState<'files' | 'transactions'>('files');

  // const { accountId } = useParams<{ accountId: string }>(); // Example if using react-router

  if (!account) { // Check for account object
    return <div>Loading account details or account not found...</div>;
  }

  return (
    <div className="account-detail-view">
      <h2>{account.name} ({account.type})</h2>
      <p>Bank: {account.bankName || 'N/A'} - Balance: {account.balance?.toString() || 'N/A'} {account.currency}</p>
      <div className="tabs">
        <button onClick={() => setActiveTab('files')} className={activeTab === 'files' ? 'active' : ''}>
          Files
        </button>
        <button onClick={() => setActiveTab('transactions')} className={activeTab === 'transactions' ? 'active' : ''}>
          Transactions
        </button>
      </div>
      <div className="tab-content">
        {activeTab === 'files' && <AccountFilesTab accountId={account.id} />}
        {activeTab === 'transactions' && <AccountTransactionsTab accountId={account.id} />}
        {/* {activeTab === 'transactions' && <AccountTransactionsTab accountId={accountId} />} */}
      </div>
    </div>
  );
};

export default AccountDetailView; 