import React from 'react';
import ImportTransactionsView from '@/views/ImportTransactionsView';

/**
 * ImportTransactionsPage - Route-level page component for the transaction import feature
 * 
 * This is a thin container that follows the frontend conventions:
 * - Pages are route-level containers referenced by React Router
 * - Pages should primarily compose business components/views
 * - Minimal logic - delegates to view component
 */
const ImportTransactionsPage: React.FC = () => {
    return <ImportTransactionsView />;
};

export default ImportTransactionsPage;
