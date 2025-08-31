// 1. Imports
import { z } from 'zod';
import ApiClient from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import { TransactionViewItem } from '@/schemas/Transaction';
import {
    withApiLogging,
    withServiceLogging,
    createLogger
} from '@/utils/logger';
import {
    getTransferCheckedDateRange,
    updateTransferCheckedDateRange,
    getAccountDateRangeForTransfers
} from './UserPreferencesService';

// 2. Type Definitions - Domain interfaces
export interface TransferPair {
    outgoingTransaction: TransactionViewItem;
    incomingTransaction: TransactionViewItem;
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
    startDate: string; // ISO format YYYY-MM-DD
    endDate: string;   // ISO format YYYY-MM-DD
}

export interface TransferListParams {
    startDate?: string; // ISO format YYYY-MM-DD
    endDate?: string;   // ISO format YYYY-MM-DD
    limit?: number;
    offset?: number;
}

export interface PairedTransfersResponse {
    pairedTransfers: TransferPair[];
    count: number;
    total?: number;
    hasMore?: boolean;
}

export interface DetectedTransfersResponse {
    transfers: TransferPair[];
    count: number;
    total?: number;
    hasMore?: boolean;
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
    startDate: string; // ISO format YYYY-MM-DD
    endDate: string;   // ISO format YYYY-MM-DD
}

// 3. Zod validation schemas
const TransferPairSchema = z.object({
    outgoingTransaction: z.any(), // Will be validated as TransactionViewItem
    incomingTransaction: z.any(), // Will be validated as TransactionViewItem
    amount: z.number(),
    dateDifference: z.number()
});

const PairedTransfersResponseSchema = z.object({
    pairedTransfers: z.array(TransferPairSchema),
    count: z.number(),
    total: z.number().optional(),
    hasMore: z.boolean().optional()
});

const DetectedTransfersResponseSchema = z.object({
    transfers: z.array(TransferPairSchema),
    count: z.number(),
    total: z.number().optional(),
    hasMore: z.boolean().optional()
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
 * Get existing paired transfer transactions within a date range
 * @param params Optional parameters for filtering and pagination
 * @returns Promise resolving to paired transfers response
 */
export const listPairedTransfers = (params?: TransferListParams) => {
    const query = new URLSearchParams();

    if (params?.startDate && params?.endDate) {
        // Use ISO format dates
        query.append('startDate', params.startDate);
        query.append('endDate', params.endDate);
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
                total: result.total,
                hasMore: result.hasMore
            })
        }
    );
};

/**
 * Detect potential transfer transactions within a date range
 * @param startDate Start date for detection period (ISO format YYYY-MM-DD)
 * @param endDate End date for detection period (ISO format YYYY-MM-DD)
 * @returns Promise resolving to detected transfers response
 */
