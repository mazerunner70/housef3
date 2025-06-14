import React, { useState, useRef, useCallback } from 'react';
import './TransactionFileUpload.css';

// File validation constants
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB for OFX files (can be larger)
const ALLOWED_FILE_EXTENSIONS = ['.csv', '.qif', '.ofx', '.qfx'];
const ALLOWED_MIME_TYPES = [
  'text/csv',
  'application/csv',
  'text/plain',
  'application/x-ofx',
  'application/xml',
  'text/xml',
  'application/x-quicken'
];

interface FileValidationResult {
  isValid: boolean;
  error?: string;
  fileType?: 'csv' | 'qif' | 'ofx' | 'qfx';
}

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

  // Validate file extension
  const validateFileExtension = (filename: string): boolean => {
    const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
    return ALLOWED_FILE_EXTENSIONS.includes(extension);
  };

  // Validate MIME type
  const validateMimeType = (mimeType: string): boolean => {
    return ALLOWED_MIME_TYPES.includes(mimeType.toLowerCase());
  };

  // Detect file type based on extension
  const detectFileType = (filename: string): 'csv' | 'qif' | 'ofx' | 'qfx' | null => {
    const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
    switch (extension) {
      case '.csv':
        return 'csv';
      case '.qif':
        return 'qif';
      case '.ofx':
        return 'ofx';
      case '.qfx':
        return 'qfx';
      default:
        return null;
    }
  };

  // Basic OFX content validation
  const validateOFXContent = async (file: File): Promise<boolean> => {
    if (!file.name.toLowerCase().endsWith('.ofx')) {
      return true; // Skip OFX validation for non-OFX files
    }

    try {
      // Read first 1KB of file to check for OFX headers
      const chunk = file.slice(0, 1024);
      const text = await chunk.text();
      
      // Check for OFX header indicators
      const hasOFXHeader = text.includes('<OFX>') || 
                          text.includes('OFXHEADER:') || 
                          text.includes('VERSION:') ||
                          text.includes('<STMTRS>') ||
                          text.includes('<CCSTMTRS>');
      
      return hasOFXHeader;
    } catch (error) {
      console.warn('Could not validate OFX content:', error);
      return true; // Allow file if we can't validate content
    }
  };

  // Basic CSV content validation
  const validateCSVContent = async (file: File): Promise<boolean> => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return true; // Skip CSV validation for non-CSV files
    }

    try {
      // Read first 2KB of file to check for CSV structure
      const chunk = file.slice(0, 2048);
      const text = await chunk.text();
      
      // Split into lines and check structure
      const lines = text.split('\n').filter(line => line.trim().length > 0);
      
      if (lines.length < 2) {
        return false; // Need at least header + 1 data row
      }
      
      // Check for common delimiters
      const firstLine = lines[0];
      const hasCommonDelimiters = firstLine.includes(',') || 
                                 firstLine.includes(';') || 
                                 firstLine.includes('\t');
      
      if (!hasCommonDelimiters) {
        return false; // No recognizable CSV delimiters
      }
      
      // Check if all lines have similar structure (similar number of delimiters)
      const delimiter = firstLine.includes(',') ? ',' : 
                       firstLine.includes(';') ? ';' : '\t';
      
      const headerColumnCount = firstLine.split(delimiter).length;
      
      // Check first few data rows for consistency
      const dataLinesToCheck = Math.min(3, lines.length - 1);
      for (let i = 1; i <= dataLinesToCheck; i++) {
        const columnCount = lines[i].split(delimiter).length;
        // Allow some flexibility (±1 column) for quoted fields or empty trailing columns
        if (Math.abs(columnCount - headerColumnCount) > 1) {
          console.warn(`CSV validation: Inconsistent column count. Header: ${headerColumnCount}, Row ${i}: ${columnCount}`);
        }
      }
      
      return true;
    } catch (error) {
      console.warn('Could not validate CSV content:', error);
      return true; // Allow file if we can't validate content
    }
  };

  // Basic QIF content validation
  const validateQIFContent = async (file: File): Promise<boolean> => {
    if (!file.name.toLowerCase().endsWith('.qif')) {
      return true; // Skip QIF validation for non-QIF files
    }

    try {
      // Read first 1KB of file to check for QIF structure
      const chunk = file.slice(0, 1024);
      const text = await chunk.text();
      
      // Check for QIF indicators (starts with !Type: or !Account)
      const hasQIFHeader = text.includes('!Type:') || 
                          text.includes('!Account') ||
                          text.includes('!Option:') ||
                          // Check for common QIF transaction markers
                          (text.includes('D') && text.includes('T') && text.includes('^'));
      
      return hasQIFHeader;
    } catch (error) {
      console.warn('Could not validate QIF content:', error);
      return true; // Allow file if we can't validate content
    }
  };

  // Comprehensive file validation
  const validateFile = async (file: File): Promise<FileValidationResult> => {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return {
        isValid: false,
        error: `File is too large. Maximum size is ${Math.round(MAX_FILE_SIZE / 1024 / 1024)}MB`
      };
    }

    // Check file size (minimum check)
    if (file.size < 10) {
      return {
        isValid: false,
        error: 'File appears to be empty or corrupted'
      };
    }

    // Check file extension
    if (!validateFileExtension(file.name)) {
      return {
        isValid: false,
        error: `Unsupported file type. Supported formats: ${ALLOWED_FILE_EXTENSIONS.join(', ')}`
      };
    }

    // Check MIME type (if available)
    if (file.type && !validateMimeType(file.type)) {
      console.warn(`Unexpected MIME type: ${file.type}, but allowing based on file extension`);
    }

    // Detect file type
    const fileType = detectFileType(file.name);
    if (!fileType) {
      return {
        isValid: false,
        error: 'Could not determine file type from extension'
      };
    }

    // Validate content based on file type
    let isValidContent = true;
    let contentError = '';

    switch (fileType) {
      case 'ofx':
        isValidContent = await validateOFXContent(file);
        contentError = 'File does not appear to be a valid OFX file. Please check the file format.';
        break;
      case 'csv':
        isValidContent = await validateCSVContent(file);
        contentError = 'File does not appear to be a valid CSV file. Please check that it has proper headers and delimiter structure.';
        break;
      case 'qif':
        isValidContent = await validateQIFContent(file);
        contentError = 'File does not appear to be a valid QIF file. Please check the file format.';
        break;
      case 'qfx':
        // QFX files are similar to OFX, use OFX validation
        isValidContent = await validateOFXContent(file);
        contentError = 'File does not appear to be a valid QFX file. Please check the file format.';
        break;
      default:
        isValidContent = true; // Unknown types pass through
    }

    if (!isValidContent) {
      return {
        isValid: false,
        error: contentError
      };
    }

    return {
      isValid: true,
      fileType
    };
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
  const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
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
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
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

  // Format file size for display
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="transaction-file-upload">
      <label className="upload-label">
        Upload Transaction File
        <span className="supported-formats">
          Supported formats: CSV, QIF, OFX, QFX
        </span>
      </label>

      {/* File Upload Area */}
      <div 
        className={`upload-area ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''} ${disabled ? 'disabled' : ''} ${validationResult.error ? 'has-error' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={handleUploadAreaClick}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileInputChange}
          accept={ALLOWED_FILE_EXTENSIONS.join(',')}
          className="file-input"
          disabled={disabled}
        />

        <div className="upload-content">
          {selectedFile ? (
            <div className="file-selected">
              <div className="file-icon">
                {validationResult.fileType === 'ofx' ? '📄' :
                 validationResult.fileType === 'csv' ? '📊' :
                 validationResult.fileType === 'qif' ? '💰' : '📋'}
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
                  Supports OFX, QFX, CSV, and QIF files up to {Math.round(MAX_FILE_SIZE / 1024 / 1024)}MB
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

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
              <label>File Name:</label>
              <span>{selectedFile.name}</span>
            </div>
            <div className="preview-item">
              <label>File Size:</label>
              <span>{formatFileSize(selectedFile.size)}</span>
            </div>
            <div className="preview-item">
              <label>File Type:</label>
              <span>{validationResult.fileType?.toUpperCase()}</span>
            </div>
            <div className="preview-item">
              <label>Last Modified:</label>
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