import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';

export interface FieldMap {
  fieldMapId: string;
  name: string;
  description?: string;
  accountId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface FieldMapListResponse {
  fieldMaps: FieldMap[];
}

const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/api/field-maps`;

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

// Get list of field maps
export const listFieldMaps = async (): Promise<FieldMapListResponse> => {
  try {
    const response = await authenticatedRequest(API_ENDPOINT);
    const data: FieldMapListResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error listing field maps:', error);
    throw error;
  }
};

// Get a single field map
export const getFieldMap = async (fieldMapId: string): Promise<FieldMap> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fieldMapId}`);
    const data: FieldMap = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting field map:', error);
    throw error;
  }
};

// Create a new field map
export const createFieldMap = async (fieldMap: Omit<FieldMap, 'fieldMapId' | 'createdAt' | 'updatedAt'>): Promise<FieldMap> => {
  try {
    const response = await authenticatedRequest(API_ENDPOINT, {
      method: 'POST',
      body: JSON.stringify(fieldMap)
    });
    const data: FieldMap = await response.json();
    return data;
  } catch (error) {
    console.error('Error creating field map:', error);
    throw error;
  }
};

// Update a field map
export const updateFieldMap = async (fieldMapId: string, updates: Partial<FieldMap>): Promise<FieldMap> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fieldMapId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    });
    const data: FieldMap = await response.json();
    return data;
  } catch (error) {
    console.error('Error updating field map:', error);
    throw error;
  }
};

// Delete a field map
export const deleteFieldMap = async (fieldMapId: string): Promise<void> => {
  try {
    await authenticatedRequest(`${API_ENDPOINT}/${fieldMapId}`, {
      method: 'DELETE'
    });
  } catch (error) {
    console.error('Error deleting field map:', error);
    throw error;
  }
};

export default {
  listFieldMaps,
  getFieldMap,
  createFieldMap,
  updateFieldMap,
  deleteFieldMap
}; 