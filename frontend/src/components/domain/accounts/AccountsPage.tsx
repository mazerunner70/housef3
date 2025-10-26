import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import AccountsDashboard from './AccountsDashboard';
import './AccountsPage.css';

/**
 * AccountsPage - Entry point for the accounts domain
 *
 * Role: Routing jump off point that sets up context and renders main component
 * Route: /accounts
 */
const AccountsPage: React.FC = () => {
    const { goToAccountList } = useNavigationStore();

    // Set up breadcrumbs/navigation context
    useEffect(() => {
        goToAccountList();
    }, [goToAccountList]);

    return (
        <div className="accounts-page">
            <AccountsDashboard />
        </div>
    );
};

export default AccountsPage;
