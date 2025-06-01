import React from 'react';
import AccountListItem from './AccountListItem'; // Import AccountListItem
import './AccountList.css'; // Import the CSS file
import { UIAccount } from '../../hooks/useAccounts'; // Import UIAccount type

// REMOVE LOCAL ACCOUNT DEFINITION
// interface Account {
//     id: string;
//     name: string;
//     type: string;
//     number: string; // Masked
//     currency: string;
//     transactionFilesCount: number;
// }

interface AccountListProps {
    accounts: UIAccount[];
    onEdit: (account: UIAccount) => void;
    onDelete: (accountId: string) => void;
    onViewDetails: (accountId: string) => void; // Add onViewDetails to props
}

const AccountList: React.FC<AccountListProps> = ({ accounts, onEdit, onDelete, onViewDetails }) => {
    if (!accounts || accounts.length === 0) {
        return <p className="no-accounts-message">No accounts found. Add one to get started!</p>;
    }

    return (
        <div className="account-list">
            {accounts.map(account => (
                <AccountListItem
                    key={account.id}
                    account={account} // Pass the entire account object
                    onEdit={() => onEdit(account)} // onEdit expects the full account object
                    onDelete={() => onDelete(account.id)} // onDelete expects accountId
                    onViewDetails={() => onViewDetails(account.id)} // onViewDetails expects accountId
                />
            ))}
        </div>
    );
};

export default AccountList; 