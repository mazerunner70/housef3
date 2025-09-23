
import React, { useMemo, useState } from 'react';
import { UploadedFile } from '@/new-ui/hooks/useUploadedFiles';
import { WorkflowProgressModal } from '@/new-ui/components/ui';
import './UploadedFilesList.css';

interface UploadedFilesListProps {
    files: UploadedFile[];
    isLoading?: boolean;
    error?: string | null;
    onViewFile: (fileId: string) => void;
    onDownloadFile: (fileId: string) => void;
    onDeleteFile: (fileId: string) => Promise<string | null>;
    onRetryProcessing?: (fileId: string) => void;
}

/**
 * UploadedFilesList - Enhanced file list component adapted from ImportHistoryTable
 * 
 * Features:
 * - Account-specific file display
 * - File metadata with transaction counts and date ranges
 * - Processing status indicators
 * - File operations (view, download, delete)
 * - Error handling and retry options
 * - Responsive card-based design
 * - Empty state handling
 * 
 * Design:
 * - Card-based layout for better mobile experience
 * - Status indicators with color coding
 * - Action buttons with clear labels
 * - File type icons and metadata display
 */
const UploadedFilesList: React.FC<UploadedFilesListProps> = ({
    files,
    isLoading = false,
    error = null,
    onViewFile,
    onDownloadFile,
    onDeleteFile,
    onRetryProcessing
}) => {
    // State for workflow tracking modal
    const [workflowId, setWorkflowId] = useState<string | null>(null);
    const [showWorkflowModal, setShowWorkflowModal] = useState(false);
    const [deletingFileName, setDeletingFileName] = useState<string>('');

    // Handle file deletion with workflow tracking
    const handleDeleteFile = async (fileId: string, fileName: string) => {
        const workflowIdResult = await onDeleteFile(fileId);
        if (workflowIdResult) {
            setWorkflowId(workflowIdResult);
            setDeletingFileName(fileName);
            setShowWorkflowModal(true);
        }
    };
    // Get file type icon
    const getFileTypeIcon = (fileName: string): string => {
        const extension = fileName.toLowerCase().split('.').pop();
        switch (extension) {
            case 'csv':
                return '📊';
            case 'ofx':
            case 'qfx':
                return '📄';
            case 'qif':
                return '💰';
            case 'xlsx':
            case 'xls':
                return '📈';
            default:
                return '📋';
        }
    };

    // Format file size
    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    // Format date
    const formatDate = (dateString: string): string => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Format date range
    const formatDateRange = (file: UploadedFile): string => {
        if (!file.dateRange) return 'No date range';

        const startDate = new Date(file.dateRange.startDate);
        const endDate = new Date(file.dateRange.endDate);

        const formatOptions: Intl.DateTimeFormatOptions = {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        };

        if (startDate.getTime() === endDate.getTime()) {
            return startDate.toLocaleDateString('en-US', formatOptions);
        }

        return `${startDate.toLocaleDateString('en-US', formatOptions)} - ${endDate.toLocaleDateString('en-US', formatOptions)}`;
    };

    // Get status badge class and text
    const getStatusInfo = (status?: string) => {
        switch (status) {
            case 'COMPLETED':
            case 'PROCESSED':
                return { class: 'status-success', text: 'Processed', icon: '✅' };
            case 'PROCESSING':
                return { class: 'status-processing', text: 'Processing', icon: '⏳' };
            case 'PENDING':
                return { class: 'status-pending', text: 'Pending', icon: '⏸️' };
            case 'ERROR':
                return { class: 'status-error', text: 'Error', icon: '❌' };
            default:
                return { class: 'status-unknown', text: 'Unknown', icon: '❓' };
        }
    };

    // Sort files by upload date (newest first)
    const sortedFiles = useMemo(() => {
        return [...files].sort((a, b) => {
            const aDate = new Date(a.uploadDate).getTime();
            const bDate = new Date(b.uploadDate).getTime();
            return bDate - aDate;
        });
    }, [files]);

    // Loading state
    if (isLoading) {
        return (
            <div className="uploaded-files-list">
                <h3 className="files-list-title">Uploaded Files</h3>
                <div className="files-loading">
                    <div className="loading-spinner"></div>
                    <p>Loading files...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="uploaded-files-list">
                <h3 className="files-list-title">Uploaded Files</h3>
                <div className="files-error">
                    <span className="error-icon">⚠️</span>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    // Empty state
    if (files.length === 0) {
        return (
            <div className="uploaded-files-list">
                <h3 className="files-list-title">Uploaded Files</h3>
                <div className="files-empty">
                    <div className="empty-icon">📁</div>
                    <h4>No files uploaded yet</h4>
                    <p>Upload transaction files using the area above to get started.</p>
                </div>
            </div>
        );
    }

    return (
        <>
            <div className="uploaded-files-list">
                <h3 className="files-list-title">
                    Uploaded Files ({files.length})
                </h3>

                <div className="files-grid">
                    {sortedFiles.map((file) => {
                        const statusInfo = getStatusInfo(file.processingStatus);

                        return (
                            <div key={file.fileId} className="file-card">
                                {/* File Header */}
                                <div className="file-header">
                                    <div className="file-info">
                                        <span className="file-icon" role="img" aria-label="File type">
                                            {getFileTypeIcon(file.fileName)}
                                        </span>
                                        <div className="file-details">
                                            <h4 className="file-name" title={file.fileName}>
                                                {file.fileName}
                                            </h4>
                                            <p className="file-meta">
                                                {formatFileSize(Number(file.fileSize) || 0)} • {formatDate(String(file.uploadDate))}
                                            </p>
                                        </div>
                                    </div>

                                    <div className={`status-badge ${statusInfo.class}`}>
                                        <span className="status-icon" role="img" aria-label={statusInfo.text}>
                                            {statusInfo.icon}
                                        </span>
                                        <span className="status-text">{statusInfo.text}</span>
                                    </div>
                                </div>

                                {/* File Content */}
                                <div className="file-content">
                                    <div className="file-stats">
                                        <div className="stat-item">
                                            <span className="stat-label">Transactions:</span>
                                            <span className="stat-value">
                                                {file.transactionCount?.toLocaleString() || 0}
                                            </span>
                                        </div>
                                        <div className="stat-item">
                                            <span className="stat-label">Date Range:</span>
                                            <span className="stat-value">
                                                {formatDateRange(file)}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Error Message */}
                                    {file.processingStatus === 'ERROR' && file.errorMessage && (
                                        <div className="file-error-message">
                                            <span className="error-icon">⚠️</span>
                                            <span className="error-text">{file.errorMessage}</span>
                                        </div>
                                    )}
                                </div>

                                {/* File Actions */}
                                <div className="file-actions">
                                    <button
                                        onClick={() => onViewFile(file.fileId)}
                                        className="action-button action-view"
                                        title="View file details"
                                        disabled={file.processingStatus === 'PROCESSING' || file.processingStatus === 'PENDING'}
                                    >
                                        <span className="action-icon">👁️</span>
                                        <span className="action-text">View</span>
                                    </button>

                                    <button
                                        onClick={() => onDownloadFile(file.fileId)}
                                        className="action-button action-download"
                                        title="Download original file"
                                    >
                                        <span className="action-icon">⬇️</span>
                                        <span className="action-text">Download</span>
                                    </button>

                                    {file.processingStatus === 'ERROR' && onRetryProcessing && (
                                        <button
                                            onClick={() => onRetryProcessing(file.fileId)}
                                            className="action-button action-retry"
                                            title="Retry processing"
                                        >
                                            <span className="action-icon">🔄</span>
                                            <span className="action-text">Retry</span>
                                        </button>
                                    )}

                                    <button
                                        onClick={() => handleDeleteFile(file.fileId, file.fileName)}
                                        className="action-button action-delete"
                                        title="Delete file"
                                    >
                                        <span className="action-icon">🗑️</span>
                                        <span className="action-text">Delete</span>
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Workflow Tracking Modal */}
            {workflowId && (
                <WorkflowProgressModal
                    workflowId={workflowId}
                    isOpen={showWorkflowModal}
                    onClose={() => {
                        setShowWorkflowModal(false);
                        setWorkflowId(null);
                        setDeletingFileName('');
                    }}
                    onComplete={() => {
                        // File was successfully deleted, could trigger a refresh here
                        setShowWorkflowModal(false);
                        setWorkflowId(null);
                        setDeletingFileName('');
                    }}
                    title={`Deleting ${deletingFileName}`}
                    mode="full" // Use full mode to show detailed progress
                />
            )}
        </>
    );
};

export default UploadedFilesList;