export const detectPotentialTransfers = (startDate: string, endDate: string) => {
    const query = new URLSearchParams();

    // Use ISO format dates
    query.append('startDate', startDate);
    query.append('endDate', endDate);

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
            try {
                // Convert ISO dates to milliseconds for storage
                const startMs = new Date(startDate).getTime();
                const endMs = new Date(endDate).getTime();
                await updateTransferCheckedDateRange(startMs, endMs);
                logger.info('Updated transfer checked date range', { startDate, endDate, startMs, endMs });
            } catch (error) {
                logger.warn('Failed to update transfer checked date range', {
                    startDate,
                    endDate,
                    error: error instanceof Error ? error.message : 'Unknown error'
                });
                // Don't fail the main operation if preference update fails
            }

            return result;
        },
        {
            operationName: 'detectPotentialTransfers',
            successData: (result) => ({
                detectedCount: result.transfers.length,
                total: result.total,
                hasMore: result.hasMore
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
 * @returns Promise resolving to bulk operation results
 */
export const bulkMarkTransfers = withServiceLogging(
    'TransferService',
    'bulkMarkTransfers',
    async (transferPairs: DetectedTransfer[]): Promise<BulkMarkTransfersResponse> => {
        return validateApiResponse(
            () => ApiClient.postJson<any>(`${API_ENDPOINT}/bulk-mark`, {
                transferPairs: transferPairs.map(pair => ({
                    outgoingTransactionId: pair.outgoingTransactionId,
                    incomingTransactionId: pair.incomingTransactionId
                }))
            }),
            (rawData) => {
                return BulkMarkResponseSchema.parse(rawData);
            },
            'bulk transfer marking response',
            'Failed to bulk mark transfers. The server response format is invalid.'
        );
    },
    {
        logArgs: ([transferPairs]) => ({
            pairCount: transferPairs.length,
            transactionIds: transferPairs.map(p => `${p.outgoingTransactionId}-${p.incomingTransactionId}`)
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
 * @returns Object with startDate and endDate in ISO format
 */
export const convertDaysToDateRange = (days: number): DateRange => {
    logger.info('Converting days to date range', { days });

    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);

    return {
        startDate: formatDateForAPI(startDate),
        endDate: formatDateForAPI(endDate)
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
 * @returns Formatted date range for API requests (ISO format)
 */
export const createTransferDateRange = (startDate: Date, endDate: Date): TransferDetectionRequest => {
    return {
        startDate: formatDateForAPI(startDate),
        endDate: formatDateForAPI(endDate)
    };
};

/**
 * Create a date range from number of days
 * @param days Number of days to go back from today
 * @returns Formatted date range for API requests (ISO format)
 */
export const createDateRangeFromDays = (days: number): DateRange => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);

    return {
        startDate: formatDateForAPI(startDate),
        endDate: formatDateForAPI(endDate)
    };
};

/**
 * Get the recommended date range for transfer checking based on user preferences and account data
 * @returns Promise resolving to recommended date range or null if no data available
 */
export const getRecommendedTransferDateRange = withServiceLogging(
    'TransferService',
    'getRecommendedTransferDateRange',
    async (): Promise<DateRange | null> => {
        try {
            // Get the checked date range from preferences
            const checkedRange = await getTransferCheckedDateRange();

            // Get the overall account date range
            const accountRange = await getAccountDateRangeForTransfers();

            if (!accountRange.startDate || !accountRange.endDate) {
                logger.warn('No account date range available for transfer checking');
                return null;
            }

            // If nothing has been checked yet, return the full account range
            if (!checkedRange.startDate || !checkedRange.endDate) {
                logger.info('No previous checks found, returning full account date range');
                return {
                    startDate: formatDateForAPI(new Date(accountRange.startDate)),
                    endDate: formatDateForAPI(new Date(accountRange.endDate))
                };
            }

            // If everything has been checked, suggest a recent range
            const accountEndDate = new Date(accountRange.endDate);
            const checkedEndDate = new Date(checkedRange.endDate);

            if (checkedEndDate >= accountEndDate) {
                logger.info('All data has been checked, suggesting recent 30-day range');
                return createDateRangeFromDays(30);
            }

            // Return the unchecked portion
            const nextStartDate = new Date(checkedEndDate);
            nextStartDate.setDate(nextStartDate.getDate() + 1); // Start from day after last checked

            const recommendedRange = {
                startDate: formatDateForAPI(nextStartDate),
                endDate: formatDateForAPI(new Date(accountRange.endDate))
            };

            logger.info('Returning unchecked date range', recommendedRange);
            return recommendedRange;

        } catch (error) {
            logger.error('Failed to get recommended transfer date range', {
                error: error instanceof Error ? error.message : 'Unknown error'
            });

            // Fallback to a reasonable default
            logger.info('Using fallback 30-day range');
            return createDateRangeFromDays(30);
        }
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
        try {
            const checkedRange = await getTransferCheckedDateRange();
            const accountRange = await getAccountDateRangeForTransfers();

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

        } catch (error) {
            logger.error('Failed to get transfer checking progress', {
                error: error instanceof Error ? error.message : 'Unknown error'
            });

            return {
                hasData: false,
                totalDays: 0,
                checkedDays: 0,
                progressPercentage: 0,
                isComplete: false,
                error: error instanceof Error ? error.message : 'Unknown error'
            };
        }
    },
    {
        logResult: (result) => ({
            hasData: result.hasData,
            progressPercentage: result.progressPercentage,
            isComplete: result.isComplete
        })
    }
);

// 7. Default export with all service functions
export default {
    // Core transfer operations
    listPairedTransfers,
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
    getTransferCheckingProgress
};
