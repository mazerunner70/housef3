import React from 'react';
import './ImportHeader.css';

interface ImportHeaderProps {
    onUploadClick?: () => void;
    onHistoryClick?: () => void;
}

/**
 * ImportHeader - Page title, subtitle, and quick action buttons for import workflow
 * 
 * Features:
 * - Clear page title and description
 * - Quick action buttons (placeholder functionality for Stage 1)
 * - Responsive design
 */
const ImportHeader: React.FC<ImportHeaderProps> = ({
    onUploadClick,
    onHistoryClick
}) => {
    return (
        <div className="import-header">
            <div className="import-header-content">
                <div className="import-header-text">
                    <h1 className="import-header-title">Import Transactions</h1>
                    <p className="import-header-subtitle">
                        Select an account to import transaction files
                    </p>
                </div>

                <div className="import-header-actions">
                    <button
                        className="import-action-button secondary"
                        onClick={onHistoryClick}
                        disabled={!onHistoryClick}
                    >
                        📊 View Import History
                    </button>
                    <button
                        className="import-action-button primary"
                        onClick={onUploadClick}
                        disabled={!onUploadClick}
                    >
                        📤 Upload New File
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ImportHeader;
