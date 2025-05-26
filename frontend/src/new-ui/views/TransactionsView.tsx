import React, { useState } from 'react';
import TransactionsListTab from './TransactionsListTab';
import CategoryManagementTab from './CategoryManagementTab';
import StatementsImportsTab from './StatementsImportsTab';
import './TransactionsView.css'; // Main CSS file for the view, should contain tab styles

type TransactionViewTabId = 'TRANSACTIONS_LIST' | 'CATEGORY_MANAGEMENT' | 'STATEMENTS_IMPORTS';

const TransactionsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TransactionViewTabId>('TRANSACTIONS_LIST');

  const renderTabContent = () => {
    switch (activeTab) {
      case 'TRANSACTIONS_LIST':
        return <TransactionsListTab />;
      case 'CATEGORY_MANAGEMENT':
        return <CategoryManagementTab />;
      case 'STATEMENTS_IMPORTS':
        return <StatementsImportsTab />;
      default:
        // Should not happen with defined types, but good practice for a default
        return <p>Please select a tab.</p>; 
    }
  };

  return (
    // Using class names that should align with your existing TransactionsView.css
    <div className="transactions-view"> {/* Overall container for the entire view */} 
      <header className="transactions-view-header">
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

      <div className="transactions-view-tabs"> {/* Container for tab buttons */} 
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
      </div>

      <div className="transactions-tab-content"> {/* Area to render the active tab's content */} 
        {renderTabContent()}
      </div>
    </div>
  );
};

export default TransactionsView; 