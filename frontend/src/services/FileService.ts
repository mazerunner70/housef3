import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';
import { FieldMap } from './FileMapService';
import { v4 as uuidv4 } from 'uuid';
import Decimal from 'decimal.js';

export interface FileMetadata {
  fileId: string;
  fileName: string;
  contentType?: string;
  fileSize: number;
  uploadDate: string | number;
  lastModified?: string;
  accountId?: string;
  accountName?: string;
  fileFormat?: 'csv' | 'ofx' | 'qfx' | 'pdf' | 'xlsx' | 'other';
  processingStatus?: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'ERROR' | 'PROCESSED' | 'processed';
  processedDate?: number;
  errorMessage?: string;
  openingBalance?: Decimal | string;  // Can be Decimal or string from API
  closingBalance?: Decimal | string;  // Can be Decimal or string from API
  currency?: string;
  fieldMap?: {
    fieldMapId?: string; // API uses this field name
    name: string;
    description?: string | null;
  };
  // API response structure for date range
  dateRange?: {
    start_date: number;
    end_date: number;
  };
  // Legacy fields for backward compatibility
  startDate?: number;  // Unix timestamp
  endDate?: number;    // Unix timestamp
  transactionCount: number;
  duplicateCount?: number;
  s3Key?: string;
  userId?: string;
  createdAt?: number;
  updatedAt?: number;
}

export interface FileListResponse {
  files: FileMetadata[];
  user: {
    id: string;
    email: string;
    auth_time: string;
  };
  metadata: {
    totalFiles: number;
    timestamp: string;
  };
}

export interface UploadUrlResponse {
  fileId: string;
  uploadUrl: string;
  fileName: string;
  contentType: string;
  expires: number;
}

export interface DownloadUrlResponse {
  fileId: string;
  downloadUrl: string;
  fileName: string;
  contentType: string;
  expires: number;
}

export interface File {
  fileId: string;
  fileName: string;
  contentType: string;
  size: number;
  uploadedAt: string;
  userId: string;
  accountId?: string;
  fieldMap?: FieldMap;
  openingBalance?: Decimal;  // Frontend uses Decimal for precision
}

export interface FilePreviewResponse {
  data: Array<Record<string, any>>;
  totalRows: number;
  columns: string[];
}

export interface FileResponse {
  fileId: string;
  fileName: string;
  contentType: string;
  fileSize: number;
  content: string;
  uploadDate: string;
  accountId?: string;
  fieldMap?: {
    fileMapId: string;
    name: string;
    description?: string;
  };
}

// This interface represents the actual structure returned by the getUploadUrl backend endpoint
export interface GetUploadUrlResponse {
  fileId: string;
  url: string; // This is the S3 presigned URL
  fields: Record<string, string>; // These are the S3 presigned POST fields
  expires: number;
}

// Get API endpoint from environment variables
const API_BASE_URL = import.meta.env.VITE_API_ENDPOINT;
const ACCOUNTS_API_ENDPOINT = `${API_BASE_URL}/api/accounts`;
const FILES_API_ENDPOINT = `${API_BASE_URL}/api/files`;

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
          const error = new Error(`Request failed after token refresh: ${retryResponse.status} ${retryResponse.statusText}`);
          (error as any).status = retryResponse.status;
          (error as any).statusText = retryResponse.statusText;
          throw error;
        }

        return retryResponse;
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        throw new Error('Session expired. Please log in again.');
      }
    }

    if (!response.ok) {
      const error = new Error(`Request failed: ${response.status} ${response.statusText}`);
      (error as any).status = response.status;
      (error as any).statusText = response.statusText;
      throw error;
    }

    return response;
  } catch (error) {
    console.error('Error with authenticated request:', error);
    throw error;
  }
};

// Helper function to convert backend response to frontend FileMetadata with Decimal conversion
const convertBackendFileToFileMetadata = (backendFile: any): FileMetadata => {
  return {
    ...backendFile,
    openingBalance: backendFile.openingBalance ? new Decimal(backendFile.openingBalance) : undefined,
    closingBalance: backendFile.closingBalance ? new Decimal(backendFile.closingBalance) : undefined,
  };
};

