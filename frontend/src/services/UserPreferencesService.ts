import ApiClient from "@/utils/apiClient";
import {
    withApiLogging,
    withServiceLogging,
    createLogger
} from '@/utils/logger';
import { validateApiResponse } from "@/utils/zodErrorHandler";
import { z } from 'zod';

// Logger for simple operations only
const logger = createLogger('UserPreferencesService');

// Zod Schemas for validation
const TransferPreferencesSchema = z.object({
    defaultDateRangeDays: z.number().optional(),
    lastUsedDateRanges: z.array(z.number()).optional(),
    autoExpandSuggestion: z.boolean().optional(),
    checkedDateRangeStart: z.number().optional(),
    checkedDateRangeEnd: z.number().optional()
});

const UIPreferencesSchema = z.object({
    theme: z.string().optional(),
    compactView: z.boolean().optional(),
    defaultPageSize: z.number().optional()
});

const TransactionPreferencesSchema = z.object({
    defaultSortBy: z.string().optional(),
    defaultSortOrder: z.string().optional(),
    defaultPageSize: z.number().optional()
});

const UserPreferencesSchema = z.object({
    userId: z.string().optional(),
    preferences: z.object({
        transfers: TransferPreferencesSchema.optional(),
        ui: UIPreferencesSchema.optional(),
        transactions: TransactionPreferencesSchema.optional()
    }).optional(),
    createdAt: z.number().optional(),
    updatedAt: z.number().optional()
});

