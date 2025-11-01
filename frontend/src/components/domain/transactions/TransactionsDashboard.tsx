import React, { useState } from 'react';
import TransactionsListTab from './TransactionsListTab';
import CategoriesDashboard from '@/components/domain/categories/CategoriesDashboard';
import ImportDashboard from '@/components/domain/import/ImportDashboard';
import TransfersDashboard from '@/components/domain/transfers/TransfersDashboard';
import './TransactionsDashboard.css';

type TransactionPageTabId = 'TRANSACTIONS_LIST' | 'CATEGORY_MANAGEMENT' | 'STATEMENTS_IMPORTS' | 'TRANSFERS';

/**
 * TransactionsDashboard - Main dashboard for transactions domain
 * 
 * Provides tabbed interface for:
 * - Transactions List
 * - Category Management
 * - Statements & Imports
 * - Transfers
 * 
 * Note: This component is rendered within NewUILayout, so page title/breadcrumbs
 * are handled by the layout component.
 */
const TransactionsDashboard: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TransactionPageTabId>('TRANSACTIONS_LIST');

    const renderTabContent = () => {
        switch (activeTab) {
            case 'TRANSACTIONS_LIST':
                return <TransactionsListTab />;
            case 'CATEGORY_MANAGEMENT':
                return <CategoriesDashboard />;
            case 'STATEMENTS_IMPORTS':
                return <ImportDashboard />;
            case 'TRANSFERS':
                return <TransfersDashboard />;
            default:
                return <p>Please select a tab.</p>;
        }
    };

    return (
        <div className="transactions-dashboard">
            <div className="transactions-dashboard-header">
                <h1>Transactions</h1>
                <button
                    className="add-transaction-button-global"
                    onClick={() => alert('Add Transaction Clicked!')}
                    aria-label="Add new transaction"
                >
                    ➕ Add Transaction
                </button>
            </div>

            <div className="transactions-dashboard-tabs">
                <button
                    className={`tab-button ${activeTab === 'TRANSACTIONS_LIST' ? 'active' : ''}`}
                    onClick={() => setActiveTab('TRANSACTIONS_LIST')}
                >
                    Transactions List
                </button>
                <button
                    className={`tab-button ${activeTab === 'CATEGORY_MANAGEMENT' ? 'active' : ''}`}
                    onClick={() => setActiveTab('CATEGORY_MANAGEMENT')}
                >
                    Category Management
                </button>
                <button
                    className={`tab-button ${activeTab === 'STATEMENTS_IMPORTS' ? 'active' : ''}`}
                    onClick={() => setActiveTab('STATEMENTS_IMPORTS')}
                >
                    Statements & Imports
                </button>
                <button
                    className={`tab-button ${activeTab === 'TRANSFERS' ? 'active' : ''}`}
                    onClick={() => setActiveTab('TRANSFERS')}
                >
                    Transfers
                </button>
            </div>

            <div className="transactions-tab-content">
                {renderTabContent()}
            </div>
        </div>
    );
};

export default TransactionsDashboard;

