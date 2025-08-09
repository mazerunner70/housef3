import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';

// FZIP Backup Types
export enum FZIPBackupStatus {
  INITIATED = "backup_initiated",
  COLLECTING_DATA = "backup_processing", 
  BUILDING_FZIP_PACKAGE = "backup_processing",
  UPLOADING = "backup_processing",
  COMPLETED = "backup_completed",
  FAILED = "backup_failed"
}

export enum FZIPBackupType {
  COMPLETE = "complete",
  ACCOUNTS_ONLY = "accounts_only",
  TRANSACTIONS_ONLY = "transactions_only",
  CATEGORIES_ONLY = "categories_only"
}

export interface FZIPBackupJob {
  backupId: string;
  status: FZIPBackupStatus;
  backupType: FZIPBackupType;
  requestedAt: number;
  completedAt?: number;
  progress: number;
  downloadUrl?: string;
  expiresAt?: number;
  packageSize?: number;
  description?: string;
  validation?: {
    overall_quality: string;
    data_integrity_score: number;
    completeness_score: number;
    files_processed: number;
    files_failed: number;
    compression_ratio: number;
    processing_time_seconds: number;
    issues: string[];
    recommendations: string[];
  };
  manifest_checksums?: Record<string, string>;
  error?: string;
}

// FZIP Restore Types
export enum FZIPRestoreStatus {
  // Mirror backend FZIPStatus values exactly
  UPLOADED = "restore_uploaded",
  VALIDATING = "restore_validating",
  VALIDATION_PASSED = "restore_validation_passed",
  VALIDATION_FAILED = "restore_validation_failed",
  PROCESSING = "restore_processing",
  COMPLETED = "restore_completed",
  FAILED = "restore_failed",
  CANCELED = "restore_canceled"
}

export interface FZIPRestoreJob {
  jobId: string;
  status: FZIPRestoreStatus;
  createdAt: number;
  completedAt?: number;
  progress: number;
  currentPhase: string;
  packageSize?: number;
  validationResults?: {
    profileEmpty: boolean;
    schemaValid: boolean;
    ready: boolean;
  };
  restoreResults?: {
    accounts_restored: number;
    transactions_restored: number;
    categories_restored: number;
    files_restored: number;
  };
  error?: string;
}

// API Request/Response Types
export interface InitiateFZIPBackupRequest {
  includeAnalytics?: boolean;
  backupType?: FZIPBackupType;
  description?: string;
}

export interface InitiateFZIPBackupResponse {
  backupId: string;
  status: FZIPBackupStatus;
  estimatedSize?: string;
  estimatedCompletion?: string;
}

export interface FZIPBackupListResponse {
  backups: FZIPBackupJob[];  // API uses "backups" not "exports"
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  packageFormat?: string;
}

export interface CreateFZIPRestoreRequest {
  validateOnly?: boolean;
}

export interface CreateFZIPRestoreResponse {
  restoreId: string;
  status: FZIPRestoreStatus;
  message: string;
  uploadUrl?: {
    url: string;
    fields: Record<string, string>;
  };
  profileSummary?: {
    accounts_count: number;
    transactions_count: number;
    categories_count: number;
    file_maps_count: number;
    transaction_files_count: number;
  };
  suggestion?: string;
}

export interface FZIPRestoreListResponse {
  restoreJobs: FZIPRestoreJob[];  // API returns "restoreJobs"
  nextEvaluatedKey?: string;
  packageFormat?: string;
}

export interface FZIPRestoreUploadUrlResponse {
  restoreId: string;
  url: string;
  fields: Record<string, string>;
  expiresIn: number;
}

// Get API endpoint from environment variables
const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/api`;

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

// ========== BACKUP OPERATIONS ==========

// Initiate FZIP backup
export const initiateFZIPBackup = async (
  request: InitiateFZIPBackupRequest = {}
): Promise<InitiateFZIPBackupResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/backup`, {
      method: 'POST',
      body: JSON.stringify(request)
    });
    
    const backendData = await response.json();
    
    // Map backend response fields to frontend format
    const data: InitiateFZIPBackupResponse = {
      backupId: backendData.jobId,
      status: backendData.status as FZIPBackupStatus,
      estimatedSize: backendData.estimatedSize,
      estimatedCompletion: backendData.estimatedCompletion
    };
    
    return data;
  } catch (error) {
    console.error('Error initiating FZIP backup:', error);
    throw error;
  }
};

