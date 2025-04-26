import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';
import { FieldMap } from './FieldMapService';

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
  openingBalance?: number;
  fieldMap?: {
    fieldMapId: string;
    name: string;
    description?: string;
  };
  startDate: number;  // Unix timestamp
  endDate: number;    // Unix timestamp
  transactionCount: number;
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
  openingBalance?: number;
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
    fieldMapId: string;
    name: string;
    description?: string;
  };
}

// Get API endpoint from environment variables
const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/api/files`;

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

// Update file opening balance
export interface UpdateBalanceResponse {
  fileId: string;
  openingBalance: number;
  transactionCount?: number;
  message: string;
}

export const updateFileBalance = async (fileId: string, openingBalance: number): Promise<UpdateBalanceResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/balance`, {
      method: 'POST',
      body: JSON.stringify({ openingBalance })
    });
    const data: UpdateBalanceResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error updating file balance:', error);
    throw error;
  }
};

// Associate a field map with a file
export const associateFieldMap = async (fileId: string, fieldMapId: string): Promise<void> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/field-map`, {
      method: 'PUT',
      body: JSON.stringify({ fieldMapId })
    });
    
    if (!response.ok) {
      throw new Error(`Failed to associate field map: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    console.error('Error associating field map:', error);
    throw error;
  }
};

// Get preview data for a file
// export const getFilePreview = async (fileId: string): Promise<FilePreviewResponse> => {
//   try {
//     const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/preview`);
//     const data: FilePreviewResponse = await response.json();
//     return data;
//   } catch (error) {
//     console.error('Error getting file preview:', error);
//     throw error;
//   }
// };

// Get file content
export const getFile = async (fileId: string): Promise<FileResponse> => {
  try {
    console.log(`Loading ${API_ENDPOINT}/${fileId}`);
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}`);
    const data: FileResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file:', error);
    throw error;
  }
};

export const getFileMetadata = async (fileId: string): Promise<FileMetadata> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/metadata`);
    const data: FileMetadata = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file metadata:', error);
    throw error;
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
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/content`);
    const data: FileContentResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting file content:', error);
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
  associateFileWithAccount,
  updateFileBalance,
  associateFieldMap,
  getFileMetadata,
  getFileContent
}; 