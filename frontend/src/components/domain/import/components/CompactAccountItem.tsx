import React from 'react';
import { AccountForImport } from '@/components/domain/accounts/hooks/useAccountsData';
import CurrencyAmount from '@/components/ui/CurrencyAmount';
import DateCell from '@/components/ui/DateCell';
import StatusBadge from '@/components/ui/StatusBadge';
import './CompactAccountItem.css';

interface CompactAccountItemProps {
    account: AccountForImport;
    onImportClick: (accountId: string) => void;
    onAccountClick: (accountId: string) => void;
}

/**
 * CompactAccountItem - Individual account row optimized for import workflow
 * 
 * Features:
 * - Compact 60px height design for efficient scanning
 * - Rich metadata display with import history
 * - Prominent import action button
 * - Account type icons and status indicators
 * - Hover states and accessibility support
 * - Click handlers for account details and import actions
 */
const CompactAccountItem: React.FC<CompactAccountItemProps> = ({
    account,
    onImportClick,
    onAccountClick
}) => {
    // Account type icons mapping
    const getAccountIcon = (accountType: string): string => {
        const iconMap: Record<string, string> = {
            'checking': '💳',
            'savings': '💰',
            'credit_card': '💳',
            'investment': '📈',
            'loan': '🏦',
            'other': '📊'
        };
        return iconMap[accountType] || '📊';
    };

    // Format account type for display
    const formatAccountType = (accountType: string): string => {
        const typeMap: Record<string, string> = {
            'checking': 'Checking',
            'savings': 'Savings',
            'credit_card': 'Credit Card',
            'investment': 'Investment',
            'loan': 'Loan',
            'other': 'Other'
        };
        return typeMap[accountType] || 'Other';
    };

    // Calculate import date range display
    const getImportRangeDisplay = (): string => {
        if (!account.importsStartDate || !account.importsEndDate) {
            return 'No imports yet';
        }

        const startDate = new Date(account.importsStartDate);
        const endDate = new Date(account.importsEndDate);

        // Format as MM/DD/YYYY for compact display
        const formatDate = (date: Date) => {
            return date.toLocaleDateString('en-US', {
                month: '2-digit',
                day: '2-digit',
                year: 'numeric'
            });
        };

        return `${formatDate(startDate)} - ${formatDate(endDate)}`;
    };

    // Handle keyboard navigation
    const handleKeyDown = (event: React.KeyboardEvent, action: () => void) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            action();
        }
    };

    // Handle account row click (excluding action button area)
    const handleAccountRowClick = (event: React.MouseEvent) => {
        // Don't trigger account click if clicking on the import button
        const target = event.target as HTMLElement;
        if (target.closest('.import-action-button')) {
            return;
        }
        onAccountClick(account.accountId);
    };

    return (
        <button
            className="compact-account-item"
            onClick={handleAccountRowClick}
            onKeyDown={(e) => handleKeyDown(e, () => onAccountClick(account.accountId))}
            aria-label={`Account: ${account.accountName}. Click to view details.`}
        >
            {/* Left Section: Account Info */}
            <div className="account-info-section">
                <div className="account-primary-info">
                    <span className="account-icon" aria-hidden="true">
                        {getAccountIcon(account.accountType)}
                    </span>
                    <div className="account-name-container">
                        <h3 className="account-name">{account.accountName}</h3>
                        <div className="account-metadata">
                            <span className="institution">{account.institution}</span>
                            <span className="separator">•</span>
                            <span className="account-type">{formatAccountType(account.accountType)}</span>
                        </div>
                    </div>
                </div>

                <div className="import-range-info">
                    <span className="import-range-label">Import Range:</span>
                    <span className="import-range-value">{getImportRangeDisplay()}</span>
                </div>
            </div>

            {/* Center Section: Financial Info */}
            <div className="financial-info-section">
                <div className="balance-container">
                    <span className="balance-label">Balance:</span>
                    <CurrencyAmount
                        amount={account.balance}
                        currency={account.currency}
                        className="account-balance"
                    />
                </div>

                <div className="last-import-container">
                    <span className="last-import-label">Last Import:</span>
                    {account.importsEndDate ? (
                        <DateCell
                            date={account.importsEndDate}
                            format="short"
                            className="last-import-date"
                        />
                    ) : (
                        <span className="no-import-text">Never</span>
                    )}
                </div>
            </div>

            {/* Right Section: Status & Action */}
            <div className="status-action-section">
                <div className="account-status">
                    <StatusBadge
                        status={account.isActive ? 'Active' : 'Inactive'}
                        variant={account.isActive ? 'success' : 'warning'}
                        size="small"
                    />
                </div>

                <button
                    className="import-action-button"
                    onClick={(e) => {
                        e.stopPropagation(); // Prevent row click
                        onImportClick(account.accountId);
                    }}
                    onKeyDown={(e) => {
                        e.stopPropagation();
                        handleKeyDown(e, () => onImportClick(account.accountId));
                    }}
                    aria-label={`Import transactions for ${account.accountName}`}
                    disabled={!account.isActive}
                >
                    <span className="import-icon" aria-hidden="true">📤</span>
                    <span className="import-text">Import</span>
                </button>
            </div>
        </button>
    );
};

export default CompactAccountItem;