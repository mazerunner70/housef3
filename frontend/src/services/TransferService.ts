// 1. Imports
import { z } from 'zod';
import ApiClient from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import {
    withApiLogging,
    withServiceLogging,
    createLogger
} from '@/utils/logger';
import {
    getTransferDataForProgress,
    resetTransferCheckedDateRange
} from './UserPreferencesService';
import {
    epochToDate,
    dateRangeToEpochRange,
    formatDisplayDate,
    subtractDays
} from '@/utils/dateUtils';

// 2. Type Definitions - Domain interfaces
// Simplified transaction type for transfer operations (matches backend output)
export interface TransferTransaction {
    transactionId: string;
    fileId: string;
    userId: string;
    date: number;
    description: string;
    amount: number;
    balance: number;
    currency: string;
    accountId?: string | null;
    transactionType?: string | null;
    category?: string | null;
    payee?: string | null;
    memo?: string | null;
    checkNumber?: string | null;
    reference?: string | null;
    status?: string | null;
    debitOrCredit?: string | null;
    importOrder?: number | null;
    id?: string | null;
    primaryCategoryId?: string | null;
    categories?: any[] | null;
    account?: string | null;
    type?: string | null;
    notes?: string | null;
    isSplit?: boolean | null;
    [key: string]: any; // Allow additional fields
}

export interface TransferPair {
    outgoingTransaction: TransferTransaction;
    incomingTransaction: TransferTransaction;
    amount: number;
    dateDifference: number; // Days between transactions
}

export interface DetectedTransfer {
    outgoingTransactionId: string;
    incomingTransactionId: string;
    amount: number;
    dateDifference: number;
}

// Request/Response interfaces following conventions
export interface TransferDetectionRequest {
    startDate: number; // milliseconds since epoch - API layer
    endDate: number;   // milliseconds since epoch - API layer
}

export interface TransferListParams {
    startDate?: number; // milliseconds since epoch - API layer
    endDate?: number;   // milliseconds since epoch - API layer
    limit?: number;
    offset?: number;
}

export interface PairedTransfersResponse {
    pairedTransfers: TransferPair[];
    count: number;
    dateRange?: {
        startDate: number;
        endDate: number;
    };
}

export interface DetectedTransfersResponse {
    transfers: TransferPair[];
    count: number;
    dateRange: {
        startDate: number;
        endDate: number;
    };
    progressTrackingWarning?: string; // Warning if progress tracking failed
}

export interface MarkTransferPairRequest {
    outgoingTransactionId: string;
    incomingTransactionId: string;
}

export interface BulkMarkTransfersRequest {
    transferPairs: Array<{
        outgoingTransactionId: string;
        incomingTransactionId: string;
    }>;
}

export interface BulkMarkTransfersResponse {
    successCount: number;
    failureCount: number;
    successful: Array<{ outgoingTransactionId: string; incomingTransactionId: string }>;
    failed: Array<{ pair: any; error: string }>;
}

// Date range utilities - keeping API types separate from application types
export interface ApiDateRange {
    startDate: number; // milliseconds since epoch - for API communication
    endDate: number;   // milliseconds since epoch - for API communication
}

// Application layer should use the Date object version from dateUtils
export interface DateRange {
    startDate: Date; // Application layer works with Date objects
    endDate: Date;   // Application layer works with Date objects
}

// Transfer progress data interfaces
export interface TransferProgressData {
    hasData: boolean;
    totalDays: number;
    checkedDays: number;
    progressPercentage: number;
    isComplete: boolean;
    accountDateRange?: ApiDateRange;  // Keep as epoch for this legacy interface
    checkedDateRange?: ApiDateRange; // Keep as epoch for this legacy interface  
    error?: string;
}

export interface CheckedRange {
    startDate?: number | null; // milliseconds since epoch
    endDate?: number | null;   // milliseconds since epoch
}

export interface AccountRange {
    startDate?: number | null; // milliseconds since epoch
    endDate?: number | null;   // milliseconds since epoch
}

