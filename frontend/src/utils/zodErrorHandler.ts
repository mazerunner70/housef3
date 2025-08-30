import { ZodError } from 'zod';

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
}

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

        // Log detailed error information for debugging
        console.error(`${context} validation failed:`, {
            issues: zodError.issues || [],
            message: zodError.message,
            ...(includeDebugInfo && rawData && {
                rawDataSample: JSON.stringify(rawData).substring(0, 1000) + (JSON.stringify(rawData).length > 1000 ? '...' : ''),
                rawDataType: typeof rawData,
                rawDataKeys: typeof rawData === 'object' && rawData !== null ? Object.keys(rawData) : 'N/A'
            }),
            fullError: zodError
        });

        // Throw user-friendly error
        const defaultMessage = `${context.charAt(0).toUpperCase() + context.slice(1)} format is invalid. Please refresh the page or contact support if the issue persists.`;
        throw new Error(userMessage || defaultMessage);
    }

    // If it's not a Zod error, re-throw the original error
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
 * Convenience function for API response validation
 * Combines API call + validation + error handling in one step
 */
export const validateApiResponse = async <T>(
    apiCall: () => Promise<any>,
    validator: (data: any) => T,
    context: string,
    userMessage?: string
): Promise<T> => {
    let rawData: any = null;

    try {
        rawData = await apiCall();
        return validateWithErrorHandling(
            () => validator(rawData),
            {
                context,
                rawData,
                userMessage
            }
        );
    } catch (error) {
        // If it's already a handled Zod error, re-throw it
        if (error instanceof Error && error.message?.includes('format is invalid')) {
            throw error;
        }

        // Handle other API errors
        console.error(`Error in ${context}:`, error);
        throw error;
    }
};