// Helper function to convert backend UpdateBalanceResponse to frontend format
const convertBackendUpdateBalanceResponse = (backendResponse: any): UpdateBalanceResponse => {
  return {
    ...backendResponse,
    openingBalance: new Decimal(backendResponse.openingBalance),
  };
};

// Update file closing balance (which calculates new opening balance)
export interface UpdateClosingBalanceResponse extends FileMetadata {
  // This is now the full FileMetadata object since backend returns complete transaction file
}

// Helper function to convert backend UpdateClosingBalanceResponse to frontend format
const convertBackendUpdateClosingBalanceResponse = (backendResponse: any): UpdateClosingBalanceResponse => {
  // Backend now returns full transaction file, so convert like any FileMetadata
  return convertBackendFileToFileMetadata(backendResponse);
};

// Get list of files
export const listFiles = async (): Promise<FileListResponse> => {
  try {
    const response = await authenticatedRequest(FILES_API_ENDPOINT);
    const data: any = await response.json();

    // Convert backend files to frontend FileMetadata with Decimal conversion
    const convertedFiles = data.files.map(convertBackendFileToFileMetadata);

    return {
      ...data,
      files: convertedFiles,
    };
  } catch (error) {
    console.error('Error listing files:', error);
    throw error;
  }
};

// Get list of files for a specific account
export const listFilesByAccount = async (accountId: string): Promise<FileListResponse> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/account/${accountId}`);
    const data: any = await response.json();

    // Convert backend files to frontend FileMetadata with Decimal conversion
    const convertedFiles = data.files.map(convertBackendFileToFileMetadata);

    return {
      ...data,
      files: convertedFiles,
    };
  } catch (error) {
    console.error(`Error listing files for account ${accountId}:`, error);
    throw error;
  }
};

// Get upload URL for a file
export const getUploadUrl = async (
  fileName: string,
  contentType: string,
  fileSize: number,
  userId: string,
  accountId?: string
): Promise<GetUploadUrlResponse> => {
  try {
    // Generate a unique file ID
    const fileId = uuidv4();

    // Create the S3 key using the user ID, file ID, and filename
    const s3Key = `${userId}/${fileId}/${fileName}`;

    console.log('Getting presigned URL with:', {
      fileName,
      contentType,
      fileSize,
      userId,
      accountId,
      fileId,
      s3Key
    });

    // Get presigned URL for S3 upload
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/upload`, {
      method: 'POST',
      body: JSON.stringify({
        key: s3Key,
        contentType,
        fileId,  // Pass file_id explicitly
        accountId,
        metadata: {
          fileid: fileId,  // Store file_id in metadata
          ...(accountId && { accountid: accountId })
        }
      })
    });

    const data: GetUploadUrlResponse = await response.json();
    console.log('Received presigned URL data:', data);

    return data;
  } catch (error) {
    console.error('Error getting upload URL:', error);
    throw error;
  }
};

// Upload file to S3 using presigned URL
export const uploadFileToS3 = async (presignedUploadData: GetUploadUrlResponse, file: Blob, accountId?: string): Promise<void> => {
  try {
    // For logging, safely get file properties
    const fileName = file instanceof File ? file.name : 'unnamed-blob';
    const fileType = file.type || 'application/octet-stream';
    const fileSize = file.size;

    console.log('Starting S3 upload with:', {
      url: presignedUploadData.url,
      fields: presignedUploadData.fields,
      accountId,
      fileName,
      fileType,
      fileSize
    });

    const formData = new FormData();

    // Add all fields from presigned URL - these MUST come before the file
    // The order of fields is important for S3's policy validation
    Object.entries(presignedUploadData.fields).forEach(([key, value]) => {
      formData.append(key, value);
      console.log(`Adding presigned field: ${key} = ${value}`);
    });

    // Add the file - MUST be the last field and named 'file'
    formData.append('file', file);

    console.log('FormData contents:');
    for (const [key, value] of formData.entries()) {
      console.log(`${key}: ${value instanceof Blob ? 'File data' : value}`);
    }

    // Set proper options for S3 direct upload
    const uploadOptions = {
      method: 'POST',
      body: formData
    };

    const response = await fetch(presignedUploadData.url, uploadOptions);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Upload failed with response:', {
        status: response.status,
        statusText: response.statusText,
        headers: Object.fromEntries(response.headers.entries()),
        body: errorText
      });
      throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    console.log('Upload successful:', {
      status: response.status,
      headers: Object.fromEntries(response.headers.entries())
    });
  } catch (error) {
    console.error('Error uploading file to S3:', error);
    throw error;
  }
};

