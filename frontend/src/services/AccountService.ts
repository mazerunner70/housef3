import { FileMetadata } from './FileService';
import {
  Account,
  AccountListResponse,
  AccountSchema,
  AccountListResponseSchema
} from '@/schemas/Account';
import { ApiClient } from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import { z } from 'zod';

// Import efficient logging utilities
import {
  withApiLogging,
  withServiceLogging,
  createLogger
} from '@/utils/logger';


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

// API endpoint path - ApiClient will handle the full URL construction
const API_ENDPOINT = '/accounts';

// Logger for simple operations that don't need API wrapper
const logger = createLogger('AccountService');

// ============ EFFICIENT LOGGING IMPLEMENTATIONS ============

// Get list of accounts - with automatic API logging
export const listAccounts = withApiLogging(
  'AccountService',
  API_ENDPOINT,
  'GET',
  async (url) => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => {
        // Only log business-specific data - everything else is automatic
        logger.info('Account list processed', {
          accountCount: rawData.accounts?.length || 0,
          hasMetadata: !!rawData.metadata
        });
        return AccountListResponseSchema.parse(rawData);
      },
      'account list data'
    );
  },
  {
    successData: (result) => ({ accountCount: result.accounts.length })
  }
);

// Get single account by ID - with automatic API logging
export const getAccount = (accountId: string) => withApiLogging(
  'AccountService',
  `${API_ENDPOINT}/${accountId}`,
  'GET',
  async (url) => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => {
        const validatedAccount = AccountSchema.parse(rawData.account);
        return { account: validatedAccount };
      },
      'account data',
      `Failed to load account ${accountId}. The account data format is invalid.`
    );
  },
  {
    operationName: `getAccount:${accountId}`,
    successData: (result) => ({
      accountId,
      accountName: result.account.accountName,
      accountType: result.account.accountType,
      balance: result.account.balance.toString()
    })
  }
);

// List files associated with an account - with automatic API logging
export const listAccountFiles = (accountId: string) => withApiLogging(
  'AccountService',
  `${API_ENDPOINT}/${accountId}/files`,
  'GET',
  async (url) => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => {
        // Log business-specific data for large file sets
        if (rawData.files?.length > 50) {
          logger.info('Large file set detected', {
            accountId,
            fileCount: rawData.files.length,
            totalSize: rawData.files.reduce((sum: number, f: any) => sum + (f.fileSize || 0), 0)
          });
        }
        return AccountFilesResponseSchema.parse(rawData);
      },
      'account files data',
      `Failed to load files for account ${accountId}. The file data format is invalid.`
    );
  },
  {
    operationName: `listAccountFiles:${accountId}`,
    successData: (result) => ({
      accountId,
      fileCount: result.files.length,
      totalFiles: result.metadata.totalFiles
    })
  }
);

// Get upload URL for a file associated with an account - with automatic API logging
export const getAccountFileUploadUrl = (
  accountId: string,
  fileName: string,
  contentType: string,
  fileSize: number
) => withApiLogging(
  'AccountService',
  `${API_ENDPOINT}/${accountId}/files`,
  'POST',
  async (url) => {
    return validateApiResponse(
      () => ApiClient.postJson<any>(url, {
        fileName,
        contentType,
        fileSize
      }),
      (rawData) => UploadFileToAccountResponseSchema.parse(rawData),
      'file upload URL data',
      `Failed to get upload URL for account ${accountId}. The server response format is invalid.`
    );
  },
  {
    operationName: `getUploadUrl:${accountId}:${fileName}`,
    successData: (result) => ({
      accountId,
      fileId: result.fileId,
      fileName: result.fileName,
      fileFormat: result.fileFormat,
      fileSizeMB: Math.round(fileSize / 1024 / 1024 * 100) / 100
    })
  }
);

// Delete account - simple operation with basic logging
export const deleteAccount = async (accountId: string): Promise<void> => {
  logger.info('Deleting account', { accountId });

  try {
    await ApiClient.delete(`${API_ENDPOINT}/${accountId}`);
    logger.info('Account deleted successfully', { accountId });
  } catch (error) {
    logger.error('Account deletion failed', { accountId });
    throw error;
  }
};

// Create a new account - with service-level logging
export const createAccount = withServiceLogging(
  'AccountService',
  'createAccount',
  async (accountData: Partial<Account>) => {
    return validateApiResponse(
      () => ApiClient.postJson<any>(API_ENDPOINT, accountData),
      (rawData) => {
        const validatedAccount = AccountSchema.parse(rawData.account);
        return { account: validatedAccount };
      },
      'created account data',
      'Failed to create account. The server response format is invalid.'
    );
  },
  {
    logArgs: ([accountData]) => ({
      accountName: accountData.accountName,
      accountType: accountData.accountType,
      fieldsProvided: Object.keys(accountData)
    }),
    logResult: (result) => ({
      accountId: result.account.accountId,
      accountName: result.account.accountName,
      accountType: result.account.accountType
    })
  }
);

// Update an existing account - with automatic API logging
export const updateAccount = (accountId: string, accountData: Partial<Account>) => withApiLogging(
  'AccountService',
  `${API_ENDPOINT}/${accountId}`,
  'PUT',
  async (url) => {
    return validateApiResponse(
      () => ApiClient.putJson<any>(url, accountData),
      (rawData) => {
        const validatedAccount = AccountSchema.parse(rawData.account);
        return { account: validatedAccount };
      },
      'updated account data',
      `Failed to update account ${accountId}. The server response format is invalid.`
    );
  },
  {
    operationName: `updateAccount:${accountId}`,
    successData: (result) => ({
      accountId,
      accountName: result.account.accountName,
      accountType: result.account.accountType,
      updatedFields: Object.keys(accountData)
    })
  }
);

export interface TimelineResponse {
  timeline: FileMetadata[];
  accountId: string;
}

// Zod schema for TimelineResponse validation
const TimelineResponseSchema = z.object({
  timeline: z.array(z.any()), // FileMetadata schema would need to be imported from FileService
  accountId: z.string()
});

// Get file timeline (overlaps) for an account - with automatic API logging
export const getFileTimeline = (accountId: string) => withApiLogging(
  'AccountService',
  `${API_ENDPOINT}/${accountId}/timeline`,
  'GET',
  async (url) => {
    return validateApiResponse(
      () => ApiClient.getJson<any>(url),
      (rawData) => TimelineResponseSchema.parse(rawData),
      'file timeline data',
      `Failed to load file timeline for account ${accountId}. The timeline data format is invalid.`
    );
  },
  {
    operationName: `getFileTimeline:${accountId}`,
    successData: (result) => ({
      accountId,
      timelineEntries: result.timeline.length
    })
  }
);

export default {
  listAccounts,
  getAccount,
  listAccountFiles,
  getAccountFileUploadUrl,
  deleteAccount,
  createAccount,
  updateAccount,
  getFileTimeline
}; 