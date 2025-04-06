import React, { useEffect, useState, useCallback } from 'react';
import { Account, listAccounts } from '../services/AccountService';
import './AccountList.css';

interface AccountListProps {
  onSelectAccount: (accountId: string) => void;
  selectedAccountId: string | null;
  refreshTrigger?: number; // Optional prop to trigger refresh
}

const AccountList: React.FC<AccountListProps> = ({ 
  onSelectAccount, 
  selectedAccountId,
  refreshTrigger = 0 
}) => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await listAccounts();
      setAccounts(response.accounts);
      
      // Auto-select the first account if none is selected and accounts are available
      if (!selectedAccountId && response.accounts.length > 0) {
        onSelectAccount(response.accounts[0].accountId);
      } else if (selectedAccountId && response.accounts.length > 0) {
        // Check if selected account still exists after refresh
        const accountExists = response.accounts.some(
          account => account.accountId === selectedAccountId
        );
        
        if (!accountExists) {
          // If selected account was deleted, select the first available account
          onSelectAccount(response.accounts[0].accountId);
        }
      } else if (response.accounts.length === 0) {
        // If no accounts left, clear selection
        onSelectAccount('');
      }
    } catch (err) {
      console.error('Error fetching accounts:', err);
      setError('Failed to load accounts. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [onSelectAccount, selectedAccountId]);
  
  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts, refreshTrigger]); // Re-fetch when refreshTrigger changes

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
      <div className="account-list-header">
        <h3>Your Accounts</h3>
        <button className="create-account-btn" onClick={() => window.alert('Create Account functionality will be implemented soon!')}>
          + New Account
        </button>
      </div>
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