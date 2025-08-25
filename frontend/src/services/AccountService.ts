import { FileMetadata } from './FileService';
import {
  Account,
  AccountListResponse,
  AccountSchema,
  AccountListResponseSchema
} from '../schemas/Account';
import { ApiClient } from '../utils/apiClient';
import { validateApiResponse } from '../utils/zodErrorHandler';
import { z } from 'zod';


// Account-specific response interfaces (not moved to types as they're service-specific)
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

// Zod schema for AccountFilesResponse validation
const AccountFilesResponseSchema = z.object({
  files: z.array(z.any()), // FileMetadata schema would need to be imported from FileService
  user: z.object({
    id: z.string(),
    email: z.string(),
    auth_time: z.string()
  }),
  metadata: z.object({
    totalFiles: z.number(),
    accountId: z.string(),
    accountName: z.string()
  })
});

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

// Zod schema for UploadFileToAccountResponse validation
const UploadFileToAccountResponseSchema = z.object({
  fileId: z.string(),
  uploadUrl: z.string(),
  fileName: z.string(),
  contentType: z.string(),
  expires: z.number(),
  processingStatus: z.string(),
  fileFormat: z.string(),
  accountId: z.string()
});

// Get API endpoint from environment variables
const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/api/accounts`;



// Get list of accounts
export const listAccounts = async (): Promise<AccountListResponse> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(API_ENDPOINT),
    (rawData) => {
      // Log raw data for debugging (only in development)
      if (process.env.NODE_ENV === 'development') {
        console.log('Raw account data received:', rawData);
      }
      return AccountListResponseSchema.parse(rawData);
    },
    'account list data'
  );
};

// Get single account by ID
export const getAccount = async (accountId: string): Promise<{ account: Account }> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/${accountId}`),
    (rawData) => {
      const validatedAccount = AccountSchema.parse(rawData.account);
      return { account: validatedAccount };
    },
    'account data',
    `Failed to load account ${accountId}. The account data format is invalid.`
  );
};

// List files associated with an account
export const listAccountFiles = async (accountId: string): Promise<AccountFilesResponse> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/${accountId}/files`),
    (rawData) => AccountFilesResponseSchema.parse(rawData),
    'account files data',
    `Failed to load files for account ${accountId}. The file data format is invalid.`
  );
};

// Get upload URL for a file associated with an account
export const getAccountFileUploadUrl = async (
  accountId: string,
  fileName: string,
  contentType: string,
  fileSize: number
): Promise<UploadFileToAccountResponse> => {
  return validateApiResponse(
    () => ApiClient.postJson<any>(`${API_ENDPOINT}/${accountId}/files`, {
      fileName,
      contentType,
      fileSize
    }),
    (rawData) => UploadFileToAccountResponseSchema.parse(rawData),
    'file upload URL data',
    `Failed to get upload URL for account ${accountId}. The server response format is invalid.`
  );
};

export const deleteAccount = async (accountId: string): Promise<void> => {
  await ApiClient.delete(`${API_ENDPOINT}/${accountId}`);
};

// Create a new account
export const createAccount = async (accountData: Partial<Account>): Promise<{ account: Account }> => {
  return validateApiResponse(
    () => ApiClient.postJson<any>(API_ENDPOINT, accountData),
    (rawData) => {
      const validatedAccount = AccountSchema.parse(rawData.account);
      return { account: validatedAccount };
    },
    'created account data',
    'Failed to create account. The server response format is invalid.'
  );
};

// Update an existing account
export const updateAccount = async (accountId: string, accountData: Partial<Account>): Promise<{ account: Account }> => {
  return validateApiResponse(
    () => ApiClient.putJson<any>(`${API_ENDPOINT}/${accountId}`, accountData),
    (rawData) => {
      const validatedAccount = AccountSchema.parse(rawData.account);
      return { account: validatedAccount };
    },
    'updated account data',
    `Failed to update account ${accountId}. The server response format is invalid.`
  );
};

interface TimelineResponse {
  timeline: FileMetadata[];
  accountId: string;
}

// Zod schema for TimelineResponse validation
const TimelineResponseSchema = z.object({
  timeline: z.array(z.any()), // FileMetadata schema would need to be imported from FileService
  accountId: z.string()
});

// Get file timeline (overlaps) for an account
export const getFileTimeline = async (accountId: string): Promise<TimelineResponse> => {
  return validateApiResponse(
    () => ApiClient.getJson<any>(`${API_ENDPOINT}/${accountId}/timeline`),
    (rawData) => TimelineResponseSchema.parse(rawData),
    'file timeline data',
    `Failed to load file timeline for account ${accountId}. The timeline data format is invalid.`
  );
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