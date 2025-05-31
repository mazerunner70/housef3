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
    // onSelect: (accountId: string) => void; // For navigating to detail view
}

const AccountList: React.FC<AccountListProps> = ({ accounts, onEdit, onDelete }) => {
    if (!accounts || accounts.length === 0) {
        return <p className="no-accounts-message">No accounts found. Add one to get started!</p>;
    }

    return (
        <div className="account-list">
            {accounts.map(account => (
                <AccountListItem
                    key={account.id}
                    id={account.id}
                    name={account.name}
                    type={account.type}
                    currency={account.currency}
                    balance={account.balance}
                    bankName={account.bankName}
                    onEdit={() => onEdit(account)}
                    onDelete={() => onDelete(account.id)}
                />
            ))}
        </div>
    );
};

export default AccountList; 