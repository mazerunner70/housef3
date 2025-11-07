/**
 * Recurring Charge Detection Store
 * 
 * Zustand store for managing recurring charge patterns and predictions with intelligent caching.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import {
    RecurringChargePattern,
    RecurringChargePatternUpdate,
    RecurringChargePrediction,
    RecurringChargeFilters
} from '@/types/RecurringCharge';
import {
    getPatterns,
    getPattern,
    updatePattern as serviceUpdatePattern,
    deletePattern as serviceDeletePattern,
    getPredictions,
    togglePatternActive,
    linkPatternToCategory,
    unlinkPatternFromCategory,
    triggerDetection,
    getPatternStatistics
} from '@/services/RecurringChargeService';

interface RecurringChargeState {
    // Data
    patterns: RecurringChargePattern[];
    predictions: RecurringChargePrediction[];

    // Loading states
    isLoading: boolean;
    isUpdating: boolean;
    isDeleting: boolean;
    isDetecting: boolean;

    // Error handling
    error: string | null;

    // Cache management
    lastFetched: number | null;
    cacheExpiry: number;

    // Filters
    filters: RecurringChargeFilters;

    // Actions
    fetchPatterns: (force?: boolean) => Promise<void>;
    fetchPredictions: (force?: boolean) => Promise<void>;
    updatePattern: (patternId: string, updates: RecurringChargePatternUpdate) => Promise<RecurringChargePattern | null>;
    deletePattern: (patternId: string) => Promise<boolean>;
    toggleActive: (patternId: string, active: boolean) => Promise<boolean>;
    linkToCategory: (patternId: string, categoryId: string, autoCategorize: boolean) => Promise<boolean>;
    unlinkFromCategory: (patternId: string) => Promise<boolean>;
    triggerDetection: (accountIds?: string[], startDate?: string, endDate?: string) => Promise<string | null>;

    // Utility actions
    setFilters: (filters: Partial<RecurringChargeFilters>) => void;
    clearFilters: () => void;
    clearError: () => void;
    invalidateCache: () => void;
    getPatternById: (patternId: string) => RecurringChargePattern | undefined;
    getPredictionsByPatternId: (patternId: string) => RecurringChargePrediction[];
    refreshPatterns: () => Promise<void>;

    // Statistics
    getStatistics: () => Promise<{
        totalPatterns: number;
        activePatterns: number;
        averageConfidence: number;
        patternsWithCategories: number;
        patternsByFrequency: Record<string, number>;
    } | null>;
}

// Cache duration: 5 minutes
const CACHE_DURATION = 5 * 60 * 1000;

export const useRecurringChargeStore = create<RecurringChargeState>()(
    persist(
        (set, get) => ({
            // Initial state
            patterns: [],
            predictions: [],
            isLoading: false,
            isUpdating: false,
            isDeleting: false,
            isDetecting: false,
            error: null,
            lastFetched: null,
            cacheExpiry: CACHE_DURATION,
            filters: {},

            // Fetch patterns with intelligent caching
            fetchPatterns: async (force = false) => {
                const state = get();
                const now = Date.now();

                // Check if we need to fetch
                const shouldFetch = force ||
                    !state.lastFetched ||
                    (now - state.lastFetched) > state.cacheExpiry ||
                    state.patterns.length === 0;

                if (!shouldFetch) {
                    return;
                }

                set({ isLoading: true, error: null });

                try {
                    const response = await getPatterns(state.filters);
                    set({
                        patterns: response.patterns,
                        isLoading: false,
                        lastFetched: now,
                        error: null
                    });
                } catch (err: any) {
                    console.error('Error fetching recurring charge patterns:', err);
                    set({
                        error: err.message || 'Failed to fetch patterns',
                        isLoading: false
                    });
                }
            },

            // Fetch predictions
            fetchPredictions: async (force = false) => {
                const state = get();

                set({ isLoading: true, error: null });

                try {
                    const response = await getPredictions({
                        minConfidence: state.filters.minConfidence
                    });
                    set({
                        predictions: response.predictions,
                        isLoading: false,
                        error: null
                    });
                } catch (err: any) {
                    console.error('Error fetching predictions:', err);
                    set({
                        error: err.message || 'Failed to fetch predictions',
                        isLoading: false
                    });
                }
            },

            // Update pattern with optimistic updates
            updatePattern: async (patternId: string, updates: RecurringChargePatternUpdate) => {
                const state = get();
                const originalPattern = state.patterns.find(p => p.patternId === patternId);

                if (!originalPattern) {
                    set({ error: 'Pattern not found' });
                    return null;
                }

                // Optimistic update
                const optimisticPattern: RecurringChargePattern = {
                    ...originalPattern,
                    ...updates,
                    updatedAt: Date.now()
                };

                set(state => ({
                    patterns: state.patterns.map(p =>
                        p.patternId === patternId ? optimisticPattern : p
                    ),
                    isUpdating: true,
                    error: null
                }));

                try {
                    const updatedPattern = await serviceUpdatePattern(patternId, updates);

                    set(state => ({
                        patterns: state.patterns.map(p =>
                            p.patternId === patternId ? updatedPattern : p
                        ),
                        isUpdating: false,
                        error: null
                    }));

                    return updatedPattern;
                } catch (err: any) {
                    console.error('Error updating pattern:', err);

                    // Revert optimistic update
                    set(state => ({
                        patterns: state.patterns.map(p =>
                            p.patternId === patternId ? originalPattern : p
                        ),
                        error: err.message || 'Failed to update pattern',
                        isUpdating: false
                    }));
                    return null;
                }
            },

            // Delete pattern with optimistic updates
            deletePattern: async (patternId: string) => {
                const state = get();
                const originalPatterns = [...state.patterns];

                // Optimistic delete
                set(state => ({
                    patterns: state.patterns.filter(p => p.patternId !== patternId),
                    isDeleting: true,
                    error: null
                }));

                try {
                    await serviceDeletePattern(patternId);
                    set({ isDeleting: false, error: null });
                    return true;
                } catch (err: any) {
                    console.error('Error deleting pattern:', err);

                    // Revert optimistic delete
                    set({
                        patterns: originalPatterns,
                        error: err.message || 'Failed to delete pattern',
                        isDeleting: false
                    });
                    return false;
                }
            },

            // Toggle pattern active status
            toggleActive: async (patternId: string, active: boolean) => {
                const result = await get().updatePattern(patternId, { active });
                return result !== null;
            },

            // Link pattern to category
            linkToCategory: async (patternId: string, categoryId: string, autoCategorize: boolean) => {
                try {
                    set({ isUpdating: true, error: null });
                    await linkPatternToCategory(patternId, { categoryId, autoCategorize });

                    // Update local state
                    set(state => ({
                        patterns: state.patterns.map(p =>
                            p.patternId === patternId
                                ? { ...p, suggestedCategoryId: categoryId, autoCategorize }
                                : p
                        ),
                        isUpdating: false,
                        error: null
                    }));

                    return true;
                } catch (err: any) {
                    console.error('Error linking pattern to category:', err);
                    set({
                        error: err.message || 'Failed to link pattern to category',
                        isUpdating: false
                    });
                    return false;
                }
            },

            // Unlink pattern from category
            unlinkFromCategory: async (patternId: string) => {
                try {
                    set({ isUpdating: true, error: null });
                    await unlinkPatternFromCategory(patternId);

                    // Update local state
                    set(state => ({
                        patterns: state.patterns.map(p =>
                            p.patternId === patternId
                                ? { ...p, suggestedCategoryId: undefined, autoCategorize: false }
                                : p
                        ),
                        isUpdating: false,
                        error: null
                    }));

                    return true;
                } catch (err: any) {
                    console.error('Error unlinking pattern from category:', err);
                    set({
                        error: err.message || 'Failed to unlink pattern from category',
                        isUpdating: false
                    });
                    return false;
                }
            },

            // Trigger detection
            triggerDetection: async (accountIds?: string[], startDate?: string, endDate?: string) => {
                try {
                    set({ isDetecting: true, error: null });
                    const response = await triggerDetection({ accountIds, startDate, endDate });
                    set({ isDetecting: false });

                    // Invalidate cache to force refresh on next fetch
                    get().invalidateCache();

                    return response.operationId;
                } catch (err: any) {
                    console.error('Error triggering detection:', err);
                    set({
                        error: err.message || 'Failed to trigger detection',
                        isDetecting: false
                    });
                    return null;
                }
            },

            // Set filters
            setFilters: (newFilters: Partial<RecurringChargeFilters>) => {
                set(state => ({
                    filters: { ...state.filters, ...newFilters }
                }));
                // Invalidate cache when filters change
                get().invalidateCache();
            },

            // Clear filters
            clearFilters: () => {
                set({ filters: {} });
                get().invalidateCache();
            },

            // Utility actions
            clearError: () => set({ error: null }),

            invalidateCache: () => set({ lastFetched: null }),

            getPatternById: (patternId: string) => {
                const state = get();
                return state.patterns.find(p => p.patternId === patternId);
            },

            getPredictionsByPatternId: (patternId: string) => {
                const state = get();
                return state.predictions.filter(pred => pred.patternId === patternId);
            },

            refreshPatterns: async () => {
                set({ lastFetched: null });
                await get().fetchPatterns(true);
            },

            // Get statistics
            getStatistics: async () => {
                try {
                    const stats = await getPatternStatistics();
                    return stats;
                } catch (err: any) {
                    console.error('Error fetching statistics:', err);
                    return null;
                }
            }
        }),
        {
            name: 'recurring-charge-storage',
            storage: createJSONStorage(() => localStorage),
            partialize: (state) => ({
                patterns: state.patterns,
                predictions: state.predictions,
                lastFetched: state.lastFetched,
                cacheExpiry: state.cacheExpiry,
                filters: state.filters
            })
        }
    )
);

// Selector hooks with explicit return types
export const usePatterns = (): RecurringChargePattern[] =>
    useRecurringChargeStore(state => state.patterns);

export const usePredictions = (): RecurringChargePrediction[] =>
    useRecurringChargeStore(state => state.predictions);

export const useRecurringChargeLoading = (): {
    isLoading: boolean;
    isUpdating: boolean;
    isDeleting: boolean;
    isDetecting: boolean;
} => useRecurringChargeStore(state => ({
    isLoading: state.isLoading,
    isUpdating: state.isUpdating,
    isDeleting: state.isDeleting,
    isDetecting: state.isDetecting
}));

export const useRecurringChargeError = (): string | null =>
    useRecurringChargeStore(state => state.error);

export const useRecurringChargeFilters = (): RecurringChargeFilters =>
    useRecurringChargeStore(state => state.filters);

// Individual action selectors
export const useFetchPatterns = (): ((force?: boolean) => Promise<void>) =>
    useRecurringChargeStore(state => state.fetchPatterns);

export const useFetchPredictions = (): ((force?: boolean) => Promise<void>) =>
    useRecurringChargeStore(state => state.fetchPredictions);

export const useUpdatePattern = (): ((patternId: string, updates: RecurringChargePatternUpdate) => Promise<RecurringChargePattern | null>) =>
    useRecurringChargeStore(state => state.updatePattern);

export const useDeletePattern = (): ((patternId: string) => Promise<boolean>) =>
    useRecurringChargeStore(state => state.deletePattern);

export const useTogglePatternActive = (): ((patternId: string, active: boolean) => Promise<boolean>) =>
    useRecurringChargeStore(state => state.toggleActive);

export const useLinkToCategory = (): ((patternId: string, categoryId: string, autoCategorize: boolean) => Promise<boolean>) =>
    useRecurringChargeStore(state => state.linkToCategory);

export const useUnlinkFromCategory = (): ((patternId: string) => Promise<boolean>) =>
    useRecurringChargeStore(state => state.unlinkFromCategory);

export const useTriggerDetection = (): ((accountIds?: string[], startDate?: string, endDate?: string) => Promise<string | null>) =>
    useRecurringChargeStore(state => state.triggerDetection);

// Combined hook for convenience (single subscription pattern)
export const useRecurringCharges = () => {
    const storeState = useRecurringChargeStore();

    return {
        patterns: storeState.patterns,
        predictions: storeState.predictions,
        isLoading: storeState.isLoading || storeState.isUpdating || storeState.isDeleting || storeState.isDetecting,
        error: storeState.error,
        filters: storeState.filters,
        fetchPatterns: storeState.fetchPatterns,
        fetchPredictions: storeState.fetchPredictions,
        updatePattern: storeState.updatePattern,
        deletePattern: storeState.deletePattern,
        toggleActive: storeState.toggleActive,
        linkToCategory: storeState.linkToCategory,
        unlinkFromCategory: storeState.unlinkFromCategory,
        triggerDetection: storeState.triggerDetection,
        setFilters: storeState.setFilters,
        clearFilters: storeState.clearFilters,
        clearError: storeState.clearError,
        invalidateCache: storeState.invalidateCache,
        getPatternById: storeState.getPatternById,
        getPredictionsByPatternId: storeState.getPredictionsByPatternId,
        refreshPatterns: storeState.refreshPatterns,
        getStatistics: storeState.getStatistics
    };
};

export default useRecurringCharges;