// 3. Zod validation schemas
// Simplified transaction schema for transfer operations (matches backend model_dump output)
const TransferTransactionSchema = z.object({
    transactionId: z.string(),
    fileId: z.string(),
    userId: z.string(),
    date: z.number(),
    description: z.string(),
    amount: z.union([z.number(), z.string()]).transform(val => Number(val)), // Backend returns as number/string
    balance: z.union([z.number(), z.string()]).transform(val => Number(val)), // Backend returns as number/string
    currency: z.string(),
    accountId: z.string().nullish(), // Handle null values from backend
    transactionType: z.string().nullish(), // Handle null values from backend
    category: z.string().nullish(), // Handle null values from backend
    payee: z.string().nullish(), // Handle null values from backend
    memo: z.string().nullish(), // Handle null values from backend
    checkNumber: z.string().nullish(), // Handle null values from backend
    reference: z.string().nullish(), // Handle null values from backend
    status: z.string().nullish(), // Handle null values from backend
    debitOrCredit: z.string().nullish(), // Handle null values from backend
    importOrder: z.number().nullish(), // Handle null values from backend
    id: z.string().nullish(), // Handle null values from backend
    primaryCategoryId: z.string().nullish(), // Handle null values from backend
    categories: z.array(z.any()).nullish(), // Handle null values from backend
    account: z.string().nullish(), // Handle null values from backend
    type: z.string().nullish(), // Handle null values from backend
    notes: z.string().nullish(), // Handle null values from backend
    isSplit: z.boolean().nullish() // Handle null values from backend
}); // Allow additional fields from backend

const TransferPairSchema = z.object({
    outgoingTransaction: TransferTransactionSchema,
    incomingTransaction: TransferTransactionSchema,
    amount: z.union([z.number(), z.string()]).transform(val => Number(val)), // Backend may return as string
    dateDifference: z.number()
});

const PairedTransfersResponseSchema = z.object({
    pairedTransfers: z.array(TransferPairSchema),
    count: z.number(),
    dateRange: z.object({
        startDate: z.number(),
        endDate: z.number()
    }).nullable().optional()
});

const DetectedTransfersResponseSchema = z.object({
    transfers: z.array(TransferPairSchema),
    count: z.number(),
    dateRange: z.object({
        startDate: z.number(),
        endDate: z.number()
    }),
    progressTrackingWarning: z.string().optional()
});

const BulkMarkResponseSchema = z.object({
    successful: z.array(z.object({
        outgoingTransactionId: z.string(),
        incomingTransactionId: z.string()
    })),
    failed: z.array(z.object({
        pair: z.any(),
        error: z.string()
    })),
    successCount: z.number(),
    failureCount: z.number()
});

// 4. Constants and logger setup
const API_ENDPOINT = '/transfers';
const logger = createLogger('TransferService');

// 5. Exported Functions - API operations with efficient logging

/**
 * Get total count of all paired transfers for the user (no date filtering)
 * @returns Promise resolving to total count
 */
export const getTotalPairedTransfersCount = () => {
    const query = new URLSearchParams();
    query.append('count_only', 'true');

    return withApiLogging(
        'TransferService',
        `${API_ENDPOINT}/paired`,
        'GET',
        async (url) => {
            return validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    // Expect just a count response
                    return rawData.count || 0;
                },
                'paired transfers count',
                'Failed to load paired transfers count.'
            );
        },
        {
            operationName: 'getTotalPairedTransfersCount',
            queryParams: query,
            successData: (result) => ({
                totalCount: result
            })
        }
    );
};

/**
 * Get existing paired transfer transactions within a date range
 * @param params Optional parameters for filtering and pagination
 * @returns Promise resolving to paired transfers response
 */
