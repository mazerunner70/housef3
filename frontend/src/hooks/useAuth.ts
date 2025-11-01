import { useState, useEffect } from 'react';
import {
    getCurrentUser,
    isAuthenticated,
    refreshToken,
    signIn,
    signOut,
    AuthUser
} from '@/services/AuthService';

/**
 * Custom hook for managing authentication state
 * Handles token validation, refresh, login, logout, and authentication status
 */
export const useAuth = () => {
    const [authenticated, setAuthenticated] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(true);
    const [user, setUser] = useState<AuthUser | null>(null);
    const [loginLoading, setLoginLoading] = useState<boolean>(false);
    const [loginError, setLoginError] = useState<string | null>(null);

    // Check authentication status on hook mount
    useEffect(() => {
        const checkAuth = async () => {
            setLoading(true);

            try {
                // Get current user
                const currentUser = getCurrentUser();

                // Check if user is authenticated
                if (currentUser) {
                    // If token expired, try to refresh
                    if (!isAuthenticated() && currentUser.refreshToken) {
                        try {
                            const refreshedUser = await refreshToken(currentUser.refreshToken);
                            setAuthenticated(true);
                            setUser(refreshedUser);
                            return;
                        } catch (error) {
                            console.error('Failed to refresh token:', error);
                            setAuthenticated(false);
                            setUser(null);
                            return;
                        }
                    }

                    // Token still valid
                    if (isAuthenticated()) {
                        setAuthenticated(true);
                        setUser(currentUser);
                        return;
                    }
                }

                // No user or invalid token
                setAuthenticated(false);
                setUser(null);
            } catch (error) {
                console.error('Authentication check error:', error);
                setAuthenticated(false);
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    /**
     * Handles user login with credentials
     * @param username - User's username
     * @param password - User's password
     * @returns Promise that resolves with the authenticated user or rejects with an error
     */
    const handleLogin = async (username: string, password: string): Promise<AuthUser> => {
        setLoginLoading(true);
        setLoginError(null);

        try {
            // Call the authentication service
            const authenticatedUser = await signIn(username, password);

            // Update state on successful login
            setAuthenticated(true);
            setUser(authenticatedUser);

            return authenticatedUser;
        } catch (error) {
            // Handle authentication errors
            const errorMessage = error instanceof Error
                ? error.message
                : 'Authentication failed. Please check your credentials and try again.';

            setLoginError(errorMessage);
            setAuthenticated(false);
            setUser(null);

            throw error;
        } finally {
            setLoginLoading(false);
        }
    };

    /**
     * Handles user sign out
     * Clears session, tokens, and resets authentication state
     */
    const handleSignOut = async (): Promise<void> => {
        try {
            // Call the sign out service to clear tokens on backend
            await signOut();
        } catch (error) {
            console.error('Error during sign out:', error);
            // Continue with local cleanup even if backend call fails
        } finally {
            // Always clear local state
            setAuthenticated(false);
            setUser(null);
            setLoginError(null);
        }
    };

    return {
        authenticated,
        loading,
        user,
        loginLoading,
        loginError,
        handleLogin,
        handleSignOut
    };
};

