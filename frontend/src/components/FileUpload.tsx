import React, { useState, useRef, useCallback, useEffect } from 'react';
import { getUploadUrl, uploadFileToS3 } from '../services/FileService';
import { Account, listAccounts } from '../services/AccountService';
import './FileUpload.css';

// Maximum file size (5MB)
const MAX_FILE_SIZE = 5 * 1024 * 1024;

// Allowed file extensions matching FileFormat enum in backend
const ALLOWED_FILE_EXTENSIONS = ['csv', 'ofx', 'qfx', 'pdf', 'json', 'xml'];

// Get allowed file types string for file input accept attribute
const ALLOWED_FILE_TYPES = ALLOWED_FILE_EXTENSIONS.map(ext => `.${ext}`).join(',');

interface FileUploadProps {
  onUploadComplete: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadComplete }) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const [loadingAccounts, setLoadingAccounts] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch accounts when component mounts
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        setLoadingAccounts(true);
        const accountsData = await listAccounts();
        setAccounts(accountsData.accounts);
      } catch (err) {
        console.error('Error fetching accounts:', err);
      } finally {
        setLoadingAccounts(false);
      }
    };

    fetchAccounts();
  }, []);

  // Handle file selection validation
  const validateAndSetFile = (file: File) => {
    setError(null);
    
    // Check file type
    if (!ALLOWED_FILE_EXTENSIONS.includes(file.name.split('.').pop() || '')) {
      setError(`Unsupported file type. Allowed types: ${ALLOWED_FILE_EXTENSIONS.join(', ')}`);
      return false;
    }
    
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      setError(`File is too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB`);
      return false;
    }
    
    // Set selected file
    setSelectedFile(file);
    return true;
  };

  // Handle drag events
  const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  // Handle drop event
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  }, []);

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      validateAndSetFile(file);
    }
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }
    
    try {
      setError(null);
      setUploadProgress(0);
      setUploading(true);
      setSuccess(false);
      
      // Step 1: Get presigned URL (now with optional accountId)
      const uploadUrlData = await getUploadUrl(
        selectedFile.name,
        selectedFile.type,
        selectedFile.size,
        selectedAccountId ?? undefined // Convert null to undefined
      );
      
      // Step 2: Upload file to S3
      await uploadFileToS3(uploadUrlData.uploadUrl, selectedFile);
      
      // Upload complete
      setUploadProgress(100);
      setSuccess(true);
      setSelectedFile(null);
      setSelectedAccountId(null); // Reset selected account
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Notify parent component
      onUploadComplete();
      
      // Reset success message after 3 seconds
      setTimeout(() => {
        setSuccess(false);
      }, 3000);
    } catch (error) {
      console.error('Upload error:', error);
      setError(error instanceof Error ? error.message : 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  // Handle cancel upload
  const handleCancel = () => {
    setSelectedFile(null);
    setError(null);
    setUploadProgress(0);
    setSelectedAccountId(null); // Reset selected account
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle account selection change
  const handleAccountChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const accountId = e.target.value;
    setSelectedAccountId(accountId === "none" ? null : accountId);
  };

  return (
    <div className="file-upload-container">
      <h2>Upload File</h2>
      
      {/* Drag and drop area */}
      <div 
        className={`file-upload-area ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          accept={ALLOWED_FILE_TYPES}
          className="file-input"
        />
        
        {selectedFile ? (
          <div className="selected-file-info">
            <div className="file-name">{selectedFile.name}</div>
            <div className="file-size">{(selectedFile.size / 1024).toFixed(2)} KB</div>
            <div className="file-type">{selectedFile.type}</div>
          </div>
        ) : (
          <div className="upload-prompt">
            <div className="upload-icon">📁</div>
            <p>Drag and drop a file here, or click to select</p>
            <p className="file-types-hint">
              Supported file types: CSV, Excel (XLSX), PDF, OFX/QFX (financial), and text formats (TXT, JSON, XML, MD)
            </p>
            <p className="file-size-hint">
              Maximum file size: {MAX_FILE_SIZE / 1024 / 1024}MB
            </p>
          </div>
        )}
      </div>
      
      {/* Account selection */}
      {selectedFile && (
        <div className="account-selection">
          <label htmlFor="account-select">Associate with Account (Optional):</label>
          <select 
            id="account-select" 
            value={selectedAccountId || "none"} 
            onChange={handleAccountChange}
            disabled={uploading || loadingAccounts}
          >
            <option value="none">None (No account association)</option>
            {loadingAccounts ? (
              <option disabled>Loading accounts...</option>
            ) : (
              accounts.map(account => (
                <option key={account.accountId} value={account.accountId}>
                  {account.accountName} ({account.accountType})
                </option>
              ))
            )}
          </select>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="upload-error">
          <span className="error-icon">⚠️</span> {error}
        </div>
      )}
      
      {/* Success message */}
      {success && (
        <div className="upload-success">
          <span className="success-icon">✅</span> File uploaded successfully!
        </div>
      )}
      
      {/* Upload progress */}
      {uploading && (
        <div className="upload-progress-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <div className="progress-text">{uploadProgress}%</div>
        </div>
      )}
      
      {/* Action buttons */}
      <div className="upload-actions">
        {selectedFile && !uploading && (
          <>
            <button 
              className="upload-button" 
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
            >
              Upload
            </button>
            <button 
              className="cancel-button" 
              onClick={handleCancel}
              disabled={uploading}
            >
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default FileUpload; 