// Get download URL for a file
export const getDownloadUrl = async (fileId: string): Promise<DownloadUrlResponse> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/download`);
    const data: DownloadUrlResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting download URL:', error);
    throw error;
  }
};

// Delete a file - returns operation ID for tracking
export const deleteFile = async (fileId: string): Promise<{ operationId: string }> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}`, {
      method: 'DELETE'
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
};

// Unassociate a file from an account
export const unassociateFileFromAccount = async (fileId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/unassociate`, {
      method: 'POST'
    });
  } catch (error) {
    console.error('Error unassociating file from account:', error);
    throw error;
  }
};

// Associate a file with an account
export const associateFileWithAccount = async (fileId: string, accountId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/associate`, {
      method: 'PUT',
      body: JSON.stringify({ accountId })
    });
  } catch (error) {
    console.error('Error associating file with account:', error);
    throw error;
  }
};

// Update file opening balance
export interface UpdateBalanceResponse {
  fileId: string;
  openingBalance: Decimal;  // Frontend uses Decimal for precision
  transactionCount?: number;
  message: string;
}

export const updateFileBalance = async (fileId: string, openingBalance: Decimal): Promise<UpdateBalanceResponse> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/balance`, {
      method: 'PUT',
      body: JSON.stringify({ openingBalance: openingBalance.toString() })  // Send as string to backend
    });
    const data = await response.json();
    return convertBackendUpdateBalanceResponse(data);  // Convert to Decimal
  } catch (error) {
    console.error('Error updating file balance:', error);
    throw error;
  }
};

// Update file closing balance
export const updateFileClosingBalance = async (fileId: string, closingBalance: Decimal): Promise<UpdateClosingBalanceResponse> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/closing-balance`, {
      method: 'PUT',
      body: JSON.stringify({ closingBalance: closingBalance.toString() })  // Send as string to backend
    });
    const data = await response.json();
    return convertBackendUpdateClosingBalanceResponse(data);  // Convert to Decimal
  } catch (error) {
    console.error('Error updating file closing balance:', error);
    throw error;
  }
};

// Associate a field map with a file
export const associateFieldMap = async (fileId: string, fieldMapId: string): Promise<void> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/file-map`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        fileMapId: fieldMapId  // Use fileMapId as expected by the backend
      })
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.message || `Failed to associate field map: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error('Error associating field map:', error);
    throw error;
  }
};

//Get preview data for a file
export const getFilePreview = async (fileId: string): Promise<FilePreviewResponse> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/preview`);
    const data: FilePreviewResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file preview:', error);
    throw error;
  }
};

// Get file content
export const getFile = async (fileId: string): Promise<FileResponse> => {
  try {
    console.log(`Loading ${FILES_API_ENDPOINT}/${fileId}`);
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}`);
    const data: FileResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file:', error);
    throw error;
  }
};

