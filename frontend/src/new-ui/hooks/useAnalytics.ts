import { useState, useEffect, useCallback, useMemo } from 'react';
import analyticsService from '../../services/AnalyticsService';
import {
  AnalyticsFilters,
  AnalyticsViewState,
  CashFlowData,
  CategoryData,
  AccountData,
  FinancialHealthData,
  AnalyticsStatusResponse,
  TimeRange,
  AnalyticType,
  AnalyticsError
} from '../../types/Analytics';

interface UseAnalyticsOptions {
  initialFilters?: Partial<AnalyticsFilters>;
  autoFetch?: boolean;
  refreshInterval?: number; // minutes
}

export interface AnalyticsHookResult {
  // Data
  overview: {
    cashFlow: CashFlowData | null;
    financialHealth: FinancialHealthData | null;
  };
  categories: CategoryData | null;
  accounts: AccountData | null;
  status: AnalyticsStatusResponse | null;
  
  // State
  loading: boolean;
  error: string | null;
  refreshing: boolean;
  dataFreshness: 'fresh' | 'stale' | 'very_stale';
  lastUpdated: string | null;
  
  // Filters
  filters: AnalyticsFilters;
  setFilters: (filters: Partial<AnalyticsFilters>) => void;
  
  // Actions
  refreshData: (force?: boolean) => Promise<void>;
  refreshAnalytics: (analyticTypes?: AnalyticType[], force?: boolean) => Promise<void>;
  clearError: () => void;
  
  // Utilities
  formatCurrency: (amount: number) => string;
  formatPercentage: (value: number, total: number) => string;
  formatDate: (dateString: string) => string;
}

