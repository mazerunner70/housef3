import React from 'react';
import { Account } from '@/schemas/Account';
import './SimpleAccountsList.css';

interface SimpleAccountsListProps {
    accounts: Account[];
    onImportClick: (accountId: string) => void;
    onAccountClick: (accountId: string) => void;
    isLoading?: boolean;
}

/**
 * SimpleAccountsList - Basic accounts list for Stage 1 implementation
 * 
 * Features:
 * - Simple table layout with essential account information
 * - Placeholder import buttons
 * - Loading state
 * - Responsive design
 * - Will be enhanced in Stage 2 with compact design
 */
const SimpleAccountsList: React.FC<SimpleAccountsListProps> = ({
    accounts,
    onImportClick,
    onAccountClick,
    isLoading = false
}) => {
    // Split currency for decimal alignment
    const formatCurrencyParts = (amount: any, currency: string = 'USD') => {
        try {
            const numValue = typeof amount?.toNumber === 'function' ? amount.toNumber() : parseFloat(amount);
            const formatted = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency
            }).format(numValue);

            // Split on decimal point
            const parts = formatted.split('.');
            return {
                dollars: parts[0],
                cents: parts[1] ? `.${parts[1]}` : '.00'
            };
        } catch (error) {
            return { dollars: '$0', cents: '.00' };
        }
    };

    const formatDate = (timestamp?: number | null) => {
        if (!timestamp) return 'Never';
        try {
            return new Date(timestamp).toLocaleDateString();
        } catch (error) {
            return 'Invalid Date';
        }
    };

    const getAccountTypeDisplay = (type: string) => {
        const typeMap: Record<string, string> = {
            'checking': 'Checking',
            'savings': 'Savings',
            'credit_card': 'Credit Card',
            'investment': 'Investment',
            'loan': 'Loan',
            'other': 'Other'
        };
        return typeMap[type] || type;
    };

    const getAccountIcon = (type: string) => {
        const iconMap: Record<string, string> = {
            'checking': '💳',
            'savings': '💰',
            'credit_card': '💳',
            'investment': '📈',
            'loan': '🏠',
            'other': '🏦'
        };
        return iconMap[type] || '🏦';
    };

    if (isLoading) {
        return (
            <div className="simple-accounts-list loading">
                <div className="loading-message">
                    <div className="loading-spinner"></div>
                    <p>Loading accounts...</p>
                </div>
            </div>
        );
    }

    if (accounts.length === 0) {
        return (
            <div className="simple-accounts-list empty">
                <div className="empty-message">
                    <p>No accounts found. Create an account to start importing transactions.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="simple-accounts-list">
            <div className="accounts-table-container">
                <table className="accounts-table">
                    <thead>
                        <tr>
                            <th>Account</th>
                            <th>Institution</th>
                            <th>Type</th>
                            <th>Balance</th>
                            <th>Last Import</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {accounts.map((account) => (
                            <tr key={account.accountId} className="account-row">
                                <td className="account-name-cell">
                                    <div className="account-name-content">
                                        <span className="account-icon">
                                            {getAccountIcon(account.accountType)}
                                        </span>
                                        <button
                                            className="account-name-button"
                                            onClick={() => onAccountClick(account.accountId)}
                                        >
                                            {account.accountName}
                                        </button>
                                    </div>
                                </td>
                                <td className="institution-cell">
                                    {account.institution}
                                </td>
                                <td className="type-cell">
                                    {getAccountTypeDisplay(account.accountType)}
                                </td>
                                <td className="balance-cell">
                                    <div className="balance-aligned">
                                        <span className="balance-dollars">
                                            {formatCurrencyParts(account.balance, account.currency).dollars}
                                        </span>
                                        <span className="balance-cents">
                                            {formatCurrencyParts(account.balance, account.currency).cents}
                                        </span>
                                    </div>
                                </td>
                                <td className="import-date-cell">
                                    {formatDate(account.importsEndDate)}
                                </td>
                                <td className="status-cell">
                                    <span className={`status-badge ${account.isActive ? 'active' : 'inactive'}`}>
                                        {account.isActive ? '✓ Active' : '⚠ Inactive'}
                                    </span>
                                </td>
                                <td className="actions-cell">
                                    <button
                                        className="import-button"
                                        onClick={() => onImportClick(account.accountId)}
                                    >
                                        📤 Import
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default SimpleAccountsList;
