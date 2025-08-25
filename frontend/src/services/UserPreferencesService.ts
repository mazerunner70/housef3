import { apiClient } from '@/utils/apiClient';

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
    try {
        const response = await apiClient.get('/user-preferences');
        return response.data;
    } catch (error) {
        console.error('Failed to get user preferences:', error);
        throw error;
    }
};

/**
 * Update user preferences
 */
export const updateUserPreferences = async (preferences: Partial<UserPreferences['preferences']>): Promise<UserPreferences> => {
    try {
        const response = await apiClient.put('/user-preferences', { preferences });
        return response.data;
    } catch (error) {
        console.error('Failed to update user preferences:', error);
        throw error;
    }
};

/**
 * Get transfer-specific preferences
 */
export const getTransferPreferences = async (): Promise<TransferPreferences> => {
    try {
        const response = await apiClient.get('/user-preferences/transfers');
        return response.data;
    } catch (error) {
        console.error('Failed to get transfer preferences:', error);
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
    try {
        const response = await apiClient.put('/user-preferences/transfers', transferPrefs);
        return response.data;
    } catch (error) {
        console.error('Failed to update transfer preferences:', error);
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
