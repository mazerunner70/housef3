import React from 'react';
import AccountsView from '../views/AccountsView';
import './AccountsPage.css';

/**
 * AccountsPage - Route-level page component for the accounts feature
 * 
 * This is a thin container that follows the frontend conventions:
 * - Pages are route-level containers referenced by React Router
 * - Pages should primarily compose business components/views
 * - Minimal direct UI logic - delegate to views and business components
 */
const AccountsPage: React.FC = () => {
    return (
        <div className="accounts-page">
            <AccountsView />
        </div>
    );
};

export default AccountsPage;
