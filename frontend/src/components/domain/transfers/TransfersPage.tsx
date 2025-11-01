import React from 'react';
import TransfersDashboard from './TransfersDashboard';
import './TransfersPage.css';

/**
 * TransfersPage - Entry point for the transfers domain
 * 
 * Role: Routing jump off point that renders main component
 * Route: /transfers
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const TransfersPage: React.FC = () => {
    return (
        <div className="transfers-page">
            <TransfersDashboard />
        </div>
    );
};

export default TransfersPage;
