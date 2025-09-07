import React from 'react';
import AccountsWithSidebar from '@/new-ui/components/navigation/AccountsWithSidebar';
import { useSessionRouting } from '@/hooks/useSessionRouting';
import './AccountsPage.css';

/**
 * AccountsPage - Route-level page component for the accounts feature
 * 
 * This is a thin container that follows the frontend conventions:
 * - Pages are route-level containers referenced by React Router
 * - Pages should primarily compose business components/views
 * - Minimal direct UI logic - delegate to views and business components
 * 
 * Updated to use the new contextual sidebar navigation pattern with route synchronization.
 * All nested account routes (/accounts, /accounts/:id, /accounts/:id/files/:fileId, etc.)
 * are handled by this single page component with contextual navigation.
 */
const AccountsPage: React.FC = () => {
    // Sync React Router with navigation store using session URL compression
    useSessionRouting();

    return (
        <div className="accounts-page">
            <AccountsWithSidebar />
        </div>
    );
};

export default AccountsPage;
