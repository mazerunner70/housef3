import Decimal from 'decimal.js';
import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';
import { FileMetadata } from './FileService';


// Define enums to match backend
export enum AccountType {
  CHECKING = "checking",
  SAVINGS = "savings",
  CREDIT_CARD = "credit_card",
  INVESTMENT = "investment",
  LOAN = "loan",
  OTHER = "other"
}

export enum Currency {
  USD = "USD",
  EUR = "EUR",
  GBP = "GBP",
  CAD = "CAD",
  JPY = "JPY",
  AUD = "AUD",
  CHF = "CHF",
  CNY = "CNY",
  OTHER = "other"
}

// Define interfaces
export interface Account {
  accountId: string;
  userId: string;
  accountName: string;
  accountType: AccountType;
  institution: string;
  balance: Decimal;
  currency: Currency;
  notes?: string;
  isActive: boolean;
  defaultFileMapId?: string;
  lastTransactionDate?: number;  // milliseconds since epoch
  createdAt: number;
  updatedAt: number;
}

export interface AccountListResponse {
  accounts: Account[];
  user: {
    id: string;
    email: string;
    auth_time: string;
  };
  metadata: {
    totalAccounts: number;
  };
}

export interface AccountFilesResponse {
  files: FileMetadata[];
  user: {
    id: string;
    email: string;
    auth_time: string;
  };
  metadata: {
    totalFiles: number;
    accountId: string;
    accountName: string;
  };
}

export interface UploadFileToAccountResponse {
  fileId: string;
  uploadUrl: string;
  fileName: string;
  contentType: string;
  expires: number;
  processingStatus: string;
  fileFormat: string;
  accountId: string;
}

// Get API endpoint from environment variables
const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/api/accounts`;

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
        
        return retryResponse;
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        throw new Error('Session expired. Please log in again.');
      }
    }
    
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`);
    }
    
    return response;
  } catch (error) {
    console.error('Error with authenticated request:', error);
    throw error;
  }
};

// Get list of accounts
export const listAccounts = async (): Promise<AccountListResponse> => {
  try {
    const response = await authenticatedRequest(API_ENDPOINT);
    const data: AccountListResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error listing accounts:', error);
    throw error;
  }
};

// Get single account by ID
export const getAccount = async (accountId: string): Promise<{ account: Account }> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${accountId}`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Error getting account ${accountId}:`, error);
    throw error;
  }
};

// List files associated with an account
export const listAccountFiles = async (accountId: string): Promise<AccountFilesResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${accountId}/files`);
    const data: AccountFilesResponse = await response.json();
    return data;
  } catch (error) {
    console.error(`Error listing files for account ${accountId}:`, error);
    throw error;
  }
};

// Get upload URL for a file associated with an account
export const getAccountFileUploadUrl = async (
  accountId: string,
  fileName: string,
  contentType: string,
  fileSize: number
): Promise<UploadFileToAccountResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${accountId}/files`, {
      method: 'POST',
      body: JSON.stringify({
        fileName,
        contentType,
        fileSize
      })
    });
    
    const data: UploadFileToAccountResponse = await response.json();
    return data;
  } catch (error) {
    console.error(`Error getting upload URL for account ${accountId}:`, error);
    throw error;
  }
};

export const deleteAccount = async (accountId: string): Promise<void> => {
  await authenticatedRequest(`${API_ENDPOINT}/${accountId}`, {
    method: 'DELETE'
  });
};

// Create a new account
export const createAccount = async (accountData: Partial<Account>): Promise<{ account: Account }> => {
  try {
    const response = await authenticatedRequest(API_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify(accountData)
    });
    const data: { account: Account } = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating account:', error);
    throw error;
  }
};

// Update an existing account
export const updateAccount = async (accountId: string, accountData: Partial<Account>): Promise<{ account: Account }> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${accountId}`, {
      method: 'PUT',
      body: JSON.stringify(accountData)
    });
    const data: { account: Account } = await response.json();
    return data;
  } catch (error) {
    console.error(`Error updating account ${accountId}:`, error);
    throw error;
  }
};

interface TimelineResponse {
  timeline: FileMetadata[];
  accountId: string;
}

// Get file timeline (overlaps) for an account
export const getFileTimeline = async (accountId: string): Promise<TimelineResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${accountId}/timeline`);
    const data: TimelineResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching file timeline:', error);
    throw error;
  }
};

export default {
  listAccounts,
  getAccount,
  listAccountFiles,
  getAccountFileUploadUrl,
  deleteAccount,
  createAccount,
  updateAccount
}; 