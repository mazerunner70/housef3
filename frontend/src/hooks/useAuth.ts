import { useState, useEffect } from 'react';
import { getCurrentUser, isAuthenticated, refreshToken } from '@/services/AuthService';

/**
 * Custom hook for managing authentication state
 * Handles token validation, refresh, and authentication status
 */
export const useAuth = () => {
    const [authenticated, setAuthenticated] = useState<boolean>(false);
    const [loading, setLoading] = useState<boolean>(true);

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
                            await refreshToken(currentUser.refreshToken);
                            setAuthenticated(true);
                            return;
                        } catch (error) {
                            console.error('Failed to refresh token:', error);
                            setAuthenticated(false);
                            return;
                        }
                    }

                    // Token still valid
                    if (isAuthenticated()) {
                        setAuthenticated(true);
                        return;
                    }
                }

                // No user or invalid token
                setAuthenticated(false);
            } catch (error) {
                console.error('Authentication check error:', error);
                setAuthenticated(false);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    const handleLogin = () => {
        setAuthenticated(true);
    };

    const handleSignOut = () => {
        setAuthenticated(false);
    };

    return {
        authenticated,
        loading,
        handleLogin,
        handleSignOut
    };
};

