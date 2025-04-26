import React, { useEffect, useState } from 'react';
import { Account, getAccount, getFileTimeline, deleteAccount } from '../services/AccountService';
import { FileMetadata, deleteFile, getDownloadUrl } from '../services/FileService';
import { Transaction, getAccountTransactions } from '../services/TransactionService';
import TimelineView from './TimelineView';
import './AccountDetail.css';

interface AccountDetailProps {
  accountId: string | null;
  onAccountDeleted?: () => void;
}

const AccountDetail: React.FC<AccountDetailProps> = ({ accountId, onAccountDeleted }) => {
  const [account, setAccount] = useState<Account | null>(null);
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [sortField, setSortField] = useState<keyof Transaction>('importOrder');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  useEffect(() => {
    if (accountId) {
      fetchAccountDetails(accountId);
    } else {
      setAccount(null);
      setFiles([]);
      setTransactions([]);
    }
    // Reset confirmation when changing accounts
    setDeleteConfirm(false);
  }, [accountId]);

  const fetchAccountDetails = async (id: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const accountData = await getAccount(id);
      setAccount(accountData.account);
      
      // Use getFileTimeline for timeline data
      const timelineFiles = await getFileTimeline(id);
      console.log('[Timeline Diagnostics] Timeline files:', timelineFiles);
      // Extract the timeline array if present
      const filesArray = Array.isArray(timelineFiles.timeline)
        ? timelineFiles.timeline
        : Array.isArray(timelineFiles)
          ? timelineFiles
          : [];
      const safeFiles = filesArray
        .filter(f => f.startDate && f.endDate)
        .map(f => ({
          ...f,
          startDate: typeof f.startDate === 'string' ? new Date(f.startDate).getTime() : f.startDate,
          endDate: typeof f.endDate === 'string' ? new Date(f.endDate).getTime() : f.endDate,
        }));
      console.log('[Timeline Diagnostics] Safe files:', safeFiles);
      setFiles(safeFiles);

      const transactionsData = await getAccountTransactions(id);
      setTransactions(transactionsData.transactions || []);
    } catch (err) {
      console.error('Error fetching account details:', err);
      setError('Failed to load account details');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (fileId: string, fileName: string) => {
    try {
      const downloadData = await getDownloadUrl(fileId);
      
      // Create a temporary link to trigger download
      const link = document.createElement('a');
      link.href = downloadData.downloadUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error downloading file:', err);
      alert('Failed to download file');
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    if (!window.confirm('Are you sure you want to delete this file?')) {
      return;
    }
    
    try {
      await deleteFile(fileId);
      // Refresh the files list
      if (accountId) {
        const filesData = await getFileTimeline(accountId);
        const filesArray = Array.isArray(filesData.timeline)
          ? filesData.timeline
          : Array.isArray(filesData)
            ? filesData
            : [];
        const safeFiles = filesArray
          .filter(f => f.startDate && f.endDate)
          .map(f => ({
            ...f,
            startDate: typeof f.startDate === 'string' ? new Date(f.startDate).getTime() : f.startDate,
            endDate: typeof f.endDate === 'string' ? new Date(f.endDate).getTime() : f.endDate,
          }));
        setFiles(safeFiles);
      }
    } catch (err) {
      console.error('Error deleting file:', err);
      alert('Failed to delete file');
    }
  };

  const handleDeleteAccount = async () => {
    if (!account) return;
    
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      return;
    }
    
    try {
      setDeleting(true);
      
      await deleteAccount(account.accountId);
      
      // Account deleted successfully, notify the parent component
      if (onAccountDeleted) {
        onAccountDeleted();
      } else {
        // If no callback provided, use fallback refresh method
        alert(`Account "${account.accountName}" has been deleted successfully`);
        window.location.reload();
      }
    } catch (err) {
      console.error('Error deleting account:', err);
      alert('Failed to delete account');
      setDeleteConfirm(false);
    } finally {
      setDeleting(false);
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm(false);
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

  const formatDate = (dateString: string | number) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const handleFileTimelineClick = (fileId: string) => {
    // Filter transactions to show only those from the selected file
    const file = files.find(f => f.fileId === fileId);
    if (file) {
      // TODO: Implement transaction filtering by file
      console.log(`Showing transactions for file: ${file.fileName}`);
    }
  };

  const handleGapTimelineClick = (startDate: number, endDate: number) => {
    // TODO: Implement export dialog with pre-filled dates
    console.log(`Suggest export for date range: ${new Date(startDate).toLocaleDateString()} to ${new Date(endDate).toLocaleDateString()}`);
  };

  // Diagnostics: log files before rendering TimelineView
  useEffect(() => {
    if (files) {
      console.log('[Timeline Diagnostics] Files passed to TimelineView:', files);
    }
  }, [files]);

  if (loading || !account) {
    return (
      <div className="account-detail">
        <div className="loading-message">
          {loading ? 'Loading account details...' : 'No account selected'}
        </div>
      </div>
    );
  }

  return (
    <div className="account-detail">
      {/* Diagnostics: show a warning if no files are available for the timeline */}
      {files.length === 0 && (
        <div style={{ color: 'orange', marginBottom: '1rem' }}>
          [Diagnostics] No files available for timeline. Check backend response and filtering logic.
        </div>
      )}
      <div className="account-detail-header">
        <h3>{account.accountName}</h3>
        <div className="account-detail-info">
          <div>
            <span className="account-detail-label">Type:</span>
            <span className="account-detail-type">{account.accountType}</span>
          </div>
          <div>
            <span className="account-detail-label">Balance:</span>
            <span className="account-detail-balance">{formatCurrency(account.balance)}</span>
          </div>
          {account.institution && (
            <div>
              <span className="account-detail-label">Institution:</span>
              <span>{account.institution}</span>
            </div>
          )}
        </div>
        
        <div className="account-actions">
          {!deleteConfirm ? (
            <button 
              className="delete-account-btn" 
              onClick={handleDeleteAccount}
              disabled={deleting}
            >
              Delete Account
            </button>
          ) : (
            <div className="delete-confirmation">
              <p>Are you sure? This will remove all account-file associations.</p>
              <div className="delete-confirmation-buttons">
                <button 
                  className="confirm-delete-btn" 
                  onClick={handleDeleteAccount}
                  disabled={deleting}
                >
                  {deleting ? 'Deleting...' : 'Yes, Delete Account'}
                </button>
                <button 
                  className="cancel-delete-btn" 
                  onClick={cancelDelete}
                  disabled={deleting}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <TimelineView 
        files={files}
        onFileClick={handleFileTimelineClick}
        onGapClick={handleGapTimelineClick}
      />

      <div className="account-files-section">
        <h4>Associated Files</h4>
        {files.length === 0 ? (
          <div className="no-files-message">No files associated with this account.</div>
        ) : (
          <div className="account-files-list">
            {files.map(file => (
              <div key={file.fileId} className="account-file-item">
                <div className="file-info">
                  <div className="file-name">{file.fileName}</div>
                  <div className="file-date">
                    Uploaded: {formatDate(file.uploadDate)}
                  </div>
                </div>
                <div className="file-actions">
                  <button
                    className="download-btn"
                    onClick={() => handleDownload(file.fileId, file.fileName)}
                  >
                    Download
                  </button>
                  <button
                    className="delete-btn"
                    onClick={() => handleDeleteFile(file.fileId)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="transactions-section">
        <h4>Transactions</h4>
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
                className={`header-cell balance ${sortField === 'balance' ? sortDirection : ''}`}
                onClick={() => handleSortChange('balance')}
              >
                Balance
              </div>
              <div 
                className={`header-cell import-order ${sortField === 'importOrder' ? sortDirection : ''}`}
                onClick={() => handleSortChange('importOrder')}
              >
                Order
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
                  if (sortField === 'amount' || sortField === 'balance' || sortField === 'importOrder') {
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
                    <div className="cell transaction-balance">
                      {formatCurrency(transaction.balance)}
                    </div>
                    <div className="cell import-order">
                      {transaction.importOrder}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountDetail; 