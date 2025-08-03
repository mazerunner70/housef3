import React, { useState, useRef } from 'react';
import { CreateFZIPRestoreResponse } from '../../services/FZIPService';
import Button from './Button';
import './FZIPRestoreUpload.css';

interface FZIPRestoreUploadProps {
  onCreateRestore: () => Promise<CreateFZIPRestoreResponse>;
  onUploadFile: (restoreId: string, file: File, uploadUrl: CreateFZIPRestoreResponse['uploadUrl']) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
  profileError?: string | null;
  profileSummary?: CreateFZIPRestoreResponse['profileSummary'] | null;
  onClearErrors?: () => void;
}

const FZIPRestoreUpload: React.FC<FZIPRestoreUploadProps> = ({
  onCreateRestore,
  onUploadFile,
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
      // Create restore job
      const restoreResponse = await onCreateRestore();
      setUploadProgress(25);

      // Upload file
      await onUploadFile(restoreResponse.restoreId, selectedFile, restoreResponse.uploadUrl);
      setUploadProgress(100);

      // Reset form
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
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
              size="small"
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
                  size="small"
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
                <span>Uploading and processing...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="upload-actions">
            <Button
              variant="primary"
              onClick={handleUpload}
              disabled={!selectedFile || isFormDisabled}
              loading={isUploading}
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