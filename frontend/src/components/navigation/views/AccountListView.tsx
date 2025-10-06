import React from 'react';
import AccountList from '@/components/accounts/AccountList';
import AccountTimeline from '@/components/accounts/AccountTimeline';
import useAccountsWithStore from '@/stores/useAccountsStore';
import { useNavigationStore } from '@/stores/navigationStore';
import './AccountListView.css';

const AccountListView: React.FC = () => {
    const {
        accounts,
        isLoading,
        error,
        clearError
    } = useAccountsWithStore();

    const { selectAccount } = useNavigationStore();

    const handleViewAccountDetails = (accountId: string) => {
        const account = accounts.find(acc => acc.accountId === accountId);
        if (account) {
            selectAccount(account);
        }
    };

    const handleEditAccount = (account: any) => {
        // TODO: Implement edit account functionality
        console.log('Edit account:', account);
    };

    const handleDeleteAccount = (accountId: string) => {
        // TODO: Implement delete account functionality
        console.log('Delete account:', accountId);
    };

    const handleViewTransactions = (accountId: string) => {
        // TODO: Implement view transactions functionality
        console.log('View transactions for account:', accountId);
    };

    const handleTimelineAccountClick = (accountId: string) => {
        // TODO: Implement timeline account click (scroll to account)
        console.log('Timeline account click:', accountId);
    };

    if (isLoading) {
        return (
            <div className="account-list-view">
                <div className="loading-state">
                    <p>Loading accounts...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="account-list-view">
                <div className="error-state">
                    <div className="error-content">
                        <div className="error-icon">⚠️</div>
                        <div className="error-details">
                            <h4>Unable to Load Accounts</h4>
                            <p>{error}</p>
                        </div>
                    </div>
                    <button onClick={clearError} className="clear-error-button">
                        Dismiss
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="account-list-view">
            <div className="account-list-header">
                <h1>My Accounts</h1>
                <p className="account-summary">
                    {accounts.length} account{accounts.length !== 1 ? 's' : ''} total
                </p>
            </div>

            {accounts.length > 0 && (
                <div className="accounts-content">
                    <div className="timeline-section">
                        <h2>Account Timeline</h2>
                        <AccountTimeline
                            accounts={accounts}
                            onAccountClick={handleTimelineAccountClick}
                        />
                    </div>

                    <div className="accounts-list-section">
                        <h2>Account Details</h2>
                        <AccountList
                            accounts={accounts}
                            onEdit={handleEditAccount}
                            onDelete={handleDeleteAccount}
                            onViewDetails={handleViewAccountDetails}
                            onViewTransactions={handleViewTransactions}
                        />
                    </div>
                </div>
            )}

            {accounts.length === 0 && (
                <div className="empty-state">
                    <div className="empty-icon">🏦</div>
                    <h3>No Accounts Found</h3>
                    <p>Get started by adding your first account.</p>
                    <button className="add-account-button">
                        Add New Account
                    </button>
                </div>
            )}
        </div>
    );
};

export default AccountListView;
