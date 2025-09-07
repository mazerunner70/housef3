import React from 'react';
import { Account } from '@/schemas/Account';
import { CurrencyDisplay, DateCell } from '@/new-ui/components/ui';
import './AccountDetailView.css';

interface AccountDetailViewProps {
    account: Account;
}

const AccountDetailView: React.FC<AccountDetailViewProps> = ({ account }) => {
    return (
        <div className="account-detail-view">
            <div className="account-detail-header">
                <div className="account-title">
                    <h1>{account.accountName}</h1>
                    <div className="account-subtitle">
                        <span className="account-type">
                            {account.accountType.charAt(0).toUpperCase() + account.accountType.slice(1).replace('_', ' ')}
                        </span>
                        {account.institution && (
                            <>
                                <span className="separator">•</span>
                                <span className="account-institution">{account.institution}</span>
                            </>
                        )}
                    </div>
                </div>

                <div className="account-balance">
                    <CurrencyDisplay
                        amount={Number(account.balance || 0)}
                        currency={account.currency}
                        showSign={true}
                        className="balance-display"
                    />
                </div>
            </div>

            <div className="account-detail-content">
                <div className="account-info-grid">
                    <div className="info-card">
                        <h3>Account Information</h3>
                        <div className="info-items">
                            <div className="info-item">
                                <span className="info-label">Currency:</span>
                                <span className="info-value">{account.currency}</span>
                            </div>
                            {account.notes && (
                                <div className="info-item">
                                    <span className="info-label">Notes:</span>
                                    <span className="info-value">{account.notes}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="info-card">
                        <h3>Transaction History</h3>
                        <div className="info-items">
                            <div className="info-item">
                                <span className="info-label">Last Transaction:</span>
                                <span className="info-value">
                                    {account.lastTransactionDate ? (
                                        <DateCell
                                            date={account.lastTransactionDate}
                                            format="iso"
                                        />
                                    ) : (
                                        'No transactions'
                                    )}
                                </span>
                            </div>
                            {(account.importsStartDate || account.importsEndDate) && (
                                <div className="info-item">
                                    <span className="info-label">Import Range:</span>
                                    <span className="info-value">
                                        {account.importsStartDate ? (
                                            <DateCell date={account.importsStartDate} format="iso" />
                                        ) : 'N/A'}
                                        {' - '}
                                        {account.importsEndDate ? (
                                            <DateCell date={account.importsEndDate} format="iso" />
                                        ) : 'N/A'}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="account-actions-section">
                    <h3>Quick Actions</h3>
                    <div className="action-buttons">
                        <button className="action-button primary">
                            <span className="button-icon">📁</span>
                            View Transaction Files
                        </button>
                        <button className="action-button secondary">
                            <span className="button-icon">📊</span>
                            View All Transactions
                        </button>
                        <button className="action-button secondary">
                            <span className="button-icon">📥</span>
                            Import New File
                        </button>
                    </div>
                </div>

                <div className="recent-activity-section">
                    <h3>Recent Activity</h3>
                    <div className="activity-placeholder">
                        <p>Recent transactions and file imports will appear here.</p>
                        <p className="placeholder-note">This section will be implemented in Phase 2.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AccountDetailView;
