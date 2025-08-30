// Zod schemas for Transaction types
// These schemas provide runtime validation for Transaction-related data

import { z } from 'zod';
import { Decimal } from 'decimal.js';

// Custom Zod transform for Decimal.js
// Handles strings, numbers, and existing Decimal objects safely
const DecimalSchema = z.union([
    z.string(),
    z.number(),
    z.instanceof(Decimal)
]).transform((val) => {
    if (val instanceof Decimal) return val;
    return new Decimal(val?.toString() || '0');
});

// Transaction Type Enums
export const TransactionTypeSchema = z.enum(['income', 'expense', 'transfer']);
export const DebitCreditSchema = z.enum(['debit', 'credit']);
export const TransactionStatusSchema = z.enum(['pending', 'cleared', 'reconciled']);

// Currency Schema (reused from Account schema pattern)
export const CurrencySchema = z.enum([
    "USD", "EUR", "GBP", "CAD", "JPY", "AUD", "CHF", "CNY", "other"
]);

// Core Transaction Schema
export const TransactionSchema = z.object({
    transactionId: z.string(),
    fileId: z.string(),
    userId: z.string(),
    date: z.number(), // milliseconds since epoch
    description: z.string(),
    amount: DecimalSchema,
    balance: DecimalSchema,
    currency: CurrencySchema,
    transactionType: z.string().optional(),
    category: z.string().optional(),
    payee: z.string().optional(),
    memo: z.string().optional(),
    checkNumber: z.string().optional(),
    reference: z.string().optional(),
    accountId: z.string().optional(),
    status: z.string().optional(),
    debitOrCredit: z.string().optional(),
    importOrder: z.number().optional()
});

// Transaction View Item Schema (for main transactions view)
export const TransactionViewItemSchema = z.object({
    transactionId: z.string(),
    fileId: z.string(),
    userId: z.string(),
    date: z.number(),
    description: z.string(),
    amount: DecimalSchema,
    balance: DecimalSchema,
    currency: CurrencySchema,
    transactionType: z.string().optional(),
    category: z.string().optional(),
    payee: z.string().optional(),
    memo: z.string().optional(),
    checkNumber: z.string().optional(),
    reference: z.string().optional(),
    accountId: z.string().optional(),
    status: z.string().optional(),
    debitOrCredit: z.string().optional(),
    importOrder: z.number().optional(),
    id: z.string(),
    primaryCategoryId: z.string().optional(),
    categories: z.array(z.any()).optional(),
    account: z.string().optional(),
    type: TransactionTypeSchema,
    notes: z.string().optional(),
    isSplit: z.boolean().optional()
});

// Category Info Schema
export const CategoryInfoSchema = z.object({
    categoryId: z.string(),
    name: z.string(),
    userId: z.string(),
    type: z.string(),
    parentCategoryId: z.string().nullable()
});

// Account Info Schema (minimal for transaction service)
export const AccountInfoSchema = z.object({
    accountId: z.string(),
    accountName: z.string().optional(),
    userId: z.string().optional(),
    accountType: z.string().optional(),
    institution: z.string().optional(),
    balance: z.string().optional(),
    currency: z.string().optional(),
    notes: z.string().optional(),
    isActive: z.boolean().optional(),
    defaultFileMapId: z.string().optional(),
    lastTransactionDate: z.number().nullable().optional(),
    createdAt: z.number().optional(),
    updatedAt: z.number().optional()
}).passthrough().transform((data) => ({
    ...data,
    id: data.accountId, // Map accountId to id for backward compatibility
    name: data.accountName // Map accountName to name for backward compatibility
})); // Allow additional fields

// Load More Info Schema
export const LoadMoreInfoSchema = z.object({
    hasMore: z.boolean(),
    lastEvaluatedKey: z.record(z.string(), z.any()).optional(),
    itemsInCurrentBatch: z.number()
});