export const listPairedTransfers = (params?: TransferListParams) => {
    const query = new URLSearchParams();

    if (params?.startDate && params?.endDate) {
        // Use milliseconds since epoch
        query.append('startDate', params.startDate.toString());
        query.append('endDate', params.endDate.toString());
    }

    if (params?.limit) {
        query.append('limit', params.limit.toString());
    }

    if (params?.offset) {
        query.append('offset', params.offset.toString());
    }

    return withApiLogging(
        'TransferService',
        `${API_ENDPOINT}/paired`,
        'GET',
        async (url) => {
            return validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    const validatedResponse = PairedTransfersResponseSchema.parse(rawData);
                    return validatedResponse;
                },
                'paired transfers data',
                'Failed to load paired transfers. The transfer data format is invalid.'
            );
        },
        {
            operationName: 'listPairedTransfers',
            queryParams: query.toString() ? query : undefined,
            successData: (result) => ({
                transferCount: result.pairedTransfers.length,
                hasDateRange: !!result.dateRange
            })
        }
    );
};

/**
 * Detect potential transfer transactions within a date range (APPLICATION LAYER)
 * @param dateRange DateRange with Date objects from application logic
 * @returns Promise resolving to detected transfers response with Date objects
 */
export const detectPotentialTransfers = (dateRange: DateRange) => {
    // BOUNDARY CONVERSION: Convert Date objects to epoch for API
    const apiRange = dateRangeToEpochRange(dateRange);

    const query = new URLSearchParams();
    query.append('startDate', apiRange.startDate.toString());
    query.append('endDate', apiRange.endDate.toString());

    return withApiLogging(
        'TransferService',
        `${API_ENDPOINT}/detect`,
        'GET',
        async (url) => {
            const result = await validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    const validatedResponse = DetectedTransfersResponseSchema.parse(rawData);

                    // BOUNDARY CONVERSION: Convert epoch timestamps back to Date objects
                    const convertedResponse = {
                        ...validatedResponse,
                        transfers: validatedResponse.transfers.map(pair => ({
                            ...pair,
                            outgoingTransaction: {
                                ...pair.outgoingTransaction,
                                dateObject: epochToDate(pair.outgoingTransaction.date) // Add converted date
                            },
                            incomingTransaction: {
                                ...pair.incomingTransaction,
                                dateObject: epochToDate(pair.incomingTransaction.date) // Add converted date
                            }
                        })),
                        dateRange: validatedResponse.dateRange ? {
                            ...validatedResponse.dateRange,
                            startDateObject: epochToDate(validatedResponse.dateRange.startDate),
                            endDateObject: epochToDate(validatedResponse.dateRange.endDate)
                        } : undefined
                    };

                    return convertedResponse;
                },
                'detected transfers data',
                'Failed to detect transfers. The transfer data format is invalid.'
            );

            // REMOVED: Automatic preference update
            // The checked range should only update at the END of the review cycle,
            // not when candidates are first detected. This allows users to leave
            // mid-review and return to the same range without losing candidates.

            return result;
        },
        {
            operationName: 'detectPotentialTransfers',
            queryParams: query,
            successData: (result) => ({
                detectedCount: result.transfers.length,
                hasDateRange: !!result.dateRange,
                dateRangeFormatted: result.dateRange ?
                    `${formatDisplayDate(epochToDate(result.dateRange.startDate))} - ${formatDisplayDate(epochToDate(result.dateRange.endDate))}` :
                    'No date range'
            })
        }
    );
};

/**
 * Legacy function for backward compatibility - converts epoch params to Date objects
 * @deprecated Use detectPotentialTransfers(DateRange) instead
 */
export const detectPotentialTransfersLegacy = (startDate: number, endDate: number) => {
    return detectPotentialTransfers({
        startDate: epochToDate(startDate),
        endDate: epochToDate(endDate)
    });
};

/**
 * Mark a single pair of transactions as transfers
 * @param outgoingTransactionId ID of the outgoing transaction
 * @param incomingTransactionId ID of the incoming transaction
 * @returns Promise resolving to boolean indicating success
 */
