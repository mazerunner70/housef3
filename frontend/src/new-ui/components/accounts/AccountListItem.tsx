import React from 'react';
import './AccountListItem.css'; // Import the CSS file
// import { Decimal } from 'decimal.js'; // Re-enable if using Decimal.js
import { UIAccount } from '../../hooks/useAccounts';

// This interface should align with UIAccount from useAccounts.ts
export interface AccountListItemData {
    id: string;
    name: string;
    type: string;
    currency: string;
    balance?: number; // Temporarily number, change to Decimal when library is used
    bankName?: string;
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
    const displayBalance = balance ? balance.toString() : 'N/A'; // Assuming balance is already a string or number from UIAccount

    const handleViewDetailsClick = () => {
        onViewDetails(id);
    };

    return (
        <div className="account-list-item">
            <div className="account-info">
                <h3 onClick={handleViewDetailsClick} style={{cursor: 'pointer'}} title="View Details">{name}</h3>
                <p>Type: {type}</p>
                <p>Bank: {bankName || 'N/A'}</p>
                <p>Balance: {displayBalance} {currency}</p>
            </div>
            <div className="account-actions">
                <button onClick={() => onEdit(account)} className="edit-button">Edit</button>
                <button onClick={() => onDelete(id)} className="delete-button">Delete</button>
            </div>
        </div>
    );
};

export default AccountListItem; 