// TypeScript Interfaces (following naming conventions)
export interface TransferPreferences {
    defaultDateRangeDays?: number;
    lastUsedDateRanges?: number[];
    autoExpandSuggestion?: boolean;
    checkedDateRangeStart?: number; // milliseconds since epoch
    checkedDateRangeEnd?: number;   // milliseconds since epoch
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

export interface UserPreferencesResponse {
    userId?: string;
    preferences?: {
        transfers?: TransferPreferences;
        ui?: UIPreferences;
        transactions?: TransactionPreferences;
    };
    createdAt?: number;
    updatedAt?: number;
}

export interface UserPreferencesUpdateRequest {
    preferences: {
        transfers?: TransferPreferences;
        ui?: UIPreferences;
        transactions?: TransactionPreferences;
    };
}

/**
 * Get all user preferences
 */
export const getUserPreferences = withApiLogging(
    'UserPreferencesService',
    '/user-preferences',
    'GET',
    async () => {
        return validateApiResponse(
            () => ApiClient.getJson<any>('/user-preferences'),
            (rawData) => UserPreferencesSchema.parse(rawData),
            'user preferences data'
        );
    },
    {
        successData: (result) => ({
            hasPreferences: !!result.preferences,
            hasTransfers: !!result.preferences?.transfers,
            hasUI: !!result.preferences?.ui,
            hasTransactions: !!result.preferences?.transactions
        })
    }
);

/**
 * Update user preferences
 */
export const updateUserPreferences = withServiceLogging(
    'UserPreferencesService',
    'updateUserPreferences',
    async (preferences: Partial<UserPreferencesResponse['preferences']>) => {
        return validateApiResponse(
            () => ApiClient.putJson<any>('/user-preferences', { preferences }),
            (rawData) => UserPreferencesSchema.parse(rawData),
            'updated user preferences data',
            'Failed to update user preferences. The server response format is invalid.'
        );
    },
    {
        logArgs: ([preferences]) => ({
            updateKeys: Object.keys(preferences || {}),
            hasTransfers: !!preferences?.transfers,
            hasUI: !!preferences?.ui,
            hasTransactions: !!preferences?.transactions
        }),
        logResult: (result) => ({
            userId: result.userId,
            hasPreferences: !!result.preferences,
            updatedKeys: Object.keys(result.preferences || {})
        })
    }
);

/**
 * Get transfer-specific preferences with graceful degradation
 */
export const getTransferPreferences = async (): Promise<TransferPreferences> => {
    logger.info('Fetching transfer preferences');

    try {
        const preferences = await validateApiResponse(
            () => ApiClient.getJson<any>('/user-preferences/transfers'),
            (rawData) => TransferPreferencesSchema.parse(rawData),
            'transfer preferences data'
        );

        logger.info('Transfer preferences fetched successfully', {
            defaultDays: preferences.defaultDateRangeDays,
            hasLastUsedRanges: !!preferences.lastUsedDateRanges?.length,
            autoExpand: preferences.autoExpandSuggestion
        });

        return preferences;
    } catch (error) {
        logger.warn('Failed to fetch transfer preferences, returning defaults', {
            operation: 'getTransferPreferences',
            fallbackUsed: true
        });

        // Return sensible defaults for non-critical data
        return {
            defaultDateRangeDays: 7,
            lastUsedDateRanges: [7, 14, 30],
            autoExpandSuggestion: true,
            checkedDateRangeStart: undefined,
            checkedDateRangeEnd: undefined
        };
    }
};

/**
 * Update transfer-specific preferences
 */
export const updateTransferPreferences = withServiceLogging(
    'UserPreferencesService',
    'updateTransferPreferences',
    async (transferPrefs: Partial<TransferPreferences>) => {
        return validateApiResponse(
            () => ApiClient.putJson<any>('/user-preferences/transfers', transferPrefs),
            (rawData) => UserPreferencesSchema.parse(rawData),
            'updated transfer preferences data',
            'Failed to update transfer preferences. The server response format is invalid.'
        );
    },
    {
        logArgs: ([transferPrefs]) => ({
            updateKeys: Object.keys(transferPrefs),
            defaultDays: transferPrefs.defaultDateRangeDays,
            hasDateRanges: !!transferPrefs.lastUsedDateRanges?.length,
            autoExpand: transferPrefs.autoExpandSuggestion
        }),
        logResult: (result) => ({
            userId: result.userId,
            hasPreferences: !!result.preferences,
            hasTransfers: !!result.preferences?.transfers
        })
    }
);

/**
 * Get the date range that has been checked so far for transfer pairs
 */
export const getTransferCheckedDateRange = withServiceLogging(
    'UserPreferencesService',
    'getTransferCheckedDateRange',
    async (): Promise<{ startDate: number | null; endDate: number | null }> => {
        const preferences = await getTransferPreferences();

        return {
            startDate: preferences.checkedDateRangeStart || null,
            endDate: preferences.checkedDateRangeEnd || null
        };
    },
    {
        logResult: (result) => ({
            hasStartDate: result.startDate !== null,
            hasEndDate: result.endDate !== null,
            startDate: result.startDate,
            endDate: result.endDate
        })
    }
);

/**
 * Update the date range that has been checked for transfer pairs
 */
export const updateTransferCheckedDateRange = withServiceLogging(
    'UserPreferencesService',
    'updateTransferCheckedDateRange',
    async (startDate: number, endDate: number) => {
        const updateData: Partial<TransferPreferences> = {
            checkedDateRangeStart: startDate,
            checkedDateRangeEnd: endDate
        };

        return await updateTransferPreferences(updateData);
    },
    {
        logArgs: ([startDate, endDate]) => ({
            startDate,
            endDate,
            operation: 'updateTransferCheckedDateRange'
        }),
        logResult: (result) => ({
            userId: result.userId,
            success: !!result.preferences?.transfers
        })
    }
);

/**
 * Get the overall account date range for transfer checking
 */
export const getAccountDateRangeForTransfers = withApiLogging(
    'UserPreferencesService',
    '/user-preferences/account-date-range',
    'GET',
    async () => {
        return validateApiResponse(
            () => ApiClient.getJson<any>('/user-preferences/account-date-range'),
            (rawData) => z.object({
                startDate: z.number().nullable(),
                endDate: z.number().nullable()
            }).parse(rawData),
            'account date range data',
            'Failed to get account date range for transfers.'
        );
    },
    {
        successData: (result) => ({
            hasDateRange: !!(result.startDate && result.endDate),
            startDate: result.startDate,
            endDate: result.endDate
        })
    }
);

// Default preference functions
/**
 * Get default transfer preferences
 */
export const getDefaultTransferPreferences = (): TransferPreferences => {
    return {
        defaultDateRangeDays: 7,
        lastUsedDateRanges: [7, 14, 30],
        autoExpandSuggestion: true,
        checkedDateRangeStart: undefined,
        checkedDateRangeEnd: undefined
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
