import React, { useState, useEffect } from 'react';
import AccountList from './AccountList';
import AccountDetail from './AccountDetail';
import './AccountManager.css';

const AccountManager: React.FC = () => {
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);

  const handleAccountSelect = (accountId: string) => {
    setSelectedAccountId(accountId);
  };

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
          />
        </div>
        
        <div className="account-detail-section">
          <AccountDetail accountId={selectedAccountId} />
        </div>
      </div>
    </div>
  );
};

export default AccountManager; 