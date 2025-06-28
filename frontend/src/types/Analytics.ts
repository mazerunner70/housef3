// Analytics Type Definitions
// These interfaces match the backend analytics models and API responses

export enum AnalyticType {
  CASH_FLOW = 'CASH_FLOW',
  CATEGORY_TRENDS = 'CATEGORY_TRENDS',
  ACCOUNT_EFFICIENCY = 'ACCOUNT_EFFICIENCY',
  FINANCIAL_HEALTH = 'FINANCIAL_HEALTH',
  SPENDING_PATTERNS = 'SPENDING_PATTERNS',
  BUDGET_VARIANCE = 'BUDGET_VARIANCE',
  MERCHANT_ANALYSIS = 'MERCHANT_ANALYSIS',
  PAYMENT_BEHAVIOR = 'PAYMENT_BEHAVIOR',
  CREDIT_UTILIZATION = 'CREDIT_UTILIZATION',
  GOAL_PROGRESS = 'GOAL_PROGRESS'
}

export enum ComputationStatus {
  COMPLETED = 'COMPLETED',
  PENDING = 'PENDING',
  ERROR = 'ERROR',
  NOT_COMPUTED = 'NOT_COMPUTED'
}

export enum DataQuality {
  EXCELLENT = 'EXCELLENT',
  GOOD = 'GOOD',
  FAIR = 'FAIR',
  POOR = 'POOR',
  INSUFFICIENT = 'INSUFFICIENT'
}

// Core Analytics Data Structure
export interface AnalyticsData {
  userId: string;
  analyticType: AnalyticType;
  timePeriod: string;
  accountId?: string;
  data: any; // JSON data specific to each analytic type
  computedDate: string;
  dataThroughDate: string;
  dataQuality: DataQuality;
}

// Analytics Processing Status
export interface AnalyticsProcessingStatus {
  userId: string;
  analyticType: AnalyticType;
  lastComputedDate?: string;
  dataAvailableThrough?: string;
  computationNeeded: boolean;
  processingPriority: number;
  status: ComputationStatus;
}

// API Response Types
export interface AnalyticsResponse {
  status: 'success' | 'error';
  analytic_type: string;
  data: any;
  computed_date?: string;
  data_through_date?: string;
  cache_status: 'hit' | 'computed_on_demand';
  message?: string;
}

export interface AnalyticsStatusResponse {
  status: 'success' | 'error';
  user_id: string;
  timestamp: string;
  summary: {
    total_analytics: number;
    pending_computation: number;
    up_to_date: number;
  };
  analytics_status: Array<{
    analytic_type: string;
    last_computed?: string;
    computation_needed: boolean;
    processing_priority: number;
    status: string;
  }>;
}

export interface RefreshResponse {
  status: 'refresh_initiated' | 'error';
  message: string;
  results: Array<{
    analytic_type: string;
    status: 'queued' | 'error';
    message: string;
  }>;
}

// Specific Analytics Data Types

// Cash Flow Analytics
export interface CashFlowData {
  totalIncome: number;
  totalExpenses: number;
  netCashFlow: number;
  monthlyTrends: MonthlyTrend[];
  incomeStability: {
    score: number;
    variance: number;
    consistency: number;
  };
  expensePatterns: {
    fixed: number;
    variable: number;
    discretionary: number;
  };
}

export interface MonthlyTrend {
  period: string; // YYYY-MM
  income: number;
  expenses: number;
  netFlow: number;
  transactionCount: number;
}

// Category Analytics
export interface CategoryData {
  categories: CategoryBreakdown[];
  trends: CategoryTrend[];
  topByAmount: CategorySummary[];
  topByCount: CategorySummary[];
  budgetVariance?: BudgetVariance[];
}

export interface CategoryBreakdown {
  categoryId: string;
  categoryName: string;
  totalAmount: number;
  transactionCount: number;
  percentage: number;
  avgTransactionAmount: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  growthRate: number;
}