export const markTransferPair = (outgoingTransactionId: string, incomingTransactionId: string) => {
    return withApiLogging(
        'TransferService',
        `${API_ENDPOINT}/mark-pair`,
        'POST',
        async (url) => {
            return validateApiResponse(
                () => ApiClient.postJson<any>(url, {
                    outgoingTransactionId,
                    incomingTransactionId
                }),
                (rawData) => {
                    return rawData.message === "Transfer pair marked successfully";
                },
                'transfer pair marking response',
                'Failed to mark transfer pair. The server response format is invalid.'
            );
        },
        {
            operationName: `markTransferPair:${outgoingTransactionId}-${incomingTransactionId}`,
            successData: () => ({
                outgoingTransactionId,
                incomingTransactionId,
                marked: true
            })
        }
    );
};

/**
 * Mark multiple detected transfer pairs as transfers
 * @param transferPairs Array of transfer pairs to mark
 * @param scannedDateRange Optional date range that was scanned to update checked range
 * @returns Promise resolving to bulk operation results
 */
export const bulkMarkTransfers = withServiceLogging(
    'TransferService',
    'bulkMarkTransfers',
    async (transferPairs: DetectedTransfer[], scannedDateRange?: DateRange): Promise<BulkMarkTransfersResponse> => {
        const requestBody: any = {
            transferPairs: transferPairs.map(pair => ({
                outgoingTransactionId: pair.outgoingTransactionId,
                incomingTransactionId: pair.incomingTransactionId
            }))
        };

        // Include scanned date range if provided to update checked range in preferences
        if (scannedDateRange) {
            requestBody.scannedStartDate = scannedDateRange.startDate;
            requestBody.scannedEndDate = scannedDateRange.endDate;
        }

        return validateApiResponse(
            () => ApiClient.postJson<any>(`${API_ENDPOINT}/bulk-mark`, requestBody),
            (rawData) => {
                return BulkMarkResponseSchema.parse(rawData);
            },
            'bulk transfer marking response',
            'Failed to bulk mark transfers. The server response format is invalid.'
        );
    },
    {
        logArgs: ([transferPairs, scannedDateRange]) => ({
            pairCount: transferPairs.length,
            transactionIds: transferPairs.map(p => `${p.outgoingTransactionId}-${p.incomingTransactionId}`),
            hasScannedRange: !!scannedDateRange
        }),
        logResult: (result) => ({
            successCount: result.successCount,
            failureCount: result.failureCount,
            totalProcessed: result.successCount + result.failureCount
        })
    }
);


// 6. Utility functions for date range handling

/**
 * Convert number of days to a date range ending today (APPLICATION LAYER)
 * @param days Number of days to go back from today
 * @returns DateRange with Date objects for application logic
 */
export const convertDaysToDateRange = (days: number): DateRange => {
    logger.info('Converting days to date range', { days });

    // Work with Date objects in application layer
    const endDate = new Date();
    const startDate = subtractDays(endDate, days);

    return {
        startDate,
        endDate
    };
};

/**
 * Convert number of days to API date range ending today (API BOUNDARY)
 * @param days Number of days to go back from today
 * @returns ApiDateRange with epoch timestamps for API communication
 */
export const convertDaysToApiDateRange = (days: number): ApiDateRange => {
    const dateRange = convertDaysToDateRange(days);
    return dateRangeToEpochRange(dateRange);
};

/**
 * Format a date for display in US locale
 * @param date Date to format
 * @returns Formatted date string (e.g., "Jan 15, 2024")
 */
export const formatDateForDisplay = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
};

/**
 * Format date for API requests (ISO format YYYY-MM-DD)
 * @param date Date to format
 * @returns ISO format date string
 */
export const formatDateForAPI = (date: Date): string => {
    return date.toISOString().split('T')[0]; // YYYY-MM-DD
};

/**
 * Format date and time for API requests (full ISO format)
 * @param date Date to format
 * @returns Full ISO format date string
 */
export const formatDateTimeForAPI = (date: Date): string => {
    return date.toISOString(); // Full ISO 8601 with timezone
};

/**
 * Parse date from API response
 * @param dateString ISO format date string
 * @returns Date object
 */
export const parseDateFromAPI = (dateString: string): Date => {
    return new Date(dateString);
};

