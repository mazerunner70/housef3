import React, { useState, useEffect } from 'react';
import { listAssociatedFiles } from '../../../services/FileService';
import { DateCell } from '../ui';
import './TransactionFilesDialog.css';

interface TransactionFilesDialogProps {
    isOpen: boolean;
    onClose: () => void;
    accountId: string;
    accountName: string;
}

interface TransactionFileDisplay {
    fileId: string;
    fileName: string;
    uploadDate: number;
    startDate: number;
    endDate: number;
    transactionCount: number;
    processingStatus?: string;
}

const TransactionFilesDialog: React.FC<TransactionFilesDialogProps> = ({
    isOpen,
    onClose,
    accountId,
    accountName
}) => {
    const [files, setFiles] = useState<TransactionFileDisplay[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen && accountId) {
            fetchTransactionFiles();
        }
    }, [isOpen, accountId]);

    const fetchTransactionFiles = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await listAssociatedFiles(accountId);

            // Convert ServiceFile to TransactionFileDisplay and sort by most recent first
            const transactionFiles: TransactionFileDisplay[] = response
                .map((file: any) => ({
                    fileId: file.fileId,
                    fileName: file.fileName,
                    uploadDate: typeof file.uploadDate === 'string'
                        ? new Date(file.uploadDate).getTime()
                        : file.uploadDate,
                    startDate: file.startDate || 0,
                    endDate: file.endDate || 0,
                    transactionCount: file.transactionCount || 0,
                    processingStatus: file.processingStatus
                }))
                .sort((a, b) => {
                    // Sort by end date first (most recent transactions), then by upload date
                    if (a.endDate !== b.endDate) {
                        return b.endDate - a.endDate;
                    }
                    return b.uploadDate - a.uploadDate;
                });

            setFiles(transactionFiles);
        } catch (err: any) {
            console.error('Error fetching transaction files:', err);
            setError(err.message || 'Failed to load transaction files');
        } finally {
            setLoading(false);
        }
    };

    const handleBackdropClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
            onClose();
        }
        // Support Enter and Space for backdrop button role
        if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onClose();
        }
    };

    if (!isOpen) {
        return null;
    }

    return (
        <div
            className="transaction-files-dialog-backdrop"
            onClick={handleBackdropClick}
            onKeyDown={handleKeyDown}
            role="button"
            tabIndex={0}
            aria-label="Close dialog"
        >
            <div className="transaction-files-dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
                <div className="dialog-header">
                    <h2 id="dialog-title">Transaction Files for {accountName}</h2>
                    <button
                        className="close-button"
                        onClick={onClose}
                        aria-label="Close dialog"
                    >
                        ×
                    </button>
                </div>

                <div className="dialog-content">
                    {loading && (
                        <div className="loading-state">
                            <p>Loading transaction files...</p>
                        </div>
                    )}

                    {error && (
                        <div className="error-state">
                            <p className="error-message">Error: {error}</p>
                            <button onClick={fetchTransactionFiles} className="retry-button">
                                Retry
                            </button>
                        </div>
                    )}

                    {!loading && !error && files.length === 0 && (
                        <div className="empty-state">
                            <p>No transaction files found for this account.</p>
                        </div>
                    )}

                    {!loading && !error && files.length > 0 && (
                        <div className="files-list">
                            <div className="files-header">
                                <span className="file-name-header">File Name</span>
                                <span className="date-range-header">Transaction Period</span>
                                <span className="upload-date-header">Upload Date</span>
                                <span className="transaction-count-header">Transactions</span>
                                <span className="status-header">Status</span>
                            </div>

                            {files.map((file) => (
                                <div key={file.fileId} className="file-item">
                                    <div className="file-name">
                                        <span title={file.fileName}>{file.fileName}</span>
                                    </div>

                                    <div className="date-range">
                                        {file.startDate && file.endDate ? (
                                            <>
                                                <DateCell date={file.startDate} format="iso" />
                                                <span className="date-separator">to</span>
                                                <DateCell date={file.endDate} format="iso" />
                                            </>
                                        ) : (
                                            <span className="no-dates">No date range</span>
                                        )}
                                    </div>

                                    <div className="upload-date">
                                        <DateCell date={file.uploadDate} format="iso" />
                                    </div>

                                    <div className="transaction-count">
                                        {file.transactionCount.toLocaleString()}
                                    </div>

                                    <div className={`status ${file.processingStatus?.toLowerCase() || 'unknown'}`}>
                                        {file.processingStatus || 'Unknown'}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="dialog-footer">
                    <button onClick={onClose} className="close-dialog-button">
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default TransactionFilesDialog;
