import React, { useState, useEffect } from 'react';
import { Account, getAccount, listAccountFiles, deleteAccount } from '../services/AccountService';
import { Transaction, getAccountTransactions } from '../services/TransactionService';
import { FileMetadata } from '../services/FileService';
import AccountForm from './AccountForm';
import './AccountDetails.css';

interface AccountDetailsProps {
  accountId: string;
  onAccountDeleted: () => void;
}

const AccountDetails: React.FC<AccountDetailsProps> = ({ accountId, onAccountDeleted }) => {
  const [account, setAccount] = useState<Account | null>(null);
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<keyof Transaction>('date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const fetchAccountDetails = async () => {
    try {
      const response = await getAccount(accountId);
      setAccount(response.account);
    } catch (err) {
      console.error('Error fetching account:', err);
      setError('Failed to load account details');
    } finally {
      setLoading(false);
    }
  };

  const fetchAccountFiles = async () => {
    try {
      const response = await listAccountFiles(accountId);
      setFiles(response.files);
    } catch (err) {
      console.error('Error fetching account files:', err);
      setError('Failed to load account files');
    }
  };

  const fetchAccountTransactions = async () => {
    try {
      const response = await getAccountTransactions(accountId);
      setTransactions(response.transactions);
    } catch (err) {
      console.error('Error fetching account transactions:', err);
      setError('Failed to load account transactions');
    }
  };

  useEffect(() => {
    fetchAccountDetails();
    fetchAccountFiles();
    fetchAccountTransactions();
  }, [accountId]);

  const handleUpdateAccount = async (updatedData: Partial<Account>) => {
    try {
      // TODO: Implement update account API call
      await fetchAccountDetails();
      setIsEditing(false);
    } catch (err) {
      console.error('Error updating account:', err);
      setError('Failed to update account');
    }
  };

  const handleDeleteAccount = async () => {
    if (window.confirm('Are you sure you want to delete this account? This action cannot be undone.')) {
      try {
        await deleteAccount(accountId);
        onAccountDeleted();
      } catch (err) {
        console.error('Error deleting account:', err);
        setError('Failed to delete account');
      }
    }
  };

  const handleSortChange = (field: keyof Transaction) => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: account?.currency || 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  if (loading) {
    return <div className="account-details loading">Loading account details...</div>;
  }

  if (error) {
    return <div className="account-details error">{error}</div>;
  }

  if (!account) {
    return <div className="account-details error">Account not found</div>;
  }

  if (isEditing) {
    return (
      <div className="account-details">
        <AccountForm
          account={account}
          onSubmit={handleUpdateAccount}
          onCancel={() => setIsEditing(false)}
        />
      </div>
    );
  }

  return (
    <div className="account-details">
      <div className="account-header">
        <h2>{account.accountName}</h2>
        <div className="account-actions">
          <button onClick={() => setIsEditing(true)} className="edit-button">
            Edit Account
          </button>
          <button onClick={handleDeleteAccount} className="delete-button">
            Delete Account
          </button>
        </div>
      </div>

      <div className="account-info-grid">
        <div className="info-section">
          <h3>Account Information</h3>
          <div className="info-item">
            <span className="label">Type:</span>
            <span className="value">{account.accountType}</span>
          </div>
          <div className="info-item">
            <span className="label">Institution:</span>
            <span className="value">{account.institution}</span>
          </div>
          <div className="info-item">
            <span className="label">Balance:</span>
            <span className="value">
              {formatCurrency(account.balance)}
            </span>
          </div>
          <div className="info-item">
            <span className="label">Currency:</span>
            <span className="value">{account.currency}</span>
          </div>
          <div className="info-item">
            <span className="label">Status:</span>
            <span className={`value status ${account.isActive ? 'active' : 'inactive'}`}>
              {account.isActive ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>

        <div className="info-section">
          <h3>Additional Information</h3>
          {account.notes && (
            <div className="info-item">
              <span className="label">Notes:</span>
              <span className="value">{account.notes}</span>
            </div>
          )}
          <div className="info-item">
            <span className="label">Created:</span>
            <span className="value">{new Date(account.createdAt).toLocaleDateString()}</span>
          </div>
          <div className="info-item">
            <span className="label">Last Updated:</span>
            <span className="value">{new Date(account.updatedAt).toLocaleDateString()}</span>
          </div>
        </div>
      </div>

      <div className="transactions-section">
        <h3>Transactions</h3>
        {transactions.length === 0 ? (
          <div className="no-transactions">No transactions found for this account.</div>
        ) : (
          <div className="transactions-table">
            <div className="transactions-header">
              <div 
                className={`header-cell date ${sortField === 'date' ? sortDirection : ''}`}
                onClick={() => handleSortChange('date')}
              >
                Date
              </div>
              <div 
                className={`header-cell description ${sortField === 'description' ? sortDirection : ''}`}
                onClick={() => handleSortChange('description')}
              >
                Description
              </div>
              <div 
                className={`header-cell amount ${sortField === 'amount' ? sortDirection : ''}`}
                onClick={() => handleSortChange('amount')}
              >
                Amount
              </div>
              <div 
                className={`header-cell category ${sortField === 'category' ? sortDirection : ''}`}
                onClick={() => handleSortChange('category')}
              >
                Category
              </div>
            </div>
            <div className="transactions-body">
              {transactions
                .sort((a, b) => {
                  const aValue = a[sortField];
                  const bValue = b[sortField];
                  const direction = sortDirection === 'asc' ? 1 : -1;
                  
                  if (sortField === 'date') {
                    return direction * (new Date(aValue as string).getTime() - new Date(bValue as string).getTime());
                  }
                  if (sortField === 'amount') {
                    return direction * ((aValue as number) - (bValue as number));
                  }
                  return direction * String(aValue).localeCompare(String(bValue));
                })
                .map(transaction => (
                  <div key={transaction.transactionId} className="transaction-row">
                    <div className="cell date">{formatDate(transaction.date)}</div>
                    <div className="cell description">{transaction.description}</div>
                    <div className={`cell amount ${transaction.amount >= 0 ? 'positive' : 'negative'}`}>
                      {formatCurrency(transaction.amount)}
                    </div>
                    <div className="cell category">{transaction.category || '-'}</div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      <div className="files-section">
        <h3>Associated Files</h3>
        {files.length === 0 ? (
          <div className="no-files">No files associated with this account</div>
        ) : (
          <div className="files-list">
            {files.map(file => (
              <div key={file.fileId} className="file-item">
                <div className="file-name">{file.fileName}</div>
                <div className="file-meta">
                  <span className="file-date">
                    {new Date(file.uploadDate).toLocaleDateString()}
                  </span>
                  <span className="file-status">{file.processingStatus}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountDetails; 