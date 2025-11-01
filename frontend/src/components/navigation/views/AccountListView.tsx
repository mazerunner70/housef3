import React from 'react';
import { useNavigate } from 'react-router-dom';
import AccountList from '@/components/domain/accounts/components/AccountList';
import AccountTimeline from '@/components/domain/accounts/components/AccountTimeline';
import useAccountsWithStore from '@/components/domain/accounts/stores/useAccountsStore';
import { useNavigationStore } from '@/stores/navigationStore';
import './AccountListView.css';

const AccountListView: React.FC = () => {
    const navigate = useNavigate();
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

    const handleEditAccount = (account: { accountId: string;[key: string]: unknown }) => {
        // Navigate to account edit page
        navigate(`/accounts/${account.accountId}?action=edit`);
    };

    const handleDeleteAccount = (accountId: string) => {
        // Navigate to account delete confirmation page
        navigate(`/accounts/${accountId}?action=delete`);
    };

    const handleViewTransactions = (accountId: string) => {
        // Navigate to transactions page for this account
        navigate(`/transactions?account=${accountId}`);
    };

    const handleTimelineAccountClick = (accountId: string) => {
        // Scroll to account in the list or navigate to account detail
        const accountElement = document.getElementById(`account-${accountId}`);
        if (accountElement) {
            accountElement.scrollIntoView({ behavior: 'smooth' });
        } else {
            navigate(`/accounts/${accountId}`);
        }
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
                    {accounts.length} account{accounts.length === 1 ? '' : 's'} total
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
