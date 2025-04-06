import React, { useEffect, useState } from 'react';
import { Account, getAccount, listAccountFiles } from '../services/AccountService';
import { FileMetadata, deleteFile, getDownloadUrl } from '../services/FileService';
import './AccountDetail.css';

interface AccountDetailProps {
  accountId: string | null;
}

const AccountDetail: React.FC<AccountDetailProps> = ({ accountId }) => {
  const [account, setAccount] = useState<Account | null>(null);
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [downloadingFileId, setDownloadingFileId] = useState<string | null>(null);
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);

  useEffect(() => {
    if (!accountId) {
      setAccount(null);
      setFiles([]);
      return;
    }

    const fetchAccountData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch account details
        const accountData = await getAccount(accountId);
        setAccount(accountData);
        
        // Fetch files associated with this account
        const accountFiles = await listAccountFiles(accountId);
        setFiles(accountFiles.files);
      } catch (err) {
        console.error('Error fetching account data:', err);
        setError('Failed to load account details. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchAccountData();
  }, [accountId]);

  const handleDownload = async (fileId: string, fileName: string) => {
    try {
      setDownloadingFileId(fileId);
      const downloadUrl = await getDownloadUrl(fileId);
      
      // Create a temporary anchor element to trigger the download
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Error downloading file:', err);
      alert('Failed to download the file. Please try again.');
    } finally {
      setDownloadingFileId(null);
    }
  };

  const handleDelete = async (fileId: string) => {
    const confirmDelete = window.confirm('Are you sure you want to delete this file?');
    if (!confirmDelete) return;

    try {
      setDeletingFileId(fileId);
      await deleteFile(fileId);
      
      // Update the files list after successful deletion
      setFiles(prevFiles => prevFiles.filter(file => file.fileId !== fileId));
    } catch (err) {
      console.error('Error deleting file:', err);
      alert('Failed to delete the file. Please try again.');
    } finally {
      setDeletingFileId(null);
    }
  };

  if (!accountId) {
    return (
      <div className="account-detail-empty">
        <p>Select an account to view its details and associated files.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="account-detail-loading">
        <p>Loading account details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="account-detail-error">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="account-detail">
      {account && (
        <div className="account-detail-header">
          <h3>{account.accountName}</h3>
          <div className="account-detail-info">
            <div>
              <span className="account-detail-label">Type:</span>
              <span className="account-detail-type">{account.accountType}</span>
            </div>
            <div>
              <span className="account-detail-label">Balance:</span>
              <span className="account-detail-balance">${parseFloat(account.balance.toString()).toFixed(2)}</span>
            </div>
            {account.institution && (
              <div>
                <span className="account-detail-label">Institution:</span>
                <span>{account.institution}</span>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="account-files-section">
        <h4>Associated Files</h4>
        
        {files.length === 0 ? (
          <p className="no-files-message">No files associated with this account.</p>
        ) : (
          <div className="account-files-list">
            {files.map(file => (
              <div key={file.fileId} className="account-file-item">
                <div className="file-info">
                  <span className="file-name">{file.fileName}</span>
                  <span className="file-date">
                    {new Date(file.uploadDate).toLocaleDateString()}
                  </span>
                </div>
                
                <div className="file-actions">
                  <button
                    className="download-btn"
                    onClick={() => handleDownload(file.fileId, file.fileName)}
                    disabled={downloadingFileId === file.fileId}
                  >
                    {downloadingFileId === file.fileId ? 'Downloading...' : 'Download'}
                  </button>
                  
                  <button
                    className="delete-btn"
                    onClick={() => handleDelete(file.fileId)}
                    disabled={deletingFileId === file.fileId}
                  >
                    {deletingFileId === file.fileId ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AccountDetail; 