export const getFileMetadata = async (fileId: string): Promise<FileMetadata> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/metadata`);
    const data: FileMetadata = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file metadata:', error);
    throw error;
  }
};

// Wait for file processing to complete after S3 upload
export const waitForFileProcessing = async (
  fileId: string,
  maxWaitTime: number = 10000,
  pollInterval: number = 500
): Promise<FileMetadata> => {
  console.log(`Waiting for file ${fileId} to be processed...`);
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitTime) {
    try {
      const metadata = await getFileMetadata(fileId);
      console.log(`File ${fileId} status: ${metadata.processingStatus}`);

      // File exists and has been processed
      if (metadata.processingStatus &&
        ['COMPLETED', 'PROCESSED', 'ERROR'].includes(metadata.processingStatus)) {
        return metadata;
      }

      // File exists but still processing, continue polling
      if (metadata.processingStatus &&
        ['PENDING', 'PROCESSING'].includes(metadata.processingStatus)) {
        console.log(`File ${fileId} still processing, waiting...`);
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        continue;
      }

      // File exists but unknown status, return it anyway
      return metadata;

    } catch (error: any) {
      // If 404, the file hasn't been created yet, continue polling
      if (error.status === 404 ||
        error.message?.includes('404') ||
        error.message?.includes('Not Found') ||
        error.message?.includes('File not found')) {
        console.log(`File ${fileId} not found yet (${error.status || 'unknown status'}), continuing to poll...`);
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        continue;
      }

      // If it's a network error, retry
      if (error.message?.includes('NetworkError') ||
        error.message?.includes('fetch') ||
        error.message?.includes('Failed to fetch')) {
        console.log(`Network error while polling for file ${fileId}, retrying...`);
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        continue;
      }

      // Other error, re-throw
      console.error(`Error while waiting for file ${fileId}:`, error);
      throw error;
    }
  }

  throw new Error(`File processing timeout after ${maxWaitTime}ms for file ${fileId}`);
};

// Enhanced parseFile function for components that need more control
export const parseFileWithPolling = async (
  fileId: string,
  onStatusUpdate?: (status: string) => void
): Promise<{ data?: any[], headers?: string[], error?: string, file_format?: 'csv' | 'ofx' | 'qfx' | 'qif' }> => {
  try {
    console.log(`Starting parseFileWithPolling for fileId: ${fileId}`);
    onStatusUpdate?.('Waiting for file processing...');

    // Wait for the file to be processed
    let metadata: FileMetadata;
    try {
      metadata = await waitForFileProcessing(fileId, 15000, 1000);
      onStatusUpdate?.(`File processed: ${metadata.processingStatus}`);
    } catch (waitError: any) {
      console.error(`Timeout waiting for file ${fileId}:`, waitError);
      onStatusUpdate?.('Processing timeout');
      return { error: `File processing timeout. Please try again.` };
    }

    // Check processing status
    if (metadata.processingStatus === 'ERROR') {
      const errorMsg = metadata.errorMessage || 'File processing failed';
      onStatusUpdate?.('Processing failed');
      return { error: errorMsg };
    }

    onStatusUpdate?.('Generating preview...');
    return await getFilePreviewData(fileId);

  } catch (error: any) {
    console.error('Error in parseFileWithPolling:', error);
    onStatusUpdate?.('Error occurred');
    return { error: error.message || 'An error occurred' };
  }
};

// Get file content directly from API
export interface FileContentResponse {
  fileId: string;
  content: string;
  contentType: string;
  fileName: string;
}

export const getFileContent = async (fileId: string): Promise<FileContentResponse> => {
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/content`);
    const data: FileContentResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file content:', error);
    throw error;
  }
};

// TODO: Define these types more accurately based on actual backend responses
// These are initial placeholders based on hook types and design doc.
export interface ServiceFile {
  fileId: string;
  fileName: string;
  uploadDate: string; // Or number (timestamp)
  status?: string;     // e.g., "Processed", "Pending"
  transactionCount?: number;
  accountId?: string | null;
  // Add other fields that the backend might return for a file
}

export interface LinkFileRequestBody {
  accountId: string;
}

/**
 * Lists files associated with a specific account.
 * Uses GET /api/accounts/{accountId}/files as per updated design.
 */
export const listAssociatedFiles = async (accountId: string): Promise<ServiceFile[]> => {
  // Use the /api/accounts/{accountId}/files endpoint
  const url = `${ACCOUNTS_API_ENDPOINT}/${accountId}/files`;
  const response = await authenticatedRequest(url);
  const data = await response.json();
  // The response structure from account_files_handler might be different.
  // Assuming it returns an object with a 'files' array similar to other list endpoints.
  // Adjust if necessary based on actual backend response.
  return data.files || [];
};

/**
 * Lists unlinked files for the current user.
 * GET /api/files (no accountId implies unlinked for the user)
 */
