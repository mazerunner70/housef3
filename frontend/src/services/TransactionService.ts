import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';
import { Decimal } from 'decimal.js';
import {

  TransactionListResponse,
  TransactionViewItem,
  TransactionsViewResponse,
  TransactionRequestParams,

  CategoryInfo,
  AccountInfo,
  transactionFields
} from '../types/Transaction';

// Get API endpoint from environment variables
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// Function to fetch transactions for the main transaction view - Simple LoadMore approach
export const getUserTransactions = async (params: TransactionRequestParams): Promise<TransactionsViewResponse> => {
  const pageSize = params.pageSize || 25;

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

  const endpoint = `${API_ENDPOINT}/api/transactions?${query.toString()}`;

  console.log(`Frontend LoadMore: Requesting from endpoint with lastEvaluatedKey:`, params.lastEvaluatedKey);

  try {
    const response = await authenticatedRequest(endpoint);
    const data = response as any; // Backend response format

    // Transform backend response to match TransactionViewItem interface
    const processedTransactions = data.transactions.map((tx: any) => ({
      ...tx,
      amount: new Decimal(tx.amount),
      balance: new Decimal(tx.balance),
      // Leave primaryCategoryId as-is, will be transformed in the component
    }));

    console.log(`Frontend LoadMore: Received ${processedTransactions.length} transactions`);

    const processedResponse: TransactionsViewResponse = {
      transactions: processedTransactions,
      loadMore: {
        hasMore: !!data.pagination?.lastEvaluatedKey,
        lastEvaluatedKey: data.pagination?.lastEvaluatedKey,
        itemsInCurrentBatch: processedTransactions.length
      }
    };

    return processedResponse;

  } catch (error) {
    console.error(`Frontend LoadMore: Error fetching transactions:`, error);
    throw error;
  }
};

// Function to fetch all categories
export const getCategories = async (): Promise<CategoryInfo[]> => {
  const endpoint = `${API_ENDPOINT}/api/categories`;
  try {
    const response = await authenticatedRequest(endpoint);

    // Backend returns { categories: [...], metadata: {...} }
    if (response && response.categories && Array.isArray(response.categories)) {
      return response.categories as CategoryInfo[];
    }
    // Fallback: if response is already an array (for backward compatibility)
    if (Array.isArray(response)) {
      return response as CategoryInfo[];
    }
    console.warn('Categories response is not in expected format:', response);
    return [];
  } catch (error) {
    console.error('Error fetching categories:', error);
    throw error;
  }
};

// Function to fetch all accounts
export const getAccounts = async (): Promise<AccountInfo[]> => {
  const endpoint = `${API_ENDPOINT}/api/accounts`;
  try {
    const response = await authenticatedRequest(endpoint);
    // Assuming API returns [{ id: "acc_123", name: "Checking Account" }, ...]
    return response as AccountInfo[]; // Adjust if API returns a more complex object e.g. { accounts: [] }
  } catch (error) {
    console.error('Error fetching accounts:', error);
    throw error;
  }
};

// Function for quick category update
export const quickUpdateTransactionCategory = async (transactionId: string, categoryId: string): Promise<TransactionViewItem | { success: boolean }> => {
  const endpoint = `${API_ENDPOINT}/api/transactions/${transactionId}/category`;
  try {
    const response = await authenticatedRequest(endpoint, {
      method: 'PUT',
      body: JSON.stringify({ categoryId }),
    });

    // If response contains transaction data, parse the amounts
    if (response && response.amount && response.balance) {
      return {
        ...response,
        amount: new Decimal(response.amount),
        balance: new Decimal(response.balance),
      };
    }

    // Otherwise, return the response as-is (likely a simple success message)
    return response;
  } catch (error) {
    console.error('Error updating transaction category:', error);
    throw error;
  }
};

// Re-export transactionFields for backward compatibility
export { transactionFields };

// --- End of New interfaces and functions ---

// Helper function to handle API requests with authentication
const authenticatedRequest = async (url: string, options: RequestInit = {}) => {
  const currentUser = getCurrentUser();

  if (!currentUser || !currentUser.token) {
    throw new Error('User not authenticated');
  }

  try {
    // Check if token is valid
    if (!isAuthenticated()) {
      // Try to refresh token
      await refreshToken(currentUser.refreshToken);
    }

    // Get the user again after potential refresh
    const user = getCurrentUser();
    if (!user || !user.token) {
      throw new Error('Authentication failed');
    }

    // Set up headers with authentication
    const headers = {
      'Authorization': user.token,
      'Content-Type': 'application/json',
      ...options.headers
    };

    const requestOptions = {
      ...options,
      headers
    };

    const response = await fetch(url, requestOptions);

    // Handle 401 error specifically - try to refresh token
    if (response.status === 401) {
      try {
        const refreshedUser = await refreshToken(user.refreshToken);

        // Update headers with new token
        const retryHeaders = {
          'Authorization': refreshedUser.token,
          'Content-Type': 'application/json',
          ...options.headers
        };

        // Retry the request with the new token
        const retryResponse = await fetch(url, {
          ...options,
          headers: retryHeaders
        });

        if (!retryResponse.ok) {
          throw new Error(`Request failed after token refresh: ${retryResponse.status} ${retryResponse.statusText}`);
        }

        return await retryResponse.json();
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        throw new Error('Session expired. Please log in again.');
      }
    }

    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error with authenticated request:', error);
    throw error;
  }
};

// Get transactions for a file
export const getFileTransactions = async (fileId: string): Promise<TransactionListResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/api/files/${fileId}/transactions`);

    // Transform the response to convert string amounts to Decimal objects
    const processedTransactions = response.transactions.map((tx: any) => ({
      ...tx,
      amount: new Decimal(tx.amount),
      balance: new Decimal(tx.balance),
    }));

    return {
      ...response,
      transactions: processedTransactions
    };
  } catch (error) {
    console.error('Error fetching file transactions:', error);
    throw error;
  }
};

// Get transactions for an account
export const getAccountTransactions = async (accountId: string, limit: number = 50): Promise<TransactionListResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/api/accounts/${accountId}/transactions?limit=${limit}`);

    // Transform the response to convert string amounts to Decimal objects
    const processedTransactions = response.transactions.map((tx: any) => ({
      ...tx,
      amount: new Decimal(tx.amount),
      balance: new Decimal(tx.balance),
    }));

    return {
      ...response,
      transactions: processedTransactions
    };
  } catch (error) {
    console.error('Error fetching account transactions:', error);
    throw error;
  }
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