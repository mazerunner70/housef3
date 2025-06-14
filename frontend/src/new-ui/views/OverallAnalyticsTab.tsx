import React from 'react';

const OverallAnalyticsTab: React.FC = () => {
  return (
    <div className="overall-analytics-tab">
      {/* Key Metrics Overview */}
      <div className="analytics-overview-grid">
        <div className="analytics-card">
          <h3>Total Annual Spending</h3>
          <div className="analytics-metric">$12,456.78</div>
          <small>This year</small>
        </div>
        
        <div className="analytics-card">
          <h3>Average Monthly Spending</h3>
          <div className="analytics-metric">$1,038.07</div>
          <small>Per month</small>
        </div>
        
        <div className="analytics-card">
          <h3>Transaction Count</h3>
          <div className="analytics-metric">324</div>
          <small>Total transactions</small>
        </div>
        
        <div className="analytics-card">
          <h3>Average Transaction</h3>
          <div className="analytics-metric">$38.46</div>
          <small>Per transaction</small>
        </div>
      </div>

      {/* Monthly Spending Trend Chart */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Monthly Spending Trends</h3>
          <select className="analytics-chart-filter">
            <option>Last 12 Months</option>
            <option>This Year</option>
            <option>Last Year</option>
          </select>
        </div>
        <div className="analytics-placeholder">
          📈 Monthly spending trend chart will be displayed here
          <br />
          <small>Line chart showing spending patterns over time</small>
        </div>
      </div>

      {/* Spending Distribution */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Spending vs Income Comparison</h3>
        </div>
        <div className="analytics-placeholder">
          📊 Spending vs Income bar chart will be displayed here
          <br />
          <small>Monthly comparison of spending and income trends</small>
        </div>
      </div>

      {/* Recent Spending Highlights */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Recent Highlights</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
          <div className="analytics-card">
            <h4>Largest Transaction</h4>
            <div className="analytics-metric negative">$456.78</div>
            <small>Electronics Store - Dec 15</small>
          </div>
          
          <div className="analytics-card">
            <h4>Most Active Day</h4>
            <div className="analytics-metric">$289.45</div>
            <small>Dec 22 - 7 transactions</small>
          </div>
          
          <div className="analytics-card">
            <h4>Top Merchant</h4>
            <div className="analytics-metric">$789.12</div>
            <small>Grocery Store - 23 visits</small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OverallAnalyticsTab; 