import React from 'react';
import { ImportStatus } from '@/hooks/useImportState';
import './ImportHeader.css';

interface ImportHeaderProps {
    onUploadClick?: () => void;
    onHistoryClick?: () => void;
    importStatus?: ImportStatus;
    accountCount?: number;
    activeAccountCount?: number;
    lastUpdated?: number | null;
}

/**
 * Enhanced ImportHeader - Page title, subtitle, and quick action buttons for import workflow
 * 
 * Stage 1 Features:
 * - Clear page title and description with enhanced context
 * - Import status and progress display with real-time updates
 * - Quick action buttons with improved states and accessibility
 * - Account statistics and last updated information
 * - Responsive design with mobile optimization
 * - Enhanced visual feedback and loading states
 */
const ImportHeader: React.FC<ImportHeaderProps> = ({
    onUploadClick,
    onHistoryClick,
    importStatus,
    accountCount = 0,
    activeAccountCount = 0,
    lastUpdated
}) => {
    // Format last updated time
    const formatLastUpdated = (timestamp: number | null): string => {
        if (!timestamp) return 'Never';

        const now = Date.now();
        const diff = now - timestamp;
        const minutes = Math.floor(diff / (1000 * 60));
        const hours = Math.floor(diff / (1000 * 60 * 60));

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;

        return new Date(timestamp).toLocaleDateString();
    };

    // Generate dynamic subtitle based on context
    const getSubtitle = (): string => {
        if (importStatus?.isImporting) {
            return `Importing ${importStatus.currentFile?.fileName || 'file'}...`;
        }

        if (accountCount === 0) {
            return 'No accounts found. Create an account to start importing.';
        }

        if (activeAccountCount === 0) {
            return `${accountCount} account${accountCount !== 1 ? 's' : ''} found, but none are active.`;
        }

        return `Select from ${activeAccountCount} active account${activeAccountCount !== 1 ? 's' : ''} to import transaction files`;
    };

    return (
        <div className="import-header">
            <div className="import-header-content">
                <div className="import-header-text">
                    <div className="header-title-section">
                        <h1 className="import-header-title">Import Transactions</h1>

                        {/* Account Statistics Badge */}
                        {accountCount > 0 && (
                            <div className="account-stats-badge">
                                <span className="stats-icon">🏦</span>
                                <span className="stats-text">
                                    {activeAccountCount}/{accountCount} active
                                </span>
                            </div>
                        )}
                    </div>

                    <p className="import-header-subtitle">
                        {getSubtitle()}
                    </p>

                    {/* Last Updated Info */}
                    {lastUpdated && (
                        <div className="last-updated-info">
                            <span className="update-icon">🔄</span>
                            <span className="update-text">
                                Last updated: {formatLastUpdated(lastUpdated)}
                            </span>
                        </div>
                    )}

                    {/* Import Progress Indicator */}
                    {importStatus?.isImporting && importStatus.currentFile && (
                        <div className="import-progress-container">
                            <div className="progress-info">
                                <span className="progress-text">
                                    {importStatus.currentFile.status === 'uploading' && '📤 Uploading file...'}
                                    {importStatus.currentFile.status === 'parsing' && '🔍 Parsing transactions...'}
                                    {importStatus.currentFile.status === 'processing' && '⚙️ Processing data...'}
                                    {importStatus.currentFile.status === 'complete' && '✅ Import complete!'}
                                    {importStatus.currentFile.status === 'error' && '❌ Import failed'}
                                </span>
                                <span className="progress-percentage">
                                    {importStatus.currentFile.progress}%
                                </span>
                            </div>
                            <div className="progress-bar">
                                <div
                                    className={`progress-fill ${importStatus.currentFile.status === 'error' ? 'error' : ''}`}
                                    style={{ width: `${importStatus.currentFile.progress}%` }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Recent Imports Summary */}
                    {importStatus?.recentImports && importStatus.recentImports.length > 0 && !importStatus.isImporting && (
                        <div className="recent-imports-summary">
                            <span className="recent-icon">📋</span>
                            <span className="recent-text">
                                {importStatus.recentImports.length} recent import{importStatus.recentImports.length !== 1 ? 's' : ''}
                            </span>
                        </div>
                    )}
                </div>

                <div className="import-header-actions">
                    <button
                        className="import-action-button secondary"
                        onClick={onHistoryClick}
                        disabled={!onHistoryClick || importStatus?.isImporting}
                        aria-label="View import history and manage previous imports"
                    >
                        <span className="button-icon">📊</span>
                        <span className="button-text">View History</span>
                    </button>
                    <button
                        className="import-action-button primary"
                        onClick={onUploadClick}
                        disabled={!onUploadClick || importStatus?.isImporting || activeAccountCount === 0}
                        aria-label="Upload new transaction file"
                        title={activeAccountCount === 0 ? 'No active accounts available for import' : 'Upload new transaction file'}
                    >
                        <span className="button-icon">📤</span>
                        <span className="button-text">Upload File</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ImportHeader;
