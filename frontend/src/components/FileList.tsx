import React, { useState, useEffect } from 'react';
import { 
  listFiles, 
  deleteFile, 
  getDownloadUrl, 
  unassociateFileFromAccount,
  associateFileWithAccount,
  updateFileBalance,
  FileMetadata 
} from '../services/FileService';
import {
  listAccounts,
  Account
} from '../services/AccountService';
import './FileList.css';
import TransactionList from './TransactionList';
import FileFieldMapStatus from './FileFieldMapStatus';
import FieldMapList from './FieldMapList';
import { FieldMapForm } from './FieldMapForm';
import FileService, { File } from '../services/FileService';
import { FieldMap } from '../services/FieldMapService';
import { downloadFile } from '../utils/downloadUtils';

interface FileListProps {
  onRefreshNeeded: boolean;
  onRefreshComplete: () => void;
}

const FileList: React.FC<FileListProps> = ({ onRefreshNeeded, onRefreshComplete }) => {
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortField, setSortField] = useState<'fileName' | 'uploadDate' | 'fileSize'>('uploadDate');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [deletingFileId, setDeletingFileId] = useState<string | null>(null);
  const [downloadingFileId, setDownloadingFileId] = useState<string | null>(null);
  const [unassociatingFileId, setUnassociatingFileId] = useState<string | null>(null);
  const [associatingFileId, setAssociatingFileId] = useState<string | null>(null);
  const [editingBalanceFileId, setEditingBalanceFileId] = useState<string | null>(null);
  const [balanceInput, setBalanceInput] = useState<string>('');
  const [savingBalanceFileId, setSavingBalanceFileId] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [success, setSuccess] = useState<string | null>(null);
  const [viewingTransactionsFileId, setViewingTransactionsFileId] = useState<string | null>(null);
  const [viewingTransactionsFile, setViewingTransactionsFile] = useState<FileMetadata | null>(null);
  const [selectedMapFileId, setSelectedMapFileId] = useState<string | null>(null);
  const [showFieldMapModal, setShowFieldMapModal] = useState<boolean>(false);
  const [showFieldMapForm, setShowFieldMapForm] = useState(false);
  const [selectedFileForMap, setSelectedFileForMap] = useState<string | null>(null);

  // Load files from API
  const loadFiles = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await listFiles();
      const filesWithAccounts = response.files || [];
      
      // For files with accountId but no accountName, we could fetch accounts in bulk
      // For now, we'll leave them with just the ID display
      
      setFiles(filesWithAccounts);
    } catch (error) {
      console.error('Error loading files:', error);
      setError(error instanceof Error ? error.message : 'Failed to load files');
      setFiles([]);
    } finally {
      setLoading(false);
      if (onRefreshNeeded) {
        onRefreshComplete();
      }
    }
  };

  // Load accounts for association dropdown
  const loadAccounts = async () => {
    try {
      const response = await listAccounts();
      setAccounts(response.accounts || []);
    } catch (error) {
      console.error('Error loading accounts:', error);
      // Don't set error state here to avoid disrupting the main file list UI
      setAccounts([]);
    }
  };

  // Load files on component mount and when refresh is needed
  useEffect(() => {
    loadFiles();
    loadAccounts();
  }, [onRefreshNeeded]);

  // Handle file deletion
  const handleDeleteFile = async (fileId: string) => {
    if (!confirm('Are you sure you want to delete this file?')) {
      return;
    }
    
    setDeletingFileId(fileId);
    setError(null);
    
    try {
      await deleteFile(fileId);
      // Refresh file list
      await loadFiles();
    } catch (error) {
      console.error('Error deleting file:', error);
      setError(error instanceof Error ? error.message : 'Failed to delete file');
    } finally {
      setDeletingFileId(null);
    }
  };

  // Handle file download
  const handleDownload = async (fileId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      const fileData = await FileService.getFileContent(fileId);
      await downloadFile(fileData.content, fileData.fileName, fileData.contentType);
    } catch (err) {
      setError('Failed to download file');
      console.error('Download error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle unassociating a file from an account
  const handleUnassociateFile = async (fileId: string) => {
    if (!confirm('Are you sure you want to remove this file from its associated account?')) {
      return;
    }
    
    setUnassociatingFileId(fileId);
    setError(null);
    
    try {
      await unassociateFileFromAccount(fileId);
      // Refresh file list
      await loadFiles();
    } catch (error) {
      console.error('Error unassociating file:', error);
      setError(error instanceof Error ? error.message : 'Failed to unassociate file from account');
    } finally {
      setUnassociatingFileId(null);
    }
  };

  // Handle file-account association
  const handleAssociateFile = async (fileId: string, accountId: string) => {
    if (!accountId) {
      alert('Please select an account');
      return;
    }
    
    setAssociatingFileId(fileId);
    setError(null);
    
    try {
      await associateFileWithAccount(fileId, accountId);
      // Clear the selected account ID
      setSelectedAccountId('');
      // Stop showing the association UI
      setAssociatingFileId(null);
      // Refresh file list
      await loadFiles();
    } catch (error) {
      console.error('Error associating file:', error);
      setError(error instanceof Error ? error.message : 'Failed to associate file with account');
      setAssociatingFileId(null);
    }
  };

  // Start the association process for a file
  const startAssociateFile = (fileId: string) => {
    // Toggle association UI if clicking the same file
    if (associatingFileId === fileId) {
      setAssociatingFileId(null);
      setSelectedAccountId('');
    } else {
      setAssociatingFileId(fileId);
      setSelectedAccountId('');
    }
  };

  // Handle account selection in dropdown
  const handleAccountSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedAccountId(e.target.value);
  };

  // Handle sort change
  const handleSortChange = (field: 'fileName' | 'uploadDate' | 'fileSize') => {
    // If clicking on the same field, toggle direction
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Default to descending for dates, ascending for names
      const newDirection = field === 'uploadDate' ? 'desc' : 'asc';
      setSortField(field);
      setSortDirection(newDirection);
    }
  };

  // Format date string
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch (error) {
      return dateString;
    }
  };

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Filter and sort files
  const getFilteredAndSortedFiles = () => {
    // First filter by search term
    const filtered = searchTerm.trim() === '' 
      ? files
      : files.filter(file => 
          file.fileName.toLowerCase().includes(searchTerm.toLowerCase())
        );
    
    // Then sort
    return filtered.sort((a, b) => {
      let comparison = 0;
      
      if (sortField === 'fileName') {
        comparison = a.fileName.localeCompare(b.fileName);
      } else if (sortField === 'uploadDate') {
        comparison = new Date(a.uploadDate).getTime() - new Date(b.uploadDate).getTime();
      } else if (sortField === 'fileSize') {
        comparison = a.fileSize - b.fileSize;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });
  };

  // Get sorting indicator
  const getSortIndicator = (field: 'fileName' | 'uploadDate' | 'fileSize') => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? '↑' : '↓';
  };

  // Handle search
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  // Handle refresh button click
  const handleRefresh = () => {
    loadFiles();
  };

  // Handle adding a balance to a file
  const handleAddBalance = (fileId: string) => {
    setEditingBalanceFileId(fileId);
    setBalanceInput('');
  };

  // Handle editing an existing balance
  const handleEditBalance = (fileId: string, currentBalance: number | undefined) => {
    setEditingBalanceFileId(fileId);
    setBalanceInput(currentBalance !== undefined ? currentBalance.toString() : '');
  };

  // Handle saving the balance
  const handleSaveBalance = async (fileId: string) => {
    // Validate the input is a valid number
    const balanceValue = parseFloat(balanceInput);
    if (isNaN(balanceValue)) {
      setError('Please enter a valid number for the opening balance');
      return;
    }
    
    setSavingBalanceFileId(fileId);
    setError(null);
    
    try {
      // Call the API to update the file's opening balance
      const response = await updateFileBalance(fileId, balanceValue);
      
      // Update the file in our local state, including transaction count if returned
      const updatedFiles = files.map(file => {
        if (file.fileId === fileId) {
          return {
            ...file,
            openingBalance: balanceValue,
          };
        }
        return file;
      });
      
      setFiles(updatedFiles);
      setEditingBalanceFileId(null);
      setBalanceInput('');
      
      // If transactions were processed, show a success message
      if (response.transactionCount !== undefined) {
        setSuccess(`Opening balance updated and ${response.transactionCount} transactions processed`);
      } else {
        setSuccess('Opening balance updated successfully');
      }
    } catch (error) {
      console.error('Error saving balance:', error);
      setError(error instanceof Error ? error.message : 'Failed to save opening balance');
    } finally {
      setSavingBalanceFileId(null);
    }
  };

  // Handle cancel balance edit
  const handleCancelBalanceEdit = () => {
    setEditingBalanceFileId(null);
    setBalanceInput('');
  };

  // Handle balance input change
  const handleBalanceInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBalanceInput(e.target.value);
  };

  // Add this function to handle viewing transactions
  const handleViewTransactions = (file: FileMetadata) => {
    setViewingTransactionsFileId(file.fileId);
    setViewingTransactionsFile(file);
  };

  // Add this function to handle closing the transaction view
  const handleCloseTransactions = () => {
    setViewingTransactionsFileId(null);
    setViewingTransactionsFile(null);
  };

  const handleSelectMap = (fileId: string) => {
    setSelectedFileForMap(fileId);
    setShowFieldMapForm(true);
  };

  const handleFieldMapSave = async (fieldMap: FieldMap) => {
    try {
      if (selectedFileForMap) {
        await FileService.associateFieldMap(selectedFileForMap, fieldMap.fieldMapId);
        await loadFiles();
      }
      setShowFieldMapForm(false);
      setSelectedFileForMap(null);
    } catch (error) {
      console.error('Error saving field map:', error);
      setError(error instanceof Error ? error.message : 'Failed to save field map');
    }
  };

  // Render filtered and sorted files
  const filteredAndSortedFiles = getFilteredAndSortedFiles();

  return (
    <div className="file-list-container">
      <h2>Your Files</h2>
      
      {/* Search and refresh controls */}
      <div className="file-list-controls">
        <div className="search-container">
          <input
            type="text"
            placeholder="Search files..."
            value={searchTerm}
            onChange={handleSearch}
            className="search-input"
          />
        </div>
        <button 
          className="refresh-button" 
          onClick={handleRefresh}
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
      
      {/* Error message */}
      {error && (
        <div className="file-list-error">
          <span className="error-icon">⚠️</span> {error}
        </div>
      )}
      
      {/* Success message */}
      {success && (
        <div className="file-list-success">
          <span className="success-icon">✅</span> {success}
        </div>
      )}
      
      {/* File listing */}
      {loading && files.length === 0 ? (
        <div className="loading-files">Loading files...</div>
      ) : (
        <>
          {filteredAndSortedFiles.length === 0 ? (
            <div className="no-files">
              {searchTerm.trim() !== '' 
                ? 'No files match your search.' 
                : 'You have not uploaded any files yet.'}
            </div>
          ) : (
            <div className="file-table-container">
              <table className="file-table">
                <thead>
                  <tr>
                    <th 
                      className="sortable"
                      onClick={() => handleSortChange('fileName')}
                    >
                      Name {getSortIndicator('fileName')}
                    </th>
                    <th 
                      className="sortable"
                      onClick={() => handleSortChange('uploadDate')}
                    >
                      Date Uploaded {getSortIndicator('uploadDate')}
                    </th>
                    <th 
                      className="sortable"
                      onClick={() => handleSortChange('fileSize')}
                    >
                      Size {getSortIndicator('fileSize')}
                    </th>
                    <th>Type</th>
                    <th>Format</th>
                    <th>Status</th>
                    <th>Account</th>
                    <th>Opening Balance</th>
                    <th>Field Map</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAndSortedFiles.map(file => (
                    <tr key={file.fileId}>
                      <td className="file-name-cell">{file.fileName}</td>
                      <td>{formatDate(file.uploadDate)}</td>
                      <td>{formatFileSize(file.fileSize)}</td>
                      <td>{file.contentType}</td>
                      <td>{file.fileFormat ? file.fileFormat.toUpperCase() : 'OTHER'}</td>
                      <td>
                        {file.processingStatus && (
                          <span className={`processing-status status-${file.processingStatus}`}>
                            {file.processingStatus.charAt(0).toUpperCase() + file.processingStatus.slice(1)}
                          </span>
                        )}
                      </td>
                      <td className="file-account-cell">
                        {file.accountId ? (
                          <div className="account-with-action">
                            <span className="account-badge">{file.accountName || `${file.accountId.substring(0, 8)}...`}</span>
                            <button 
                              className="unassociate-button"
                              onClick={() => handleUnassociateFile(file.fileId)}
                              disabled={unassociatingFileId === file.fileId}
                              title="Remove account association"
                            >
                              {unassociatingFileId === file.fileId ? '...' : '×'}
                            </button>
                          </div>
                        ) : (
                          <div className="account-with-action">
                            {associatingFileId === file.fileId ? (
                              <div className="associate-control">
                                <select 
                                  value={selectedAccountId} 
                                  onChange={handleAccountSelect}
                                  className="account-select"
                                >
                                  <option value="">Select account...</option>
                                  {accounts.map(account => (
                                    <option key={account.accountId} value={account.accountId}>
                                      {account.accountName}
                                    </option>
                                  ))}
                                </select>
                                <div className="associate-buttons">
                                  <button 
                                    className="confirm-associate-button" 
                                    onClick={() => handleAssociateFile(file.fileId, selectedAccountId)}
                                    disabled={!selectedAccountId}
                                  >
                                    ✓
                                  </button>
                                  <button 
                                    className="cancel-associate-button"
                                    onClick={() => setAssociatingFileId(null)}
                                  >
                                    ×
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <button 
                                className="associate-button"
                                onClick={() => startAssociateFile(file.fileId)}
                                title="Associate with account"
                              >
                                Link
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="file-balance-cell">
                        {file.openingBalance !== undefined ? (
                          editingBalanceFileId === file.fileId ? (
                            <div className="balance-input-container">
                              <input
                                type="text"
                                value={balanceInput}
                                onChange={handleBalanceInputChange}
                                className="balance-input"
                                placeholder="0.00"
                                autoFocus
                              />
                              <div className="balance-input-actions">
                                <button
                                  className="save-balance-button"
                                  onClick={() => handleSaveBalance(file.fileId)}
                                  disabled={savingBalanceFileId === file.fileId}
                                >
                                  {savingBalanceFileId === file.fileId ? '...' : '✓'}
                                </button>
                                <button
                                  className="cancel-balance-button"
                                  onClick={handleCancelBalanceEdit}
                                  disabled={savingBalanceFileId === file.fileId}
                                >
                                  ×
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="balance-with-edit">
                              <span className="balance-display">${file.openingBalance.toFixed(2)}</span>
                              <button
                                className="edit-balance-button"
                                onClick={() => handleEditBalance(file.fileId, file.openingBalance)}
                                title="Edit opening balance"
                              >
                                ✎
                              </button>
                            </div>
                          )
                        ) : editingBalanceFileId === file.fileId ? (
                          <div className="balance-input-container">
                            <input
                              type="text"
                              value={balanceInput}
                              onChange={handleBalanceInputChange}
                              className="balance-input"
                              placeholder="0.00"
                              autoFocus
                            />
                            <div className="balance-input-actions">
                              <button
                                className="save-balance-button"
                                onClick={() => handleSaveBalance(file.fileId)}
                                disabled={savingBalanceFileId === file.fileId}
                              >
                                {savingBalanceFileId === file.fileId ? '...' : '✓'}
                              </button>
                              <button
                                className="cancel-balance-button"
                                onClick={handleCancelBalanceEdit}
                                disabled={savingBalanceFileId === file.fileId}
                              >
                                ×
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button 
                            className="add-balance-button"
                            onClick={() => handleAddBalance(file.fileId)}
                            title="Add opening balance"
                          >
                            Add Balance
                          </button>
                        )}
                      </td>
                      <td>
                        <FileFieldMapStatus
                          fieldMap={file.fieldMap}
                          onSelectMap={() => handleSelectMap(file.fileId)}
                          onCreateMap={() => {
                            setSelectedFileForMap(file.fileId);
                            setShowFieldMapForm(true);
                          }}
                          className="file-list-field-map"
                        />
                      </td>
                      <td className="file-actions">
                        <button 
                          className="download-button"
                          onClick={() => handleDownload(file.fileId)}
                          disabled={loading}
                        >
                          {loading ? '...' : 'Download'}
                        </button>
                        <button 
                          className="delete-button"
                          onClick={() => handleDeleteFile(file.fileId)}
                          disabled={deletingFileId === file.fileId}
                        >
                          {deletingFileId === file.fileId ? '...' : 'Delete'}
                        </button>
                        <button
                          className="view-transactions-button"
                          onClick={() => handleViewTransactions(file)}
                          disabled={!file.openingBalance}
                          title={!file.openingBalance ? "Set opening balance to view transactions" : "View transactions"}
                        >
                          View Transactions
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          <div className="file-count">
            {filteredAndSortedFiles.length} file{filteredAndSortedFiles.length !== 1 ? 's' : ''}
            {searchTerm.trim() !== '' && files.length > filteredAndSortedFiles.length && 
              ` (filtered from ${files.length})`
            }
          </div>
        </>
      )}

      {viewingTransactionsFileId && viewingTransactionsFile && (
        <div className="modal-overlay">
          <div className="modal-content">
            <TransactionList
              fileId={viewingTransactionsFileId}
              fileName={viewingTransactionsFile.fileName}
              openingBalance={viewingTransactionsFile.openingBalance}
              onClose={handleCloseTransactions}
            />
          </div>
        </div>
      )}

      {showFieldMapModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <FieldMapList
              onSelectMap={(map) => {
                if (selectedFileForMap) {
                  FileService.associateFieldMap(selectedFileForMap, map.fieldMapId)
                    .then(() => {
                      loadFiles();
                      setShowFieldMapModal(false);
                      setSelectedFileForMap(null);
                    })
                    .catch(console.error);
                }
              }}
              onCreateMap={() => {
                setSelectedFileForMap(selectedMapFileId);
                setShowFieldMapForm(true);
              }}
              onEditMap={(map) => {
                // Handle map editing
                setShowFieldMapModal(false);
              }}
              onDeleteMap={(map) => {
                // Handle map deletion
                setShowFieldMapModal(false);
              }}
            />
            <button 
              className="modal-close-button"
              onClick={() => {
                setShowFieldMapModal(false);
                setSelectedFileForMap(null);
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {showFieldMapForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Create Field Map</h2>
            <FieldMapForm
              onSave={handleFieldMapSave}
              onCancel={() => {
                setShowFieldMapForm(false);
                setSelectedFileForMap(null);
              }}
              accountId={selectedFileForMap ? files.find(f => f.fileId === selectedFileForMap)?.accountId : undefined}
              fileId={selectedFileForMap || undefined}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FileList; 