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
import { ApiClient } from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import { z } from 'zod';

// Service-specific response interfaces
export interface QuickUpdateCategoryResponse {
  success: boolean;
  transaction?: TransactionViewItem;
}

// Schemas are now imported from ../schemas/Transaction.ts

// API base path - ApiClient will handle the full URL construction
const API_ENDPOINT = '';

// Function to fetch transactions for the main transaction view - Simple LoadMore approach
export const getUserTransactions = async (params: TransactionRequestParams): Promise<TransactionsViewResponse> => {
  const pageSize = params.pageSize || 20;

  console.log(`Frontend LoadMore: Fetching ${pageSize} transactions`);

  // Build query parameters for this request
  const query = new URLSearchParams();
  if (params.pageSize) query.append('pageSize', pageSize.toString());

  // Append timestamps as strings
  if (params.startDate !== undefined) query.append('startDate', params.startDate.toString());
  if (params.endDate !== undefined) query.append('endDate', params.endDate.toString());

  if (params.accountIds && params.accountIds.length > 0) query.append('accountIds', params.accountIds.join(','));
  if (params.categoryIds && params.categoryIds.length > 0) query.append('categoryIds', params.categoryIds.join(','));
  if (params.transactionType) query.append('transactionType', params.transactionType);
  if (params.searchTerm) query.append('searchTerm', params.searchTerm);
  if (params.sortBy) query.append('sortBy', params.sortBy as string);
  if (params.sortOrder) query.append('sortOrder', params.sortOrder);

  if (params.lastEvaluatedKey) {
    // Fix data types for DynamoDB compatibility: convert date from string to number
    // This happens because JSON serialization converts numbers to strings
    const processedKey = { ...params.lastEvaluatedKey };
    if (processedKey.date && typeof processedKey.date === 'string') {
      const dateNum = parseInt(processedKey.date, 10);
      if (!isNaN(dateNum)) {
        processedKey.date = dateNum;
        console.log(`Frontend: Converted lastEvaluatedKey date from string "${params.lastEvaluatedKey.date}" to number ${dateNum}`);
      } else {
        console.warn(`Frontend: Failed to convert lastEvaluatedKey date "${processedKey.date}" to number`);
      }
    }
    query.append('lastEvaluatedKey', JSON.stringify(processedKey));
  }

  if (params.ignoreDup !== undefined) query.append('ignoreDup', params.ignoreDup.toString());

  const endpoint = `${API_ENDPOINT}/transactions?${query.toString()}`;

  console.log(`Frontend LoadMore: Requesting from endpoint with lastEvaluatedKey:`, params.lastEvaluatedKey);

  return validateApiResponse(
    () => ApiClient.getJson<any>(endpoint),
    (rawData) => {
      console.log(`Frontend LoadMore: Received ${rawData.transactions?.length || 0} transactions`);

      // Transform response to match expected format
      const processedResponse = {
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

      return TransactionsViewResponseSchema.parse(processedResponse);
    },
    'transaction list data',
    'Failed to load transactions. The transaction data format is invalid.'
  );
};

// Function to fetch all categories
export const getCategories = async (): Promise<CategoryInfo[]> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/categories`),
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
};

// Function to fetch all accounts
export const getAccounts = async (): Promise<AccountInfo[]> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/accounts`),
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
};

// Function for quick category update
export const quickUpdateTransactionCategory = async (transactionId: string, categoryId: string): Promise<TransactionViewItem | { success: boolean }> => {
  return validateApiResponse(
    () => ApiClient.putJson<any>(`${API_ENDPOINT}/transactions/${transactionId}/category`, { categoryId }),
    (rawData) => {
      const validatedResponse = QuickUpdateResponseSchema.parse(rawData);

      // If it's a success response with transaction data
      if (typeof validatedResponse === 'object' && validatedResponse !== null && 'success' in validatedResponse) {
        if (validatedResponse.transaction) {
          return validatedResponse.transaction as any;
        }
        return { success: validatedResponse.success };
      }

      // If it's a transaction object directly
      if (typeof validatedResponse === 'object' && validatedResponse !== null &&
        ('transactionId' in validatedResponse || 'id' in validatedResponse)) {
        return validatedResponse as any;
      }

      // Otherwise return success response
      return { success: true };
    },
    'transaction category update data',
    `Failed to update category for transaction ${transactionId}. The server response format is invalid.`
  );
};

// Re-export transactionFields for backward compatibility
export { transactionFields };

// --- End of New interfaces and functions ---

// Get transactions for a file
export const getFileTransactions = async (fileId: string): Promise<TransactionListResponse> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/files/${fileId}/transactions`),
    (rawData) => TransactionListResponseSchema.parse(rawData),
    'file transactions data',
    `Failed to load transactions for file ${fileId}. The transaction data format is invalid.`
  );
};

// Get transactions for an account
export const getAccountTransactions = async (accountId: string, limit: number = 50): Promise<TransactionListResponse> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/accounts/${accountId}/transactions?limit=${limit}`),
    (rawData) => TransactionListResponseSchema.parse(rawData),
    'account transactions data',
    `Failed to load transactions for account ${accountId}. The transaction data format is invalid.`
  );
};

// Default export
export default {
  getFileTransactions,
  getAccountTransactions,
  getUserTransactions,
  getCategories,
  getAccounts,
  quickUpdateTransactionCategory
};