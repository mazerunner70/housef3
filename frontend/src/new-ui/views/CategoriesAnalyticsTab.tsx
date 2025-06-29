import React, { useState } from 'react';
import { AnalyticsHookResult } from '../hooks/useAnalytics';

interface CategoriesAnalyticsTabProps {
  analytics: AnalyticsHookResult;
}

const CategoriesAnalyticsTab: React.FC<CategoriesAnalyticsTabProps> = ({ analytics }) => {
  const { categories, formatCurrency, formatPercentage, filters, setFilters } = analytics;
  const [selectedPeriod, setSelectedPeriod] = useState(filters.timeRange);

  // Calculate total for percentages
  const totalAmount = categories?.categories.reduce((sum, cat) => sum + cat.totalAmount, 0) || 0;

  // Transform category data for display
  const categoryData = categories?.categories.map(cat => ({
    name: cat.categoryName,
    amount: cat.totalAmount,
    percentage: totalAmount > 0 ? ((cat.totalAmount / totalAmount) * 100) : 0,
    transactions: cat.transactionCount,
    trend: cat.trend === 'increasing' ? `+${cat.growthRate.toFixed(1)}%` : 
           cat.trend === 'decreasing' ? `-${cat.growthRate.toFixed(1)}%` : 
           `${cat.growthRate.toFixed(1)}%`
  })) || [];

  return (
    <div className="categories-analytics-tab">
      {/* Period Selector */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Category Spending Analysis</h3>
          <select 
            value={selectedPeriod} 
            onChange={(e) => {
              const newTimeRange = e.target.value as any;
              setSelectedPeriod(newTimeRange);
              setFilters({ timeRange: newTimeRange });
            }}
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
          {analytics.loading ? (
            <>
              🔄 Loading category breakdown...
              <br />
              <small>Analyzing your spending by category</small>
            </>
          ) : categoryData.length > 0 ? (
            <>
              🥧 Category data available for {categoryData.length} categories
              <br />
              <small>Chart visualization coming soon - data is ready for display</small>
            </>
          ) : (
            <>
              📊 No category data available yet
              <br />
              <small>Upload transaction files to see your spending breakdown</small>
            </>
          )}
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
          <div className="analytics-metric negative">
            {categoryData.length > 0 ? formatCurrency(categoryData[0].amount) : formatCurrency(0)}
          </div>
          <small>
            {categoryData.length > 0 ? `${categoryData[0].name} (${categoryData[0].percentage.toFixed(1)}%)` : 'No data'}
          </small>
        </div>
        
        <div className="analytics-card">
          <h3>Fastest Growing</h3>
          <div className="analytics-metric positive">
            {categoryData.length > 0 ? 
              categoryData.find(cat => cat.trend.startsWith('+'))?.trend || 'N/A' : 
              'N/A'
            }
          </div>
          <small>
            {categoryData.length > 0 ? 
              categoryData.find(cat => cat.trend.startsWith('+'))?.name || 'No growth trends' :
              'No data'
            }
          </small>
        </div>
        
        <div className="analytics-card">
          <h3>Most Transactions</h3>
          <div className="analytics-metric">
            {categoryData.length > 0 ? 
              Math.max(...categoryData.map(cat => cat.transactions)) : 
              0
            }
          </div>
          <small>
            {categoryData.length > 0 ? 
              categoryData.find(cat => cat.transactions === Math.max(...categoryData.map(c => c.transactions)))?.name || 'No data' :
              'No data'
            }
          </small>
        </div>
        
        <div className="analytics-card">
          <h3>Average per Category</h3>
          <div className="analytics-metric">
            {categoryData.length > 0 ? formatCurrency(totalAmount / categoryData.length) : formatCurrency(0)}
          </div>
          <small>Across {categoryData.length} categories</small>
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