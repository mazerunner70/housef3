import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';
import { Currency } from './AccountService';
import { Decimal } from 'decimal.js';

// Money interface to match backend model
export interface Money {
  amount: number;
  currency: Currency;
}

// Get API endpoint from environment variables
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// Transaction interface
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

// Extract the fields from the Transaction interface
export const transactionFields = [
  'date',
  'description',
  'amount',
  'debitOrCredit',
  'currency'
];

// Response interface for transaction list
export interface TransactionListResponse {
  transactions: Transaction[];
  metadata: {
    totalTransactions: number;
    fileId: string;
    fileName?: string;
  };
}

// --- New interfaces and functions for Transactions View ---

export interface CategoryInfo {
  id: string;
  name: string;
  // Add other fields if your API returns more, e.g., type, parentId
}

export interface AccountInfo {
  id: string;
  // name: string; // Remove name, as we'll fetch it separately
  // Add other fields if your API returns more, e.g., type, currency
}

export interface TransactionViewItem extends Omit<Transaction, 'category' | 'account' | 'date' | 'amount'> {
  id: string; // transactionId from existing Transaction interface
  date: number; // milliseconds since epoch
  description: string;
  payee?: string;
  category: CategoryInfo; // Use new CategoryInfo
  account?: string;   // Changed to string (accountId)
  amount: Decimal; 
  balance: Decimal; 
  currency: Currency;
  type: 'income' | 'expense' | 'transfer';
  notes?: string;
  isSplit?: boolean;
}

export interface PaginationInfo {
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  lastEvaluatedKey?: Record<string, any>;
}

export interface TransactionsViewResponse {
  transactions: TransactionViewItem[];
  pagination: PaginationInfo;
}

export interface TransactionRequestParams {
  page?: number;
  pageSize?: number;
  startDate?: number; // Changed to number for millisecond timestamp
  endDate?: number;   // Changed to number for millisecond timestamp
  accountIds?: string[];
  categoryIds?: string[];
  transactionType?: 'all' | 'income' | 'expense' | 'transfer';
  searchTerm?: string;
  sortBy?: keyof TransactionViewItem | string;
  sortOrder?: 'asc' | 'desc';
  lastEvaluatedKey?: Record<string, any>;
  ignoreDup?: boolean;
}

// Function to fetch transactions for the main transaction view
export const getUserTransactions = async (params: TransactionRequestParams): Promise<TransactionsViewResponse> => {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.pageSize) query.append('pageSize', params.pageSize.toString());
  
  // Append timestamps as strings
  if (params.startDate !== undefined) query.append('startDate', params.startDate.toString());
  if (params.endDate !== undefined) query.append('endDate', params.endDate.toString());
  
  if (params.accountIds && params.accountIds.length > 0) query.append('accountIds', params.accountIds.join(','));
  if (params.categoryIds && params.categoryIds.length > 0) query.append('categoryIds', params.categoryIds.join(','));
  if (params.transactionType) query.append('transactionType', params.transactionType);
  if (params.searchTerm) query.append('searchTerm', params.searchTerm);
  if (params.sortBy) query.append('sortBy', params.sortBy as string);
  if (params.sortOrder) query.append('sortOrder', params.sortOrder);
  if (params.lastEvaluatedKey) query.append('lastEvaluatedKey', JSON.stringify(params.lastEvaluatedKey));
  if (params.ignoreDup !== undefined) query.append('ignoreDup', params.ignoreDup.toString());

  const endpoint = `${API_ENDPOINT}/api/transactions?${query.toString()}`; 
  try {
    const response = await authenticatedRequest(endpoint);
    const data = response as TransactionsViewResponse; // Cast to the expected response type

    // Ensure financial values are Decimal instances
    const processedTransactions = data.transactions.map(tx => ({
      ...tx,
      amount: new Decimal(tx.amount),
      balance: new Decimal(tx.balance),
    }));

    const processedResponse: TransactionsViewResponse = {
      ...data,
      transactions: processedTransactions,
    };
    
    console.log('processedResponse size', processedResponse.transactions.length);
    return processedResponse;
  } catch (error) {
    console.error('Error fetching user transactions:', error);
    throw error;
  }
};

// Function to fetch all categories
export const getCategories = async (): Promise<CategoryInfo[]> => {
  const endpoint = `${API_ENDPOINT}/api/categories`;
  try {
    const response = await authenticatedRequest(endpoint);
    // Assuming API returns [{ id: "cat_abc", name: "Groceries" }, ...]
    return response as CategoryInfo[]; // Adjust if API returns a more complex object e.g. { categories: [] }
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
    // The response could be the updated transaction or a simple success message
    return response; 
  } catch (error) {
    console.error('Error updating transaction category:', error);
    throw error;
  }
};

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
    return response;
  } catch (error) {
    console.error('Error fetching file transactions:', error);
    throw error;
  }
};

// Get transactions for an account
export const getAccountTransactions = async (accountId: string, limit: number = 50): Promise<TransactionListResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/api/accounts/${accountId}/transactions?limit=${limit}`);
    return response;
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