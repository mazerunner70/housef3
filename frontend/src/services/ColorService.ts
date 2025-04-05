import { getCurrentUser, refreshToken, isAuthenticated } from './AuthService';

export interface Color {
  name: string;
  hexCode: string;
  category: string;
}

export interface ColorResponse {
  colors: Color[];
  user: {
    id: string;
    email: string;
    authTime: number;
    scope: string;
  };
  metadata: {
    totalColors: number;
    timestamp: string;
    version: string;
  };
}

// Get CloudFront domain from environment variables
const CLOUDFRONT_DOMAIN = import.meta.env.VITE_CLOUDFRONT_DOMAIN || '';

export const getColors = async (): Promise<ColorResponse> => {
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
    
    const response = await fetch(`https://${CLOUDFRONT_DOMAIN}/colors`, {
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
        const retryResponse = await fetch(`https://${CLOUDFRONT_DOMAIN}/colors`, {
          headers: {
            'Authorization': `Bearer ${refreshedUser.token}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (!retryResponse.ok) {
          throw new Error(`Failed to fetch colors after token refresh: ${retryResponse.status} ${retryResponse.statusText}`);
        }
        
        const data: ColorResponse = await retryResponse.json();
        return data;
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        throw new Error('Session expired. Please log in again.');
      }
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch colors: ${response.status} ${response.statusText}`);
    }
    
    const data: ColorResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching colors:', error);
    throw error;
  }
}; 