import React from 'react';
import { Account } from '@/schemas/Account';
import { TransactionFile } from '@/stores/navigationStore';
import './FileTransactionsView.css';

interface FileTransactionsViewProps {
    account: Account;
    file: TransactionFile;
}

const FileTransactionsView: React.FC<FileTransactionsViewProps> = ({ account: _, file }) => {
    return (
        <div className="file-transactions-view">
            <div className="file-header">
                <div className="file-info">
                    <h1>{file.fileName}</h1>
                    <div className="file-metadata">
                        <span className="transaction-count">
                            {file.transactionCount} transactions
                        </span>
                        <span className="date-range">
                            {new Date(file.startDate).toLocaleDateString()} - {new Date(file.endDate).toLocaleDateString()}
                        </span>
                        <span className="upload-date">
                            Uploaded: {new Date(file.uploadDate).toLocaleDateString()}
                        </span>
                    </div>
                </div>

                <div className="file-actions">
                    <button className="action-button secondary">
                        <span className="button-icon">📥</span> Download
                    </button>
                    <button className="action-button danger">
                        <span className="button-icon">🗑️</span> Remove
                    </button>
                </div>
            </div>

            <div className="file-content">
                <div className="transactions-section">
                    <h2>Transactions</h2>
                    <div className="transactions-placeholder">
                        <p>Transaction table will be implemented in Phase 3.</p>
                        <p>This will show all {file.transactionCount} transactions from this file.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FileTransactionsView;
