import React, { useState } from 'react';
import OverallAnalyticsTab from './OverallAnalyticsTab';
import CategoriesAnalyticsTab from '../components/domain/categories/CategoriesAnalyticsTab';
import AccountsAnalyticsTab from '@/components/domain/accounts/views/AccountsAnalyticsTab';
import useAnalytics from '../hooks/useAnalytics';
import './AnalyticsView.css';

type AnalyticsViewTabId = 'OVERALL' | 'CATEGORIES' | 'ACCOUNTS';

const AnalyticsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AnalyticsViewTabId>('OVERALL');
  const analytics = useAnalytics({
    initialFilters: {
      timeRange: '12months'
    },
    autoFetch: true,
    refreshInterval: 5
  });

  const handleExportReport = () => {
    // TODO: Implement export functionality
    alert('Export Analytics - Coming Soon!');
  };

  const handleDateRangeChange = () => {
    // TODO: Implement date range picker
    alert('Date Range Filter - Coming Soon!');
  };

  const handleRefreshAnalytics = async () => {
    try {
      await analytics.refreshAnalytics();
    } catch (error) {
      console.error('Failed to refresh analytics:', error);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'OVERALL':
        return <OverallAnalyticsTab analytics={analytics} />;
      case 'CATEGORIES':
        return <CategoriesAnalyticsTab analytics={analytics} />;
      case 'ACCOUNTS':
        return <AccountsAnalyticsTab analytics={analytics} />;
      default:
        return <p>Please select a tab.</p>;
    }
  };

  return (
    <div className="analytics-view">
      <header className="analytics-view-header">
        <h1>Analytics</h1>

        {/* Data Status Indicator */}
        <div className="analytics-status">
          {analytics.loading && (
            <span className="status-loading">Loading...</span>
          )}
          {analytics.refreshing && (
            <span className="status-refreshing">Refreshing...</span>
          )}
          {analytics.error && (
            <span
              className="status-error"
              onClick={analytics.clearError}
              onKeyDown={(e) => e.key === 'Enter' && analytics.clearError()}
              tabIndex={0}
              role="button"
              aria-label="Dismiss error message"
            >
              ⚠️ {analytics.error} (click to dismiss)
            </span>
          )}
          {analytics.dataFreshness === 'stale' && (
            <span className="status-stale">Data may be outdated</span>
          )}
          {analytics.lastUpdated && !analytics.loading && !analytics.error && (
            <span className="status-fresh">
              Updated {analytics.formatDate(analytics.lastUpdated)}
            </span>
          )}
        </div>

        <div className="analytics-view-actions">
          <button
            className="analytics-action-button"
            onClick={handleRefreshAnalytics}
            disabled={analytics.refreshing}
          >
            🔄 {analytics.refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <button className="analytics-action-button" onClick={handleExportReport}>
            📊 Export Report
          </button>
          <button className="analytics-action-button" onClick={handleDateRangeChange}>
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