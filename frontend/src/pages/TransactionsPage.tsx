import React from 'react';
import TransactionsList from '@/components/domain/transactions/TransactionsList';
import './TransactionsPage.css';

/**
 * TransactionsPage - Entry point for the transactions domain
 * 
 * Role: Routing jump off point that renders transactions list
 * Route: /transactions
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const TransactionsPage: React.FC = () => {
    return (
        <div className="transactions-page">
            <TransactionsList />
        </div>
    );
};

export default TransactionsPage;
