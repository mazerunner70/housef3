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
  DataAvailability
} from '../types/Analytics';

class AnalyticsService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_ENDPOINT || 'https://api.housef3.com';
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = localStorage.getItem('authToken');
    
    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, config);
      
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
      `/analytics/cash_flow?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve cash flow analytics',
        response
      );
    }

    return response.data as CashFlowData;
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
      `/analytics/category_trends?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve category analytics',
        response
      );
    }

    return response.data as CategoryData;
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
      `/analytics/account_efficiency?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve account analytics',
        response
      );
    }

    return response.data as AccountData;
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
      `/analytics/financial_health?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || 'Failed to retrieve financial health analytics',
        response
      );
    }

    return response.data as FinancialHealthData;
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
      `/analytics/${analyticType.toLowerCase()}?${params.toString()}`
    );

    if (response.status !== 'success') {
      throw new AnalyticsError(
        'ANALYTICS_ERROR',
        response.message || `Failed to retrieve ${analyticType} analytics`,
        response
      );
    }

    return response.data;
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
      '/analytics/status'
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
      '/analytics/refresh',
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
  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  }

  /**
   * Calculate percentage with proper formatting
   */
  formatPercentage(value: number, total: number): string {
    if (total === 0) return '0.0%';
    const percentage = (value / total) * 100;
    return `${percentage.toFixed(1)}%`;
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
  calculateTrend(current: number, previous: number): {
    direction: 'up' | 'down' | 'stable';
    percentage: number;
    display: string;
  } {
    if (previous === 0) {
      return { direction: 'stable', percentage: 0, display: 'N/A' };
    }

    const change = ((current - previous) / previous) * 100;
    const direction = change > 5 ? 'up' : change < -5 ? 'down' : 'stable';
    
    return {
      direction,
      percentage: Math.abs(change),
      display: `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`
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
}

// Create and export a singleton instance
const analyticsService = new AnalyticsService();
export default analyticsService; 