// API Response Schemas
export const TransactionsViewResponseSchema = z.object({
    transactions: z.array(z.any()).transform((txs: any[]) =>
        txs.map(tx => ({
            ...tx,
            amount: new Decimal(tx.amount?.toString() || '0'),
            balance: new Decimal(tx.balance?.toString() || '0')
        }))
    ),
    loadMore: LoadMoreInfoSchema,
    pagination: z.object({
        lastEvaluatedKey: z.record(z.string(), z.any()).optional()
    }).optional()
});

export const CategoriesResponseSchema = z.object({
    categories: z.array(CategoryInfoSchema)
}).or(z.array(CategoryInfoSchema)); // Support both wrapped and unwrapped formats

export const TransactionListResponseSchema = z.object({
    transactions: z.array(z.any()).transform((txs: any[]) =>
        txs.map(tx => ({
            ...tx,
            amount: new Decimal(tx.amount?.toString() || '0'),
            balance: new Decimal(tx.balance?.toString() || '0')
        }))
    ),
    metadata: z.object({
        totalTransactions: z.number(),
        fileId: z.string(),
        fileName: z.string().optional()
    }).passthrough() // Allow additional metadata fields
}).passthrough();

export const QuickUpdateResponseSchema = z.union([
    z.object({
        success: z.boolean(),
        transaction: z.any().optional()
    }),
    z.any().transform(tx => {
        // If it looks like a transaction, transform it
        if (tx.transactionId || tx.id) {
            return {
                ...tx,
                amount: new Decimal(tx.amount?.toString() || '0'),
                balance: new Decimal(tx.balance?.toString() || '0')
            };
        }
        return tx;
    })
]);

// Request Parameter Schemas
export const TransactionRequestParamsSchema = z.object({
    page: z.number().optional(),
    pageSize: z.number().optional(),
    startDate: z.number().optional(), // millisecond timestamp
    endDate: z.number().optional(),   // millisecond timestamp
    accountIds: z.array(z.string()).optional(),
    categoryIds: z.array(z.string()).optional(),
    transactionType: z.enum(['all', 'income', 'expense', 'transfer']).optional(),
    searchTerm: z.string().optional(),
    sortBy: z.string().optional(),
    sortOrder: z.enum(['asc', 'desc']).optional(),
    lastEvaluatedKey: z.record(z.string(), z.any()).optional(),
    ignoreDup: z.boolean().optional()
});

// Transaction Operations Schemas
export const TransactionCategoryUpdateRequestSchema = z.object({
    categoryId: z.string()
});

export const TransactionCategoryUpdateResponseSchema = z.object({
    success: z.boolean(),
    transaction: TransactionViewItemSchema.optional()
});

// Bulk Operations Schemas
export const BulkTransactionUpdateRequestSchema = z.object({
    transactionIds: z.array(z.string()),
    updates: z.object({
        category: z.string().optional(),
        payee: z.string().optional(),
        memo: z.string().optional(),
        notes: z.string().optional()
    })
});

export const BulkTransactionUpdateResponseSchema = z.object({
    updated: z.number(),
    errors: z.array(z.object({
        transactionId: z.string(),
        error: z.string()
    })).optional()
});

// Transaction Filters Schema
export const TransactionFiltersSchema = z.object({
    dateRange: z.object({
        start: z.number(),
        end: z.number()
    }).optional(),
    accountIds: z.array(z.string()).optional(),
    categoryIds: z.array(z.string()).optional(),
    amountRange: z.object({
        min: DecimalSchema,
        max: DecimalSchema
    }).optional(),
    transactionTypes: z.array(TransactionTypeSchema).optional(),
    searchTerm: z.string().optional(),
    hasCategory: z.boolean().optional(),
    isReconciled: z.boolean().optional()
});

