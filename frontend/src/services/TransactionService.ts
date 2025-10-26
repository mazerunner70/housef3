import { Decimal } from 'decimal.js';
import {
  TransactionListResponse,
  TransactionViewItem,
  TransactionsViewResponse,
  TransactionRequestParams,
  CategoryInfo,
  AccountInfo,
  transactionFields,
  TransactionsViewResponseSchema,
  CategoriesResponseSchema,
  AccountInfoSchema,
  TransactionListResponseSchema,
  QuickUpdateResponseSchema
} from '@/schemas/Transaction';
import ApiClient from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import {
  withApiLogging,
  withServiceLogging
} from '@/utils/logger';
import { z } from 'zod';

// Service-specific response interfaces
export interface QuickUpdateCategoryResponse {
  success: boolean;
  transaction?: TransactionViewItem;
}

export interface TransactionListRequest {
  fileId?: string;
  accountId?: string;
  limit?: number;
}

export interface CategoryUpdateRequest {
  categoryId: string;
}

// Note: Using efficient logging patterns (withApiLogging, withServiceLogging) instead of manual logger

// Helper function to add basic query parameters
const addBasicQueryParams = (query: URLSearchParams, params: TransactionRequestParams): void => {
  const pageSize = params.pageSize || 20;
  if (params.pageSize) query.append('pageSize', pageSize.toString());
  if (params.startDate !== undefined) query.append('startDate', params.startDate.toString());
  if (params.endDate !== undefined) query.append('endDate', params.endDate.toString());
  if (params.transactionType) query.append('transactionType', params.transactionType);
  if (params.searchTerm) query.append('searchTerm', params.searchTerm);
  if (params.sortBy) query.append('sortBy', params.sortBy);
  if (params.sortOrder) query.append('sortOrder', params.sortOrder);
  if (params.ignoreDup !== undefined) query.append('ignoreDup', params.ignoreDup.toString());
};

// Helper function to add array parameters
const addArrayQueryParams = (query: URLSearchParams, params: TransactionRequestParams): void => {
  if (params.accountIds && params.accountIds.length > 0) {
    query.append('accountIds', params.accountIds.join(','));
  }
  if (params.categoryIds && params.categoryIds.length > 0) {
    query.append('categoryIds', params.categoryIds.join(','));
  }
};

// Helper function to add pagination parameters
const addPaginationParams = (query: URLSearchParams, params: TransactionRequestParams): void => {
  if (params.lastEvaluatedKey) {
    const processedKey = { ...params.lastEvaluatedKey };
    if (processedKey.date && typeof processedKey.date === 'string') {
      const dateNum = Number.parseInt(processedKey.date, 10);
      if (!Number.isNaN(dateNum)) {
        processedKey.date = dateNum;
      }
    }
    query.append('lastEvaluatedKey', JSON.stringify(processedKey));
  }
};

// Helper function to build query parameters
const buildTransactionQuery = (params: TransactionRequestParams): URLSearchParams => {
  const query = new URLSearchParams();
  addBasicQueryParams(query, params);
  addArrayQueryParams(query, params);
  addPaginationParams(query, params);
  return query;
};

// Helper function to transform transaction response
const transformTransactionResponse = (rawData: any) => {
  return {
    transactions: rawData.transactions.map((tx: any) => ({
      ...tx,
      amount: new Decimal(tx.amount?.toString() || '0'),
      balance: new Decimal(tx.balance?.toString() || '0'),
    })),
    loadMore: {
      hasMore: !!rawData.pagination?.lastEvaluatedKey,
      lastEvaluatedKey: rawData.pagination?.lastEvaluatedKey,
      itemsInCurrentBatch: rawData.transactions?.length || 0
    }
  };
};

// Function to fetch transactions for the main transaction view - Simple LoadMore approach
export const listTransactions = withServiceLogging(
  'TransactionService',
  'listTransactions',
  async (params: TransactionRequestParams): Promise<TransactionsViewResponse> => {
    const query = buildTransactionQuery(params);
    const endpoint = `/transactions?${query.toString()}`;

    return validateApiResponse(
      () => ApiClient.getJson<any>(endpoint),
      (rawData) => {
        const processedResponse = transformTransactionResponse(rawData);
        return TransactionsViewResponseSchema.parse(processedResponse);
      },
      'transaction list data',
      'Failed to load transactions. The transaction data format is invalid.'
    );
  },
  {
    logArgs: ([params]) => ({
      pageSize: params.pageSize || 20,
      hasFilters: !!(params.accountIds?.length || params.categoryIds?.length || params.searchTerm),
      hasDateRange: !!(params.startDate || params.endDate),
      hasPagination: !!params.lastEvaluatedKey
    }),
    logResult: (result) => ({
      transactionCount: result.transactions.length,
      hasMore: result.loadMore.hasMore,
      itemsInBatch: result.loadMore.itemsInCurrentBatch
    })
  }
);

