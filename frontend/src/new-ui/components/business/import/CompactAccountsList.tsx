import React from 'react';
import { AccountForImport } from '@/new-ui/hooks/useAccountsData';
import CompactAccountItem from './CompactAccountItem';
import LoadingState from '@/new-ui/components/ui/LoadingState';
import './CompactAccountsList.css';

interface CompactAccountsListProps {
    accounts: AccountForImport[];
    onImportClick: (accountId: string) => void;
    onAccountClick: (accountId: string) => void;
    isLoading?: boolean;
}

/**
 * CompactAccountsList - Optimized list view for account selection in import workflow
 * 
 * Features:
 * - Compact, scannable list design optimized for import workflow
 * - Accounts sorted by updatedAt (oldest first) for import priority
 * - Rich metadata display with import history and financial info
 * - Loading states and empty state handling
 * - Responsive design with mobile optimization
 * - Accessibility support with keyboard navigation
 * - Performance optimized for large account lists
 */
const CompactAccountsList: React.FC<CompactAccountsListProps> = ({
    accounts,
    onImportClick,
    onAccountClick,
    isLoading = false
}) => {
    // Loading state
    if (isLoading) {
        return (
            <div className="compact-accounts-list-container">
                <LoadingState
                    message="Loading accounts..."
                    size="medium"
                    variant="spinner"
                />
            </div>
        );
    }

    // Empty state
    if (accounts.length === 0) {
        return (
            <div className="compact-accounts-list-container">
                <div className="empty-accounts-state">
                    <div className="empty-state-icon">🏦</div>
                    <h3 className="empty-state-title">No Accounts Found</h3>
                    <p className="empty-state-description">
                        Create an account to start importing transaction files.
                    </p>
                    <button
                        className="create-account-button"
                        onClick={() => {
                            // TODO: Implement account creation navigation
                            console.log('Navigate to account creation');
                        }}
                    >
                        Create Your First Account
                    </button>
                </div>
            </div>
        );
    }

    // Calculate summary statistics
    const activeAccounts = accounts.filter(account => account.isActive);
    const accountsWithImports = accounts.filter(account => account.importsEndDate);
    const accountsNeedingImports = accounts.filter(account => !account.importsEndDate);

    return (
        <div className="compact-accounts-list-container">
            {/* Summary Header */}
            <div className="accounts-summary-header">
                <div className="summary-stats">
                    <div className="stat-item">
                        <span className="stat-value">{accounts.length}</span>
                        <span className="stat-label">Total Accounts</span>
                    </div>
                    <div className="stat-separator">•</div>
                    <div className="stat-item">
                        <span className="stat-value">{activeAccounts.length}</span>
                        <span className="stat-label">Active</span>
                    </div>
                    <div className="stat-separator">•</div>
                    <div className="stat-item">
                        <span className="stat-value">{accountsNeedingImports.length}</span>
                        <span className="stat-label">Need Imports</span>
                    </div>
                </div>

                <div className="sort-info">
                    <span className="sort-icon">📊</span>
                    <span className="sort-text">Sorted by import priority (oldest first)</span>
                </div>
            </div>

            {/* Accounts List */}
            <div
                className="compact-accounts-list"
                role="list"
                aria-label="Accounts available for import"
            >
                {accounts.map((account) => (
                    <div key={account.accountId} role="listitem">
                        <CompactAccountItem
                            account={account}
                            onImportClick={onImportClick}
                            onAccountClick={onAccountClick}
                        />
                    </div>
                ))}
            </div>

            {/* Footer Info */}
            {accounts.length > 0 && (
                <div className="accounts-list-footer">
                    <div className="footer-info">
                        <span className="info-icon">💡</span>
                        <span className="info-text">
                            Accounts are prioritized by last update date.
                            Accounts that haven't been updated recently appear first.
                        </span>
                    </div>

                    {accountsWithImports.length > 0 && (
                        <div className="import-stats">
                            <span className="import-stats-text">
                                {accountsWithImports.length} account{accountsWithImports.length !== 1 ? 's' : ''}
                                {' '}with existing imports
                            </span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default CompactAccountsList;