/**
 * Create a date range for transfer operations
 * @param startDate Start date
 * @param endDate End date
 * @returns Formatted date range for API requests (milliseconds since epoch)
 */
export const createTransferDateRange = (startDate: Date, endDate: Date): TransferDetectionRequest => {
    return {
        startDate: startDate.getTime(),
        endDate: endDate.getTime()
    };
};

/**
 * Create a date range from number of days (APPLICATION LAYER)
 * @param days Number of days to go back from today
 * @returns DateRange with Date objects for application logic
 */
export const createDateRangeFromDays = (days: number): DateRange => {
    const endDate = new Date();
    const startDate = subtractDays(endDate, days);

    return {
        startDate,
        endDate
    };
};

/**
 * Create an API date range from number of days (API BOUNDARY)
 * @param days Number of days to go back from today
 * @returns ApiDateRange with epoch timestamps for API communication
 */
export const createApiDateRangeFromDays = (days: number): ApiDateRange => {
    const dateRange = createDateRangeFromDays(days);
    return dateRangeToEpochRange(dateRange);
};

// Helper function to calculate transfer progress
const calculateTransferProgress = (checkedRange: CheckedRange, accountRange: AccountRange): TransferProgressData => {
    if (!accountRange.startDate || !accountRange.endDate) {
        return {
            hasData: false,
            totalDays: 0,
            checkedDays: 0,
            progressPercentage: 0,
            isComplete: false
        };
    }

    const accountStart = new Date(accountRange.startDate);
    const accountEnd = new Date(accountRange.endDate);
    const totalDays = Math.ceil((accountEnd.getTime() - accountStart.getTime()) / (1000 * 60 * 60 * 24));

    let checkedDays = 0;
    if (checkedRange.startDate && checkedRange.endDate) {
        const checkedStart = new Date(Math.max(checkedRange.startDate, accountStart.getTime()));
        const checkedEnd = new Date(Math.min(checkedRange.endDate, accountEnd.getTime()));
        checkedDays = Math.max(0, Math.ceil((checkedEnd.getTime() - checkedStart.getTime()) / (1000 * 60 * 60 * 24)));
    }

    const progressPercentage = totalDays > 0 ? Math.round((checkedDays / totalDays) * 100) : 0;
    const isComplete = progressPercentage >= 100;

    return {
        hasData: true,
        totalDays,
        checkedDays,
        progressPercentage,
        isComplete,
        accountDateRange: accountRange.startDate && accountRange.endDate ? {
            startDate: accountRange.startDate,
            endDate: accountRange.endDate
        } : undefined,
        checkedDateRange: checkedRange.startDate && checkedRange.endDate ? {
            startDate: checkedRange.startDate,
            endDate: checkedRange.endDate
        } : undefined
    };
};

// Helper function to calculate initial recommendation when nothing is checked
const calculateInitialRecommendation = (accountStartDate: Date, accountEndDate: Date, chunkDays: number): ApiDateRange => {
    logger.info('No previous checks found, suggesting recent chunk from actual transaction data');

    const suggestedEnd = accountEndDate;
    const suggestedStart = new Date(suggestedEnd);
    suggestedStart.setDate(suggestedStart.getDate() - chunkDays);

    // Don't go before account start
    const effectiveStart = new Date(Math.max(suggestedStart.getTime(), accountStartDate.getTime()));

    return {
        startDate: effectiveStart.getTime(),
        endDate: suggestedEnd.getTime()
    };
};

// Helper function to calculate forward extension recommendation
const calculateForwardRecommendation = (
    checkedEndDate: Date,
    accountEndDate: Date,
    overlapDays: number,
    chunkDays: number
): ApiDateRange => {
    logger.info('Extending forward from checked range with overlap');

    const nextStart = new Date(checkedEndDate);
    nextStart.setDate(nextStart.getDate() - overlapDays);

    const nextEnd = new Date(nextStart);
    nextEnd.setDate(nextEnd.getDate() + chunkDays);

    // Cap at actual account data boundary
    const effectiveEnd = new Date(Math.min(nextEnd.getTime(), accountEndDate.getTime()));

    const recommendation = {
        startDate: nextStart.getTime(),
        endDate: effectiveEnd.getTime()
    };

    logger.info('Forward extension recommendation', {
        nextStart: nextStart.toISOString().split('T')[0],
        effectiveEnd: effectiveEnd.toISOString().split('T')[0],
        overlapDays
    });

    return recommendation;
};