// Transaction Statistics Schema
export const TransactionStatsSchema = z.object({
    totalCount: z.number(),
    totalIncome: DecimalSchema,
    totalExpenses: DecimalSchema,
    netAmount: DecimalSchema,
    averageTransaction: DecimalSchema,
    dateRange: z.object({
        earliest: z.number(),
        latest: z.number()
    }),
    accountBreakdown: z.array(z.object({
        accountId: z.string(),
        accountName: z.string(),
        transactionCount: z.number(),
        totalAmount: DecimalSchema
    })),
    categoryBreakdown: z.array(z.object({
        categoryId: z.string(),
        categoryName: z.string(),
        transactionCount: z.number(),
        totalAmount: DecimalSchema
    }))
});

// Error Schemas
export const TransactionErrorSchema = z.object({
    code: z.string(),
    message: z.string(),
    field: z.string().optional(),
    details: z.any().optional()
});

export const TransactionApiResponseSchema = z.object({
    success: z.boolean(),
    data: z.any().optional(),
    error: TransactionErrorSchema.optional(),
    message: z.string().optional()
});

// Form State Schema
export const TransactionFormStateSchema = z.object({
    transaction: TransactionSchema.partial(),
    isEditing: z.boolean(),
    isDirty: z.boolean(),
    isValid: z.boolean(),
    errors: z.record(z.string(), z.string())
});

// Type inference from schemas
export type Transaction = z.infer<typeof TransactionSchema>;
export type TransactionViewItem = z.infer<typeof TransactionViewItemSchema>;
export type CategoryInfo = z.infer<typeof CategoryInfoSchema>;
export type AccountInfo = z.infer<typeof AccountInfoSchema>;
export type LoadMoreInfo = z.infer<typeof LoadMoreInfoSchema>;
export type TransactionsViewResponse = z.infer<typeof TransactionsViewResponseSchema>;
export type TransactionListResponse = z.infer<typeof TransactionListResponseSchema>;
export type TransactionRequestParams = z.infer<typeof TransactionRequestParamsSchema>;
export type TransactionCategoryUpdateRequest = z.infer<typeof TransactionCategoryUpdateRequestSchema>;
export type TransactionCategoryUpdateResponse = z.infer<typeof TransactionCategoryUpdateResponseSchema>;
export type BulkTransactionUpdateRequest = z.infer<typeof BulkTransactionUpdateRequestSchema>;
export type BulkTransactionUpdateResponse = z.infer<typeof BulkTransactionUpdateResponseSchema>;
export type TransactionFilters = z.infer<typeof TransactionFiltersSchema>;
export type TransactionStats = z.infer<typeof TransactionStatsSchema>;
export type TransactionError = z.infer<typeof TransactionErrorSchema>;
export type TransactionApiResponse<T = any> = z.infer<typeof TransactionApiResponseSchema> & { data?: T };
export type TransactionFormState = z.infer<typeof TransactionFormStateSchema>;

// Export enum values for backward compatibility
export const TransactionType = {
    INCOME: "income" as const,
    EXPENSE: "expense" as const,
    TRANSFER: "transfer" as const
} as const;

export const DebitCredit = {
    DEBIT: "debit" as const,
    CREDIT: "credit" as const
} as const;

export const TransactionStatus = {
    PENDING: "pending" as const,
    CLEARED: "cleared" as const,
    RECONCILED: "reconciled" as const
} as const;

export const Currency = {
    USD: "USD" as const,
    EUR: "EUR" as const,
    GBP: "GBP" as const,
    CAD: "CAD" as const,
    JPY: "JPY" as const,
    AUD: "AUD" as const,
    CHF: "CHF" as const,
    CNY: "CNY" as const,
    OTHER: "other" as const
} as const;

// Transaction fields for form/display purposes
export const transactionFields = [
    'date',
    'description',
    'amount',
    'debitOrCredit',
    'currency'
] as const;

export type TransactionField = typeof transactionFields[number];
export type TransactionSortField = keyof Transaction | 'categoryName' | 'accountName';
export type TransactionSortOrder = 'asc' | 'desc';
