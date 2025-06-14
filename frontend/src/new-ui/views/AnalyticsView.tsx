import React, { useState } from 'react';
import OverallAnalyticsTab from './OverallAnalyticsTab';
import CategoriesAnalyticsTab from './CategoriesAnalyticsTab';
import AccountsAnalyticsTab from './AccountsAnalyticsTab';
import './AnalyticsView.css';

type AnalyticsViewTabId = 'OVERALL' | 'CATEGORIES' | 'ACCOUNTS';

const AnalyticsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AnalyticsViewTabId>('OVERALL');

  const renderTabContent = () => {
    switch (activeTab) {
      case 'OVERALL':
        return <OverallAnalyticsTab />;
      case 'CATEGORIES':
        return <CategoriesAnalyticsTab />;
      case 'ACCOUNTS':
        return <AccountsAnalyticsTab />;
      default:
        return <p>Please select a tab.</p>;
    }
  };

  return (
    <div className="analytics-view">
      <header className="analytics-view-header">
        <h1>Analytics</h1>
        <div className="analytics-view-actions">
          <button className="analytics-action-button" onClick={() => alert('Export Analytics - Coming Soon!')}>
            📊 Export Report
          </button>
          <button className="analytics-action-button" onClick={() => alert('Date Range Filter - Coming Soon!')}>
            📅 Date Range
          </button>
        </div>
      </header>

      <div className="analytics-view-tabs">
        <button
          className={`tab-button ${activeTab === 'OVERALL' ? 'active' : ''}`}
          onClick={() => setActiveTab('OVERALL')}
        >
          Overall
        </button>
        <button
          className={`tab-button ${activeTab === 'CATEGORIES' ? 'active' : ''}`}
          onClick={() => setActiveTab('CATEGORIES')}
        >
          Categories
        </button>
        <button
          className={`tab-button ${activeTab === 'ACCOUNTS' ? 'active' : ''}`}
          onClick={() => setActiveTab('ACCOUNTS')}
        >
          Accounts
        </button>
      </div>

      <div className="analytics-tab-content">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default AnalyticsView; 