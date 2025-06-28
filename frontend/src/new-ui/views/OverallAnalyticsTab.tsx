import React from 'react';
import { AnalyticsHookResult } from '../hooks/useAnalytics';

interface OverallAnalyticsTabProps {
  analytics: AnalyticsHookResult;
}

const OverallAnalyticsTab: React.FC<OverallAnalyticsTabProps> = ({ analytics }) => {
  const { overview, formatCurrency } = analytics;
  const { cashFlow, financialHealth } = overview;
  return (
    <div className="overall-analytics-tab">
      {/* Key Metrics Overview */}
      <div className="analytics-overview-grid">
        <div className="analytics-card">
          <h3>Total Income</h3>
          <div className="analytics-metric positive">
            {cashFlow ? formatCurrency(cashFlow.totalIncome) : formatCurrency(0)}
          </div>
          <small>This period</small>
        </div>
        
        <div className="analytics-card">
          <h3>Total Expenses</h3>
          <div className="analytics-metric negative">
            {cashFlow ? formatCurrency(cashFlow.totalExpenses) : formatCurrency(0)}
          </div>
          <small>This period</small>
        </div>
        
        <div className="analytics-card">
          <h3>Net Cash Flow</h3>
          <div className={`analytics-metric ${cashFlow && cashFlow.netCashFlow >= 0 ? 'positive' : 'negative'}`}>
            {cashFlow ? formatCurrency(cashFlow.netCashFlow) : formatCurrency(0)}
          </div>
          <small>Income - Expenses</small>
        </div>
        
        <div className="analytics-card">
          <h3>Financial Health Score</h3>
          <div className="analytics-metric">
            {financialHealth ? Math.round(financialHealth.overallScore) : 0}/100
          </div>
          <small>Overall wellness</small>
        </div>
      </div>

      {/* Monthly Cash Flow Trend Chart */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Monthly Cash Flow Trends</h3>
          <select className="analytics-chart-filter" onChange={(e) => {
            const newTimeRange = e.target.value as any;
            analytics.setFilters({ timeRange: newTimeRange });
          }}>
            <option value="3months">Last 3 Months</option>
            <option value="6months">Last 6 Months</option>
            <option value="12months" selected>Last 12 Months</option>
          </select>
        </div>
        <div className="analytics-placeholder">
          {analytics.loading ? (
            <>
              🔄 Loading monthly cash flow data...
              <br />
              <small>Please wait while we calculate your trends</small>
            </>
          ) : cashFlow && cashFlow.monthlyTrends && cashFlow.monthlyTrends.length > 0 ? (
            <>
              📈 Cash flow data available for {cashFlow.monthlyTrends.length} months
              <br />
              <small>Chart visualization coming soon - data is ready for display</small>
            </>
          ) : (
            <>
              📊 No cash flow data available yet
              <br />
              <small>Upload some transaction files to see your trends</small>
            </>
          )}
        </div>
      </div>

      {/* Financial Health Breakdown */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Financial Health Breakdown</h3>
        </div>
        {financialHealth ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px' }}>
            <div className="analytics-card">
              <h4>Cash Flow</h4>
              <div className="analytics-metric">{Math.round(financialHealth.componentScores.cashFlowScore)}/100</div>
              <small>Income vs Expenses</small>
            </div>
            
            <div className="analytics-card">
              <h4>Expense Stability</h4>
              <div className="analytics-metric">{Math.round(financialHealth.componentScores.expenseStabilityScore)}/100</div>
              <small>Spending Consistency</small>
            </div>
            
            <div className="analytics-card">
              <h4>Emergency Fund</h4>
              <div className="analytics-metric">{Math.round(financialHealth.componentScores.emergencyFundScore)}/100</div>
              <small>{financialHealth.healthIndicators.emergencyFundMonths.toFixed(1)} months covered</small>
            </div>

            <div className="analytics-card">
              <h4>Debt Management</h4>
              <div className="analytics-metric">{Math.round(financialHealth.componentScores.debtManagementScore)}/100</div>
              <small>{(financialHealth.healthIndicators.debtToIncomeRatio * 100).toFixed(1)}% debt-to-income</small>
            </div>

            <div className="analytics-card">
              <h4>Savings Rate</h4>
              <div className="analytics-metric">{Math.round(financialHealth.componentScores.savingsRateScore)}/100</div>
              <small>{(financialHealth.healthIndicators.savingsRate * 100).toFixed(1)}% of income saved</small>
            </div>
          </div>
        ) : (
          <div className="analytics-placeholder">
            {analytics.loading ? (
              <>
                🔄 Calculating financial health scores...
                <br />
                <small>Analyzing your financial patterns</small>
              </>
            ) : (
              <>
                📊 Financial health data will appear here
                <br />
                <small>Upload transaction data to see your financial wellness score</small>
              </>
            )}
          </div>
        )}
      </div>

      {/* Recommendations and Insights */}
      <div className="analytics-chart-container">
        <div className="analytics-chart-header">
          <h3 className="analytics-chart-title">Insights & Recommendations</h3>
        </div>
        {financialHealth && (financialHealth.recommendations.length > 0 || financialHealth.riskFactors.length > 0) ? (
          <div style={{ display: 'grid', gap: '15px' }}>
            {financialHealth.recommendations.length > 0 && (
              <div className="analytics-card">
                <h4>💡 Recommendations</h4>
                <ul style={{ margin: '10px 0', paddingLeft: '20px' }}>
                  {financialHealth.recommendations.slice(0, 3).map((rec, index) => (
                    <li key={index} style={{ marginBottom: '5px', fontSize: '0.9em' }}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {financialHealth.riskFactors.length > 0 && (
              <div className="analytics-card">
                <h4>⚠️ Risk Factors</h4>
                <ul style={{ margin: '10px 0', paddingLeft: '20px' }}>
                  {financialHealth.riskFactors.slice(0, 3).map((risk, index) => (
                    <li key={index} style={{ marginBottom: '5px', fontSize: '0.9em', color: '#dc3545' }}>{risk}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="analytics-placeholder">
            {analytics.loading ? (
              <>
                🔄 Generating personalized insights...
                <br />
                <small>Analyzing your data for recommendations</small>
              </>
            ) : (
              <>
                💡 Personalized recommendations will appear here
                <br />
                <small>We'll provide insights once we have enough transaction data</small>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OverallAnalyticsTab; 