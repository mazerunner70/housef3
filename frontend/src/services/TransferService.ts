import { z } from 'zod';
import { ApiClient } from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import { TransactionViewItem } from '@/schemas/Transaction';

// Transfer pair interfaces
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

// API response schemas
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



// API base path - ApiClient will handle the full URL construction
const API_ENDPOINT = '';

/**
 * Get existing paired transfer transactions within a date range
 */
export const getPairedTransfers = async (
    startDate?: Date,
    endDate?: Date
): Promise<TransferPair[]> => {
    const query = new URLSearchParams();

    if (startDate && endDate) {
        // Use specific start and end dates (ISO 8601)
        query.append('startDate', startDate.toISOString());
        query.append('endDate', endDate.toISOString());
    }

    const url = query.toString()
        ? `${API_ENDPOINT}/transfers/paired?${query.toString()}`
        : `${API_ENDPOINT}/transfers/paired`;

    return validateApiResponse(
        () => ApiClient.getJson<any>(url),
        (rawData) => {
            const validatedResponse = PairedTransfersResponseSchema.parse(rawData);
            return validatedResponse.pairedTransfers;
        },
        'paired transfers data',
        'Failed to load paired transfers. The transfer data format is invalid.'
    );
};

/**
 * Detect potential transfer transactions within a date range
 */
export const detectTransfers = async (
    startDate: Date,
    endDate: Date
): Promise<TransferPair[]> => {
    const query = new URLSearchParams();

    // Use specific start and end dates (ISO 8601)
    query.append('startDate', startDate.toISOString());
    query.append('endDate', endDate.toISOString());

    return validateApiResponse(
        () => ApiClient.getJson<any>(`${API_ENDPOINT}/transfers/detect?${query.toString()}`),
        (rawData) => {
            const validatedResponse = DetectedTransfersResponseSchema.parse(rawData);
            return validatedResponse.transfers;
        },
        'detected transfers data',
        'Failed to detect transfers. The transfer data format is invalid.'
    );
};

/**
 * Mark a single pair of transactions as transfers
 */
export const markTransferPair = async (
    outgoingTransactionId: string,
    incomingTransactionId: string
): Promise<boolean> => {
    return validateApiResponse(
        () => ApiClient.postJson<any>(`${API_ENDPOINT}/transfers/mark-pair`, {
            outgoingTransactionId,
            incomingTransactionId
        }),
        (rawData) => {
            return rawData.message === "Transfer pair marked successfully";
        },
        'transfer pair marking response',
        'Failed to mark transfer pair. The server response format is invalid.'
    );
};

/**
 * Mark multiple detected transfer pairs as transfers
 */
export const bulkMarkTransfers = async (transferPairs: DetectedTransfer[]): Promise<{
    successCount: number;
    failureCount: number;
    successful: Array<{ outgoingTransactionId: string; incomingTransactionId: string }>;
    failed: Array<{ pair: any; error: string }>;
}> => {
    return validateApiResponse(
        () => ApiClient.postJson<any>(`${API_ENDPOINT}/transfers/bulk-mark`, {
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
};



// Additional utility functions for date range handling
export const convertDaysToDateRange = (days: number): { startDate: Date; endDate: Date } => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);
    return { startDate, endDate };
};

export const formatDateForDisplay = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
};

// Default export
export default {
    getPairedTransfers,
    detectTransfers,
    markTransferPair,
    bulkMarkTransfers,
    convertDaysToDateRange,
    formatDateForDisplay
};
