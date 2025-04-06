import React, { useState, useEffect } from 'react';
import { listFiles, deleteFile, getDownloadUrl, unassociateFileFromAccount, FileMetadata } from '../services/FileService';
import './FileList.css';

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

  // Load files on component mount and when refresh is needed
  useEffect(() => {
    loadFiles();
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
  const handleDownloadFile = async (fileId: string) => {
    setDownloadingFileId(fileId);
    setError(null);
    
    try {
      const downloadData = await getDownloadUrl(fileId);
      
      // Create a temporary link element and trigger download
      const link = document.createElement('a');
      link.href = downloadData.downloadUrl;
      link.setAttribute('download', downloadData.fileName);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error downloading file:', error);
      setError(error instanceof Error ? error.message : 'Failed to download file');
    } finally {
      setDownloadingFileId(null);
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
                    <th>Account</th>
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
                          <span className="no-account">—</span>
                        )}
                      </td>
                      <td className="file-actions">
                        <button 
                          className="download-button"
                          onClick={() => handleDownloadFile(file.fileId)}
                          disabled={downloadingFileId === file.fileId}
                        >
                          {downloadingFileId === file.fileId ? '...' : 'Download'}
                        </button>
                        <button 
                          className="delete-button"
                          onClick={() => handleDeleteFile(file.fileId)}
                          disabled={deletingFileId === file.fileId}
                        >
                          {deletingFileId === file.fileId ? '...' : 'Delete'}
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
    </div>
  );
};

export default FileList; 