export const useAnalytics = (options: UseAnalyticsOptions = {}): AnalyticsHookResult => {
  const {
    initialFilters = {},
    autoFetch = true,
    refreshInterval = 5
  } = options;

  // State
  const [overview, setOverview] = useState<{
    cashFlow: CashFlowData | null;
    financialHealth: FinancialHealthData | null;
  }>({
    cashFlow: null,
    financialHealth: null
  });
  
  const [categories, setCategories] = useState<CategoryData | null>(null);
  const [accounts, setAccounts] = useState<AccountData | null>(null);
  const [status, setStatus] = useState<AnalyticsStatusResponse | null>(null);
  
  const [viewState, setViewState] = useState<AnalyticsViewState>({
    loading: false,
    error: undefined,
    lastUpdated: undefined,
    dataFreshness: 'fresh',
    refreshing: false
  });

  // Filters with defaults
  const [filters, setFiltersState] = useState<AnalyticsFilters>({
    timeRange: '12months',
    accountIds: undefined,
    categoryIds: undefined,
    customDateRange: undefined,
    ...initialFilters
  });

  // Derived state
  const loading = viewState.loading;
  const error = viewState.error || null;
  const refreshing = viewState.refreshing;
  const dataFreshness = viewState.dataFreshness;
  const lastUpdated = viewState.lastUpdated || null;

  // Update filters
  const setFilters = useCallback((newFilters: Partial<AnalyticsFilters>) => {
    setFiltersState(prev => ({ ...prev, ...newFilters }));
  }, []);

  // Error handling
  const handleError = useCallback((error: any) => {
    let errorMessage = 'An error occurred while fetching analytics data';
    
    if (error instanceof AnalyticsError) {
      errorMessage = error.message;
    } else if (error?.message) {
      errorMessage = error.message;
    }

    setViewState(prev => ({
      ...prev,
      loading: false,
      refreshing: false,
      error: errorMessage
    }));

    console.error('Analytics error:', error);
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setViewState(prev => ({ ...prev, error: undefined }));
  }, []);

  // Fetch overview data
  const fetchOverviewData = useCallback(async () => {
    try {
      const data = await analyticsService.getOverviewData(filters);
      setOverview({
        cashFlow: data.cashFlow,
        financialHealth: data.financialHealth
      });
      
      setViewState(prev => ({
        ...prev,
        lastUpdated: data.lastUpdated,
        dataFreshness: data.dataFreshness as any
      }));
    } catch (error) {
      // If there's an error, set placeholder data for development
      if (process.env.NODE_ENV === 'development') {
        setOverview({
          cashFlow: {
            totalIncome: 0,
            totalExpenses: 0,
            netCashFlow: 0,
            monthlyTrends: [],
            incomeStability: { score: 0, variance: 0, consistency: 0 },
            expensePatterns: { fixed: 0, variable: 0, discretionary: 0 }
          },
          financialHealth: {
            overallScore: 0,
            componentScores: {
              cashFlowScore: 0,
              expenseStabilityScore: 0,
              emergencyFundScore: 0,
              debtManagementScore: 0,
              savingsRateScore: 0
            },
            healthIndicators: {
              emergencyFundMonths: 0,
              debtToIncomeRatio: 0,
              savingsRate: 0,
              expenseVolatility: 0
            },
            recommendations: [],
            riskFactors: []
          }
        });
      }
      throw error;
    }
  }, [filters]);

  // Fetch categories data
  const fetchCategoriesData = useCallback(async () => {
    try {
      const data = await analyticsService.getCategoriesData(filters);
      setCategories(data.categories);
    } catch (error) {
      // Set placeholder data for development
      if (process.env.NODE_ENV === 'development') {
        setCategories({
          categories: [],
          trends: [],
          topByAmount: [],
          topByCount: [],
          budgetVariance: []
        });
      }
      throw error;
    }
  }, [filters]);

  // Fetch accounts data
  const fetchAccountsData = useCallback(async () => {
    try {
      const data = await analyticsService.getAccountsData(filters);
      setAccounts(data.accounts);
    } catch (error) {
      // Set placeholder data for development
      if (process.env.NODE_ENV === 'development') {
        setAccounts({
          accounts: [],
          creditUtilization: [],
          paymentPatterns: [],
          accountEfficiency: []
        });
      }
      throw error;
    }
  }, [filters]);

  // Fetch analytics status
  const fetchStatus = useCallback(async () => {
    try {
      const statusData = await analyticsService.getAnalyticsStatus();
      setStatus(statusData);
    } catch (error) {
      // Status is optional, so don't throw
      console.warn('Failed to fetch analytics status:', error);
    }
  }, []);

  // Fetch all data
  const fetchAllData = useCallback(async () => {
    setViewState(prev => ({ ...prev, loading: true, error: undefined }));

    try {
      await Promise.all([
        fetchOverviewData(),
        fetchCategoriesData(),
        fetchAccountsData(),
        fetchStatus()
      ]);

      setViewState(prev => ({
        ...prev,
        loading: false,
        lastUpdated: new Date().toISOString()
      }));
    } catch (error) {
      handleError(error);
    }
  }, [fetchOverviewData, fetchCategoriesData, fetchAccountsData, fetchStatus, handleError]);

  // Refresh data
  const refreshData = useCallback(async (force: boolean = false) => {
    await fetchAllData();
  }, [fetchAllData]);

  // Refresh analytics computation
  const refreshAnalytics = useCallback(async (
    analyticTypes?: AnalyticType[],
    force: boolean = false
  ) => {
    setViewState(prev => ({ ...prev, refreshing: true }));

    try {
      await analyticsService.refreshAnalytics(analyticTypes, force);
      
      // Wait a moment for computation to start, then refresh data
      setTimeout(() => {
        fetchAllData();
      }, 2000);
    } catch (error) {
      handleError(error);
    } finally {
      setViewState(prev => ({ ...prev, refreshing: false }));
    }
  }, [fetchAllData, handleError]);

  // Check data freshness
  const checkFreshness = useCallback(async () => {
    try {
      const freshness = await analyticsService.checkDataFreshness();
      
      let dataFreshness: 'fresh' | 'stale' | 'very_stale' = 'fresh';
      if (freshness.staleDays > 7) {
        dataFreshness = 'very_stale';
      } else if (freshness.staleDays > 1) {
        dataFreshness = 'stale';
      }

      setViewState(prev => ({ ...prev, dataFreshness }));
    } catch (error) {
      console.warn('Failed to check data freshness:', error);
    }
  }, []);

  // Auto-fetch on mount and filter changes
  useEffect(() => {
    if (autoFetch) {
      fetchAllData();
      checkFreshness();
    }
  }, [autoFetch, fetchAllData, checkFreshness]);

  // Periodic refresh check
  useEffect(() => {
    if (refreshInterval > 0) {
      const interval = setInterval(() => {
        checkFreshness();
      }, refreshInterval * 60 * 1000); // Convert minutes to milliseconds

      return () => clearInterval(interval);
    }
  }, [refreshInterval, checkFreshness]);

  // Utility functions
  const formatCurrency = useCallback((amount: number) => {
    return analyticsService.formatCurrency(amount);
  }, []);

  const formatPercentage = useCallback((value: number, total: number) => {
    return analyticsService.formatPercentage(value, total);
  }, []);

  const formatDate = useCallback((dateString: string) => {
    return analyticsService.formatDate(dateString);
  }, []);

  // Memoized result
  const result = useMemo(() => ({
    // Data
    overview,
    categories,
    accounts,
    status,
    
    // State
    loading,
    error,
    refreshing,
    dataFreshness,
    lastUpdated,
    
    // Filters
    filters,
    setFilters,
    
    // Actions
    refreshData,
    refreshAnalytics,
    clearError,
    
    // Utilities
    formatCurrency,
    formatPercentage,
    formatDate
  }), [
    overview,
    categories,
    accounts,
    status,
    loading,
    error,
    refreshing,
    dataFreshness,
    lastUpdated,
    filters,
    setFilters,
    refreshData,
    refreshAnalytics,
    clearError,
    formatCurrency,
    formatPercentage,
    formatDate
  ]);

  return result;
};

export default useAnalytics; 