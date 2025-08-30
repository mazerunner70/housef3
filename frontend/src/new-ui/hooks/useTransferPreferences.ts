import { useState, useEffect, useCallback } from 'react';
import {
    TransferPreferences,
    getTransferPreferences,
    updateTransferPreferences,
    getDefaultTransferPreferences
} from '@/services/UserPreferencesService';

export interface UseTransferPreferencesReturn {
    preferences: TransferPreferences;
    updatePreferences: (updates: Partial<TransferPreferences>) => Promise<void>;
    loading: boolean;
    error: string | null;
    resetToDefaults: () => Promise<void>;
}

/**
 * Hook for managing transfer-specific preferences
 */
export const useTransferPreferences = (): UseTransferPreferencesReturn => {
    const [preferences, setPreferences] = useState<TransferPreferences>(getDefaultTransferPreferences());
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Load preferences on mount
    useEffect(() => {
        const loadPreferences = async () => {
            try {
                setLoading(true);
                setError(null);
                const userPrefs = await getTransferPreferences();
                setPreferences(prev => ({ ...prev, ...userPrefs }));
            } catch (err) {
                console.error('Failed to load transfer preferences:', err);
                setError(err instanceof Error ? err.message : 'Failed to load preferences');
                // Keep default preferences on error
            } finally {
                setLoading(false);
            }
        };

        loadPreferences();
    }, []);

    // Update preferences
    const updatePreferences = useCallback(async (updates: Partial<TransferPreferences>) => {
        // Capture original state before optimistic update
        const originalPreferences = preferences;

        try {
            setError(null);

            // Optimistically update local state
            const newPreferences = { ...preferences, ...updates };
            setPreferences(newPreferences);

            // Update on server
            await updateTransferPreferences(updates);
        } catch (err) {
            console.error('Failed to update transfer preferences:', err);
            setError(err instanceof Error ? err.message : 'Failed to update preferences');

            // Revert optimistic update on error using original state
            setPreferences(originalPreferences);
            throw err;
        }
    }, [preferences]);

    // Reset to defaults
    const resetToDefaults = useCallback(async () => {
        const defaults = getDefaultTransferPreferences();
        await updatePreferences(defaults);
    }, [updatePreferences]);

    return {
        preferences,
        updatePreferences,
        loading,
        error,
        resetToDefaults
    };
};

/**
 * Hook for managing date range preferences specifically
 */
export const useDateRangePreferences = () => {
    const { preferences, updatePreferences, loading, error } = useTransferPreferences();

    const updateDateRange = useCallback(async (newDays: number) => {
        // Update the default and add to recently used ranges
        const currentRanges = preferences.lastUsedDateRanges || [7, 14, 30];
        const updatedRanges = [
            newDays,
            ...currentRanges.filter(d => d !== newDays)
        ].slice(0, 3); // Keep only last 3

        await updatePreferences({
            defaultDateRangeDays: newDays,
            lastUsedDateRanges: updatedRanges
        });
    }, [preferences.lastUsedDateRanges, updatePreferences]);

    const getQuickRangeOptions = useCallback(() => {
        return preferences.lastUsedDateRanges || [7, 14, 30];
    }, [preferences.lastUsedDateRanges]);

    return {
        currentDateRange: preferences.defaultDateRangeDays || 7,
        quickRangeOptions: getQuickRangeOptions(),
        updateDateRange,
        autoExpandSuggestion: preferences.autoExpandSuggestion ?? true,
        loading,
        error
    };
};
