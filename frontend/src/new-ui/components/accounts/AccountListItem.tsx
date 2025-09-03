import { forwardRef } from 'react';
import './AccountListItem.css';
import { UIAccount } from '../../hooks/useAccounts';
import { CurrencyDisplay, DateCell } from '../ui';

// This interface should align with UIAccount from useAccounts.ts
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
    account: UIAccount;
    onEdit: (account: UIAccount) => void;
    onDelete: (accountId: string) => void;
    onViewDetails: (accountId: string) => void; // Add onViewDetails prop
}

const AccountListItem = forwardRef<HTMLDivElement, AccountListItemProps>(({ account, onEdit, onDelete, onViewDetails }, ref) => {
    const { id, name, type, balance, currency, bankName } = account;

    // Format balance for display - balance is handled by CurrencyDisplay component

    const handleViewDetailsClick = () => {
        onViewDetails(id);
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
                        aria-label={`View details for ${name} account`}
                    >
                        {name}
                    </h3>
                    <div className="account-type-bank">
                        <span className="account-type">
                            {type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                        </span>
                        {bankName && (
                            <span className="account-bank">{bankName}</span>
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
                <button onClick={() => onEdit(account)} className="edit-button">
                    Edit
                </button>
                <button onClick={() => onDelete(id)} className="delete-button">
                    Delete
                </button>
            </div>
        </div>
    );
});

export default AccountListItem; 