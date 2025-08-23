// Transaction Type Definitions
// These interfaces define the data models for transactions and related operations

import { Decimal } from 'decimal.js';
import { Currency } from './Account';

// Core Transaction Model
export interface Transaction {
    transactionId: string;
    fileId: string;
    userId: string;
    date: number;  // milliseconds since epoch
    description: string;
    amount: Decimal;
    balance: Decimal;
    currency: Currency;
    transactionType?: string;
    category?: string;
    payee?: string;
    memo?: string;
    checkNumber?: string;
    reference?: string;
    accountId?: string;
    status?: string;
    debitOrCredit?: string;
    importOrder?: number;
}

// Transaction fields for form/display purposes
export const transactionFields = [
    'date',
    'description',
    'amount',
    'debitOrCredit',
    'currency'
] as const;

// API Response Types
export interface TransactionListResponse {
    transactions: Transaction[];
    metadata: {
        totalTransactions: number;
        fileId: string;
        fileName?: string;
    };
}

// Transaction View Models (for main transactions view)
export interface CategoryInfo {
    categoryId: string;
    name: string;
    userId: string;
    type: string;
    parentCategoryId: string | null;
}

export interface AccountInfo {
    id: string;
    // Additional fields can be added as needed
}

export interface TransactionViewItem extends Omit<Transaction, 'category' | 'account' | 'date' | 'amount'> {
    id: string; // transactionId from existing Transaction interface
    date: number; // milliseconds since epoch
    description: string;
    payee?: string;
    category?: CategoryInfo; // Optional - will be populated from primaryCategoryId
    primaryCategoryId?: string; // From backend response
    categories?: any[]; // Category assignments from backend
    account?: string;   // Changed to string (accountId)
    amount: Decimal;
    balance: Decimal;
    currency: Currency;
    type: 'income' | 'expense' | 'transfer';
    notes?: string;
    isSplit?: boolean;
}

// Pagination and Load More
export interface LoadMoreInfo {
    hasMore: boolean;
    lastEvaluatedKey?: Record<string, any>;
    itemsInCurrentBatch: number;
}

export interface TransactionsViewResponse {
    transactions: TransactionViewItem[];
    loadMore: LoadMoreInfo;
}

// Request Parameters
export interface TransactionRequestParams {
    page?: number;
    pageSize?: number;
    startDate?: number; // millisecond timestamp
    endDate?: number;   // millisecond timestamp
    accountIds?: string[];
    categoryIds?: string[];
    transactionType?: 'all' | 'income' | 'expense' | 'transfer';
    searchTerm?: string;
    sortBy?: keyof TransactionViewItem | string;
    sortOrder?: 'asc' | 'desc';
    lastEvaluatedKey?: Record<string, any>;
    ignoreDup?: boolean;
}

// Transaction Operations
export interface TransactionCategoryUpdateRequest {
    categoryId: string;
}

export interface TransactionCategoryUpdateResponse {
    success: boolean;
    transaction?: TransactionViewItem;
}

// Bulk Operations
export interface BulkTransactionUpdateRequest {
    transactionIds: string[];
    updates: Partial<Pick<Transaction, 'category' | 'payee' | 'memo' | 'notes'>>;
}

export interface BulkTransactionUpdateResponse {
    updated: number;
    errors?: Array<{
        transactionId: string;
        error: string;
    }>;
}

// Transaction Filtering and Search
export interface TransactionFilters {
    dateRange?: {
        start: number;
        end: number;
    };
    accountIds?: string[];
    categoryIds?: string[];
    amountRange?: {
        min: Decimal;
        max: Decimal;
    };
    transactionTypes?: Array<'income' | 'expense' | 'transfer'>;
    searchTerm?: string;
    hasCategory?: boolean;
    isReconciled?: boolean;
}

// Transaction Statistics
export interface TransactionStats {
    totalCount: number;
    totalIncome: Decimal;
    totalExpenses: Decimal;
    netAmount: Decimal;
    averageTransaction: Decimal;
    dateRange: {
        earliest: number;
        latest: number;
    };
    accountBreakdown: Array<{
        accountId: string;
        accountName: string;
        transactionCount: number;
        totalAmount: Decimal;
    }>;
    categoryBreakdown: Array<{
        categoryId: string;
        categoryName: string;
        transactionCount: number;
        totalAmount: Decimal;
    }>;
}

// Form State Types
export interface TransactionFormState {
    transaction: Partial<Transaction>;
    isEditing: boolean;
    isDirty: boolean;
    isValid: boolean;
    errors: Record<string, string>;
}

// Error Types
export interface TransactionError {
    code: string;
    message: string;
    field?: string;
    details?: any;
}

export interface TransactionApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: TransactionError;
    message?: string;
}

// Utility Types
export type TransactionSortField = keyof Transaction | 'categoryName' | 'accountName';
export type TransactionSortOrder = 'asc' | 'desc';

// Export type for transaction field names (for type safety)
export type TransactionField = typeof transactionFields[number];
