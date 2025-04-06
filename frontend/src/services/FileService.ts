import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';

export interface FileMetadata {
  fileId: string;
  fileName: string;
  contentType: string;
  fileSize: number;
  uploadDate: string;
  lastModified: string;
  accountId?: string;
  accountName?: string;
  fileFormat?: 'csv' | 'ofx' | 'qfx' | 'pdf' | 'xlsx' | 'other';
  processingStatus?: 'pending' | 'processing' | 'processed' | 'error';
  errorMessage?: string;
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

// Get CloudFront domain from environment variables
const CLOUDFRONT_DOMAIN = import.meta.env.VITE_CLOUDFRONT_DOMAIN || '';
const API_ENDPOINT = `https://${CLOUDFRONT_DOMAIN}/files`;

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

// Get list of files
export const listFiles = async (): Promise<FileListResponse> => {
  try {
    const response = await authenticatedRequest(API_ENDPOINT);
    const data: FileListResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error listing files:', error);
    throw error;
  }
};

// Get upload URL for a file
export const getUploadUrl = async (
  fileName: string, 
  contentType: string, 
  fileSize: number, 
  accountId?: string
): Promise<UploadUrlResponse> => {
  try {
    const requestBody: any = {
      fileName,
      contentType,
      fileSize
    };
    
    // Add accountId to request if provided
    if (accountId) {
      requestBody.accountId = accountId;
    }
    
    const response = await authenticatedRequest(`${API_ENDPOINT}/upload`, {
      method: 'POST',
      body: JSON.stringify(requestBody)
    });
    
    const data: UploadUrlResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting upload URL:', error);
    throw error;
  }
};

// Upload file to S3 using presigned URL
export const uploadFileToS3 = async (uploadUrl: string, file: File): Promise<void> => {
  try {
    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type
      }
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error('Error uploading file to S3:', error);
    throw error;
  }
};

// Get download URL for a file
export const getDownloadUrl = async (fileId: string): Promise<DownloadUrlResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/download`);
    const data: DownloadUrlResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting download URL:', error);
    throw error;
  }
};

// Delete a file
export const deleteFile = async (fileId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/${fileId}`, {
      method: 'DELETE'
    });
  } catch (error) {
    console.error('Error deleting file:', error);
    throw error;
  }
};

// Unassociate a file from an account
export const unassociateFileFromAccount = async (fileId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/${fileId}/unassociate`, {
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
    await authenticatedRequest(`${API_ENDPOINT}/${fileId}/associate`, {
      method: 'POST',
      body: JSON.stringify({ accountId })
    });
  } catch (error) {
    console.error('Error associating file with account:', error);
    throw error;
  }
};

export default {
  listFiles,
  getUploadUrl,
  uploadFileToS3,
  getDownloadUrl,
  deleteFile,
  unassociateFileFromAccount,
  associateFileWithAccount
}; 