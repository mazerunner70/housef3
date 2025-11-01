import React from 'react';
import AccountsDashboard from './AccountsDashboard';
import './AccountsPage.css';

/**
 * AccountsPage - Entry point for the accounts domain
 *
 * Role: Routing jump off point that renders main component
 * Route: /accounts
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const AccountsPage: React.FC = () => {
    return (
        <div className="accounts-page">
            <AccountsDashboard />
        </div>
    );
};

export default AccountsPage;
