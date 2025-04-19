import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';

// Get API endpoint from environment variables
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT;

// Transaction interface
export interface Transaction {
  transactionId: string;
  fileId: string;
  date: string;
  description: string;
  amount: number;
  runningTotal: number;
  transactionType?: string;
  category?: string;
  payee?: string;
  memo?: string;
  checkNumber?: string;
  reference?: string;
  debitOrCredit?: string;
}
// Extract the fields from the Transaction interface
export const transactionFields = [
  'date',
  'description',
  'amount',
  'transactionType',
  'category',
  'debitOrCredit'
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
export const getAccountTransactions = async (accountId: string): Promise<TransactionListResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/api/account/${accountId}`);
    return response;
  } catch (error) {
    console.error('Error fetching account transactions:', error);
    throw error;
  }
};

// Default export
export default {
  getFileTransactions,
  getAccountTransactions
}; 