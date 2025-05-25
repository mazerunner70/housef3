import React, { useState } from 'react';
import './TransactionsView.css';

// Placeholder for a potential future Modal component
// For now, we can use alerts or simple divs
const ModalPlaceholder: React.FC<{ title: string; onClose: () => void; children: React.ReactNode }> = ({ title, onClose, children }) => {
  return (
    <div className="modal-backdrop-placeholder">
      <div className="modal-content-placeholder">
        <h2>{title}</h2>
        {children}
        <button onClick={onClose} className="modal-close-button">
          <span role="img" aria-label="close">❌</span> Close
        </button>
      </div>
    </div>
  );
};

type TransactionTab = 'TRANSACTIONS_LIST' | 'CATEGORY_MANAGEMENT' | 'STATEMENTS_IMPORTS';

const TransactionsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TransactionTab>('TRANSACTIONS_LIST');
  const [showAddTransactionModal, setShowAddTransactionModal] = useState(false);
  const [showImportStatementModal, setShowImportStatementModal] = useState(false);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'TRANSACTIONS_LIST':
        return (
          <div className="tab-content-container">
            {/* Section 3.1 Filtering and Search Controls will go here */}
            {/* Section 3.2 Transaction Table will go here */}
            {/* Section 3.4 Bulk Actions Bar will go here (conditionally) */}
            <p>Transaction list, filters, and editing dialogs will appear here.</p>
            <p>This tab will fulfill section 3 of the design document.</p>
          </div>
        );
      case 'CATEGORY_MANAGEMENT':
        return (
          <div className="tab-content-container">
            <p>Category management, including regex rules, will appear here.</p>
            <p>This tab will fulfill section 4 of the design document.</p>
          </div>
        );
      case 'STATEMENTS_IMPORTS':
        return (
          <div className="tab-content-container">
            <p>Statement import workflow and history will appear here.</p>
            <p>This tab will fulfill section 5 of the design document.</p>
            <button 
              className="action-button import-statement-button-tab"
              onClick={() => setShowImportStatementModal(true)}
            >
              <span role="img" aria-label="import">📥</span> Initiate Import
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="transactions-view-container">
      <header className="transactions-view-header">
        <h1>Transactions</h1>
        <button 
          className="action-button add-transaction-button-global"
          onClick={() => setShowAddTransactionModal(true)}
        >
          <span role="img" aria-label="add">➕</span> Add Transaction
        </button>
      </header>

      <nav className="transactions-view-tabs">
        <button 
          className={`tab-button ${activeTab === 'TRANSACTIONS_LIST' ? 'active' : ''}`}
          onClick={() => setActiveTab('TRANSACTIONS_LIST')}
        >
          <span role="img" aria-label="list">📋</span> Transactions List
        </button>
        <button 
          className={`tab-button ${activeTab === 'CATEGORY_MANAGEMENT' ? 'active' : ''}`}
          onClick={() => setActiveTab('CATEGORY_MANAGEMENT')}
        >
          <span role="img" aria-label="categories">🏷️</span> Category Management
        </button>
        <button 
          className={`tab-button ${activeTab === 'STATEMENTS_IMPORTS' ? 'active' : ''}`}
          onClick={() => setActiveTab('STATEMENTS_IMPORTS')}
        >
          <span role="img" aria-label="statements">📄</span> Statements & Imports
        </button>
      </nav>

      <div className="transactions-tab-content">
        {renderTabContent()}
      </div>

      {showAddTransactionModal && (
        <ModalPlaceholder title="Add New Transaction" onClose={() => setShowAddTransactionModal(false)}>
          <p>Form for adding a new transaction will be here.</p>
          {/* Future: <AddTransactionForm onSubmit={...} onCancel={...} /> */}
        </ModalPlaceholder>
      )}

      {showImportStatementModal && (
        <ModalPlaceholder title="Import Statement - Step 1: Upload" onClose={() => setShowImportStatementModal(false)}>
          <p>File upload (drag & drop, file selector) and account selection will be here.</p>
          <p>This is the entry point for Section 4 (File Management: Import Workflow).</p>
          {/* Future: <ImportStep1 onNext={...} onCancel={...} /> */}
        </ModalPlaceholder>
      )}

    </div>
  );
};

export default TransactionsView; 