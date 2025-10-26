import { useRef, useImperativeHandle, forwardRef } from 'react';
import AccountListItem from './AccountListItem'; // Import AccountListItem
import './AccountList.css'; // Import the CSS file
import { Account } from '@/schemas/Account'; // Import Account type

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
    accounts: Account[];
    onEdit: (account: Account) => void;
    onDelete: (accountId: string) => void;
    onViewDetails: (accountId: string) => void; // Add onViewDetails to props
    onViewTransactions: (accountId: string) => void; // Add onViewTransactions to props
}

export interface AccountListRef {
    scrollToAccount: (accountId: string) => void;
}

const AccountList = forwardRef<AccountListRef, AccountListProps>(({ accounts, onEdit, onDelete, onViewDetails, onViewTransactions }, ref) => {
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
                    key={account.accountId}
                    ref={(el) => {
                        if (el) {
                            accountRefs.current[account.accountId] = el;
                        } else {
                            delete accountRefs.current[account.accountId];
                        }
                    }}
                    account={account} // Pass the entire account object
                    onEdit={() => onEdit(account)} // onEdit expects the full account object
                    onDelete={() => onDelete(account.accountId)} // onDelete expects accountId
                    onViewDetails={() => onViewDetails(account.accountId)} // onViewDetails expects accountId
                    onViewTransactions={() => onViewTransactions(account.accountId)} // onViewTransactions expects accountId
                />
            ))}
        </div>
    );
});

export default AccountList;
