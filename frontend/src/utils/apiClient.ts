import { getCurrentUser, refreshToken, isAuthenticated } from '../services/AuthService';
import { apiEndpoint } from './env';

/**
 * Configuration options for API requests
 */
export interface ApiRequestOptions extends RequestInit {
    /** Skip automatic JSON content-type header */
    skipJsonContentType?: boolean;
    /** Custom headers to merge with default headers */
    headers?: HeadersInit;
}

/**
 * Centralized API client with authentication handling
 * 
 * This utility handles:
 * - Automatic authentication token injection
 * - Token refresh on 401 errors
 * - Consistent error handling
 * - Standard headers setup
 */
export class ApiClient {
    /**
     * Resolves a relative API path to a full API endpoint
     * All paths are treated as API endpoints and get the /api prefix automatically
     */
    private static resolveUrl(path: string): string {
        // Ensure path starts with /
        const normalizedPath = path.startsWith('/') ? path : `/${path}`;
        return `${apiEndpoint}${normalizedPath}`;
    }

    /**
     * Makes an authenticated API request with automatic token management
     * 
     * @param path - The API endpoint path (automatically gets /api prefix)
     * @param options - Request options (method, body, headers, etc.)
     * @returns Promise<Response> - The fetch response
     * @throws Error if authentication fails or request fails after retry
     */
    static async request(path: string, options: ApiRequestOptions = {}): Promise<Response> {
        const url = this.resolveUrl(path);
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
            const defaultHeaders: HeadersInit = {
                'Authorization': user.token,
            };

            // Add JSON content type unless explicitly skipped
            if (!options.skipJsonContentType) {
                (defaultHeaders as Record<string, string>)['Content-Type'] = 'application/json';
            }

            // Merge with provided headers
            const headers = {
                ...defaultHeaders,
                ...options.headers
            };

            const requestOptions: RequestInit = {
                ...options,
                headers
            };

            const response = await fetch(url, requestOptions);

            // Handle 401 error specifically - try to refresh token
            if (response.status === 401) {
                try {
                    const refreshedUser = await refreshToken(user.refreshToken);

                    // Update headers with new token
                    const retryHeaders: HeadersInit = {
                        'Authorization': refreshedUser.token,
                    };

                    if (!options.skipJsonContentType) {
                        (retryHeaders as Record<string, string>)['Content-Type'] = 'application/json';
                    }

                    // Merge with provided headers for retry
                    const finalRetryHeaders = {
                        ...retryHeaders,
                        ...options.headers
                    };

                    // Retry the request with the new token
                    const retryResponse = await fetch(url, {
                        ...options,
                        headers: finalRetryHeaders
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
    }

    /**
     * Convenience method for GET requests
     */
    static async get(url: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<Response> {
        return this.request(url, { ...options, method: 'GET' });
    }

    /**
     * Convenience method for POST requests
     */
    static async post(url: string, body?: any, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<Response> {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: body ? JSON.stringify(body) : undefined
        });
    }

    /**
     * Convenience method for PUT requests
     */
    static async put(url: string, body?: any, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<Response> {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: body ? JSON.stringify(body) : undefined
        });
    }

    /**
 * Convenience method for DELETE requests
 */
    static async delete(url: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<Response> {
        return this.request(url, { ...options, method: 'DELETE' });
    }

    // JSON-specific wrapper methods for automatic response parsing

    /**
     * Makes a GET request and automatically parses JSON response
     */
    static async getJson<T = any>(url: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<T> {
        const response = await this.get(url, options);
        return response.json();
    }

    /**
     * Makes a POST request and automatically parses JSON response
     */
    static async postJson<T = any>(url: string, body?: any, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<T> {
        const response = await this.post(url, body, options);
        return response.json();
    }

    /**
     * Makes a PUT request and automatically parses JSON response
     */
    static async putJson<T = any>(url: string, body?: any, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<T> {
        const response = await this.put(url, body, options);
        return response.json();
    }

    /**
     * Makes a DELETE request and automatically parses JSON response (if any)
     * Returns void for DELETE requests that don't return content
     */
    static async deleteJson<T = any>(url: string, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<T | void> {
        const response = await this.delete(url, options);

        // Check if response has content to parse
        const contentLength = response.headers.get('content-length');
        const contentType = response.headers.get('content-type');

        if (contentLength === '0' || !contentType?.includes('application/json')) {
            return;
        }

        try {
            return await response.json();
        } catch {
            // If JSON parsing fails, return void (common for DELETE operations)
            return;
        }
    }

    /**
     * Generic JSON request method with automatic response parsing
     * Useful for custom HTTP methods or when you need full control
     */
    static async requestJson<T = any>(url: string, options: ApiRequestOptions = {}): Promise<T> {
        const response = await this.request(url, options);
        return response.json();
    }

    // Additional convenience methods for common patterns

    /**
     * Makes a PATCH request and automatically parses JSON response
     */
    static async patchJson<T = any>(url: string, body?: any, options: Omit<ApiRequestOptions, 'method' | 'body'> = {}): Promise<T> {
        const response = await this.request(url, {
            ...options,
            method: 'PATCH',
            body: body ? JSON.stringify(body) : undefined
        });
        return response.json();
    }

    /**
     * Upload file with multipart/form-data (skips JSON content-type)
     */
    static async uploadFile(url: string, formData: FormData, options: Omit<ApiRequestOptions, 'method' | 'body' | 'skipJsonContentType'> = {}): Promise<Response> {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: formData,
            skipJsonContentType: true // Don't set Content-Type for FormData
        });
    }

    /**
     * Upload file and parse JSON response
     */
    static async uploadFileJson<T = any>(url: string, formData: FormData, options: Omit<ApiRequestOptions, 'method' | 'body' | 'skipJsonContentType'> = {}): Promise<T> {
        const response = await this.uploadFile(url, formData, options);
        return response.json();
    }
}

/**
 * Legacy function for backward compatibility
 * @deprecated Use ApiClient.request() instead
 */
export const authenticatedRequest = ApiClient.request;

export default ApiClient;
