import React, { useRef, useState } from 'react';
import { getFZIPRestoreUploadUrl } from '../../services/FZIPService';
import Button from './Button';
import './FZIPRestoreUpload.css';

interface FZIPRestoreUploadProps {
  onUploaded?: () => void | Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
  profileError?: string | null;
  profileSummary?: {
    accounts_count: number;
    transactions_count: number;
    categories_count: number;
    file_maps_count: number;
    transaction_files_count: number;
  } | null;
  onClearErrors?: () => void;
}

const FZIPRestoreUpload: React.FC<FZIPRestoreUploadProps> = ({
  onUploaded,
  isLoading = false,
  disabled = false,
  profileError,
  profileSummary,
  onClearErrors
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleFileSelect = (file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.fzip')) {
      alert('Please select a valid FZIP file (.fzip extension)');
      return;
    }

    // Validate file size (max 500MB)
    const maxSize = 500 * 1024 * 1024; // 500MB
    if (file.size > maxSize) {
      alert('File size must be less than 500MB');
      return;
    }

    setSelectedFile(file);
    onClearErrors?.();
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);

    const file = event.dataTransfer.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
  };

  const handleUpload = async () => {
    if (!selectedFile || isUploading || disabled) return;

    setIsUploading(true);
    setUploadProgress(0);

    try {
      // Get presigned POST for direct S3 upload
      const { url, fields } = await getFZIPRestoreUploadUrl();

      // Prepare form data
      const formData = new FormData();
      Object.entries(fields).forEach(([key, value]) => formData.append(key, value));
      formData.append('file', selectedFile);

      // Start upload with abort capability
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      // We cannot track true byte progress with fetch; show stepped progress
      setUploadProgress(50);

      const uploadResponse = await fetch(url, {
        method: 'POST',
        body: formData,
        signal: abortController.signal
      });

      if (!uploadResponse.ok) {
        throw new Error(`Upload failed: ${uploadResponse.status} ${uploadResponse.statusText}`);
      }

      console.log('Upload successful, status:', uploadResponse.status);
      setUploadProgress(100);

      // Reset form
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Notify parent to refresh list; validation will start automatically server-side
      console.log('Calling onUploaded callback...');
      if (onUploaded) {
        await onUploaded();
        console.log('onUploaded callback completed');
      } else {
        console.warn('No onUploaded callback provided');
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadProgress(0);
    } finally {
      abortControllerRef.current = null;
      setIsUploading(false);
    }
  };

  const handleCancelUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const isFormDisabled = isLoading || disabled || isUploading;

  return (
    <div className="fzip-restore-upload">
      <div className="fzip-restore-upload__header">
        <h3>Restore Financial Profile</h3>
        <p>Upload a FZIP backup file to restore your complete financial profile. Your current profile must be completely empty.</p>
      </div>

      {profileError && profileSummary && (
        <div className="profile-error">
          <div className="profile-error__message">
            <h4>Profile Not Empty</h4>
            <p>Restore requires a completely empty financial profile. Your current profile contains:</p>
          </div>
          
          <div className="profile-summary">
            <div className="profile-summary__grid">
              <div className="summary-item">
                <span className="summary-label">Accounts:</span>
                <span className="summary-value">{profileSummary.accounts_count}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Transactions:</span>
                <span className="summary-value">{profileSummary.transactions_count}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Categories:</span>
                <span className="summary-value">{profileSummary.categories_count}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">File Maps:</span>
                <span className="summary-value">{profileSummary.file_maps_count}</span>
              </div>
              <div className="summary-item">
                <span className="summary-label">Files:</span>
                <span className="summary-value">{profileSummary.transaction_files_count}</span>
              </div>
            </div>
          </div>

          <div className="profile-error__suggestion">
            <p><strong>Suggestion:</strong> Please use a new user account or clear all existing data before attempting to restore.</p>
            <Button
              variant="secondary"
              size="compact"
              onClick={onClearErrors}
            >
              Try Again
            </Button>
          </div>
        </div>
      )}

      {!profileError && (
        <div className="upload-section">
          <div
            className={`file-drop-zone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".fzip"
              onChange={handleFileInputChange}
              disabled={isFormDisabled}
              className="file-input"
            />

            {selectedFile ? (
              <div className="selected-file">
                <div className="file-icon">📦</div>
                <div className="file-info">
                  <div className="file-name">{selectedFile.name}</div>
                  <div className="file-size">{formatFileSize(selectedFile.size)}</div>
                </div>
                <Button
                  variant="secondary"
                  size="compact"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                    }
                  }}
                  disabled={isFormDisabled}
                >
                  Change
                </Button>
              </div>
            ) : (
              <div className="drop-zone-content">
                <div className="drop-zone-icon">📁</div>
                <div className="drop-zone-text">
                  <p><strong>Click to select</strong> or drag and drop</p>
                  <p>FZIP backup files only (.fzip)</p>
                </div>
                <div className="drop-zone-limits">
                  <p>Maximum file size: 500MB</p>
                </div>
              </div>
            )}
          </div>

          {isUploading && (
            <div className="upload-progress">
              <div className="progress-info">
                <span>Uploading to S3...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <div className="progress-actions">
                <Button
                  variant="secondary"
                  size="compact"
                  onClick={handleCancelUpload}
                  disabled={!isUploading}
                >
                  Cancel Upload
                </Button>
              </div>
            </div>
          )}

          <div className="upload-actions">
            <Button
              variant="primary"
              onClick={handleUpload}
              disabled={!selectedFile || isFormDisabled}
            >
              {isUploading ? 'Uploading...' : 'Start Restore'}
            </Button>
          </div>
        </div>
      )}

      <div className="restore-info">
        <h4>Important Information:</h4>
        <ul>
          <li><strong>Empty Profile Required:</strong> Your financial profile must be completely empty before restore</li>
          <li><strong>Complete Restore:</strong> All data from the backup will be restored exactly as it was</li>
          <li><strong>File Format:</strong> Only FZIP backup files (.fzip) are supported</li>
          <li><strong>Data Integrity:</strong> The restore process includes validation to ensure data consistency</li>
          <li><strong>Processing Time:</strong> Large backups may take several minutes to restore</li>
        </ul>

        <div className="restore-requirements">
          <h4>What gets restored:</h4>
          <ul>
            <li>All accounts with balances and settings</li>
            <li>All transaction records and category assignments</li>
            <li>Complete category hierarchy and rules</li>
            <li>File mapping configurations</li>
            <li>Original transaction files and metadata</li>
            <li>All data relationships and referential integrity</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default FZIPRestoreUpload;