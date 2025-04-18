import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';

// Get API endpoint from environment variables
const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/api/colors`;

export interface Color {
  id?: string;
  name: string;
  hex: string;
  rgb?: string;
  hsl?: string;
  category?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface ColorListResponse {
  colors: Color[];
  metadata: {
    totalColors: number;
  };
  user: {
    id: string;
    email: string;
  };
}

// List colors with pagination
export const listColors = async (): Promise<ColorListResponse> => {
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
    
    const response = await fetch(API_ENDPOINT, {
      headers: {
        'Authorization': `Bearer ${user.token}`,
        'Content-Type': 'application/json'
      }
    });
    
    // Handle 401 error specifically - try to refresh token
    if (response.status === 401) {
      try {
        const refreshedUser = await refreshToken(user.refreshToken);
        
        // Retry the request with the new token
        const retryResponse = await fetch(API_ENDPOINT, {
          headers: {
            'Authorization': `Bearer ${refreshedUser.token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (!retryResponse.ok) {
          throw new Error(`Failed to fetch colors after token refresh: ${retryResponse.status} ${retryResponse.statusText}`);
        }
        
        const data: ColorListResponse = await retryResponse.json();
        return data;
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        throw new Error('Session expired. Please log in again.');
      }
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch colors: ${response.status} ${response.statusText}`);
    }
    
    const data: ColorListResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching colors:', error);
    throw error;
  }
}; 