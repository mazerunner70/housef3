import React, { useRef, useImperativeHandle, forwardRef } from 'react';
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

export interface AccountListRef {
    scrollToAccount: (accountId: string) => void;
}

const AccountList = forwardRef<AccountListRef, AccountListProps>(({ accounts, onEdit, onDelete, onViewDetails }, ref) => {
    const accountRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

    useImperativeHandle(ref, () => ({
        scrollToAccount: (accountId: string) => {
            const accountElement = accountRefs.current[accountId];
            if (accountElement) {
                accountElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });

                // Add visual feedback - highlight the account briefly
                accountElement.classList.add('scroll-highlight');
                setTimeout(() => {
                    accountElement.classList.remove('scroll-highlight');
                }, 2000);
            }
        }
    }));

    if (!accounts || accounts.length === 0) {
        return <p className="no-accounts-message">No accounts found. Add one to get started!</p>;
    }

    return (
        <div className="account-list">
            {accounts.map(account => (
                <AccountListItem
                    key={account.id}
                    ref={(el) => {
                        if (el) {
                            accountRefs.current[account.id] = el;
                        } else {
                            delete accountRefs.current[account.id];
                        }
                    }}
                    account={account} // Pass the entire account object
                    onEdit={() => onEdit(account)} // onEdit expects the full account object
                    onDelete={() => onDelete(account.id)} // onDelete expects accountId
                    onViewDetails={() => onViewDetails(account.id)} // onViewDetails expects accountId
                />
            ))}
        </div>
    );
});

export default AccountList; 