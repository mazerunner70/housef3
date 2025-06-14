import React, { useState } from 'react';

const CategoriesAnalyticsTab: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('12months');

  // Mock category data
  const categoryData = [
    { name: 'Food & Dining', amount: 3456.78, percentage: 27.8, transactions: 89, trend: '+5.2%' },
    { name: 'Transportation', amount: 2234.56, percentage: 17.9, transactions: 34, trend: '-2.1%' },
    { name: 'Shopping', amount: 1899.34, percentage: 15.3, transactions: 45, trend: '+12.4%' },
    { name: 'Bills & Utilities', amount: 1567.89, percentage: 12.6, transactions: 12, trend: '+1.1%' },
    { name: 'Entertainment', amount: 1234.50, percentage: 9.9, transactions: 28, trend: '+8.7%' },
    { name: 'Healthcare', amount: 987.65, percentage: 7.9, transactions: 15, trend: '-1.2%' },
    { name: 'Other', amount: 1076.06, percentage: 8.6, transactions: 23, trend: '+3.4%' }
  ];

  return (
    <div className="categories-analytics-tab">
      {/* Period Selector */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Category Spending Analysis</h3>
          <select 
            value={selectedPeriod} 
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="analytics-chart-filter"
          >
            <option value="1month">Last Month</option>
            <option value="3months">Last 3 Months</option>
            <option value="6months">Last 6 Months</option>
            <option value="12months">Last 12 Months</option>
          </select>
        </div>
        
        {/* Category Pie Chart Placeholder */}
        <div className="analytics-placeholder">
          🥧 Category spending pie chart will be displayed here
          <br />
          <small>Visual breakdown of spending by category</small>
        </div>
      </div>

      {/* Category Breakdown Table */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Category Breakdown</h3>
        </div>
        
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #dee2e6' }}>
              <th style={{ textAlign: 'left', padding: '12px 8px', fontWeight: 600 }}>Category</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Amount</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>% of Total</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Transactions</th>
              <th style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 600 }}>Trend</th>
            </tr>
          </thead>
          <tbody>
            {categoryData.map((category, index) => (
              <tr key={index} style={{ borderBottom: '1px solid #e9ecef' }}>
                <td style={{ padding: '12px 8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div 
                      style={{ 
                        width: '12px', 
                        height: '12px', 
                        borderRadius: '50%', 
                        backgroundColor: `hsl(${index * 50}, 70%, 60%)` 
                      }}
                    ></div>
                    {category.name}
                  </div>
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px', fontWeight: 500 }}>
                  ${category.amount.toFixed(2)}
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px' }}>
                  {category.percentage}%
                </td>
                <td style={{ textAlign: 'right', padding: '12px 8px' }}>
                  {category.transactions}
                </td>
                <td style={{ 
                  textAlign: 'right', 
                  padding: '12px 8px',
                  color: category.trend.startsWith('+') ? '#28a745' : '#dc3545',
                  fontWeight: 500
                }}>
                  {category.trend}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Category Trends Over Time */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Category Trends Over Time</h3>
        </div>
        <div className="analytics-placeholder">
          📈 Category spending trends chart will be displayed here
          <br />
          <small>Line chart showing how each category's spending changes over time</small>
        </div>
      </div>

      {/* Top Categories Analysis */}
      <div className="analytics-overview-grid">
        <div className="analytics-card">
          <h3>Highest Category</h3>
          <div className="analytics-metric negative">$3,456.78</div>
          <small>Food & Dining (27.8%)</small>
        </div>
        
        <div className="analytics-card">
          <h3>Fastest Growing</h3>
          <div className="analytics-metric positive">+12.4%</div>
          <small>Shopping category</small>
        </div>
        
        <div className="analytics-card">
          <h3>Most Transactions</h3>
          <div className="analytics-metric">89</div>
          <small>Food & Dining</small>
        </div>
        
        <div className="analytics-card">
          <h3>Average per Category</h3>
          <div className="analytics-metric">$1,779.54</div>
          <small>Across all categories</small>
        </div>
      </div>

      {/* Budget vs Actual (Future Feature) */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Budget vs Actual Spending</h3>
        </div>
        <div className="analytics-placeholder">
          📊 Budget comparison chart will be displayed here
          <br />
          <small>Compare actual spending against budget targets by category</small>
        </div>
      </div>
    </div>
  );
};

export default CategoriesAnalyticsTab; 