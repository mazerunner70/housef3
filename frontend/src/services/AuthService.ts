import { 
  CognitoIdentityProviderClient, 
  InitiateAuthCommand,
  InitiateAuthCommandInput,
  GlobalSignOutCommand
} from "@aws-sdk/client-cognito-identity-provider";

// Get these values from your Terraform outputs
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || '';
const USER_POOL_ID = import.meta.env.VITE_COGNITO_USER_POOL_ID || '';
const REGION = import.meta.env.VITE_AWS_REGION || 'eu-west-2';

// Create a Cognito client
const cognitoClient = new CognitoIdentityProviderClient({ 
  region: REGION
});

export interface AuthUser {
  username: string;
  email?: string;
  token: string;
  refreshToken: string;
  tokenExpiry: number;
}

// Current authenticated user state
let currentUser: AuthUser | null = null;

// Check local storage for existing token on initialization
const initAuth = (): void => {
  const storedUser = localStorage.getItem('authUser');
  if (storedUser) {
    currentUser = JSON.parse(storedUser);
  }
};

// Initialize on module load
initAuth();

// Store the auth user in local storage
export const storeUser = (user: AuthUser) => {
  localStorage.setItem('authUser', JSON.stringify(user));
  // Update the current user in memory
  currentUser = user;
};

// Get the current user from local storage
export const getCurrentUser = (): AuthUser | null => {
  if (!currentUser) {
    // Try to get from localStorage if not in memory
    const userStr = localStorage.getItem('authUser');
    if (userStr) {
      try {
        currentUser = JSON.parse(userStr);
      } catch (error) {
        console.error('Error parsing auth user:', error);
        return null;
      }
    }
  }
  return currentUser;
};

// Check if the user is authenticated
export const isAuthenticated = (): boolean => {
  const user = getCurrentUser();
  if (!user) return false;
  
  // Check if token has expired
  const now = Date.now();
  if (now > user.tokenExpiry) {
    // Try to refresh the token
    refreshToken(user.refreshToken).catch(() => {
      // If refresh fails, clear local storage
      localStorage.removeItem('authUser');
      currentUser = null;
    });
    return false;
  }
  
  return !!user.token;
};

// Sign out the user
export const signOut = async (): Promise<void> => {
  try {
    if (currentUser?.token) {
      const command = new GlobalSignOutCommand({
        AccessToken: currentUser.token
      });
      await cognitoClient.send(command);
    }
  } catch (error) {
    console.error('Error during sign out:', error);
  } finally {
    // Clear local storage and user state
    localStorage.removeItem('authUser');
    currentUser = null;
  }
};

// Sign in with username and password
export const signIn = async (username: string, password: string): Promise<AuthUser> => {
  const client = new CognitoIdentityProviderClient({ region: REGION });
  
  const input: InitiateAuthCommandInput = {
    AuthFlow: 'USER_PASSWORD_AUTH',
    ClientId: CLIENT_ID,
    AuthParameters: {
      USERNAME: username,
      PASSWORD: password,
    },
  };
  
  try {
    const command = new InitiateAuthCommand(input);
    const response = await client.send(command);
    
    if (!response.AuthenticationResult) {
      throw new Error('Authentication failed');
    }
    
    const { IdToken, RefreshToken, ExpiresIn, AccessToken } = response.AuthenticationResult;
    
    if (!IdToken || !RefreshToken || !AccessToken) {
      throw new Error('Missing token information');
    }
    
    // Parse the token to get user information
    const payload = parseJwt(IdToken);
    
    // Create auth user object
    const user: AuthUser = {
      username: payload['cognito:username'] || username,
      email: payload.email,
      token: IdToken,
      refreshToken: RefreshToken,
      tokenExpiry: Date.now() + (ExpiresIn || 3600) * 1000 // Convert to milliseconds
    };
    
    // Store user in local storage and update current user
    storeUser(user);
    
    return user;
  } catch (error) {
    console.error('Error signing in:', error);
    throw error;
  }
};

// Refresh the token
export const refreshToken = async (refreshToken: string): Promise<AuthUser> => {
  const client = new CognitoIdentityProviderClient({ region: REGION });
  
  const input: InitiateAuthCommandInput = {
    AuthFlow: 'REFRESH_TOKEN_AUTH',
    ClientId: CLIENT_ID,
    AuthParameters: {
      REFRESH_TOKEN: refreshToken,
    },
  };
  
  try {
    const command = new InitiateAuthCommand(input);
    const response = await client.send(command);
    
    if (!response.AuthenticationResult) {
      throw new Error('Token refresh failed');
    }
    
    const { IdToken, ExpiresIn, AccessToken } = response.AuthenticationResult;
    
    if (!IdToken || !AccessToken) {
      throw new Error('Missing token information');
    }
    
    // Get the current user
    const currentUser = getCurrentUser();
    if (!currentUser) {
      throw new Error('No user to refresh');
    }
    
    // Parse the token to get user information
    const payload = parseJwt(IdToken);
    
    // Update auth user object
    const user: AuthUser = {
      ...currentUser,
      username: payload['cognito:username'] || currentUser.username,
      email: payload.email || currentUser.email,
      token: IdToken,
      tokenExpiry: Date.now() + (ExpiresIn || 3600) * 1000 // Convert to milliseconds
    };
    
    // Store updated user in local storage and update current user
    storeUser(user);
    
    return user;
  } catch (error) {
    console.error('Error refreshing token:', error);
    throw error;
  }
};

// Helper function to parse JWT
function parseJwt(token: string) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Error parsing JWT token:', e);
    return {};
  }
}

export default {
  signIn,
  signOut,
  getCurrentUser,
  isAuthenticated
}; 