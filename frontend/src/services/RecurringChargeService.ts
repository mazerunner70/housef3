/**
 * Recurring Charge Detection Service
 * 
 * This service handles all API communication for recurring charge detection,
 * including pattern management, predictions, and detection triggers.
 */

import { ApiClient } from '@/utils/apiClient';
import { withApiLogging } from '@/utils/logger';
import {
    RecurringChargePattern,
    RecurringChargePatternUpdate,
    RecurringChargePrediction,
    PatternFeedbackCreate,
    DetectRecurringChargesRequest,
    DetectRecurringChargesResponse,
    GetPatternsRequest,
    GetPatternsResponse,
    GetPredictionsRequest,
    GetPredictionsResponse,
    ApplyPatternToCategoryRequest,
    ApplyPatternToCategoryResponse
} from '@/types/RecurringCharge';

/**
 * Trigger recurring charge detection asynchronously
 */
export const triggerDetection = async (
    request: DetectRecurringChargesRequest = {}
): Promise<DetectRecurringChargesResponse> => {
    return await ApiClient.postJson<DetectRecurringChargesResponse>(
        '/recurring-charges/detect',
        request
    );
};

/**
 * Get all recurring charge patterns with optional filters
 */
export const getPatterns = async (
    filters: GetPatternsRequest = {}
): Promise<GetPatternsResponse> => {
    const params = new URLSearchParams();

    if (filters.active !== undefined) {
        params.append('active', String(filters.active));
    }
    if (filters.minConfidence !== undefined) {
        params.append('minConfidence', String(filters.minConfidence));
    }
    if (filters.frequency) {
        params.append('frequency', filters.frequency);
    }
    if (filters.categoryId) {
        params.append('categoryId', filters.categoryId);
    }

    const queryString = params.toString();
    const url = queryString ? `/recurring-charges/patterns?${queryString}` : '/recurring-charges/patterns';

    return await ApiClient.getJson<GetPatternsResponse>(url);
};

/**
 * Get a single recurring charge pattern by ID
 */
export const getPattern = async (patternId: string): Promise<RecurringChargePattern> => {
    const response = await ApiClient.getJson<{ pattern: RecurringChargePattern }>(
        `/recurring-charges/patterns/${patternId}`
    );
    return response.pattern;
};

/**
 * Update a recurring charge pattern
 */
export const updatePattern = async (
    patternId: string,
    updates: RecurringChargePatternUpdate
): Promise<RecurringChargePattern> => {
    const response = await ApiClient.putJson<{ pattern: RecurringChargePattern }>(
        `/recurring-charges/patterns/${patternId}`,
        updates
    );
    return response.pattern;
};

/**
 * Delete a recurring charge pattern
 */
export const deletePattern = async (patternId: string): Promise<void> => {
    await ApiClient.deleteJson(`/recurring-charges/patterns/${patternId}`);
};

/**
 * Get predictions for upcoming recurring charges
 */
export const getPredictions = async (
    filters: GetPredictionsRequest = {}
): Promise<GetPredictionsResponse> => {
    const params = new URLSearchParams();

    if (filters.patternIds && filters.patternIds.length > 0) {
        params.append('patternIds', filters.patternIds.join(','));
    }
    if (filters.startDate) {
        params.append('startDate', filters.startDate);
    }
    if (filters.endDate) {
        params.append('endDate', filters.endDate);
    }
    if (filters.minConfidence !== undefined) {
        params.append('minConfidence', String(filters.minConfidence));
    }

    const queryString = params.toString();
    const url = queryString ? `/recurring-charges/predictions?${queryString}` : '/recurring-charges/predictions';

    return await ApiClient.getJson<GetPredictionsResponse>(url);
};

/**
 * Link a pattern to a category for auto-categorization
 */
