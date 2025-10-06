import React, { useState, useRef, useCallback } from 'react';
import './TransactionFileUpload.css';
import {
  validateTransactionFile,
  FileValidationResult,
  formatFileSize,
  DEFAULT_VALIDATION_CONFIG
} from '@/utils/fileValidation';

interface TransactionFileUploadProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onValidationChange: (result: FileValidationResult) => void;
  disabled?: boolean;
  showPreview?: boolean;
}

const TransactionFileUpload: React.FC<TransactionFileUploadProps> = ({
  selectedFile,
  onFileSelect,
  onValidationChange,
  disabled = false,
  showPreview = true
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [validationResult, setValidationResult] = useState<FileValidationResult>({ isValid: false });
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Helper function to get file type icon
  const getFileTypeIcon = (fileType?: string): string => {
    switch (fileType) {
      case 'ofx': return '📄';
      case 'csv': return '📊';
      case 'qif': return '💰';
      default: return '📋';
    }
  };





  // File validation using the utility
  const validateFile = async (file: File): Promise<FileValidationResult> => {
    return await validateTransactionFile(file);
  };

  // Handle file selection and validation
  const handleFileSelection = useCallback(async (file: File) => {
    const result = await validateFile(file);
    setValidationResult(result);
    onValidationChange(result);

    // Always show the selected file in UI, regardless of validation status
    // The validation error will be displayed separately
    onFileSelect(file);
  }, [onFileSelect, onValidationChange]);

  // Handle drag events
  const handleDrag = useCallback((e: React.DragEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();

    if (disabled) return;

    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, [disabled]);

  // Handle drop event
  const handleDrop = useCallback((e: React.DragEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileSelection(file);
    }
  }, [disabled, handleFileSelection]);

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled) return;

    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      handleFileSelection(file);
    }
  };

  // Clear selected file
  const handleClearFile = () => {
    setValidationResult({ isValid: false });
    onValidationChange({ isValid: false });
    onFileSelect(null);

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Handle click to open file dialog
  const handleUploadAreaClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  // Handle keyboard interaction for accessibility
  const handleUploadAreaKeyDown = (e: React.KeyboardEvent) => {
    if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  return (
    <div className="transaction-file-upload">
      <div className="upload-label">
        <span>Upload Transaction File</span>
        <span className="supported-formats">
          Supported formats: CSV, QIF, OFX, QFX
        </span>
      </div>

      {/* File Upload Area */}
      <button
        type="button"
        className={`upload-area ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''} ${disabled ? 'disabled' : ''} ${validationResult.error ? 'has-error' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={handleUploadAreaClick}
        onKeyDown={handleUploadAreaKeyDown}
        disabled={disabled}
        aria-label="Click or press Enter/Space to select a file, or drag and drop a file here"
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          accept={DEFAULT_VALIDATION_CONFIG.allowedExtensions.join(',')}
          className="file-input"
          disabled={disabled}
        />

        <div className="upload-content">
          {selectedFile ? (
            <div className="file-selected">
              <div className="file-icon">
                {getFileTypeIcon(validationResult.fileType)}
              </div>
              <div className="file-info">
                <div className="file-name">{selectedFile.name}</div>
                <div className="file-details">
                  {formatFileSize(selectedFile.size)} • {validationResult.fileType?.toUpperCase()}
                </div>
              </div>
              <button
                type="button"
                className="clear-file-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearFile();
                }}
                disabled={disabled}
              >
                ✕
              </button>
            </div>
          ) : (
            <div className="upload-prompt">
              <div className="upload-icon">📁</div>
              <div className="upload-text">
                <div className="primary-text">
                  Drag & drop your file here, or click to select
                </div>
                <div className="secondary-text">
                  Supports OFX, QFX, CSV, and QIF files up to {Math.round(DEFAULT_VALIDATION_CONFIG.maxSizeBytes / 1024 / 1024)}MB
                </div>
              </div>
            </div>
          )}
        </div>
      </button>

      {/* Validation Error Display */}
      {validationResult.error && (
        <div className="validation-error">
          <span className="error-icon">⚠️</span>
          {validationResult.error}
        </div>
      )}

      {/* File Preview */}
      {showPreview && selectedFile && validationResult.isValid && (
        <div className="file-preview">
          <h4>File Preview</h4>
          <div className="preview-grid">
            <div className="preview-item">
              <span className="preview-label">File Name:</span>
              <span>{selectedFile.name}</span>
            </div>
            <div className="preview-item">
              <span className="preview-label">File Size:</span>
              <span>{formatFileSize(selectedFile.size)}</span>
            </div>
            <div className="preview-item">
              <span className="preview-label">File Type:</span>
              <span>{validationResult.fileType?.toUpperCase()}</span>
            </div>
            <div className="preview-item">
              <span className="preview-label">Last Modified:</span>
              <span>{new Date(selectedFile.lastModified).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Format Specific Information */}
          {validationResult.fileType === 'ofx' && (
            <div className="format-info ofx-info">
              <h5>OFX File Information</h5>
              <p>
                OFX (Open Financial Exchange) files contain structured financial data
                exported directly from your bank or financial institution. This format
                provides rich transaction details including:
              </p>
              <ul>
                <li>Transaction dates and amounts</li>
                <li>Merchant/payee information</li>
                <li>Account balance information</li>
                <li>Financial institution transaction IDs</li>
              </ul>
            </div>
          )}

          {validationResult.fileType === 'csv' && (
            <div className="format-info csv-info">
              <h5>CSV File Information</h5>
              <p>
                CSV (Comma-Separated Values) files are spreadsheet-format files that require
                field mapping to match your bank's column structure. Common CSV columns include:
              </p>
              <ul>
                <li>Date (various formats supported)</li>
                <li>Description or memo</li>
                <li>Amount (positive/negative or separate debit/credit columns)</li>
                <li>Account or category information</li>
              </ul>
              <p><strong>Note:</strong> You'll configure field mapping in the next step.</p>
            </div>
          )}

          {validationResult.fileType === 'qif' && (
            <div className="format-info qif-info">
              <h5>QIF File Information</h5>
              <p>
                QIF (Quicken Interchange Format) files are text-based files with a specific
                structure used by Quicken and other financial software:
              </p>
              <ul>
                <li>Self-describing format with field codes</li>
                <li>Supports multiple account types</li>
                <li>Includes transaction categories and splits</li>
                <li>No field mapping required</li>
              </ul>
            </div>
          )}

          {validationResult.fileType === 'qfx' && (
            <div className="format-info qfx-info">
              <h5>QFX File Information</h5>
              <p>
                QFX (Quicken Financial Exchange) files are similar to OFX but optimized
                for Quicken software. They contain:
              </p>
              <ul>
                <li>Bank and credit card transactions</li>
                <li>Account balance information</li>
                <li>Investment data (if applicable)</li>
                <li>Quicken-specific formatting</li>
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Format Help */}
      <div className="format-help">
        <details>
          <summary>Supported File Formats</summary>
          <div className="format-details">
            <div className="format-item">
              <strong>OFX (.ofx)</strong> - Open Financial Exchange format used by most banks
            </div>
            <div className="format-item">
              <strong>QFX (.qfx)</strong> - Quicken Financial Exchange format
            </div>
            <div className="format-item">
              <strong>CSV (.csv)</strong> - Comma-separated values format
            </div>
            <div className="format-item">
              <strong>QIF (.qif)</strong> - Quicken Interchange Format
            </div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default TransactionFileUpload; 