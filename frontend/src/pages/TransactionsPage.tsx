import React, { useState } from 'react';
import TransactionsListTab from '@/components/domain/transactions/TransactionsListTab';
import CategoriesDashboard from '@/components/domain/categories/CategoriesDashboard';
import ImportDashboard from '@/components/domain/import/ImportDashboard';
import TransfersDashboard from '@/components/domain/transfers/TransfersDashboard';
import './TransactionsPage.css'; // Main CSS file for the page, should contain tab styles

type TransactionPageTabId = 'TRANSACTIONS_LIST' | 'CATEGORY_MANAGEMENT' | 'STATEMENTS_IMPORTS' | 'TRANSFERS';

const TransactionsPage: React.FC = () => {
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
                // Should not happen with defined types, but good practice for a default
                return <p>Please select a tab.</p>;
        }
    };

    return (
        // Using class names that should align with your existing TransactionsPage.css
        <div className="transactions-page"> {/* Overall container for the entire page */}
            <header className="transactions-page-header">
                <h1>Transactions</h1>
                {/* 
          As per docs (section 2), the "[+ Add Transaction]" button 
          should be globally accessible here, outside the tabs.
          You might need to implement a modal for this or navigate to a form.
          Example placeholder button:
        */}
                <button className="add-transaction-button-global" onClick={() => alert('Add Transaction Clicked!')}>
                    <span role="img" aria-label="add">➕</span> Add Transaction
                </button>
            </header>

            <div className="transactions-page-tabs"> {/* Container for tab buttons */}
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

            <div className="transactions-tab-content"> {/* Area to render the active tab's content */}
                {renderTabContent()}
            </div>
        </div>
    );
};

export default TransactionsPage;
