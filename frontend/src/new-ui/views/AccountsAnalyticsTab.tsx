import React, { useState } from 'react';
import { AnalyticsHookResult } from '../hooks/useAnalytics';

interface AccountsAnalyticsTabProps {
  analytics: AnalyticsHookResult;
}

const AccountsAnalyticsTab: React.FC<AccountsAnalyticsTabProps> = ({ analytics }) => {
  const { accounts, formatCurrency, filters, setFilters } = analytics;
  const [selectedView, setSelectedView] = useState('spending');

  // Transform account data for display
  const accountData = accounts?.accounts.map(acc => ({
    name: acc.accountName,
    type: acc.accountType,
    spending: acc.totalSpending,
    transactions: acc.transactionCount,
    avgTransaction: acc.avgTransactionAmount,
    balance: acc.currentBalance || 0,
    utilizationRate: acc.utilizationRate,
    trend: acc.trend
  })) || [];

  const creditCards = accountData.filter(acc => acc.type === 'Credit Card');
  const otherAccounts = accountData.filter(acc => acc.type !== 'Credit Card');

  return (
    <div className="accounts-analytics-tab">
      {/* View Selector */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Account Analysis</h3>
          <select 
            value={selectedView} 
            onChange={(e) => setSelectedView(e.target.value)}
            className="analytics-chart-filter"
          >
            <option value="spending">Spending Analysis</option>
            <option value="balances">Balance Overview</option>
            <option value="utilization">Credit Utilization</option>
          </select>
        </div>
        
        {/* Account Comparison Chart */}
        <div className="analytics-placeholder">
          {analytics.loading ? (
            <>
              🔄 Loading account analysis...
              <br />
              <small>Analyzing your account performance</small>
            </>
          ) : accountData.length > 0 ? (
            <>
              📊 Account data available for {accountData.length} accounts
              <br />
              <small>Chart visualization coming soon - data is ready for display</small>
            </>
          ) : (
            <>
              🏦 No account data available yet
              <br />
              <small>Upload transaction files to see your account analysis</small>
            </>
          )}
        </div>
      </div>

      {/* Account Summary Cards */}
      <div className="analytics-overview-grid">
        <div className="analytics-card">
          <h3>Total Accounts</h3>
          <div className="analytics-metric">{accountData.length}</div>
          <small>{creditCards.length} Credit Cards, {otherAccounts.length} Others</small>
        </div>
        
        <div className="analytics-card">
          <h3>Total Spending</h3>
          <div className="analytics-metric negative">
            ${accountData.reduce((sum, acc) => sum + acc.spending, 0).toFixed(2)}
          </div>
          <small>Across all accounts</small>
        </div>
        
        <div className="analytics-card">
          <h3>Most Active Account</h3>
          <div className="analytics-metric">{accountData[0].transactions}</div>
          <small>{accountData[0].name}</small>
        </div>
        
        <div className="analytics-card">
          <h3>Avg Credit Utilization</h3>
          <div className="analytics-metric">
            {(creditCards.reduce((sum, acc) => sum + (acc.utilizationRate || 0), 0) / creditCards.length).toFixed(1)}%
          </div>
          <small>Credit cards only</small>
        </div>
      </div>

      {/* Detailed Account Breakdown */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Account Details</h3>
        </div>
        
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #dee2e6' }}>
              <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Account</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Type</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Spending</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Transactions</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Balance</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Utilization</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Trend</th>
            </tr>
          </thead>
          <tbody>
            {accountData.map((account, index) => (
              <tr key={index} style={{ borderBottom: '1px solid #e9ecef' }}>
                <td style={{ padding: '12px 8px' }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{account.name}</div>
                    <small style={{ color: '#6c757d' }}>Avg: ${account.avgTransaction.toFixed(2)}</small>
                  </div>
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px' }}>
                  <span style={{ 
                    padding: '4px 8px', 
                    borderRadius: '12px', 
                    fontSize: '0.8em',
                    backgroundColor: account.type === 'Credit Card' ? '#e3f2fd' : '#f3e5f5',
                    color: account.type === 'Credit Card' ? '#1976d2' : '#7b1fa2'
                  }}>
                    {account.type}
                  </span>
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 500 }}>
                  ${account.spending.toFixed(2)}
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px' }}>
                  {account.transactions}
                </td>
                <td style={{ 
                  textAlign: 'right', 
                  padding: '12px 8px', 
                  fontWeight: 500,
                  color: account.balance >= 0 ? '#28a745' : '#dc3545'
                }}>
                  ${account.balance.toFixed(2)}
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px' }}>
                  {account.utilizationRate ? `${account.utilizationRate}%` : 'N/A'}
                </td>
                <td style={{ 
                  textAlign: 'right', 
                  padding: '12px 8px',
                  color: account.trend.startsWith('+') ? '#28a745' : '#dc3545',
                  fontWeight: 500
                }}>
                  {account.trend}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Credit Card Specific Analysis */}
      {creditCards.length > 0 && (
        <div className="analytics-chart-container">
          <div className="analytics-chart-header">
            <h3 className="analytics-chart-title">Credit Card Health</h3>
          </div>
          
          <div className="analytics-overview-grid">
            {creditCards.map((card, index) => (
              <div key={index} className="analytics-card">
                <h4>{card.name}</h4>
                <div className="analytics-metric" style={{ fontSize: '1.5em' }}>
                  {card.utilizationRate}%
                </div>
                <small>Utilization Rate</small>
                <div style={{ marginTop: '10px', fontSize: '0.9em' }}>
                  <div>Balance: <span style={{ color: '#dc3545', fontWeight: 500 }}>${Math.abs(card.balance).toFixed(2)}</span></div>
                  <div>Transactions: {card.transactions}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Account Performance Trends */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Account Performance Over Time</h3>
        </div>
        <div className="analytics-placeholder">
          📈 Account performance trends chart will be displayed here
          <br />
          <small>Track spending patterns and balance changes by account over time</small>
        </div>
      </div>

      {/* Account Usage Patterns */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Account Usage Patterns</h3>
        </div>
        <div className="analytics-placeholder">
          🔄 Account usage frequency chart will be displayed here
          <br />
          <small>Shows which accounts are used most frequently and for what purposes</small>
        </div>
      </div>
    </div>
  );
};

export default AccountsAnalyticsTab; 