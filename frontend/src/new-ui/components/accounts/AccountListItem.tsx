import { forwardRef } from 'react';
import './AccountListItem.css';
import { Account } from '../../../schemas/Account';
import { CurrencyDisplay, DateCell } from '../ui';

// This interface should align with UIAccount from types/UIAccount.ts
export interface AccountListItemData {
    id: string;
    name: string;
    type: string;
    currency: string;
    balance?: number; // Temporarily number, change to Decimal when library is used
    bankName?: string;
    lastTransactionDate?: number; // milliseconds since epoch
    // Removed: accountNumber, transactionFilesCount
}

interface AccountListItemProps {
    account: Account;
    onEdit: (account: Account) => void;
    onDelete: (accountId: string) => void;
    onViewDetails: (accountId: string) => void; // Add onViewDetails prop
    onViewTransactions: (accountId: string) => void; // Add onViewTransactions prop
}

const AccountListItem = forwardRef<HTMLDivElement, AccountListItemProps>(({ account, onEdit, onDelete, onViewDetails, onViewTransactions }, ref) => {
    const { accountId, accountName, accountType, balance, currency, institution } = account;

    // Format balance for display - balance is handled by CurrencyDisplay component

    const handleViewDetailsClick = () => {
        onViewDetails(accountId);
    };

    return (
        <div ref={ref} className="account-list-item">
            <div className="account-info-section">
                <div className="account-primary">
                    <h3
                        onClick={handleViewDetailsClick}
                        onKeyDown={(e) => e.key === 'Enter' && handleViewDetailsClick()}
                        className="account-name"
                        title="Click to view details"
                        tabIndex={0}
                        role="button"
                        aria-label={`View details for ${accountName} account`}
                    >
                        {accountName}
                    </h3>
                    <div className="account-type-bank">
                        <span className="account-type">
                            {accountType.charAt(0).toUpperCase() + accountType.slice(1).replace('_', ' ')}
                        </span>
                        {institution && (
                            <span className="account-bank">{institution}</span>
                        )}
                    </div>
                </div>

                <div className="account-financial">
                    <div className="account-balance">
                        <CurrencyDisplay
                            amount={Number(balance || 0)}
                            currency={currency}
                            showSign={true}
                        />
                    </div>
                    <div className="account-dates">
                        <div className="last-transaction">
                            <span className="date-label">Last Transaction:</span>
                            {account.lastTransactionDate ? (
                                <DateCell
                                    date={account.lastTransactionDate}
                                    format="iso"
                                />
                            ) : (
                                <span className="no-transactions">No transactions</span>
                            )}
                        </div>
                        {(account.importsStartDate || account.importsEndDate) && (
                            <div className="import-range">
                                <span className="date-label">Import Range:</span>
                                <span className="date-range">
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

            <div className="account-actions">
                <button onClick={() => onViewTransactions(accountId)} className="view-transactions-button">
                    View Transactions
                </button>
                <button onClick={() => onEdit(account)} className="edit-button">
                    Edit
                </button>
                <button onClick={() => onDelete(accountId)} className="delete-button">
                    Delete
                </button>
            </div>
        </div>
    );
});

export default AccountListItem; 