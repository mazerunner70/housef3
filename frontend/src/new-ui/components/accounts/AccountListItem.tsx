import React from 'react';
import './AccountListItem.css'; // Import the CSS file
// import { Decimal } from 'decimal.js'; // Re-enable if using Decimal.js

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

interface AccountListItemProps extends AccountListItemData {
    onEdit: () => void; // Changed: onEdit will receive the full account from AccountList, so just a callback here
    onDelete: () => void; // Changed: onDelete will receive the full account from AccountList
}

const AccountListItem: React.FC<AccountListItemProps> = (props) => {
    return (
        <div className="account-list-item">
            <h3>{props.name}</h3>
            <p>Type: {props.type}</p>
            <p>Bank: {props.bankName || 'N/A'}</p>
            <p>Balance: {props.balance !== undefined ? props.balance.toFixed(2) : 'N/A'} {props.currency}</p>
            {/* When using Decimal.js, use: props.balance ? props.balance.toFixed(2) : 'N/A' */}
            <div className="account-item-actions">
                <button onClick={props.onEdit} className="edit-button">Edit</button>
                <button onClick={props.onDelete} className="delete-button">Delete</button>
            </div>
        </div>
    );
};

export default AccountListItem; 