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
    updateTransferCheckedDateRange,
    getTransferDataForProgress,
    resetTransferCheckedDateRange
} from './UserPreferencesService';

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
    startDate: number; // milliseconds since epoch
    endDate: number;   // milliseconds since epoch
}

export interface TransferListParams {
    startDate?: number; // milliseconds since epoch
    endDate?: number;   // milliseconds since epoch
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

// Date range utilities
export interface DateRange {
    startDate: number; // milliseconds since epoch
    endDate: number;   // milliseconds since epoch
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

// Helper function for retrying preference updates
const retryPreferenceUpdate = async (
    startMs: number,
    endMs: number,
    startDate: string,
    endDate: string,
    maxRetries: number = 3,
    delayMs: number = 1000
): Promise<void> => {
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            await updateTransferCheckedDateRange(startMs, endMs);
            logger.info('Successfully updated transfer checked date range', {
                startDate,
                endDate,
                attempt,
                startMs,
                endMs
            });
            return; // Success, exit retry loop
        } catch (error) {
            lastError = error instanceof Error ? error : new Error('Unknown error');
            logger.warn('Preference update attempt failed', {
                startDate,
                endDate,
                attempt,
                maxRetries,
                error: lastError.message
            });

            // Wait before retrying (except on last attempt)
            if (attempt < maxRetries) {
                await new Promise(resolve => setTimeout(resolve, delayMs * attempt));
            }
        }
    }

    // All retries failed, throw the last error
    throw lastError || new Error('All preference update attempts failed');
};

// 5. Exported Functions - API operations with efficient logging

/**
 * Get total count of all paired transfers for the user (no date filtering)
 * @returns Promise resolving to total count
 */
export const getTotalPairedTransfersCount = () => {
    return withApiLogging(
        'TransferService',
        `${API_ENDPOINT}/paired?count_only=true`,
        'GET',
        async () => {
            return validateApiResponse(
                () => ApiClient.getJson<any>(`${API_ENDPOINT}/paired?count_only=true`),
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

    const url = query.toString()
        ? `${API_ENDPOINT}/paired?${query.toString()}`
        : `${API_ENDPOINT}/paired`;

    return withApiLogging(
        'TransferService',
        url,
        'GET',
        async () => {
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
            successData: (result) => ({
                transferCount: result.pairedTransfers.length,
                hasDateRange: !!result.dateRange
            })
        }
    );
};

/**
 * Detect potential transfer transactions within a date range
 * @param startDate Start date for detection period (milliseconds since epoch)
 * @param endDate End date for detection period (milliseconds since epoch)
 * @returns Promise resolving to detected transfers response
 */
export const detectPotentialTransfers = (startDate: number, endDate: number) => {
    const query = new URLSearchParams();

    // Use milliseconds since epoch
    query.append('startDate', startDate.toString());
    query.append('endDate', endDate.toString());

    const url = `${API_ENDPOINT}/detect?${query.toString()}`;

    return withApiLogging(
        'TransferService',
        url,
        'GET',
        async () => {
            const result = await validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    const validatedResponse = DetectedTransfersResponseSchema.parse(rawData);
                    return validatedResponse;
                },
                'detected transfers data',
                'Failed to detect transfers. The transfer data format is invalid.'
            );

            // Update the checked date range in preferences after successful detection
            let progressTrackingWarning: string | undefined;
            try {
                // Use the millisecond timestamps directly
                const startMs = startDate;
                const endMs = endDate;

                // Attempt to update with retry mechanism
                await retryPreferenceUpdate(startMs, endMs, new Date(startDate).toISOString().split('T')[0], new Date(endDate).toISOString().split('T')[0]);
                logger.info('Updated transfer checked date range', { startDate, endDate, startMs, endMs });
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                logger.error('Failed to update transfer checked date range after retries', {
                    startDate,
                    endDate,
                    error: errorMessage
                });

                // Set warning to be included in response
                progressTrackingWarning = `Transfer detection completed successfully, but progress tracking failed to update. You may need to manually track this date range (${new Date(startDate).toISOString().split('T')[0]} to ${new Date(endDate).toISOString().split('T')[0]}) to avoid duplicate checking.`;
            }

            // Include progress tracking warning in response if it occurred
            return {
                ...result,
                ...(progressTrackingWarning && { progressTrackingWarning })
            };
        },
        {
            operationName: 'detectPotentialTransfers',
            successData: (result) => ({
                detectedCount: result.transfers.length,
                hasDateRange: !!result.dateRange
            })
        }
    );
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
        async () => {
            return validateApiResponse(
                () => ApiClient.postJson<any>(`${API_ENDPOINT}/mark-pair`, {
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
 * Convert number of days to a date range ending today
 * @param days Number of days to go back from today
 * @returns Object with startDate and endDate in milliseconds since epoch
 */
export const convertDaysToDateRange = (days: number): DateRange => {
    logger.info('Converting days to date range', { days });

    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);

    return {
        startDate: startDate.getTime(),
        endDate: endDate.getTime()
    };
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
 * Create a date range from number of days
 * @param days Number of days to go back from today
 * @returns Formatted date range for API requests (milliseconds since epoch)
 */
export const createDateRangeFromDays = (days: number): DateRange => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);

    return {
        startDate: startDate.getTime(),
        endDate: endDate.getTime()
    };
};

// Helper function to calculate transfer progress
const calculateTransferProgress = (checkedRange: any, accountRange: any) => {
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
        accountDateRange: accountRange,
        checkedDateRange: checkedRange
    };
};

// Helper function to calculate initial recommendation when nothing is checked
const calculateInitialRecommendation = (accountStartDate: Date, accountEndDate: Date, chunkDays: number): DateRange => {
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
): DateRange => {
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
): DateRange => {
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
const calculateRecommendedRange = (checkedRange: any, accountRange: any): DateRange | null => {
    if (!accountRange.startDate || !accountRange.endDate) {
        logger.warn('No account date range available for transfer checking');
        return null;
    }

    const OVERLAP_DAYS = 3; // Days of overlap needed for transfer pair detection
    const CHUNK_DAYS = 30; // Suggest ~1 month chunks for manageable processing

    const accountStartDate = new Date(accountRange.startDate);
    const accountEndDate = new Date(accountRange.endDate); // Latest actual transaction date

    // If nothing has been checked yet, start with recent data (last 30 days of actual data)
    if (!checkedRange.startDate || !checkedRange.endDate) {
        return calculateInitialRecommendation(accountStartDate, accountEndDate, CHUNK_DAYS);
    }

    // Validate checked range against actual data boundaries
    const checkedStartDate = new Date(Math.max(checkedRange.startDate, accountStartDate.getTime()));
    const checkedEndDate = new Date(Math.min(checkedRange.endDate, accountEndDate.getTime()));

    // Determine if we can extend forward (toward present) or backward (toward past)
    const canExtendForward = checkedEndDate.getTime() < accountEndDate.getTime();
    const canExtendBackward = checkedStartDate.getTime() > accountStartDate.getTime();

    if (canExtendForward) {
        return calculateForwardRecommendation(checkedEndDate, accountEndDate, OVERLAP_DAYS, CHUNK_DAYS);
    } else if (canExtendBackward) {
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
        progress: any;
        recommendedRange: DateRange | null;
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
    async (): Promise<DateRange | null> => {
        const { recommendedRange } = await getTransferProgressAndRecommendation();
        return recommendedRange;
    },
    {
        logResult: (result) => ({
            hasRecommendation: !!result,
            startDate: result?.startDate,
            endDate: result?.endDate
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