export interface CategoryTrend {
  categoryId: string;
  categoryName: string;
  monthlyData: Array<{
    period: string;
    amount: number;
    transactionCount: number;
  }>;
  trendDirection: 'increasing' | 'decreasing' | 'stable';
  seasonalFactors: Record<string, number>;
}

export interface CategorySummary {
  categoryId: string;
  categoryName: string;
  amount: number;
  count: number;
  rank: number;
}

export interface BudgetVariance {
  categoryId: string;
  categoryName: string;
  budgeted: number;
  actual: number;
  variance: number;
  variancePercentage: number;
  onTrack: boolean;
}

// Account Analytics
export interface AccountData {
  accounts: AccountAnalytics[];
  creditUtilization: CreditUtilizationData[];
  paymentPatterns: PaymentPattern[];
  accountEfficiency: AccountEfficiency[];
}

export interface AccountAnalytics {
  accountId: string;
  accountName: string;
  accountType: string;
  totalSpending: number;
  transactionCount: number;
  avgTransactionAmount: number;
  currentBalance?: number;
  creditLimit?: number;
  utilizationRate?: number;
  trend: string;
  monthlySpending: Array<{
    period: string;
    amount: number;
    count: number;
  }>;
}

export interface CreditUtilizationData {
  accountId: string;
  accountName: string;
  currentBalance: number;
  creditLimit: number;
  utilizationPercentage: number;
  availableCredit: number;
  optimalUtilization: number;
  utilizationTrend: Array<{
    date: string;
    utilization: number;
  }>;
}

export interface PaymentPattern {
  accountId: string;
  accountName: string;
  avgPaymentAmount: number;
  paymentFrequency: number;
  onTimePaymentRate: number;
  interestCharges: number;
  feesCharged: number;
  paymentTiming: 'optimal' | 'early' | 'late';
}

export interface AccountEfficiency {
  accountId: string;
  accountName: string;
  rewardsEarned: number;
  feesPaid: number;
  interestPaid: number;
  netBenefit: number;
  efficiencyScore: number;
  recommendations: string[];
}

// Financial Health Analytics
export interface FinancialHealthData {
  overallScore: number;
  componentScores: {
    cashFlowScore: number;
    expenseStabilityScore: number;
    emergencyFundScore: number;
    debtManagementScore: number;
    savingsRateScore: number;
  };
  healthIndicators: {
    emergencyFundMonths: number;
    debtToIncomeRatio: number;
    savingsRate: number;
    expenseVolatility: number;
  };
  recommendations: string[];
  riskFactors: string[];
}

// Time Range and Filter Types
export type TimeRange = '1month' | '3months' | '6months' | '12months' | 'custom';

export interface AnalyticsFilters {
  timeRange: TimeRange;
  accountIds?: string[];
  categoryIds?: string[];
  customDateRange?: {
    start: string;
    end: string;
  };
}

// UI State Types
export interface AnalyticsViewState {
  loading: boolean;
  error?: string;
  lastUpdated?: string;
  dataFreshness: 'fresh' | 'stale' | 'very_stale';
  refreshing: boolean;
}

// Chart Data Types
export interface ChartDataPoint {
  x: string | number;
  y: number;
  label?: string;
  color?: string;
}

export interface TimeSeriesData {
  series: Array<{
    name: string;
    data: ChartDataPoint[];
    color?: string;
  }>;
  categories: string[];
}

export interface PieChartData {
  labels: string[];
  series: number[];
  colors: string[];
}

// Error Types
export class AnalyticsError extends Error {
  public code: string;
  public details?: any;
  public retry: boolean;

  constructor(code: string, message: string, details?: any, retry: boolean = false) {
    super(message);
    this.name = 'AnalyticsError';
    this.code = code;
    this.details = details;
    this.retry = retry;
  }
}

// Data Availability Types
export interface DataAvailability {
  hasData: boolean;
  earliestDate?: string;
  latestDate?: string;
  gapDays: number;
  dataQuality: DataQuality;
  missingAccounts: string[];
  recommendations: string[];
} 