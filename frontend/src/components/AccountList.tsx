import React, { useEffect, useState } from 'react';
import { Account, listAccounts } from '../services/AccountService';
import './AccountList.css';

interface AccountListProps {
  onSelectAccount: (accountId: string) => void;
  selectedAccountId: string | null;
}

const AccountList: React.FC<AccountListProps> = ({ onSelectAccount, selectedAccountId }) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAccounts = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await listAccounts();
        setAccounts(response.accounts);
        
        // Auto-select the first account if none is selected and accounts are available
        if (!selectedAccountId && response.accounts.length > 0) {
          onSelectAccount(response.accounts[0].accountId);
        }
      } catch (err) {
        console.error('Error fetching accounts:', err);
        setError('Failed to load accounts. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchAccounts();
  }, [onSelectAccount, selectedAccountId]);

  if (loading) {
    return (
      <div className="account-list">
        <h3>Your Accounts</h3>
        <div className="account-list-loading">Loading accounts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="account-list">
        <h3>Your Accounts</h3>
        <div className="account-list-error">{error}</div>
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <div className="account-list">
        <h3>Your Accounts</h3>
        <div className="account-list-empty">No accounts found.</div>
      </div>
    );
  }

  return (
    <div className="account-list">
      <h3>Your Accounts</h3>
      <div className="account-list-container">
        {accounts.map(account => (
          <div 
            key={account.accountId}
            className={`account-card ${selectedAccountId === account.accountId ? 'selected' : ''}`}
            onClick={() => onSelectAccount(account.accountId)}
          >
            <div className="account-name">{account.accountName}</div>
            <div className="account-info">
              <span className="account-type">{account.accountType}</span>
              <span className="account-balance">${parseFloat(account.balance.toString()).toFixed(2)}</span>
            </div>
            {account.institution && (
              <div className="account-institution">{account.institution}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AccountList; 