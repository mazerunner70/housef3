import { ZodError } from 'zod';
import { createLogger, collectErrorData } from './logger';

/**
 * Enhanced Zod Error Handler with Consola Logging
 * 
 * Features:
 * - Uses consola for structured, colorized logging
 * - Includes full stack traces for debugging
 * - Detailed validation error breakdown
 * - Raw data sampling for development debugging
 * - Consistent error context tracking
 * - Performance-aware logging (respects log levels)
 */

/**
 * Configuration for Zod error handling
 */
export interface ZodErrorHandlerConfig {
    /** Context description for the operation (e.g., "account data", "user profile") */
    context: string;
    /** The raw data that failed validation (for debugging) */
    rawData?: any;
    /** Whether to include detailed debugging info in development */
    includeDebugInfo?: boolean;
    /** Custom user-friendly error message */
    userMessage?: string;
    /** API metadata for better error tracking */
    apiMetadata?: {
        endpoint?: string;
        method?: string;
        service?: string;
    };
}

// Create a dedicated logger for Zod validation errors
const logger = createLogger('ZodErrorHandler');

/**
 * Standardized Zod error handler for consistent error reporting across services
 * 
 * @param error - The caught error (potentially a ZodError)
 * @param config - Configuration for error handling
 * @throws Error with user-friendly message
 */
export const handleZodValidationError = (error: any, config: ZodErrorHandlerConfig): never => {
    const {
        context,
        rawData,
        includeDebugInfo = process.env.NODE_ENV === 'development',
        userMessage
    } = config;

    // Check if this is a Zod validation error
    if (error?.name === 'ZodError' || error instanceof ZodError) {
        const zodError = error as ZodError;

        // Prepare structured error data for logging
        const errorLogData = {
            context,
            validationErrors: zodError.issues?.map(issue => ({
                path: issue.path.join('.'),
                code: issue.code,
                message: issue.message,
                expected: (issue as any).expected || 'N/A',
                received: (issue as any).received || 'N/A'
            })) || [],
            totalIssues: zodError.issues?.length || 0,
            zodMessage: zodError.message,
            ...collectErrorData(zodError), // Includes stack trace
            // Include API metadata if provided
            ...(config.apiMetadata && {
                apiEndpoint: config.apiMetadata.endpoint,
                apiMethod: config.apiMetadata.method,
                apiService: config.apiMetadata.service
            }),
            ...(includeDebugInfo && rawData && {
                rawDataSample: JSON.stringify(rawData).substring(0, 1000) + (JSON.stringify(rawData).length > 1000 ? '...' : ''),
                rawDataType: typeof rawData,
                rawDataKeys: typeof rawData === 'object' && rawData !== null ? Object.keys(rawData) : 'N/A',
                rawDataSize: rawData ? JSON.stringify(rawData).length : 0
            })
        };

        // Log with consola for better formatting and structure
        logger.error(`Zod validation failed for ${context}`, errorLogData);

        // Throw user-friendly error
        const defaultMessage = `${context.charAt(0).toUpperCase() + context.slice(1)} format is invalid. Please refresh the page or contact support if the issue persists.`;
        throw new Error(userMessage || defaultMessage);
    }

    // If it's not a Zod error, log it and re-throw
    logger.error(`Non-Zod error in ${context}`, {
        context,
        ...collectErrorData(error)
    });

    throw error;
};

/**
 * Wrapper function that handles Zod validation with automatic error handling
 * 
 * @param validationFn - Function that performs Zod validation
 * @param config - Configuration for error handling
 * @returns The validated data
 */
export const validateWithErrorHandling = <T>(
    validationFn: () => T,
    config: ZodErrorHandlerConfig
): T => {
    try {
        return validationFn();
    } catch (error) {
        return handleZodValidationError(error, config);
    }
};

/**
 * Async wrapper function that handles Zod validation with automatic error handling
 * 
 * @param validationFn - Async function that performs Zod validation
 * @param config - Configuration for error handling
 * @returns Promise of the validated data
 */
export const validateAsyncWithErrorHandling = async <T>(
    validationFn: () => Promise<T> | T,
    config: ZodErrorHandlerConfig
): Promise<T> => {
    try {
        return await validationFn();
    } catch (error) {
        return handleZodValidationError(error, config);
    }
};

/**
 * Enhanced API response validation with automatic metadata detection
 * Combines API call + validation + error handling in one step
 */
export const validateApiResponse = async <T>(
    apiCall: () => Promise<any>,
    validator: (data: any) => T,
    context: string,
    userMessage?: string,
    apiMetadata?: {
        endpoint?: string;
        method?: string;
        service?: string;
    }
): Promise<T> => {
    let rawData: any = null;

    try {
        rawData = await apiCall();
        return validateWithErrorHandling(
            () => validator(rawData),
            {
                context,
                rawData,
                userMessage,
                apiMetadata
            }
        );
    } catch (error) {
        // If it's already a handled Zod error, re-throw it
        if (error instanceof Error && error.message?.includes('format is invalid')) {
            throw error;
        }

        // Handle other API errors with structured logging
        logger.error(`API error in ${context}`, {
            context,
            apiEndpoint: apiMetadata?.endpoint,
            apiMethod: apiMetadata?.method,
            apiService: apiMetadata?.service,
            ...collectErrorData(error)
        });
        throw error;
    }
};

/**
 * Smart API response validation that automatically derives metadata from the API call
 * This version inspects the apiCall function to extract endpoint and method information
 */
export const validateApiResponseSmart = async <T>(
    apiCall: () => Promise<any>,
    validator: (data: any) => T,
    context: string,
    userMessage?: string,
    serviceName?: string
): Promise<T> => {
    // Try to derive metadata from the API call function
    const apiCallString = apiCall.toString();

    // Extract method and endpoint from common patterns
    let endpoint: string | undefined;
    let method: string | undefined;

    // Pattern: ApiClient.getJson('/some-endpoint')
    const getJsonMatch = apiCallString.match(/ApiClient\.getJson\(['"`]([^'"`]+)['"`]/);
    if (getJsonMatch) {
        endpoint = getJsonMatch[1];
        method = 'GET';
    }

    // Pattern: ApiClient.postJson('/some-endpoint')
    const postJsonMatch = apiCallString.match(/ApiClient\.postJson\(['"`]([^'"`]+)['"`]/);
    if (postJsonMatch) {
        endpoint = postJsonMatch[1];
        method = 'POST';
    }

    // Pattern: ApiClient.putJson('/some-endpoint')
    const putJsonMatch = apiCallString.match(/ApiClient\.putJson\(['"`]([^'"`]+)['"`]/);
    if (putJsonMatch) {
        endpoint = putJsonMatch[1];
        method = 'PUT';
    }

    // Pattern: ApiClient.deleteJson('/some-endpoint')
    const deleteJsonMatch = apiCallString.match(/ApiClient\.deleteJson\(['"`]([^'"`]+)['"`]/);
    if (deleteJsonMatch) {
        endpoint = deleteJsonMatch[1];
        method = 'DELETE';
    }

    const derivedMetadata = {
        endpoint,
        method,
        service: serviceName
    };

    return validateApiResponse(apiCall, validator, context, userMessage, derivedMetadata);
};