// Get FZIP backup status
export const getFZIPBackupStatus = async (backupId: string): Promise<FZIPBackupJob> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/backup/${backupId}/status`);
    const backendData = await response.json();
    return convertBackupResponseToFrontend(backendData);
  } catch (error) {
    console.error(`Error getting FZIP backup status for ${backupId}:`, error);
    throw error;
  }
};

// Get FZIP backup download URL
export const getFZIPBackupDownloadUrl = async (backupId: string): Promise<string> => {
  try {
    // Try direct JSON response first (new approach)
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/backup/${backupId}/download`);
    
    if (response.status === 200) {
      // New approach: JSON response with downloadUrl
      const data = await response.json();
      return data.downloadUrl || data.url;
    }
    
    // Fallback: handle 302 redirect (old approach)
    if (response.status === 302) {
      const location = response.headers.get('Location');
      if (location) {
        return location;
      }
    }
    
    // If neither worked, try parsing as JSON anyway
    const data = await response.json();
    return data.downloadUrl || data.url;
  } catch (error) {
    console.error(`Error getting FZIP backup download URL for ${backupId}:`, error);
    throw error;
  }
};

// Helper function to convert backend backup response to frontend format
const convertBackupResponseToFrontend = (backendBackup: any): FZIPBackupJob => {
  // Handle both FZIPResponse and FZIPStatusResponse formats
  const backupType = backendBackup.backupType || 
    (backendBackup.jobType === 'backup' ? FZIPBackupType.COMPLETE : undefined);
  
  // Handle timestamp conversion - some responses may have ISO strings, others have numbers
  const parseTimestamp = (value: any): number | undefined => {
    if (!value) return undefined;
    if (typeof value === 'number') return value;
    if (typeof value === 'string') {
      // Try parsing as ISO string first
      const date = new Date(value);
      if (!isNaN(date.getTime())) {
        return date.getTime();
      }
      // Try parsing as string number
      const num = parseInt(value);
      return isNaN(num) ? undefined : num;
    }
    return undefined;
  };

  // Parse packageSize - now just validates it's a number
  const parsePackageSize = (packageSize: any): number | undefined => {
    if (packageSize && typeof packageSize === 'number') return packageSize;
    return undefined;
  };

  return {
    backupId: backendBackup.jobId,
    status: backendBackup.status as FZIPBackupStatus,
    backupType: backupType as FZIPBackupType,
    requestedAt: parseTimestamp(backendBackup.createdAt) || Date.now(),
    completedAt: parseTimestamp(backendBackup.completedAt),
    progress: backendBackup.progress || (backendBackup.status === 'backup_completed' ? 100 : 0),
    downloadUrl: backendBackup.downloadUrl,
    expiresAt: parseTimestamp(backendBackup.expiresAt),
    packageSize: parsePackageSize(backendBackup.packageSize),
    description: backendBackup.description,
    error: backendBackup.error
  };
};



// List FZIP backups
export const listFZIPBackups = async (
  limit: number = 20,
  offset: number = 0
): Promise<FZIPBackupListResponse> => {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString()
    });
    
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/backup?${params}`);
    const backendData = await response.json();
    
    // Convert backend response to frontend format
    const convertedBackups = backendData.backups.map(convertBackupResponseToFrontend);
    
    return {
      backups: convertedBackups,
      total: backendData.total,
      limit: backendData.limit,
      offset: backendData.offset,
      hasMore: backendData.hasMore,
      packageFormat: backendData.packageFormat
    };
  } catch (error) {
    console.error('Error listing FZIP backups:', error);
    throw error;
  }
};

// Delete FZIP backup
export const deleteFZIPBackup = async (backupId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/fzip/backup/${backupId}`, {
      method: 'DELETE'
    });
  } catch (error) {
    console.error(`Error deleting FZIP backup ${backupId}:`, error);
    throw error;
  }
};

// ========== RESTORE OPERATIONS ==========

// Start FZIP restore processing (for jobs that have passed validation)
export const startFZIPRestoreProcessing = async (restoreId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/start`, {
      method: 'POST'
    });
  } catch (error) {
    console.error(`Error starting FZIP restore processing for ${restoreId}:`, error);
    throw error;
  }
};

// Get presigned POST for uploading a .fzip restore package (simplified flow)
export const getFZIPRestoreUploadUrl = async (): Promise<FZIPRestoreUploadUrlResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/upload-url`, {
      method: 'POST'
    });
    const data: FZIPRestoreUploadUrlResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting FZIP restore upload URL:', error);
    throw error;
  }
};

