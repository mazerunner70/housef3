// Analytics Type Definitions
// These interfaces match the backend analytics models and API responses

import { Decimal } from 'decimal.js';

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
  totalIncome: Decimal;
  totalExpenses: Decimal;
  netCashFlow: Decimal;
  monthlyTrends: MonthlyTrend[];
  incomeStability: {
    score: Decimal;
    variance: Decimal;
    consistency: Decimal;
  };
  expensePatterns: {
    fixed: Decimal;
    variable: Decimal;
    discretionary: Decimal;
  };
}

export interface MonthlyTrend {
  period: string; // YYYY-MM
  income: Decimal;
  expenses: Decimal;
  netFlow: Decimal;
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
  totalAmount: Decimal;
  transactionCount: number;
  percentage: Decimal;
  avgTransactionAmount: Decimal;
  trend: 'increasing' | 'decreasing' | 'stable';
  growthRate: Decimal;
}

export interface CategoryTrend {
  categoryId: string;
  categoryName: string;
  monthlyData: Array<{
    period: string;
    amount: Decimal;
    transactionCount: number;
  }>;
  trendDirection: 'increasing' | 'decreasing' | 'stable';
  seasonalFactors: Record<string, Decimal>;
}

export interface CategorySummary {
  categoryId: string;
  categoryName: string;
  amount: Decimal;
  count: number;
  rank: number;
}

export interface BudgetVariance {
  categoryId: string;
  categoryName: string;
  budgeted: Decimal;
  actual: Decimal;
  variance: Decimal;
  variancePercentage: Decimal;
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
  totalSpending: Decimal;
  transactionCount: number;
  avgTransactionAmount: Decimal;
  currentBalance?: Decimal;
  creditLimit?: Decimal;
  utilizationRate?: Decimal;
  trend: string;
  monthlySpending: Array<{
    period: string;
    amount: Decimal;
    count: number;
  }>;
}

export interface CreditUtilizationData {
  accountId: string;
  accountName: string;
  currentBalance: Decimal;
  creditLimit: Decimal;
  utilizationPercentage: Decimal;
  availableCredit: Decimal;
  optimalUtilization: Decimal;
  utilizationTrend: Array<{
    date: string;
    utilization: Decimal;
  }>;
}

export interface PaymentPattern {
  accountId: string;
  accountName: string;
  avgPaymentAmount: Decimal;
  paymentFrequency: Decimal;
  onTimePaymentRate: Decimal;
  interestCharges: Decimal;
  feesCharged: Decimal;
  paymentTiming: 'optimal' | 'early' | 'late';
}

export interface AccountEfficiency {
  accountId: string;
  accountName: string;
  rewardsEarned: Decimal;
  feesPaid: Decimal;
  interestPaid: Decimal;
  netBenefit: Decimal;
  efficiencyScore: Decimal;
  recommendations: string[];
}

// Financial Health Analytics
export interface FinancialHealthData {
  overallScore: Decimal;
  componentScores: {
    cashFlowScore: Decimal;
    expenseStabilityScore: Decimal;
    emergencyFundScore: Decimal;
    debtManagementScore: Decimal;
    savingsRateScore: Decimal;
  };
  healthIndicators: {
    emergencyFundMonths: Decimal;
    debtToIncomeRatio: Decimal;
    savingsRate: Decimal;
    expenseVolatility: Decimal;
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
  y: number | Decimal; // Can be Decimal for monetary values, number for counts/percentages
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
  series: number[]; // Chart libraries typically expect numbers, convert from Decimal when needed
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

// Utility Types for Decimal Conversion
export type DecimalLike = string | number | Decimal;

// Helper functions for Decimal conversion
export const toDecimal = (value: DecimalLike): Decimal => {
  if (value instanceof Decimal) {
    return value;
  }
  return new Decimal(value.toString());
};

export const fromDecimal = (decimal: Decimal | number | undefined | null): number => {
  if (decimal === null || decimal === undefined) {
    throw new Error('fromDecimal: Received null or undefined value');
  }
  if (typeof decimal === 'number') {
    if (isNaN(decimal)) {
      throw new Error('fromDecimal: Received NaN number');
    }
    return decimal;
  }
  if (decimal instanceof Decimal) {
    const result = decimal.toNumber();
    if (isNaN(result)) {
      throw new Error(`fromDecimal: Decimal.toNumber() returned NaN for decimal: ${decimal.toString()}`);
    }
    return result;
  }
  throw new Error(`fromDecimal: Invalid type ${typeof decimal}, expected Decimal or number`);
};

export const formatDecimalCurrency = (decimal: Decimal | undefined | null): string => {
  if (decimal === null || decimal === undefined) {
    throw new Error('formatDecimalCurrency: Received null or undefined value');
  }
  if (!(decimal instanceof Decimal)) {
    throw new Error(`formatDecimalCurrency: Invalid type ${typeof decimal}, expected Decimal`);
  }
  const numericValue = decimal.toNumber();
  if (isNaN(numericValue)) {
    throw new Error(`formatDecimalCurrency: Decimal.toNumber() returned NaN for decimal: ${decimal.toString()}`);
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(numericValue);
};

export const formatDecimalPercentage = (decimal: Decimal | undefined | null): string => {
  if (decimal === null || decimal === undefined) {
    throw new Error('formatDecimalPercentage: Received null or undefined value');
  }
  if (!(decimal instanceof Decimal)) {
    throw new Error(`formatDecimalPercentage: Invalid type ${typeof decimal}, expected Decimal`);
  }
  try {
    return `${decimal.toFixed(1)}%`;
  } catch (error) {
    throw new Error(`formatDecimalPercentage: Failed to format decimal ${decimal.toString()}: ${error}`);
  }
}; 