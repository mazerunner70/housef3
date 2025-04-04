import { 
  CognitoIdentityProviderClient, 
  InitiateAuthCommand,
  InitiateAuthCommandInput,
  InitiateAuthCommandOutput,
  SignUpCommand,
  SignUpCommandInput,
  ConfirmSignUpCommand,
  ConfirmSignUpCommandInput,
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
  email: string;
  token: string;
  isAuthenticated: boolean;
}

// Store the current user information
let currentUser: AuthUser | null = null;

// Check local storage for existing token on initialization
const initAuth = (): void => {
  const storedToken = localStorage.getItem('userToken');
  const storedUsername = localStorage.getItem('username');
  const storedEmail = localStorage.getItem('userEmail');
  
  if (storedToken && storedUsername) {
    currentUser = {
      username: storedUsername,
      email: storedEmail || '',
      token: storedToken,
      isAuthenticated: true
    };
  }
};

// Initialize on module load
initAuth();

// Sign in function
export const signIn = async (username: string, password: string): Promise<AuthUser> => {
  try {
    const params: InitiateAuthCommandInput = {
      AuthFlow: 'USER_PASSWORD_AUTH',
      ClientId: CLIENT_ID,
      AuthParameters: {
        USERNAME: username,
        PASSWORD: password
      }
    };

    const command = new InitiateAuthCommand(params);
    const response: InitiateAuthCommandOutput = await cognitoClient.send(command);
    
    if (!response.AuthenticationResult?.IdToken) {
      throw new Error('No token received');
    }

    const token = response.AuthenticationResult.IdToken;
    
    // Store token and user info
    localStorage.setItem('userToken', token);
    localStorage.setItem('username', username);
    localStorage.setItem('userEmail', username); // In Cognito, often username is email
    
    currentUser = {
      username,
      email: username,
      token,
      isAuthenticated: true
    };
    
    return currentUser;
  } catch (error) {
    console.error('Error signing in:', error);
    throw error;
  }
};

// Sign out function
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
    localStorage.removeItem('userToken');
    localStorage.removeItem('username');
    localStorage.removeItem('userEmail');
    currentUser = null;
  }
};

// Get current user
export const getCurrentUser = (): AuthUser | null => {
  return currentUser;
};

// Check if user is authenticated
export const isAuthenticated = (): boolean => {
  return currentUser !== null && currentUser.isAuthenticated;
};

export default {
  signIn,
  signOut,
  getCurrentUser,
  isAuthenticated
}; 