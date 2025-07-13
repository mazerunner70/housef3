import React from 'react';
import './AccountListItem.css';
import { UIAccount } from '../../hooks/useAccounts';
import { CurrencyDisplay, DateCell, TextWithSubtext } from '../ui';

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

const AccountListItem: React.FC<AccountListItemProps> = ({ account, onEdit, onDelete, onViewDetails }) => {
    const { id, name, type, balance, currency, bankName } = account;

    // Format balance for display
    // const displayBalance = balance instanceof Decimal ? balance.toFixed(2) : (typeof balance === 'number' ? balance.toFixed(2) : 'N/A');
    const displayBalance = balance ? balance.toString() : '0.00'; // Assuming balance is already a string or number from UIAccount

    const handleViewDetailsClick = () => {
        onViewDetails(id);
    };

    return (
        <div className="account-list-item">
            <div className="account-card-header">
                <div className="account-primary-info">
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
                </div>
                <div className="account-balance">
                    <CurrencyDisplay 
                        amount={Number(balance || 0)} 
                        currency={currency}
                        showSign={true}
                    />
                </div>
            </div>
            
            <div className="account-card-body">
                <div className="account-details">
                    <div className="account-detail-item">
                        <TextWithSubtext 
                            primaryText={type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ')}
                            variant="description"
                            subtextPrefix=""
                            subtextSuffix=""
                        />
                    </div>
                    <div className="account-detail-item">
                        <span className="detail-label">Last Transaction:</span>
                        <span className="detail-value">
                            {account.lastTransactionDate ? (
                                <DateCell 
                                    date={account.lastTransactionDate}
                                    format="iso"
                                />
                            ) : (
                                <span className="no-transactions">No transactions</span>
                            )}
                        </span>
                    </div>
                </div>
            </div>
            
            <div className="account-card-footer">
                <div className="account-actions">
                    <button onClick={() => onEdit(account)} className="edit-button">
                        Edit
                    </button>
                    <button onClick={() => onDelete(id)} className="delete-button">
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AccountListItem; 