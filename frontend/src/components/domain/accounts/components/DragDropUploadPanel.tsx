import React, { useState, useRef, useCallback } from 'react';
import './DragDropUploadPanel.css';

// File validation constants (adapted from TransactionFileUpload)
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
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

interface DragDropUploadPanelProps {
    accountId: string;
    onFileSelect: (file: File) => void;
    isUploading?: boolean;
    uploadProgress?: number;
    error?: string | null;
    onClearError?: () => void;
    disabled?: boolean;
    acceptedTypes?: string[];
    maxFileSize?: number;
}

/**
 * DragDropUploadPanel - Enhanced drag-and-drop file upload component
 * 
 * Adapted from TransactionFileUpload with enhancements:
 * - Larger, more prominent design for central placement
 * - Account-specific upload context
 * - Enhanced progress indication
 * - Improved error handling and recovery
 * - Better accessibility and keyboard support
 * 
 * Features:
 * - Drag and drop file handling with visual feedback
 * - File validation (type, size, content structure)
 * - Upload progress tracking
 * - Error state management with retry options
 * - Responsive design for all screen sizes
 */
const DragDropUploadPanel: React.FC<DragDropUploadPanelProps> = ({
    accountId,
    onFileSelect,
    isUploading = false,
    uploadProgress = 0,
    error = null,
    onClearError,
    disabled = false,
    acceptedTypes = ALLOWED_FILE_EXTENSIONS,
    maxFileSize = MAX_FILE_SIZE
}) => {
    const [dragActive, setDragActive] = useState(false);
    const [validationResult, setValidationResult] = useState<FileValidationResult>({ isValid: false });
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Validation functions (adapted from TransactionFileUpload)
    const validateFileExtension = (filename: string): boolean => {
        const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        return acceptedTypes.includes(extension);
    };

    const validateMimeType = (mimeType: string): boolean => {
        return ALLOWED_MIME_TYPES.includes(mimeType.toLowerCase());
    };

    const detectFileType = (filename: string): 'csv' | 'qif' | 'ofx' | 'qfx' | null => {
        const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        switch (extension) {
            case '.csv': return 'csv';
            case '.qif': return 'qif';
            case '.ofx': return 'ofx';
            case '.qfx': return 'qfx';
            default: return null;
        }
    };

    // Basic content validation (simplified from original)
    const validateFileContent = async (file: File): Promise<boolean> => {
        try {
            const chunk = file.slice(0, 1024);
            const text = await chunk.text();

            if (file.name.toLowerCase().endsWith('.csv')) {
                const lines = text.split('\n').filter(line => line.trim().length > 0);
                return lines.length >= 2 && (text.includes(',') || text.includes(';') || text.includes('\t'));
            }

            if (file.name.toLowerCase().endsWith('.ofx') || file.name.toLowerCase().endsWith('.qfx')) {
                return text.includes('<OFX>') || text.includes('OFXHEADER:') || text.includes('<STMTRS>');
            }

            if (file.name.toLowerCase().endsWith('.qif')) {
                return text.includes('!Type:') || text.includes('!Account') || text.includes('^');
            }

            return true;
        } catch (error) {
            console.warn('Content validation failed:', error);
            return true; // Allow file if validation fails
        }
    };

    // Comprehensive file validation
    const validateFile = async (file: File): Promise<FileValidationResult> => {
        // Check file size
        if (file.size > maxFileSize) {
            return {
                isValid: false,
                error: `File is too large. Maximum size is ${Math.round(maxFileSize / 1024 / 1024)}MB`
            };
        }

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
                error: `Unsupported file type. Supported formats: ${acceptedTypes.join(', ')}`
            };
        }

        // Detect file type
        const fileType = detectFileType(file.name);
        if (!fileType) {
            return {
                isValid: false,
                error: 'Could not determine file type from extension'
            };
        }

        // Validate content
        const isValidContent = await validateFileContent(file);
        if (!isValidContent) {
            return {
                isValid: false,
                error: 'File does not appear to be a valid transaction file. Please check the file format.'
            };
        }

        return {
            isValid: true,
            fileType
        };
    };

    // Handle file selection and validation
    const handleFileSelection = useCallback(async (file: File) => {
        if (onClearError) {
            onClearError();
        }

        const result = await validateFile(file);
        setValidationResult(result);

        if (result.isValid) {
            onFileSelect(file);
        }
    }, [onFileSelect, onClearError]);

    // Handle drag events
    const handleDrag = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();

        if (disabled || isUploading) return;

        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, [disabled, isUploading]);

    // Handle drop event
    const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (disabled || isUploading) return;

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            handleFileSelection(file);
        }
    }, [disabled, isUploading, handleFileSelection]);

    // Handle file input change
    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (disabled || isUploading) return;

        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            handleFileSelection(file);
        }
    };

    // Handle click to open file dialog
    const handleUploadAreaClick = () => {
        if (!disabled && !isUploading) {
            fileInputRef.current?.click();
        }
    };

    // Handle keyboard interaction
    const handleUploadAreaKeyDown = (e: React.KeyboardEvent) => {
        if (!disabled && !isUploading && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            fileInputRef.current?.click();
        }
    };

    // Get panel state classes
    const getPanelClasses = () => {
        const classes = ['drag-drop-upload-panel'];

        if (dragActive) classes.push('drag-active');
        if (isUploading) classes.push('uploading');
        if (disabled) classes.push('disabled');
        if (error || validationResult.error) classes.push('has-error');

        return classes.join(' ');
    };

    return (
        <div className="drag-drop-upload-container">
            <h3 className="upload-panel-title">Upload Transaction Files</h3>

            <div
                className={getPanelClasses()}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={handleUploadAreaClick}
                onKeyDown={handleUploadAreaKeyDown}
                tabIndex={disabled || isUploading ? -1 : 0}
                role="button"
                aria-label="Click or press Enter/Space to select a file, or drag and drop a file here"
                aria-disabled={disabled || isUploading}
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileInputChange}
                    accept={acceptedTypes.join(',')}
                    className="file-input"
                    disabled={disabled || isUploading}
                />

                <div className="upload-panel-content">
                    {isUploading ? (
                        <div className="upload-progress">
                            <div className="upload-icon uploading">📤</div>
                            <div className="upload-text">
                                <div className="primary-text">Uploading...</div>
                                <div className="progress-bar">
                                    <div
                                        className="progress-fill"
                                        style={{ width: `${uploadProgress}%` }}
                                    ></div>
                                </div>
                                <div className="secondary-text">{uploadProgress}% complete</div>
                            </div>
                        </div>
                    ) : (
                        <div className="upload-prompt">
                            <div className="upload-icon">📁</div>
                            <div className="upload-text">
                                <div className="primary-text">
                                    Drag & Drop Files Here
                                </div>
                                <div className="secondary-text">
                                    or click to browse files
                                </div>
                                <div className="supported-formats">
                                    Supported formats: CSV, Excel, QIF, OFX • Max {Math.round(maxFileSize / 1024 / 1024)}MB
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Error Display */}
            {(error || validationResult.error) && (
                <div className="upload-error">
                    <span className="error-icon">⚠️</span>
                    <span className="error-message">{error || validationResult.error}</span>
                    {onClearError && (
                        <button
                            onClick={onClearError}
                            className="error-dismiss"
                            aria-label="Dismiss error"
                        >
                            ✕
                        </button>
                    )}
                </div>
            )}

            {/* Help Text */}
            <div className="upload-help">
                <details>
                    <summary>Supported File Formats</summary>
                    <div className="format-details">
                        <div className="format-item">
                            <strong>CSV (.csv)</strong> - Comma-separated values format requiring field mapping
                        </div>
                        <div className="format-item">
                            <strong>OFX (.ofx)</strong> - Open Financial Exchange format from banks
                        </div>
                        <div className="format-item">
                            <strong>QFX (.qfx)</strong> - Quicken Financial Exchange format
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

export default DragDropUploadPanel;