// Function to fetch all categories
export const listCategories = withApiLogging(
  'TransactionService',
  '/categories',
  'GET',
  async (url: string): Promise<CategoryInfo[]> => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => {
        const validatedResponse = CategoriesResponseSchema.parse(rawData);

        // Handle both wrapped and unwrapped formats
        if (Array.isArray(validatedResponse)) {
          return validatedResponse;
        }
        return validatedResponse.categories;
      },
      'categories data',
      'Failed to load categories. The categories data format is invalid.'
    );
  },
  {
    successData: (result) => ({ categoryCount: result.length })
  }
);

// Function to fetch all accounts
export const listAccounts = withApiLogging(
  'TransactionService',
  '/accounts',
  'GET',
  async (url: string): Promise<AccountInfo[]> => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => {
        // Handle both array format and wrapped format
        if (Array.isArray(rawData)) {
          return z.array(AccountInfoSchema).parse(rawData);
        }
        // If wrapped in accounts property
        if (rawData.accounts && Array.isArray(rawData.accounts)) {
          return z.array(AccountInfoSchema).parse(rawData.accounts);
        }
        throw new Error('Invalid accounts response format');
      },
      'accounts data',
      'Failed to load accounts. The accounts data format is invalid.'
    );
  },
  {
    successData: (result) => ({ accountCount: result.length })
  }
);

// Function for quick category update
export const updateTransactionCategory = (transactionId: string, categoryId: string) => withApiLogging(
  'TransactionService',
  `/transactions/${transactionId}/category`,
  'PUT',
  async (url: string): Promise<TransactionViewItem | { success: boolean }> => {
    return validateApiResponse(
      () => ApiClient.putJson<any>(url, { categoryId }),
      (rawData) => {
        const validatedResponse = QuickUpdateResponseSchema.parse(rawData);

        // If it's a success response with transaction data
        if (typeof validatedResponse === 'object' && validatedResponse !== null && 'success' in validatedResponse) {
          if (validatedResponse.transaction) {
            return validatedResponse.transaction;
          }
          return { success: validatedResponse.success };
        }

        // If it's a transaction object directly
        if (typeof validatedResponse === 'object' && validatedResponse !== null &&
          ('transactionId' in validatedResponse || 'id' in validatedResponse)) {
          return validatedResponse;
        }

        // Otherwise return success response
        return { success: true };
      },
      'transaction category update data',
      `Failed to update category for transaction ${transactionId}. The server response format is invalid.`
    );
  },
  {
    operationName: `updateTransactionCategory:${transactionId}`,
    successData: (result) => ({
      transactionId,
      categoryId,
      hasTransactionData: 'transactionId' in result || 'id' in result
    })
  }
);

// Re-export transactionFields for backward compatibility
export { transactionFields };

// --- End of New interfaces and functions ---

// Get transactions for a file
export const getFileTransactions = (fileId: string) => withApiLogging(
  'TransactionService',
  `/files/${fileId}/transactions`,
  'GET',
  async (url: string): Promise<TransactionListResponse> => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => TransactionListResponseSchema.parse(rawData),
      'file transactions data',
      `Failed to load transactions for file ${fileId}. The transaction data format is invalid.`
    );
  },
  {
    operationName: `getFileTransactions:${fileId}`,
    successData: (result) => ({
      fileId,
      transactionCount: result.transactions?.length || 0
    })
  }
);

// Get transactions for an account
export const getAccountTransactions = (accountId: string, limit: number = 50) => {
  const query = new URLSearchParams();
  query.append('limit', limit.toString());

  return withApiLogging(
    'TransactionService',
    `/accounts/${accountId}/transactions`,
    'GET',
    async (url: string): Promise<TransactionListResponse> => {
      return validateApiResponse(
        () => ApiClient.getJson<any>(url),
        (rawData) => TransactionListResponseSchema.parse(rawData),
        'account transactions data',
        `Failed to load transactions for account ${accountId}. The transaction data format is invalid.`
      );
    },
    {
      operationName: `getAccountTransactions:${accountId}`,
      queryParams: query,
      successData: (result) => ({
        accountId,
        limit,
        transactionCount: result.transactions?.length || 0
      })
    }
  );
};

// Backward compatibility aliases
export const getUserTransactions = listTransactions;
export const getCategories = listCategories;
export const getAccounts = listAccounts;
export const quickUpdateTransactionCategory: (transactionId: string, categoryId: string) => Promise<any> = updateTransactionCategory;

// Default export
export default {
  listTransactions,
  listCategories,
  listAccounts,
  updateTransactionCategory,
  getFileTransactions,
  getAccountTransactions,
  // Backward compatibility
  getUserTransactions,
  getCategories,
  getAccounts,
  quickUpdateTransactionCategory
};