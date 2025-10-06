import React from 'react';
import { Account } from '@/schemas/Account';
import { Transaction, TransactionFile } from '@/stores/navigationStore';
import './TransactionDetailView.css';

interface TransactionDetailViewProps {
    transaction: Transaction;
    account?: Account;
    file?: TransactionFile;
}

const TransactionDetailView: React.FC<TransactionDetailViewProps> = ({
    transaction,
    account,
    file
}) => {
    return (
        <div className="transaction-detail-view">
            <div className="transaction-header">
                <div className="transaction-info">
                    <h1>Transaction Details</h1>
                    <div className="transaction-id">
                        ID: {transaction.transactionId}
                    </div>
                </div>

                <div className="transaction-amount">
                    <span className={`amount ${transaction.amount >= 0 ? 'positive' : 'negative'}`}>
                        {transaction.amount >= 0 ? '+' : ''}${Math.abs(transaction.amount).toFixed(2)}
                    </span>
                </div>
            </div>

            <div className="transaction-content">
                <div className="transaction-details-grid">
                    <div className="detail-card">
                        <h3>Transaction Information</h3>
                        <div className="detail-items">
                            <div className="detail-item">
                                <span className="detail-label">Description:</span>
                                <span className="detail-value">{transaction.description}</span>
                            </div>
                            <div className="detail-item">
                                <span className="detail-label">Date:</span>
                                <span className="detail-value">
                                    {new Date(transaction.date).toLocaleDateString()}
                                </span>
                            </div>
                            <div className="detail-item">
                                <span className="detail-label">Amount:</span>
                                <span className="detail-value">
                                    ${Math.abs(transaction.amount).toFixed(2)}
                                </span>
                            </div>
                            {transaction.category && (
                                <div className="detail-item">
                                    <span className="detail-label">Category:</span>
                                    <span className="detail-value">{transaction.category}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {account && (
                        <div className="detail-card">
                            <h3>Account Context</h3>
                            <div className="detail-items">
                                <div className="detail-item">
                                    <span className="detail-label">Account:</span>
                                    <span className="detail-value">{account.accountName}</span>
                                </div>
                                <div className="detail-item">
                                    <span className="detail-label">Account Type:</span>
                                    <span className="detail-value">
                                        {account.accountType.charAt(0).toUpperCase() + account.accountType.slice(1).replace('_', ' ')}
                                    </span>
                                </div>
                                {account.institution && (
                                    <div className="detail-item">
                                        <span className="detail-label">Institution:</span>
                                        <span className="detail-value">{account.institution}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {file && (
                        <div className="detail-card">
                            <h3>Source File</h3>
                            <div className="detail-items">
                                <div className="detail-item">
                                    <span className="detail-label">File:</span>
                                    <span className="detail-value">{file.fileName}</span>
                                </div>
                                <div className="detail-item">
                                    <span className="detail-label">Upload Date:</span>
                                    <span className="detail-value">
                                        {new Date(file.uploadDate).toLocaleDateString()}
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="transaction-actions-section">
                    <h3>Actions</h3>
                    <div className="action-buttons">
                        <button className="action-button primary">
                            <span className="button-icon">✏️</span>
                            Edit Transaction
                        </button>
                        <button className="action-button secondary">
                            <span className="button-icon">🏷️</span>
                            Change Category
                        </button>
                        <button className="action-button secondary">
                            <span className="button-icon">📝</span>
                            Add Note
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TransactionDetailView;
