/**
 * Recurring Charge Detection TypeScript Interfaces
 * 
 * This module provides TypeScript interfaces that mirror the backend Pydantic models
 * for ML-based recurring charge detection, including pattern representation, predictions,
 * and related enums.
 */

// Enums
export enum RecurrenceFrequency {
    DAILY = 'daily',
    WEEKLY = 'weekly',
    BI_WEEKLY = 'bi_weekly',
    SEMI_MONTHLY = 'semi_monthly',
    MONTHLY = 'monthly',
    BI_MONTHLY = 'bi_monthly',
    QUARTERLY = 'quarterly',
    SEMI_ANNUALLY = 'semi_annually',
    ANNUALLY = 'annually',
    IRREGULAR = 'irregular'
}

export enum TemporalPatternType {
    DAY_OF_WEEK = 'day_of_week',
    DAY_OF_MONTH = 'day_of_month',
    FIRST_WORKING_DAY = 'first_working_day',
    LAST_WORKING_DAY = 'last_working_day',
    FIRST_DAY_OF_MONTH = 'first_day_of_month',
    LAST_DAY_OF_MONTH = 'last_day_of_month',
    WEEKEND = 'weekend',
    WEEKDAY = 'weekday',
    FLEXIBLE = 'flexible'
}

// Core Models
export interface RecurringChargePattern {
    patternId: string;
    userId: string;

    // Pattern identification
    merchantPattern: string;
    frequency: RecurrenceFrequency;
    temporalPatternType: TemporalPatternType;

    // Temporal constraints
    dayOfWeek?: number; // 0-6 (Monday-Sunday)
    dayOfMonth?: number; // 1-31
    toleranceDays: number;

    // Amount constraints
    amountMean: string; // Decimal as string
    amountStd: string;
    amountMin: string;
    amountMax: string;
    amountTolerancePct: number;

    // Pattern metadata
    confidenceScore: number; // 0.0-1.0
    transactionCount: number;
    firstOccurrence: number; // Timestamp (ms)
    lastOccurrence: number; // Timestamp (ms)

    // ML features
    featureVector?: number[];
    clusterId?: number;

    // Associated category
    suggestedCategoryId?: string;
    autoCategorize: boolean;

    // Status
    active: boolean;
    createdAt: number; // Timestamp (ms)
    updatedAt: number; // Timestamp (ms)
}

export interface RecurringChargePatternCreate {
    userId: string;

    // Pattern identification
    merchantPattern: string;
    frequency: RecurrenceFrequency;
    temporalPatternType: TemporalPatternType;

    // Temporal constraints
    dayOfWeek?: number;
    dayOfMonth?: number;
    toleranceDays?: number;

    // Amount constraints
    amountMean: string;
    amountStd: string;
    amountMin: string;
    amountMax: string;
    amountTolerancePct?: number;

    // Pattern metadata
    confidenceScore: number;
    transactionCount: number;
    firstOccurrence: number;
    lastOccurrence: number;

    // ML features
    featureVector?: number[];
    clusterId?: number;

    // Associated category
    suggestedCategoryId?: string;
    autoCategorize?: boolean;

    // Status
    active?: boolean;
}

export interface RecurringChargePatternUpdate {
    // Pattern identification
    merchantPattern?: string;
    frequency?: RecurrenceFrequency;
    temporalPatternType?: TemporalPatternType;

    // Temporal constraints
    dayOfWeek?: number;
    dayOfMonth?: number;
    toleranceDays?: number;

    // Amount constraints
    amountMean?: string;
    amountStd?: string;
    amountMin?: string;
    amountMax?: string;
    amountTolerancePct?: number;

    // Pattern metadata
    confidenceScore?: number;
    transactionCount?: number;
    firstOccurrence?: number;
    lastOccurrence?: number;

    // ML features
    featureVector?: number[];
    clusterId?: number;

    // Associated category
    suggestedCategoryId?: string;
    autoCategorize?: boolean;

    // Status
    active?: boolean;
}

export interface RecurringChargePrediction {
    patternId: string;
    nextExpectedDate: number; // Timestamp (ms)
    expectedAmount: string; // Decimal as string
    confidence: number; // 0.0-1.0
    daysUntilDue: number;
    amountRange: {
        min: string;
        max: string;
    };
}

export interface RecurringChargePredictionCreate {
    patternId: string;
    nextExpectedDate: number;
    expectedAmount: string;
    confidence: number;
    daysUntilDue: number;
    amountRange: {
        min: string;
        max: string;
    };
}

export interface PatternFeedback {
    feedbackId: string;
    patternId: string;
    userId: string;
    feedbackType: 'correct' | 'incorrect' | 'missed_transaction' | 'false_positive';
    userCorrection?: Record<string, any>;
    transactionId?: string;
    timestamp: number;
}

export interface PatternFeedbackCreate {
    patternId: string;
    userId: string;
    feedbackType: 'correct' | 'incorrect' | 'missed_transaction' | 'false_positive';
    userCorrection?: Record<string, any>;
    transactionId?: string;
}