// Helper function to calculate backward extension recommendation
const calculateBackwardRecommendation = (
    checkedStartDate: Date,
    accountStartDate: Date,
    overlapDays: number,
    chunkDays: number
): ApiDateRange => {
    logger.info('Extending backward from checked range with overlap');

    const nextEnd = new Date(checkedStartDate);
    nextEnd.setDate(nextEnd.getDate() + overlapDays);

    const nextStart = new Date(nextEnd);
    nextStart.setDate(nextStart.getDate() - chunkDays);

    // Cap at actual account data boundary
    const effectiveStart = new Date(Math.max(nextStart.getTime(), accountStartDate.getTime()));

    const recommendation = {
        startDate: effectiveStart.getTime(),
        endDate: nextEnd.getTime()
    };

    logger.info('Backward extension recommendation', {
        effectiveStart: effectiveStart.toISOString().split('T')[0],
        nextEnd: nextEnd.toISOString().split('T')[0],
        overlapDays
    });

    return recommendation;
};

// Helper function to calculate recommended date range
const calculateRecommendedRange = (checkedRange: CheckedRange, accountRange: AccountRange): ApiDateRange | null => {
    if (!accountRange.startDate || !accountRange.endDate) {
        logger.warn('No account date range available for transfer checking');
        return null;
    }

    const OVERLAP_DAYS = 3; // Days of overlap needed for transfer pair detection
    const CHUNK_DAYS = 30; // Suggest ~1 month chunks for manageable processing

    const accountStartDate = new Date(accountRange.startDate);
    const accountEndDate = new Date(accountRange.endDate); // Latest actual transaction date

    // Explain inputs used for recommendation
    logger.info('calculateRecommendedRange: inputs', {
        accountStart: accountStartDate.toISOString(),
        accountEnd: accountEndDate.toISOString(),
        checkedRangeStart: checkedRange?.startDate ? new Date(checkedRange.startDate).toISOString() : null,
        checkedRangeEnd: checkedRange?.endDate ? new Date(checkedRange.endDate).toISOString() : null,
        overlapDays: OVERLAP_DAYS,
        chunkDays: CHUNK_DAYS
    });

    // If nothing has been checked yet, start with recent data (last 30 days of actual data)
    if (!checkedRange.startDate || !checkedRange.endDate) {
        return calculateInitialRecommendation(accountStartDate, accountEndDate, CHUNK_DAYS);
    }

    // Validate checked range against actual data boundaries
    const checkedStartDate = new Date(Math.max(checkedRange.startDate, accountStartDate.getTime()));
    const checkedEndDate = new Date(Math.min(checkedRange.endDate, accountEndDate.getTime()));

    // Show clamped boundaries after validating against account range
    logger.info('calculateRecommendedRange: clamped checked boundaries', {
        checkedStart: checkedStartDate.toISOString(),
        checkedEnd: checkedEndDate.toISOString()
    });

    // Determine if we can extend forward (toward present) or backward (toward past)
    const canExtendForward = checkedEndDate.getTime() < accountEndDate.getTime();
    const canExtendBackward = checkedStartDate.getTime() > accountStartDate.getTime();

    logger.info('calculateRecommendedRange: extension options', {
        canExtendForward,
        canExtendBackward
    });

    if (canExtendForward) {
        logger.info('calculateRecommendedRange: decision', { direction: 'forward' });
        return calculateForwardRecommendation(checkedEndDate, accountEndDate, OVERLAP_DAYS, CHUNK_DAYS);
    } else if (canExtendBackward) {
        logger.info('calculateRecommendedRange: decision', { direction: 'backward' });
        return calculateBackwardRecommendation(checkedStartDate, accountStartDate, OVERLAP_DAYS, CHUNK_DAYS);
    } else {
        // All actual transaction data has been covered
        logger.info('All actual transaction data has been checked, no recommendation needed');
        return null;
    }
};

