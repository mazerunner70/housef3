import React from 'react';
import { AccountForImport } from '@/new-ui/hooks/useAccountsData';
import './AccountUploadHeader.css';

interface AccountUploadHeaderProps {
    account: AccountForImport;
    onBackClick: () => void;
}

/**
 * AccountUploadHeader - Header component for account file upload page
 * 
 * Features:
 * - Account context display (name, institution, type)
 * - Breadcrumb navigation
 * - Back button to main import page
 * - Account metadata display
 * - Responsive design
 * 
 * Design:
 * - Clean, focused header with account information
 * - Clear navigation path
 * - Account type icon and institution display
 * - Mobile-optimized layout
 */
const AccountUploadHeader: React.FC<AccountUploadHeaderProps> = ({
    account,
    onBackClick
}) => {
    // Get account type icon
    const getAccountTypeIcon = (accountType: string): string => {
        switch (accountType.toLowerCase()) {
            case 'checking':
                return '💳';
            case 'savings':
                return '💰';
            case 'credit_card':
                return '💳';
            case 'investment':
                return '📈';
            case 'loan':
                return '🏦';
            default:
                return '📋';
        }
    };

    // Format account type for display
    const formatAccountType = (accountType: string): string => {
        return accountType
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    };

    return (
        <div className="account-upload-header">
            {/* Breadcrumb Navigation */}
            <nav className="account-upload-breadcrumb" aria-label="Breadcrumb">
                <ol className="breadcrumb-list">
                    <li className="breadcrumb-item">
                        <button
                            onClick={onBackClick}
                            className="breadcrumb-link"
                            aria-label="Back to Import Transactions"
                        >
                            Import Transactions
                        </button>
                    </li>
                    <li className="breadcrumb-separator" aria-hidden="true">
                        &gt;
                    </li>
                    <li className="breadcrumb-item breadcrumb-current" aria-current="page">
                        {account.accountName}
                    </li>
                </ol>
            </nav>

            {/* Header Content */}
            <div className="account-upload-header-content">
                <div className="account-upload-title-section">
                    <div className="account-info">
                        <span className="account-icon" role="img" aria-label={`${formatAccountType(account.accountType)} account`}>
                            {getAccountTypeIcon(account.accountType)}
                        </span>
                        <div className="account-details">
                            <h1 className="account-title">
                                Upload Files for {account.accountName}
                            </h1>
                            <p className="account-subtitle">
                                {account.institution && (
                                    <>
                                        <span className="account-institution">{account.institution}</span>
                                        <span className="account-separator"> • </span>
                                    </>
                                )}
                                <span className="account-type">{formatAccountType(account.accountType)}</span>
                                {account.balance && (
                                    <>
                                        <span className="account-separator"> • </span>
                                        <span className="account-balance">
                                            Balance: {account.currency || 'USD'} {account.balance.toString()}
                                        </span>
                                    </>
                                )}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Back Button (Mobile) */}
                <button
                    onClick={onBackClick}
                    className="back-button-mobile"
                    aria-label="Back to Import Transactions"
                >
                    <span className="back-icon" aria-hidden="true">←</span>
                    <span className="back-text">Back</span>
                </button>
            </div>

            {/* Import Status Indicator */}
            {account.importsEndDate && (
                <div className="import-status-indicator">
                    <span className="status-icon">📅</span>
                    <span className="status-text">
                        Last import: {new Date(account.importsEndDate).toLocaleDateString()}
                    </span>
                </div>
            )}
        </div>
    );
};

export default AccountUploadHeader;