// API Request/Response Types
export interface DetectRecurringChargesRequest {
    accountIds?: string[];
    startDateTs?: number; // Timestamp in milliseconds since epoch
    endDateTs?: number; // Timestamp in milliseconds since epoch
    minOccurrences?: number;
    minConfidence?: number;
}

export interface DetectRecurringChargesResponse {
    operationId: string;
    message: string;
    status: string;
}

export interface GetPatternsRequest {
    active?: boolean;
    minConfidence?: number;
    frequency?: RecurrenceFrequency;
    categoryId?: string;
}

export interface GetPatternsResponse {
    patterns: RecurringChargePattern[];
    total: number;
}

export interface GetPredictionsRequest {
    patternIds?: string[];
    startDate?: string; // ISO date
    endDate?: string; // ISO date
    minConfidence?: number;
}

export interface GetPredictionsResponse {
    predictions: RecurringChargePrediction[];
    total: number;
}

export interface ApplyPatternToCategoryRequest {
    categoryId: string;
    autoCategorize?: boolean;
}

export interface ApplyPatternToCategoryResponse {
    pattern: RecurringChargePattern;
    message: string;
}

// UI-specific Types
export interface RecurringChargeCardProps {
    pattern: RecurringChargePattern;
    onEdit?: (pattern: RecurringChargePattern) => void;
    onDelete?: (patternId: string) => void;
    onToggleActive?: (patternId: string, active: boolean) => void;
    onLinkToCategory?: (patternId: string) => void;
}

export interface PatternConfidenceBadgeProps {
    confidence: number; // 0.0-1.0
    size?: 'small' | 'medium' | 'large';
    showLabel?: boolean;
}

export interface NextOccurrencePredictionProps {
    prediction: RecurringChargePrediction;
    pattern?: RecurringChargePattern;
    compact?: boolean;
}

export interface LinkToCategoryDialogProps {
    pattern: RecurringChargePattern;
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (categoryId: string, autoCategorize: boolean) => Promise<void>;
}

export interface DetectionTriggerButtonProps {
    onTrigger: () => Promise<void>;
    disabled?: boolean;
    loading?: boolean;
}

// Utility Types
export interface RecurringChargeFilters {
    active?: boolean;
    minConfidence?: number;
    frequency?: RecurrenceFrequency;
    categoryId?: string;
    searchQuery?: string;
}

export interface RecurringChargeStats {
    totalPatterns: number;
    activePatterns: number;
    averageConfidence: number;
    patternsWithCategories: number;
    upcomingCharges: number;
}

// Helper functions for display
export const getFrequencyLabel = (frequency: RecurrenceFrequency): string => {
    const labels: Record<RecurrenceFrequency, string> = {
        [RecurrenceFrequency.DAILY]: 'Daily',
        [RecurrenceFrequency.WEEKLY]: 'Weekly',
        [RecurrenceFrequency.BI_WEEKLY]: 'Bi-Weekly',
        [RecurrenceFrequency.SEMI_MONTHLY]: 'Semi-Monthly',
        [RecurrenceFrequency.MONTHLY]: 'Monthly',
        [RecurrenceFrequency.BI_MONTHLY]: 'Bi-Monthly',
        [RecurrenceFrequency.QUARTERLY]: 'Quarterly',
        [RecurrenceFrequency.SEMI_ANNUALLY]: 'Semi-Annually',
        [RecurrenceFrequency.ANNUALLY]: 'Annually',
        [RecurrenceFrequency.IRREGULAR]: 'Irregular'
    };
    return labels[frequency];
};

export const getTemporalPatternLabel = (patternType: TemporalPatternType): string => {
    const labels: Record<TemporalPatternType, string> = {
        [TemporalPatternType.DAY_OF_WEEK]: 'Specific Day of Week',
        [TemporalPatternType.DAY_OF_MONTH]: 'Specific Day of Month',
        [TemporalPatternType.FIRST_WORKING_DAY]: 'First Working Day',
        [TemporalPatternType.LAST_WORKING_DAY]: 'Last Working Day',
        [TemporalPatternType.FIRST_DAY_OF_MONTH]: 'First Day of Month',
        [TemporalPatternType.LAST_DAY_OF_MONTH]: 'Last Day of Month',
        [TemporalPatternType.WEEKEND]: 'Weekend',
        [TemporalPatternType.WEEKDAY]: 'Weekday',
        [TemporalPatternType.FLEXIBLE]: 'Flexible'
    };
    return labels[patternType];
};

export const getDayOfWeekLabel = (dayOfWeek: number): string => {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return days[dayOfWeek] || 'Unknown';
};

export const getConfidenceLevel = (confidence: number): 'low' | 'medium' | 'high' => {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
};

export const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return '#10b981'; // green
    if (confidence >= 0.6) return '#f59e0b'; // amber
    return '#ef4444'; // red
};

export const formatAmount = (amount: string): string => {
    try {
        const num = parseFloat(amount);
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(num);
    } catch {
        return amount;
    }
};

export const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
};

export const formatRelativeDate = (timestamp: number): string => {
    const now = Date.now();
    const diff = timestamp - now;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days === -1) return 'Yesterday';
    if (days > 0) return `In ${days} days`;
    return `${Math.abs(days)} days ago`;
};