// Create FZIP restore job
export const createFZIPRestoreJob = async (
  request: CreateFZIPRestoreRequest = {}
): Promise<CreateFZIPRestoreResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/restore`, {
      method: 'POST',
      body: JSON.stringify(request)
    });
    
    const data: CreateFZIPRestoreResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating FZIP restore job:', error);
    throw error;
  }
};

// Get FZIP restore status
export const getFZIPRestoreStatus = async (restoreId: string): Promise<FZIPRestoreJob> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/status`);
    const data: FZIPRestoreJob = await response.json();
    return data;
  } catch (error) {
    console.error(`Error getting FZIP restore status for ${restoreId}:`, error);
    throw error;
  }
};

// List FZIP restore jobs
export const listFZIPRestoreJobs = async (
  limit: number = 20,
  lastEvaluatedKey?: string
): Promise<FZIPRestoreListResponse> => {
  try {
    const params = new URLSearchParams({
      limit: limit.toString()
    });
    
    if (lastEvaluatedKey) {
      params.append('lastEvaluatedKey', lastEvaluatedKey);
    }
    
    const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/restore?${params}`);
    const data: FZIPRestoreListResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error listing FZIP restore jobs:', error);
    throw error;
  }
};

// Delete FZIP restore job
export const deleteFZIPRestoreJob = async (restoreId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}`, {
      method: 'DELETE'
    });
  } catch (error) {
    console.error(`Error deleting FZIP restore job ${restoreId}:`, error);
    throw error;
  }
};

// Cancel an in-progress restore (simplified flow)
export const cancelFZIPRestore = async (restoreId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/cancel`, {
      method: 'POST'
    });
  } catch (error) {
    console.error(`Error canceling FZIP restore ${restoreId}:`, error);
    throw error;
  }
};

// Upload FZIP package for restore
export const uploadFZIPPackage = async (
  restoreId: string,
  file: File,
  uploadUrl: { url: string; fields: Record<string, string> }
): Promise<void> => {
  try {
    // Create form data for S3 upload
    const formData = new FormData();
    
    // Add S3 fields first
    Object.entries(uploadUrl.fields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    
    // Add file last (required by S3)
    formData.append('file', file);
    
    // Upload to S3
    const uploadResponse = await fetch(uploadUrl.url, {
      method: 'POST',
      body: formData
    });
    
    if (!uploadResponse.ok) {
      throw new Error(`Upload failed: ${uploadResponse.status} ${uploadResponse.statusText}`);
    }
    
    // Notify backend that upload is complete
    await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/upload`, {
      method: 'POST'
    });
    
  } catch (error) {
    console.error(`Error uploading FZIP package for restore ${restoreId}:`, error);
    throw error;
  }
};

// Helper function to download FZIP backup file
export const downloadFZIPBackup = async (backupId: string, filename?: string): Promise<void> => {
  try {
    const downloadUrl = await getFZIPBackupDownloadUrl(backupId);
    
    // Use window.open for cross-origin downloads to avoid CORS issues
    // This approach is more reliable for S3 presigned URLs
    const finalFilename = filename || `backup_${backupId}.fzip`;
    
    // First try the standard approach
    try {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = finalFilename;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (linkError) {
      // Fallback: Open in new window if link approach fails
      console.warn('Link download failed, falling back to window.open:', linkError);
      window.open(downloadUrl, '_blank');
    }
  } catch (error) {
    console.error(`Error downloading FZIP backup ${backupId}:`, error);
    throw error;
  }
};

// Helper function to format backup status for display
export const formatBackupStatus = (status: FZIPBackupStatus): string => {
  switch (status) {
    case FZIPBackupStatus.INITIATED:
      return 'Initiated';
    case FZIPBackupStatus.COLLECTING_DATA:
      return 'Processing';
    case FZIPBackupStatus.COMPLETED:
      return 'Completed';
    case FZIPBackupStatus.FAILED:
      return 'Failed';
    default:
      return status;
  }
};

// Helper function to format restore status for display
export const formatRestoreStatus = (status: FZIPRestoreStatus): string => {
  switch (status) {
    case FZIPRestoreStatus.UPLOADED:
      return 'Uploaded';
    case FZIPRestoreStatus.VALIDATING:
      return 'Validating';
    case FZIPRestoreStatus.VALIDATION_PASSED:
      return 'Validation Passed';
    case FZIPRestoreStatus.VALIDATION_FAILED:
      return 'Validation Failed';
    case FZIPRestoreStatus.PROCESSING:
      return 'Processing';
    case FZIPRestoreStatus.COMPLETED:
      return 'Completed';
    case FZIPRestoreStatus.FAILED:
      return 'Failed';
    case FZIPRestoreStatus.CANCELED:
      return 'Canceled';
    default:
      return status;
  }
};