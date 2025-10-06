import React from 'react';
import './FileUploadStatus.css';

interface FileUploadStatusProps {
    fileCount: number;
    totalTransactions: number;
    dateRange: {
        startDate: number;
        endDate: number;
    } | null;
    isLoading?: boolean;
}

/**
 * FileUploadStatus - Summary section showing upload statistics
 * 
 * Features:
 * - File count and transaction count display
 * - Date range coverage
 * - Visual indicators with icons
 * - Loading states
 * - Responsive card layout
 * 
 * Design:
 * - Clean card-based layout
 * - Icon indicators for each metric
 * - Responsive grid layout
 * - Loading skeleton states
 */
const FileUploadStatus: React.FC<FileUploadStatusProps> = ({
    fileCount,
    totalTransactions,
    dateRange,
    isLoading = false
}) => {
    // Format date range for display
    const formatDateRange = (range: { startDate: number; endDate: number } | null): string => {
        if (!range) {
            return fileCount > 0 ? 'Date range not available' : 'No files uploaded';
        }

        const startDate = new Date(range.startDate);
        const endDate = new Date(range.endDate);

        // Validate that the dates are reasonable
        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
            return 'Invalid date range';
        }

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

    // Format number with commas
    const formatNumber = (num: number): string => {
        return num.toLocaleString();
    };

    if (isLoading) {
        return (
            <div className="file-upload-status">
                <h3 className="status-title">Upload Summary</h3>
                <div className="status-grid">
                    <div className="status-card loading">
                        <div className="status-icon-skeleton"></div>
                        <div className="status-content">
                            <div className="status-label-skeleton"></div>
                            <div className="status-value-skeleton"></div>
                        </div>
                    </div>
                    <div className="status-card loading">
                        <div className="status-icon-skeleton"></div>
                        <div className="status-content">
                            <div className="status-label-skeleton"></div>
                            <div className="status-value-skeleton"></div>
                        </div>
                    </div>
                    <div className="status-card loading">
                        <div className="status-icon-skeleton"></div>
                        <div className="status-content">
                            <div className="status-label-skeleton"></div>
                            <div className="status-value-skeleton"></div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="file-upload-status">
            <h3 className="status-title">Upload Summary</h3>
            <div className="status-grid">
                {/* Files Uploaded */}
                <div className="status-card">
                    <div className="status-icon files-icon" role="img" aria-label="Files uploaded">
                        📁
                    </div>
                    <div className="status-content">
                        <div className="status-label">Files Uploaded</div>
                        <div className="status-value">
                            {formatNumber(fileCount)} {fileCount === 1 ? 'file' : 'files'}
                        </div>
                    </div>
                </div>

                {/* Total Transactions */}
                <div className="status-card">
                    <div className="status-icon transactions-icon" role="img" aria-label="Total transactions">
                        📊
                    </div>
                    <div className="status-content">
                        <div className="status-label">Total Transactions</div>
                        <div className="status-value">
                            {formatNumber(totalTransactions)} {totalTransactions === 1 ? 'transaction' : 'transactions'}
                        </div>
                    </div>
                </div>

                {/* Date Range */}
                <div className="status-card">
                    <div className="status-icon date-icon" role="img" aria-label="Date range">
                        📅
                    </div>
                    <div className="status-content">
                        <div className="status-label">Date Range</div>
                        <div className="status-value">
                            {formatDateRange(dateRange)}
                        </div>
                    </div>
                </div>
            </div>

            {/* Empty State Message */}
            {fileCount === 0 && (
                <div className="empty-state-message">
                    <p>No files have been uploaded yet. Use the upload area below to add transaction files.</p>
                </div>
            )}
        </div>
    );
};

export default FileUploadStatus;
