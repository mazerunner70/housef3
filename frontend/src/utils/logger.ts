/**
 * Structured logging utility for frontend services
 * 
 * Provides consistent logging across all service modules with:
 * - Structured log entries with timestamps and service context
 * - Different log levels (info, warn, error)
 * - Service-specific prefixes for easy filtering
 * - Future extensibility for production logging services
 */

export interface LogData {
    [key: string]: any;
}

export interface Logger {
    info: (message: string, data?: LogData) => void;
    warn: (message: string, data?: LogData) => void;
    error: (message: string, data?: LogData) => void;
}

/**
 * Creates a logger instance for a specific service
 * @param serviceName - Name of the service (e.g., 'UserPreferencesService', 'AccountService')
 * @returns Logger instance with info, warn, and error methods
 */
export const createLogger = (serviceName: string): Logger => {
    const log = (level: 'info' | 'warn' | 'error', message: string, data?: LogData) => {
        const timestamp = new Date().toISOString();
        const prefix = `[${serviceName}]`;

        if (level === 'error') {
            console.error(`${prefix} ${message}`, data ? { timestamp, ...data } : { timestamp });
        } else if (level === 'warn') {
            console.warn(`${prefix} ${message}`, data ? { timestamp, ...data } : { timestamp });
        } else {
            console.log(`${prefix} ${message}`, data ? { timestamp, ...data } : { timestamp });
        }

        // In production, this could send to a logging service
        // if (getEnvironment() === 'production') {
        //     sendToLoggingService({ level, message, serviceName, timestamp, data });
        // }
    };

    return {
        info: (message: string, data?: LogData) => log('info', message, data),
        warn: (message: string, data?: LogData) => log('warn', message, data),
        error: (message: string, data?: LogData) => log('error', message, data)
    };
};

/**
 * Performance logging wrapper for service functions
 * Automatically logs execution time and success/failure status
 * 
 * @param fn - The async function to wrap
 * @param operationName - Name of the operation for logging
 * @param logger - Logger instance to use
 * @returns Wrapped function with performance logging
 */
export const withPerformanceLogging = <T extends any[], R>(
    fn: (...args: T) => Promise<R>,
    operationName: string,
    logger: Logger
) => {
    return async (...args: T): Promise<R> => {
        const startTime = performance.now();

        try {
            const result = await fn(...args);
            const duration = performance.now() - startTime;

            logger.info(`${operationName} completed successfully`, {
                duration: `${duration.toFixed(2)}ms`,
                operation: operationName
            });

            return result;
        } catch (error) {
            const duration = performance.now() - startTime;
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';

            logger.error(`${operationName} failed`, {
                duration: `${duration.toFixed(2)}ms`,
                operation: operationName,
                error: errorMessage
            });

            throw error;
        }
    };
};