export const linkPatternToCategory = async (
    patternId: string,
    request: ApplyPatternToCategoryRequest
): Promise<ApplyPatternToCategoryResponse> => {
    return withApiLogging(
        'RecurringChargeService',
        `/recurring-charges/patterns/${patternId}/apply-category`,
        'POST',
        (url: string) => ApiClient.postJson<ApplyPatternToCategoryResponse>(url, request)
    )();
};

/**
 * Unlink a pattern from its category
 */
export const unlinkPatternFromCategory = async (patternId: string): Promise<RecurringChargePattern> => {
    return await updatePattern(patternId, {
        suggestedCategoryId: undefined,
        autoCategorize: false
    });
};

/**
 * Toggle pattern active status
 */
export const togglePatternActive = async (
    patternId: string,
    active: boolean
): Promise<RecurringChargePattern> => {
    return await updatePattern(patternId, { active });
};

/**
 * Submit feedback for a pattern
 */
export const submitPatternFeedback = async (
    feedback: PatternFeedbackCreate
): Promise<void> => {
    await ApiClient.postJson('/recurring-charges/feedback', feedback);
};

/**
 * Get patterns for a specific category
 */
export const getPatternsByCategory = async (categoryId: string): Promise<RecurringChargePattern[]> => {
    const response = await getPatterns({ categoryId });
    return response.patterns;
};

/**
 * Get upcoming predictions for the next N days
 */
export const getUpcomingPredictions = async (days: number = 30): Promise<RecurringChargePrediction[]> => {
    const startDate = new Date().toISOString().split('T')[0];
    const endDate = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

    const response = await getPredictions({ startDate, endDate });
    return response.predictions;
};

/**
 * Get patterns with high confidence (>= 0.8)
 */
export const getHighConfidencePatterns = async (): Promise<RecurringChargePattern[]> => {
    const response = await getPatterns({ minConfidence: 0.8, active: true });
    return response.patterns;
};

/**
 * Get patterns that need review (low confidence or no category)
 */
export const getPatternsNeedingReview = async (): Promise<RecurringChargePattern[]> => {
    const response = await getPatterns({ active: true });
    return response.patterns.filter(
        pattern => pattern.confidenceScore < 0.6 || !pattern.suggestedCategoryId
    );
};

/**
 * Batch update multiple patterns
 */
export const batchUpdatePatterns = async (
    updates: Array<{ patternId: string; updates: RecurringChargePatternUpdate }>
): Promise<RecurringChargePattern[]> => {
    const promises = updates.map(({ patternId, updates }) => updatePattern(patternId, updates));
    return await Promise.all(promises);
};

/**
 * Get statistics about recurring charge patterns
 */
export const getPatternStatistics = async (): Promise<{
    totalPatterns: number;
    activePatterns: number;
    averageConfidence: number;
    patternsWithCategories: number;
    patternsByFrequency: Record<string, number>;
}> => {
    const response = await getPatterns({});
    const patterns = response.patterns;

    const activePatterns = patterns.filter(p => p.active);
    const patternsWithCategories = patterns.filter(p => p.suggestedCategoryId);
    const avgConfidence = patterns.length > 0
        ? patterns.reduce((sum, p) => sum + p.confidenceScore, 0) / patterns.length
        : 0;

    const patternsByFrequency = patterns.reduce((acc, pattern) => {
        acc[pattern.frequency] = (acc[pattern.frequency] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);

    return {
        totalPatterns: patterns.length,
        activePatterns: activePatterns.length,
        averageConfidence: avgConfidence,
        patternsWithCategories: patternsWithCategories.length,
        patternsByFrequency
    };
};

// Export all functions as a service object for backward compatibility
export const RecurringChargeService = {
    triggerDetection,
    getPatterns,
    getPattern,
    updatePattern,
    deletePattern,
    getPredictions,
    linkPatternToCategory,
    unlinkPatternFromCategory,
    togglePatternActive,
    submitPatternFeedback,
    getPatternsByCategory,
    getUpcomingPredictions,
    getHighConfidencePatterns,
    getPatternsNeedingReview,
    batchUpdatePatterns,
    getPatternStatistics
};

export default RecurringChargeService;

