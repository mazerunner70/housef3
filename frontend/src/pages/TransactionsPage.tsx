import React from 'react';
import TransactionsDashboard from '@/components/domain/transactions/TransactionsDashboard';
import './TransactionsPage.css';

/**
 * TransactionsPage - Entry point for the transactions domain
 * 
 * Role: Routing jump off point that renders main component
 * Route: /transactions
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const TransactionsPage: React.FC = () => {
    return (
        <div className="transactions-page">
            <TransactionsDashboard />
        </div>
    );
};

export default TransactionsPage;
