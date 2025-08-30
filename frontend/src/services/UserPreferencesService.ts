import ApiClient from "@/utils/apiClient";
import { createLogger } from "@/utils/logger";

const logger = createLogger('UserPreferencesService');

export interface TransferPreferences {
    defaultDateRangeDays?: number;
    lastUsedDateRanges?: number[];
    autoExpandSuggestion?: boolean;
}

export interface UIPreferences {
    theme?: string;
    compactView?: boolean;
    defaultPageSize?: number;
}

export interface TransactionPreferences {
    defaultSortBy?: string;
    defaultSortOrder?: string;
    defaultPageSize?: number;
}

export interface UserPreferences {
    userId?: string;
    preferences?: {
        transfers?: TransferPreferences;
        ui?: UIPreferences;
        transactions?: TransactionPreferences;
    };
    createdAt?: number;
    updatedAt?: number;
}

export interface UserPreferencesUpdate {
    preferences: {
        transfers?: TransferPreferences;
        ui?: UIPreferences;
        transactions?: TransactionPreferences;
    };
}

/**
 * Get all user preferences
 */
export const getUserPreferences = async (): Promise<UserPreferences> => {
    logger.info('Fetching user preferences');
    const startTime = performance.now();

    try {
        const preferences = await ApiClient.getJson<UserPreferences>('/user-preferences');
        const duration = performance.now() - startTime;

        logger.info('User preferences fetched successfully', {
            duration: `${duration.toFixed(2)}ms`,
            hasPreferences: !!preferences.preferences
        });

        return preferences;
    } catch (error) {
        const duration = performance.now() - startTime;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        logger.error('Failed to fetch user preferences from API', {
            duration: `${duration.toFixed(2)}ms`,
            error: errorMessage,
            operation: 'getUserPreferences'
        });

        throw error;
    }
};

/**
 * Update user preferences
 */
export const updateUserPreferences = async (preferences: Partial<UserPreferences['preferences']>): Promise<UserPreferences> => {
    const prefsToUpdate = preferences || {};
    logger.info('Updating user preferences', {
        updateKeys: Object.keys(prefsToUpdate),
        hasTransfers: !!prefsToUpdate.transfers,
        hasUI: !!prefsToUpdate.ui,
        hasTransactions: !!prefsToUpdate.transactions
    });
    const startTime = performance.now();

    try {
        const updatedPreferences = await ApiClient.putJson<UserPreferences>('/user-preferences', { preferences });
        const duration = performance.now() - startTime;

        logger.info('User preferences updated successfully', {
            duration: `${duration.toFixed(2)}ms`,
            updatedKeys: Object.keys(prefsToUpdate)
        });

        return updatedPreferences;
    } catch (error) {
        const duration = performance.now() - startTime;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        logger.error('Failed to update user preferences via API', {
            duration: `${duration.toFixed(2)}ms`,
            error: errorMessage,
            operation: 'updateUserPreferences',
            attemptedUpdate: Object.keys(prefsToUpdate)
        });

        throw error;
    }
};

/**
 * Get transfer-specific preferences
 */
export const getTransferPreferences = async (): Promise<TransferPreferences> => {
    logger.info('Fetching transfer preferences');
    const startTime = performance.now();

    try {
        const preferences = await ApiClient.getJson<TransferPreferences>('/user-preferences/transfers');
        const duration = performance.now() - startTime;

        logger.info('Transfer preferences fetched successfully', {
            duration: `${duration.toFixed(2)}ms`,
            defaultDays: preferences.defaultDateRangeDays,
            hasLastUsedRanges: !!preferences.lastUsedDateRanges?.length
        });

        return preferences;
    } catch (error) {
        const duration = performance.now() - startTime;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        logger.warn('Failed to fetch transfer preferences, returning defaults', {
            duration: `${duration.toFixed(2)}ms`,
            error: errorMessage,
            operation: 'getTransferPreferences'
        });

        // Return defaults on error
        return {
            defaultDateRangeDays: 7,
            lastUsedDateRanges: [7, 14, 30],
            autoExpandSuggestion: true
        };
    }
};

/**
 * Update transfer-specific preferences
 */
export const updateTransferPreferences = async (transferPrefs: Partial<TransferPreferences>): Promise<UserPreferences> => {
    logger.info('Updating transfer preferences', {
        updateKeys: Object.keys(transferPrefs),
        defaultDays: transferPrefs.defaultDateRangeDays,
        hasDateRanges: !!transferPrefs.lastUsedDateRanges?.length,
        autoExpand: transferPrefs.autoExpandSuggestion
    });
    const startTime = performance.now();

    try {
        const updatedPreferences = await ApiClient.putJson<UserPreferences>('/user-preferences/transfers', transferPrefs);
        const duration = performance.now() - startTime;

        logger.info('Transfer preferences updated successfully', {
            duration: `${duration.toFixed(2)}ms`,
            updatedKeys: Object.keys(transferPrefs)
        });

        return updatedPreferences;
    } catch (error) {
        const duration = performance.now() - startTime;
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        logger.error('Failed to update transfer preferences via API', {
            duration: `${duration.toFixed(2)}ms`,
            error: errorMessage,
            operation: 'updateTransferPreferences',
            attemptedUpdate: Object.keys(transferPrefs)
        });

        throw error;
    }
};

/**
 * Get default transfer preferences
 */
export const getDefaultTransferPreferences = (): TransferPreferences => {
    return {
        defaultDateRangeDays: 7,
        lastUsedDateRanges: [7, 14, 30],
        autoExpandSuggestion: true
    };
};

/**
 * Get default UI preferences
 */
export const getDefaultUIPreferences = (): UIPreferences => {
    return {
        theme: 'light',
        compactView: false,
        defaultPageSize: 50
    };
};

/**
 * Get default transaction preferences
 */
export const getDefaultTransactionPreferences = (): TransactionPreferences => {
    return {
        defaultSortBy: 'date',
        defaultSortOrder: 'desc',
        defaultPageSize: 50
    };
};