export const listUnlinkedFiles = async (): Promise<ServiceFile[]> => {
  const url = `${FILES_API_ENDPOINT}`;
  const response = await authenticatedRequest(url);
  const data = await response.json();
  // Filter for files where accountId is null or undefined
  const unlinkedFiles = (data.files || []).filter((file: ServiceFile) => !file.accountId);
  return unlinkedFiles;
};

/**
 * Links an existing file to an account.
 * PUT /api/files/{fileId}/associate
 */
export const linkFileToAccount = async (fileId: string, accountId: string): Promise<void> => {
  const url = `${FILES_API_ENDPOINT}/${fileId}/associate`;
  const body: LinkFileRequestBody = { accountId };
  await authenticatedRequest(url, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
  // Typically, PUT operations might return the updated resource or 204 No Content
  // For simplicity, not expecting a specific response body here for void promise
};

/**
 * Unlinks a file from an account (sets its accountId to null).
 * PUT /api/files/{fileId}/unassociate
 */
export const unlinkFileFromAccount = async (fileId: string): Promise<void> => {
  const url = `${FILES_API_ENDPOINT}/${fileId}/unassociate`;
  await authenticatedRequest(url, {
    method: 'PUT',
  });
  // As above, not expecting a specific response body for void promise
};

// Internal function to call the preview endpoint directly
const getFilePreviewData = async (fileId: string): Promise<{ data?: any[], headers?: string[], error?: string, file_format?: 'csv' | 'ofx' | 'qfx' | 'qif' }> => {
  const url = `${FILES_API_ENDPOINT}/${fileId}/preview`;
  console.log(`Calling GET ${url} for parsing/previewing file.`);

  // authenticatedRequest will throw an error for non-ok HTTP responses.
  const response = await authenticatedRequest(url, { method: 'GET' });

  // We expect the backend for GET /api/files/{fileId}/preview to return a structure like:
  // { data?: any[], columns?: string[], fileFormat?: 'csv' | 'ofx' | 'qfx', error?: string /* optional error in body */ }
  // The 'fileType' field is crucial and assumed to be provided by this endpoint.
  // The 'columns' field (from existing FilePreviewResponse) will be mapped to 'headers'.
  const result: {
    data?: any[],
    columns?: string[],
    fileFormat?: 'csv' | 'ofx' | 'qfx' | 'qif',
    error?: string
  } = await response.json();

  // Check if the response body itself contains an error message, even if HTTP status was 2xx.
  if (result.error) {
    console.error(`Error message in response body from ${url}:`, result.error);
    return { error: result.error };
  }

  // Ensure essential fields are present for a successful parse, especially fileType.
  if (!result.fileFormat) {
    console.error(`'fileType' missing in response from ${url} for fileId: ${fileId}`);
    return { error: `'fileType' is missing from the preview response. Cannot determine how to process the file.` };
  }

  return {
    data: result.data,
    headers: result.columns, // Mapping 'columns' from preview response to 'headers'
    file_format: result.fileFormat,
  };
};

// Parse file function with polling for file processing completion
export const parseFile = async (fileId: string): Promise<{ data?: any[], headers?: string[], error?: string, file_format?: 'csv' | 'ofx' | 'qfx' | 'qif' }> => {
  try {
    console.log(`Starting parseFile for fileId: ${fileId}`);

    // First, wait for the file to be processed by the S3 trigger Lambda
    let metadata: FileMetadata;
    try {
      metadata = await waitForFileProcessing(fileId, 15000, 1000); // Wait up to 15 seconds
    } catch (waitError: any) {
      console.error(`Timeout waiting for file ${fileId} to be processed:`, waitError);
      return { error: `File processing timeout. The file may still be being processed. Please try again in a moment.` };
    }

    // Check if file processing failed
    if (metadata.processingStatus === 'ERROR') {
      const errorMsg = metadata.errorMessage || 'File processing failed';
      console.error(`File ${fileId} processing failed:`, errorMsg);
      return { error: errorMsg };
    }

    // Now call the preview endpoint
    return await getFilePreviewData(fileId);

  } catch (err: any) {
    // This catches errors from authenticatedRequest (network, non-ok HTTP status) 
    // or errors from response.json() if the body isn't valid JSON.
    console.error(`Error during parseFile (using GET ${FILES_API_ENDPOINT}/${fileId}/preview):`, err);
    let errorMessage = 'An unexpected error occurred while trying to retrieve file preview data.';
    if (err.message) {
      errorMessage = err.message;
    }
    return { error: errorMessage };
  }
};

export interface FileProcessResult { // Based on backend FileProcessorResponse
  fileId: string;
  fileName: string;
  statusCode: number; // HTTP status from the API call itself, or derived from processingStatus
  message: string;    // Message from backend processor
  processingStatus: string; // e.g., "COMPLETED", "FAILED", "PENDING", "PROCESSING"
  transactionCount?: number;
  accountName?: string;
}

function adaptBackendFileMetaToProcessResult(meta: FileMetadata, httpStatusCode: number = 200): FileProcessResult {
  return {
    fileId: meta.fileId,
    fileName: meta.fileName,
    statusCode: httpStatusCode,
    message: meta.errorMessage || `File status: ${meta.processingStatus || 'UNKNOWN'}`,
    processingStatus: meta.processingStatus || 'UNKNOWN',
    transactionCount: meta.transactionCount,
    accountName: meta.accountName,
  };
}

/**
 * Associates a field map with a file and triggers processing.
 * Corresponds to PUT /files/{fileId}/file-map
 * The backend for this endpoint is expected to return a FileProcessorResponse structure.
 */
export async function updateFileFieldMapAssociation(fileId: string, fileMapId: string): Promise<FileProcessResult> {
  console.log(`FileService: Associating map ${fileMapId} with file ${fileId} and triggering processing.`);
  try {
    const response = await authenticatedRequest(`${FILES_API_ENDPOINT}/${fileId}/file-map`, {
      method: 'PUT',
      body: JSON.stringify({ fileMapId: fileMapId }),
    });
    const data = await response.json();

    return {
      fileId: data.fileId || fileId,
      fileName: data.fileName,
      statusCode: response.status,
      message: data.message || (response.ok ? 'Map associated, processing triggered.' : 'Failed to associate map.'),
      // Ensure these statuses align with what your backend PUT /files/{id}/file-map actually returns in FileProcessorResponse
      processingStatus: data.processingStatus || (response.ok ? 'PROCESSING' : 'ERROR'),
      transactionCount: data.transactionCount,
      accountName: data.accountName,
    };

  } catch (error: any) {
    console.error('Error associating field map or processing file:', error);
    return {
      fileId,
      fileName: 'Unknown',
      statusCode: error.response?.status || 500,
      message: error.message || 'Failed to associate map and trigger processing.',
      processingStatus: 'ERROR',
      transactionCount: 0,
    };
  }
}

/**
 * Gets detailed metadata for a single file and adapts it to FileProcessResult.
 * Uses polling to wait for the file record to be created by the file processor.
 * Corresponds to GET /files/{fileId}/metadata.
 */
export async function getProcessedFileMetadata(fileId: string): Promise<FileProcessResult> {
  console.log(`FileService: Getting processed metadata for file ${fileId} with polling.`);
  try {
    // Use the same polling mechanism as parseFile to wait for file processing
    const metadata = await waitForFileProcessing(fileId, 15000, 1000); // Wait up to 15 seconds
    return adaptBackendFileMetaToProcessResult(metadata, 200);
  } catch (error: any) {
    console.error('Error getting processed file metadata:', error);
    return {
      fileId,
      fileName: 'Unknown',
      statusCode: error.response?.status || 500,
      message: error.message || 'Failed to retrieve file processing status. The file may still be processing.',
      processingStatus: 'ERROR',
      transactionCount: undefined,
      accountName: undefined,
    };
  }
}

export default {
  listFiles,
  getUploadUrl,
  uploadFileToS3,
  getDownloadUrl,
  deleteFile,
  unassociateFileFromAccount,
  associateFileWithAccount,
  updateFileBalance,
  updateFileClosingBalance,
  associateFieldMap,
  getFileMetadata,
  getFileContent,
  listAssociatedFiles,
  listUnlinkedFiles,
  linkFileToAccount,
  unlinkFileFromAccount,
  parseFile,
  updateFileFieldMapAssociation,
  getProcessedFileMetadata
}; 