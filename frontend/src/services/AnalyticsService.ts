import {
  AnalyticType,
  AnalyticsResponse,
  AnalyticsStatusResponse,
  RefreshResponse,
  CashFlowData,
  CategoryData,
  AccountData,
  FinancialHealthData,
  AnalyticsFilters,
  TimeRange,
  AnalyticsError,
  DataAvailability,
  toDecimal,
  fromDecimal,
  formatDecimalCurrency,
  formatDecimalPercentage
} from '../types/Analytics';
import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';
import { Decimal } from 'decimal.js';

class AnalyticsService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_ENDPOINT || 'https://api.housef3.com';
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const currentUser = getCurrentUser();
    
    if (!currentUser || !currentUser.token) {
      throw new AnalyticsError(
        'AUTH_ERROR',
        'User not authenticated',
        null,
        false
      );
    }
    
    try {
      // Check if token is valid
      if (!isAuthenticated()) {
        // Try to refresh token
        await refreshToken(currentUser.refreshToken);
      }
      
      // Get the user again after potential refresh
      const user = getCurrentUser();
      if (!user || !user.token) {
        throw new AnalyticsError(
          'AUTH_ERROR',
          'Authentication failed',
          null,
          false
        );
      }
      
      // Set up headers with authentication
      const headers = {
        'Authorization': user.token,
        'Content-Type': 'application/json',
        ...options.headers
      };
      
      const requestOptions = {
        ...options,
        headers
      };
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, requestOptions);
      
      // Handle 401 error specifically - try to refresh token
      if (response.status === 401) {
        try {
          const refreshedUser = await refreshToken(user.refreshToken);
          
          // Update headers with new token
          const retryHeaders = {
            'Authorization': refreshedUser.token,
            'Content-Type': 'application/json',
            ...options.headers
          };
          
          // Retry the request with the new token
          const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers: retryHeaders
          });
          
          if (!retryResponse.ok) {
            const errorData = await retryResponse.json().catch(() => ({}));
            throw new AnalyticsError(
              `HTTP_${retryResponse.status}`,
              errorData.message || `Request failed after token refresh: ${retryResponse.status} ${retryResponse.statusText}`,
              errorData,
              retryResponse.status >= 500
            );
          }
          
          return await retryResponse.json();
        } catch (refreshError) {
          console.error('Error refreshing token:', refreshError);
          throw new AnalyticsError(
            'AUTH_ERROR',
            'Session expired. Please log in again.',
            refreshError,
            false
          );
        }
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new AnalyticsError(
          `HTTP_${response.status}`,
          errorData.message || `Request failed with status ${response.status}`,
          errorData,
          response.status >= 500 // Retry for server errors
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof AnalyticsError) {
        throw error;
      }
      
      // Network or parsing error
      throw new AnalyticsError(
        'NETWORK_ERROR',
        'Failed to connect to analytics service',
        error,
        true
      );
    }
  }

  // Core Analytics Data Retrieval

  /**
   * Get cash flow analytics data
   */
  async getCashFlowAnalytics(
    timeRange: TimeRange = '12months',
    accountId?: string
  ): Promise<CashFlowData> {
    const params = new URLSearchParams({
      time_period: this.timeRangeToString(timeRange)
    });
    
    if (accountId) {
      params.append('account_id', accountId);
    }

    const response = await this.makeRequest<AnalyticsResponse>(
      `/api/analytics/cash_flow?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve cash flow analytics',
        response
      );
    }

    // Convert string monetary values to Decimal objects
    const convertedData = this.convertMonetaryStringsToDecimals(response.data);
    return convertedData as CashFlowData;
  }

  /**
   * Get category analytics data
   */
  async getCategoryAnalytics(
    timeRange: TimeRange = '12months',
    accountId?: string
  ): Promise<CategoryData> {
    const params = new URLSearchParams({
      time_period: this.timeRangeToString(timeRange)
    });
    
    if (accountId) {
      params.append('account_id', accountId);
    }

    const response = await this.makeRequest<AnalyticsResponse>(
      `/api/analytics/category_trends?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve category analytics',
        response
      );
    }

    // Convert string monetary values to Decimal objects
    const convertedData = this.convertMonetaryStringsToDecimals(response.data);
    return convertedData as CategoryData;
  }

  /**
   * Get account analytics data
   */
  async getAccountAnalytics(
    timeRange: TimeRange = '12months'
  ): Promise<AccountData> {
    const params = new URLSearchParams({
      time_period: this.timeRangeToString(timeRange)
    });

    const response = await this.makeRequest<AnalyticsResponse>(
      `/api/analytics/account_efficiency?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve account analytics',
        response
      );
    }

    // Convert string monetary values to Decimal objects
    const convertedData = this.convertMonetaryStringsToDecimals(response.data);
    return convertedData as AccountData;
  }

  /**
   * Get financial health analytics
   */
  async getFinancialHealthAnalytics(
    timeRange: TimeRange = '12months'
  ): Promise<FinancialHealthData> {
    const params = new URLSearchParams({
      time_period: this.timeRangeToString(timeRange)
    });

    const response = await this.makeRequest<AnalyticsResponse>(
      `/api/analytics/financial_health?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve financial health analytics',
        response
      );
    }

    // Convert string monetary values to Decimal objects
    const convertedData = this.convertMonetaryStringsToDecimals(response.data);
    return convertedData as FinancialHealthData;
  }

  /**
   * Get specific analytic type data
   */
  async getAnalyticData(
    analyticType: AnalyticType,
    timeRange: TimeRange = '12months',
    accountId?: string
  ): Promise<any> {
    const params = new URLSearchParams({
      time_period: this.timeRangeToString(timeRange)
    });
    
    if (accountId) {
      params.append('account_id', accountId);
    }

    const response = await this.makeRequest<AnalyticsResponse>(
      `/api/analytics/${analyticType.toLowerCase()}?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || `Failed to retrieve ${analyticType} analytics`,
        response
      );
    }

    // Convert string monetary values to Decimal objects
    return this.convertMonetaryStringsToDecimals(response.data);
  }

  // High-Level Overview Methods

  /**
   * Get all data needed for the Overview tab
   */
  async getOverviewData(filters: AnalyticsFilters): Promise<{
    cashFlow: CashFlowData;
    financialHealth: FinancialHealthData;
    dataFreshness: string;
    lastUpdated: string;
  }> {
    try {
      const [cashFlow, financialHealth] = await Promise.all([
        this.getCashFlowAnalytics(filters.timeRange, filters.accountIds?.[0]),
        this.getFinancialHealthAnalytics(filters.timeRange)
      ]);

      return {
        cashFlow,
        financialHealth,
        dataFreshness: 'fresh', // TODO: Calculate based on data_through_date
        lastUpdated: new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to fetch overview data:', error);
      throw error;
    }
  }

  /**
   * Get all data needed for the Categories tab
   */
  async getCategoriesData(filters: AnalyticsFilters): Promise<{
    categories: CategoryData;
    dataFreshness: string;
    lastUpdated: string;
  }> {
    try {
      const categories = await this.getCategoryAnalytics(
        filters.timeRange,
        filters.accountIds?.[0]
      );

      return {
        categories,
        dataFreshness: 'fresh',
        lastUpdated: new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to fetch categories data:', error);
      throw error;
    }
  }

  /**
   * Get all data needed for the Accounts tab
   */
  async getAccountsData(filters: AnalyticsFilters): Promise<{
    accounts: AccountData;
    dataFreshness: string;
    lastUpdated: string;
  }> {
    try {
      const accounts = await this.getAccountAnalytics(filters.timeRange);

      return {
        accounts,
        dataFreshness: 'fresh',
        lastUpdated: new Date().toISOString()
      };
    } catch (error) {
      console.error('Failed to fetch accounts data:', error);
      throw error;
    }
  }

  // Analytics Status and Management

  /**
   * Get analytics computation status
   */
  async getAnalyticsStatus(): Promise<AnalyticsStatusResponse> {
    const response = await this.makeRequest<AnalyticsStatusResponse>(
      '/api/analytics/status'
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'STATUS_ERROR',
        'Failed to retrieve analytics status',
        response
      );
    }

    return response;
  }

  /**
   * Trigger manual analytics refresh
   */
  async refreshAnalytics(
    analyticTypes?: AnalyticType[],
    force: boolean = false
  ): Promise<RefreshResponse> {
    const body: any = {
      force
    };

    if (analyticTypes && analyticTypes.length > 0) {
      body.analytic_types = analyticTypes.map(type => type.toLowerCase());
    }

    const response = await this.makeRequest<RefreshResponse>(
      '/api/analytics/refresh',
      {
        method: 'POST',
        body: JSON.stringify(body)
      }
    );

    if (response.status !== 'refresh_initiated') {
      throw new AnalyticsError(
        'REFRESH_ERROR',
        response.message || 'Failed to initiate analytics refresh',
        response
      );
    }

    return response;
  }

  /**
   * Check if analytics data is stale and needs refresh
   */
  async checkDataFreshness(): Promise<{
    isStale: boolean;
    staleDays: number;
    needsRefresh: boolean;
    recommendations: string[];
  }> {
    try {
      const status = await this.getAnalyticsStatus();
      
      const pendingCount = status.summary.pending_computation;
      const totalCount = status.summary.total_analytics;
      const stalePercentage = (pendingCount / totalCount) * 100;

      return {
        isStale: pendingCount > 0,
        staleDays: 0, // TODO: Calculate from status data
        needsRefresh: stalePercentage > 20, // Arbitrary threshold
        recommendations: pendingCount > 0 ? 
          ['Some analytics are out of date. Consider refreshing for latest insights.'] : 
          []
      };
    } catch (error) {
      console.error('Failed to check data freshness:', error);
      return {
        isStale: false,
        staleDays: 0,
        needsRefresh: false,
        recommendations: ['Unable to check data freshness']
      };
    }
  }

  // Utility Methods

  private timeRangeToString(timeRange: TimeRange): string {
    switch (timeRange) {
      case '1month':
        return '1month';
      case '3months':
        return '3months';
      case '6months':
        return '6months';
      case '12months':
        return '12months';
      case 'custom':
        return 'custom';
      default:
        return '12months';
    }
  }

  /**
   * Format monetary amounts consistently
   */
  formatCurrency(amount: number | Decimal): string {
    if (amount instanceof Decimal) {
      return formatDecimalCurrency(amount);
    }
    throw new Error(`Invalid amount type: ${typeof amount}`);
  }

  /**
   * Calculate percentage with proper formatting
   */
  formatPercentage(value: number | Decimal, total: number | Decimal): string {
    const valueDecimal = value instanceof Decimal ? value : toDecimal(value);
    const totalDecimal = total instanceof Decimal ? total : toDecimal(total);
    
    if (totalDecimal.isZero()) return '0.0%';
    const percentage = valueDecimal.div(totalDecimal).mul(100);
    return formatDecimalPercentage(percentage);
  }

  /**
   * Format dates consistently
   */
  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  /**
   * Calculate trend indicator
   */
  calculateTrend(current: number | Decimal, previous: number | Decimal): {
    direction: 'up' | 'down' | 'stable';
    percentage: number;
    display: string;
  } {
    const currentDecimal = current instanceof Decimal ? current : toDecimal(current);
    const previousDecimal = previous instanceof Decimal ? previous : toDecimal(previous);
    
    if (previousDecimal.isZero()) {
      return { direction: 'stable', percentage: 0, display: 'N/A' };
    }

    const change = currentDecimal.sub(previousDecimal).div(previousDecimal).mul(100);
    const changeNumber = change.toNumber();
    const direction = changeNumber > 5 ? 'up' : changeNumber < -5 ? 'down' : 'stable';
    
    return {
      direction,
      percentage: Math.abs(changeNumber),
      display: `${changeNumber >= 0 ? '+' : ''}${changeNumber.toFixed(1)}%`
    };
  }

  // Cache Management

  /**
   * Clear analytics cache (useful after refresh)
   */
  clearCache(): void {
    // Clear any client-side caching if implemented
    localStorage.removeItem('analytics_cache');
  }

  /**
   * Check if we should use cached data or fetch fresh
   */
  private shouldUseCachedData(cacheTimestamp: string, maxAgeMinutes: number = 5): boolean {
    const cacheTime = new Date(cacheTimestamp);
    const now = new Date();
    const ageMinutes = (now.getTime() - cacheTime.getTime()) / (1000 * 60);
    
    return ageMinutes < maxAgeMinutes;
  }

  /**
   * Check if a field name represents a monetary value
   */
  private isMonetaryField(fieldName: string): boolean {
    const monetaryFields = [
      'total_income', 'total_expenses', 'net_cash_flow', 'avg_monthly_income', 'avg_monthly_expenses',
      'avg_transaction_amount', 'income_stability_score', 'expense_ratio', 'overall_score',
      'cash_flow', 'income_stability', 'emergency_fund', 'debt_management', 'savings_rate',
      'cashFlowScore', 'expenseStabilityScore', 'emergencyFundScore', 'debtManagementScore',
      'savingsRateScore', 'overallScore', 'amount', 'percentage', 'total_spending',
      'balance', 'credit_limit', 'available_credit', 'utilization_percentage',
      'totalIncome', 'totalExpenses', 'netCashFlow', 'avgMonthlyIncome', 'avgMonthlyExpenses',
      'avgTransactionAmount', 'incomeStabilityScore', 'expenseRatio', 'score', 'variance',
      'consistency', 'fixed', 'variable', 'discretionary', 'income', 'expenses', 'netFlow',
      'totalAmount', 'growthRate', 'budgeted', 'actual', 'variancePercentage',
      'totalSpending', 'currentBalance', 'creditLimit', 'utilizationRate', 'utilizationPercentage',
      'availableCredit', 'optimalUtilization', 'utilization', 'avgPaymentAmount',
      'paymentFrequency', 'onTimePaymentRate', 'interestCharges', 'feesCharged',
      'rewardsEarned', 'feesPaid', 'interestPaid', 'netBenefit', 'efficiencyScore',
      'emergencyFundMonths', 'debtToIncomeRatio', 'savingsRate', 'expenseVolatility'
    ];
    return monetaryFields.includes(fieldName) || 
           fieldName.includes('amount') || 
           fieldName.includes('balance') ||
           fieldName.includes('score') ||
           fieldName.includes('percentage') ||
           fieldName.includes('rate') ||
           fieldName.includes('income') ||
           fieldName.includes('expense') ||
           fieldName.includes('total') ||
           fieldName.includes('avg') ||
           fieldName.includes('fees') ||
           fieldName.includes('interest') ||
           fieldName.includes('utilization');
  }

  /**
   * Check if a string represents a valid number
   */
  private isNumericString(value: string): boolean {
    return !isNaN(parseFloat(value)) && isFinite(parseFloat(value));
  }

  /**
   * Convert string monetary values to Decimal objects and handle existing Decimal objects
   */
  private convertMonetaryStringsToDecimals(data: any): any {
    if (data === null || data === undefined) {
      return data;
    }

    if (Array.isArray(data)) {
      return data.map(item => this.convertMonetaryStringsToDecimals(item));
    }

    if (typeof data === 'object') {
      // Handle case where backend returns Decimal objects (check for Decimal-like structure)
      if (data.hasOwnProperty('s') && data.hasOwnProperty('e') && data.hasOwnProperty('d')) {
        // This looks like a serialized Decimal object from decimal.js
        try {
          const decimalLike = data as { s: number; e: number; d: number[] };
          return new Decimal(decimalLike.s === 1 ? 1 : -1).mul(new Decimal(decimalLike.d.join(''))).div(new Decimal(10).pow(decimalLike.d.length - 1 - decimalLike.e));
        } catch (error) {
          console.warn('Failed to reconstruct Decimal from backend object:', data, error);
          return toDecimal(0);
        }
      }

      const converted: any = {};
      for (const [key, value] of Object.entries(data)) {
        if (value !== null && value !== undefined) {
          // Handle existing Decimal objects from backend
          if (typeof value === 'object' && value.hasOwnProperty('s') && value.hasOwnProperty('e') && value.hasOwnProperty('d')) {
            try {
              // Reconstruct Decimal from serialized form
              const decimalLike = value as { s: number; e: number; d: number[] };
              const sign = decimalLike.s === 1 ? 1 : -1;
              const digits = decimalLike.d;
              const exponent = decimalLike.e;
            
            // Convert digits array to number string
            const digitString = digits.join('');
            const decimalPlaces = digits.length - 1 - exponent;
            
            if (decimalPlaces <= 0) {
              // No decimal places needed
              converted[key] = new Decimal(sign * parseInt(digitString) * Math.pow(10, -decimalPlaces));
            } else {
              // Insert decimal point
              const beforeDecimal = digitString.slice(0, -decimalPlaces) || '0';
              const afterDecimal = digitString.slice(-decimalPlaces);
              const fullString = `${sign < 0 ? '-' : ''}${beforeDecimal}.${afterDecimal}`;
              converted[key] = new Decimal(fullString);
            }
          } catch (error) {
            console.warn('Failed to reconstruct Decimal for key', key, ':', value, error);
            converted[key] = toDecimal(0);
          }
        }
        // Convert string numbers to Decimal objects for monetary fields
        else if (typeof value === 'string' && this.isMonetaryField(key) && this.isNumericString(value)) {
          converted[key] = toDecimal(value);
        } 
        // Convert regular numbers to Decimal objects for monetary fields
        else if (typeof value === 'number' && this.isMonetaryField(key)) {
          converted[key] = toDecimal(value);
        } 
        // Recursively process nested objects
        else if (typeof value === 'object') {
          converted[key] = this.convertMonetaryStringsToDecimals(value);
        } 
        // Keep other values as-is
        else {
          converted[key] = value;
        }
      } else {
        converted[key] = value;
      }
    }
    return converted;
  }

  return data;
}
}

// Create and export a singleton instance
const analyticsService = new AnalyticsService();
export default analyticsService; 