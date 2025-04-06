import React, { useState, useEffect, useCallback } from 'react';
import AccountList from './AccountList';
import AccountDetail from './AccountDetail';
import './AccountManager.css';

const AccountManager: React.FC = () => {
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  const handleAccountSelect = (accountId: string) => {
    setSelectedAccountId(accountId === '' ? null : accountId);
  };

  const handleAccountDeleted = useCallback(() => {
    // Increment refresh trigger to force account list refresh
    setRefreshTrigger(prev => prev + 1);
    // Clear the selected account
    setSelectedAccountId(null);
  }, []);

  return (
    <div className="account-manager">
      <div className="account-manager-header">
        <h2>Account Management</h2>
        <p>View your accounts and their associated files</p>
      </div>
      
      <div className="account-manager-content">
        <div className="account-list-section">
          <AccountList 
            onSelectAccount={handleAccountSelect} 
            selectedAccountId={selectedAccountId}
            refreshTrigger={refreshTrigger}
          />
        </div>
        
        <div className="account-detail-section">
          <AccountDetail 
            accountId={selectedAccountId} 
            onAccountDeleted={handleAccountDeleted}
          />
        </div>
      </div>
    </div>
  );
};

export default AccountManager; 