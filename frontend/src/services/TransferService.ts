import { z } from 'zod';
import ApiClient from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import { TransactionViewItem } from '@/schemas/Transaction';
import { withApiLogging, withServiceLogging, createLogger } from '@/utils/logger';

// Transfer domain interfaces
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
    startDate: string; // Milliseconds since epoch as string
    endDate: string;   // Milliseconds since epoch as string
}

export interface PairedTransfersResponse {
    pairedTransfers: TransferPair[];
    count: number;
}

export interface DetectedTransfersResponse {
    transfers: TransferPair[];
    count: number;
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

// Zod validation schemas
const TransferPairSchema = z.object({
    outgoingTransaction: z.any(), // Will be validated as TransactionViewItem
    incomingTransaction: z.any(), // Will be validated as TransactionViewItem
    amount: z.number(),
    dateDifference: z.number()
});

const PairedTransfersResponseSchema = z.object({
    pairedTransfers: z.array(TransferPairSchema),
    count: z.number()
});

const DetectedTransfersResponseSchema = z.object({
    transfers: z.array(TransferPairSchema),
    count: z.number()
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



// Logger for simple operations
const logger = createLogger('TransferService');

/**
 * Get existing paired transfer transactions within a date range
 * @param startDate Optional start date for filtering
 * @param endDate Optional end date for filtering
 * @returns Promise resolving to array of transfer pairs
 */
export const listPairedTransfers = (startDate?: Date, endDate?: Date) => {
    const query = new URLSearchParams();

    if (startDate && endDate) {
        // Use specific start and end dates (milliseconds since epoch)
        query.append('startDate', startDate.getTime().toString());
        query.append('endDate', endDate.getTime().toString());
    }

    const url = query.toString()
        ? `/transfers/paired?${query.toString()}`
        : `/transfers/paired`;

    return withApiLogging(
        'TransferService',
        url,
        'GET',
        async () => {
            return validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    const validatedResponse = PairedTransfersResponseSchema.parse(rawData);
                    return validatedResponse.pairedTransfers;
                },
                'paired transfers data',
                'Failed to load paired transfers. The transfer data format is invalid.'
            );
        },
        {
            operationName: 'getPairedTransfers',
            successData: (result) => ({ transferCount: result.length })
        }
    );
};

/**
 * Detect potential transfer transactions within a date range
 * @param startDate Start date for detection period
 * @param endDate End date for detection period
 * @returns Promise resolving to array of detected transfer pairs
 */
export const detectPotentialTransfers = (startDate: Date, endDate: Date) => {
    const query = new URLSearchParams();

    // Use specific start and end dates (milliseconds since epoch)
    query.append('startDate', startDate.getTime().toString());
    query.append('endDate', endDate.getTime().toString());

    const url = `/transfers/detect?${query.toString()}`;

    return withApiLogging(
        'TransferService',
        url,
        'GET',
        async () => {
            return validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    const validatedResponse = DetectedTransfersResponseSchema.parse(rawData);
                    return validatedResponse.transfers;
                },
                'detected transfers data',
                'Failed to detect transfers. The transfer data format is invalid.'
            );
        },
        {
            operationName: 'detectTransfers',
            successData: (result) => ({ detectedCount: result.length })
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
        '/transfers/mark-pair',
        'POST',
        async () => {
            return validateApiResponse(
                () => ApiClient.postJson<any>('/transfers/mark-pair', {
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
            successData: () => ({ outgoingTransactionId, incomingTransactionId })
        }
    );
};

/**
 * Mark multiple detected transfer pairs as transfers
 * @param transferPairs Array of transfer pairs to mark
 * @returns Promise resolving to bulk operation results
 */
export interface BulkMarkTransfersResponse {
    successCount: number;
    failureCount: number;
    successful: Array<{ outgoingTransactionId: string; incomingTransactionId: string }>;
    failed: Array<{ pair: any; error: string }>;
}

export const bulkMarkTransfers = withServiceLogging(
    'TransferService',
    'bulkMarkTransfers',
    async (transferPairs: DetectedTransfer[]): Promise<BulkMarkTransfersResponse> => {
        return validateApiResponse(
            () => ApiClient.postJson<any>('/transfers/bulk-mark', {
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
            failureCount: result.failureCount
        })
    }
);



// Utility functions for date range handling

/**
 * Convert number of days to a date range ending today
 * @param days Number of days to go back from today
 * @returns Object with startDate and endDate
 */
export const convertDaysToDateRange = (days: number): { startDate: Date; endDate: Date } => {
    logger.info('Converting days to date range', { days });

    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);

    return { startDate, endDate };
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
 * Format date for API requests (milliseconds since epoch)
 * @param date Date to format
 * @returns Milliseconds since epoch as string
 */
export const formatDateForAPI = (date: Date): string => {
    return date.getTime().toString();
};

/**
 * Create a date range for transfer operations
 * @param startDate Start date
 * @param endDate End date
 * @returns Formatted date range for API requests (milliseconds since epoch)
 */
export const createTransferDateRange = (startDate: Date, endDate: Date): TransferDetectionRequest => {
    return {
        startDate: formatDateForAPI(startDate),
        endDate: formatDateForAPI(endDate)
    };
};

// Default export with all service functions
export default {
    listPairedTransfers,
    detectPotentialTransfers,
    markTransferPair,
    bulkMarkTransfers,
    convertDaysToDateRange,
    formatDateForDisplay,
    formatDateForAPI,
    createTransferDateRange
};