/**
 * Get both transfer progress and recommended date range in a single optimized call
 * This avoids duplicate API calls when both pieces of data are needed
 */
export const getTransferProgressAndRecommendation = withServiceLogging(
    'TransferService',
    'getTransferProgressAndRecommendation',
    async (): Promise<{
        progress: TransferProgressData;
        recommendedRange: ApiDateRange | null;
    }> => {
        try {
            // Get all transfer data in a single optimized call
            const { checkedRange, accountRange } = await getTransferDataForProgress();

            // Calculate progress using helper function
            const progress = calculateTransferProgress(checkedRange, accountRange);

            // Calculate recommended range using helper function
            const recommendedRange = calculateRecommendedRange(checkedRange, accountRange);

            return {
                progress,
                recommendedRange
            };

        } catch (error) {
            logger.error('Failed to get transfer progress and recommendation', {
                error: error instanceof Error ? error.message : 'Unknown error'
            });

            // Fallback values
            return {
                progress: {
                    hasData: false,
                    totalDays: 0,
                    checkedDays: 0,
                    progressPercentage: 0,
                    isComplete: false,
                    error: error instanceof Error ? error.message : 'Unknown error'
                },
                recommendedRange: null // Don't suggest anything if we can't determine proper boundaries
            };
        }
    },
    {
        logResult: (result) => ({
            hasProgress: result.progress.hasData,
            progressPercentage: result.progress.progressPercentage,
            hasRecommendation: !!result.recommendedRange
        })
    }
);

/**
 * Get the recommended date range for transfer checking based on user preferences and account data
 * @returns Promise resolving to recommended date range or null if no data available
 */
export const getRecommendedTransferDateRange = withServiceLogging(
    'TransferService',
    'getRecommendedTransferDateRange',
    async (): Promise<ApiDateRange | null> => {
        const { recommendedRange } = await getTransferProgressAndRecommendation();
        return recommendedRange;
    },
    {
        logResult: (result) => ({
            hasRecommendation: !!result,
            startDate: result?.startDate || null,
            endDate: result?.endDate || null
        })
    }
);

/**
 * Get the current status of transfer checking progress
 * @returns Promise resolving to checking progress information
 */
export const getTransferCheckingProgress = withServiceLogging(
    'TransferService',
    'getTransferCheckingProgress',
    async () => {
        const { progress } = await getTransferProgressAndRecommendation();
        return progress;
    },
    {
        logResult: (result) => ({
            hasData: result.hasData,
            progressPercentage: result.progressPercentage,
            isComplete: result.isComplete
        })
    }
);

/**
 * Reset all transfer progress tracking data
 * This clears the checked date range and allows starting fresh
 * @returns Promise resolving when reset is complete
 */
export const resetTransferProgress = withServiceLogging(
    'TransferService',
    'resetTransferProgress',
    async (): Promise<void> => {
        try {
            await resetTransferCheckedDateRange();
            logger.info('Successfully reset transfer progress tracking');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            logger.error('Failed to reset transfer progress tracking', { error: errorMessage });
            throw new Error(`Failed to reset transfer progress: ${errorMessage}`);
        }
    },
    {
        logResult: () => ({ reset: true })
    }
);

// 7. Default export with all service functions
export default {
    // Core transfer operations
    listPairedTransfers,
    getTotalPairedTransfersCount,
    detectPotentialTransfers,
    markTransferPair,
    bulkMarkTransfers,

    // Date utilities
    convertDaysToDateRange,
    formatDateForDisplay,
    formatDateForAPI,
    formatDateTimeForAPI,
    parseDateFromAPI,
    createTransferDateRange,
    createDateRangeFromDays,

    // Transfer preferences and progress
    getRecommendedTransferDateRange,
    getTransferCheckingProgress,
    getTransferProgressAndRecommendation,
    resetTransferProgress
};
