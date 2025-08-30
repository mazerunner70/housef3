/**
 * Structured logging utility for frontend services
 * 
 * Provides consistent logging across all service modules with:
 * - Structured log entries with timestamps and service context
 * - Different log levels (info, warn, error)
 * - Service-specific prefixes for easy filtering
 * - Beautiful console output with colors and formatting
 * - Production-ready extensibility
 */

import { createConsola } from 'consola';
import { getServiceLogLevel, getRuntimeLogLevel, getLoggerConfig, type LogLevel } from './loggerConfig';

/**
 * Convert string log level to numeric for Consola
 */
const logLevelToNumeric = (level: LogLevel): number => {
    switch (level) {
        case 'silent': return 0;
        case 'error': return 1;
        case 'warn': return 2;
        case 'info': return 3;
        case 'debug': return 4;
        case 'trace': return 5;
        default: return 3; // default to info
    }
};

// Base log data - only what you explicitly want to log
export interface LogData {
    // Performance fields - typed as numbers for API logger compatibility
    durationMs?: number;
    memoryUsedMB?: number;
    memoryTotalMB?: number;

    // Common fields
    operation?: string;
    error?: string;

    // Flexible data - constrained to serializable types
    [key: string]: string | number | boolean | string[] | null | undefined;
}

// Performance collector specific return type - guarantees durationMs is present
export interface PerformanceData extends LogData {
    durationMs: number;  // Required for performance data
    operation: string;   // Required for performance data
}

// Context collectors - automatically gather metadata
export interface LogContext {
    timestamp: string;
    sessionId?: string;
    userId?: string;
    requestId?: string;
    userAgent?: string;
    url?: string;
    component?: string;
}

// Context collector functions
export const createContextCollector = () => {
    const getBaseContext = (): LogContext => ({
        timestamp: new Date().toISOString(),
        sessionId: getSessionId(),
        userId: getCurrentUserId(),
        requestId: generateRequestId(),
        userAgent: navigator.userAgent,
        url: window.location.href,
    });

    const getApiContext = (endpoint?: string, method?: string) => ({
        ...getBaseContext(),
        endpoint,
        method,
        component: 'api-client'
    });

    const getComponentContext = (componentName: string) => ({
        ...getBaseContext(),
        component: componentName
    });

    return {
        base: getBaseContext,
        api: getApiContext,
        component: getComponentContext
    };
};

// Helper functions for context data
const getSessionId = (): string | undefined => {
    return sessionStorage.getItem('sessionId') || undefined;
};

const getCurrentUserId = (): string | undefined => {
    // Get from your auth context, localStorage, etc.
    return localStorage.getItem('userId') || undefined;
};

const generateRequestId = (): string => {
    // Use crypto.getRandomValues for cryptographically secure random generation
    const array = new Uint8Array(6); // 6 bytes = 48 bits of entropy
    crypto.getRandomValues(array);

    // Convert to base36 string for readability
    const randomPart = Array.from(array)
        .map(byte => byte.toString(36))
        .join('')
        .substring(0, 9);

    return `req_${Date.now()}_${randomPart}`;
};

export interface Logger {
    debug: (message: string, data?: LogData) => void;
    info: (message: string, data?: LogData) => void;
    warn: (message: string, data?: LogData) => void;
    error: (message: string, data?: LogData) => void;
}

/**
 * Creates a logger instance for a specific service using Consola with automatic context collection
 * @param serviceName - Name of the service (e.g., 'UserPreferencesService', 'AccountService')
 * @returns Logger instance with info, warn, and error methods that automatically collect context
 */
export const createLogger = (serviceName: string): Logger => {
    // Get log level for this service (runtime override takes precedence)
    const runtimeLevel = getRuntimeLogLevel(serviceName);
    const configLevel = getServiceLogLevel(serviceName);
    const logLevel = runtimeLevel || configLevel;

    const config = getLoggerConfig();

    // Convert string log level to numeric for Consola
    const numericLevel = logLevelToNumeric(logLevel);

    // Create a consola instance with service tag and level
    const consola = createConsola({
        level: numericLevel,
        defaults: {
            tag: serviceName
        },
        // Disable console output in production if configured
        reporters: config.enableConsoleOutput ? undefined : []
    });

    // Create context collector
    const contextCollector = createContextCollector();

    return {
        debug: (message: string, data?: LogData) => {
            const context = contextCollector.component(serviceName);
            consola.debug(message, { ...context, ...data });
        },
        info: (message: string, data?: LogData) => {
            const context = contextCollector.component(serviceName);
            consola.info(message, { ...context, ...data });
        },
        warn: (message: string, data?: LogData) => {
            const context = contextCollector.component(serviceName);
            consola.warn(message, { ...context, ...data });
        },
        error: (message: string, data?: LogData) => {
            const context = contextCollector.component(serviceName);
            consola.error(message, { ...context, ...data });
        }
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
                durationMs: Math.round(duration * 100) / 100,
                operation: operationName
            });

            return result;
        } catch (error) {
            const duration = performance.now() - startTime;
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';

            logger.error(`${operationName} failed`, {
                durationMs: Math.round(duration * 100) / 100,
                operation: operationName,
                error: errorMessage
            });

            throw error;
        }
    };
};

// ============ EFFICIENT DATA COLLECTION PATTERNS ============

/**
 * High-level API operation wrapper - handles all logging automatically
 * Eliminates 90% of manual logging boilerplate
 */
export const withApiLogging = <T>(
    serviceName: string,
    endpoint: string,
    method: string,
    operation: () => Promise<T>,
    options?: {
        operationName?: string;
        successData?: (result: T) => LogData;
        skipRequestLog?: boolean;
    }
) => {
    const apiLogger = createApiLogger(serviceName);
    const perf = createPerformanceCollector();
    const operationName = options?.operationName || `${method} ${endpoint}`;

    return async (): Promise<T> => {
        perf.start(operationName);

        if (!options?.skipRequestLog) {
            apiLogger.request(endpoint, method);
        }

        try {
            const result = await operation();
            const perfData = perf.end(operationName);

            const successData = options?.successData ? options.successData(result) : {};
            apiLogger.response(endpoint, method, 200, perfData.durationMs, {
                ...successData,
                ...perfData
            });

            return result;

        } catch (error) {
            const perfData = perf.end(operationName);
            apiLogger.error(endpoint, method, error, perfData.durationMs, perfData);
            throw error;
        }
    };
};

/**
 * Service operation wrapper - handles basic logging with minimal setup
 */
export const withServiceLogging = <T extends any[], R>(
    serviceName: string,
    operationName: string,
    fn: (...args: T) => Promise<R>,
    options?: {
        logArgs?: (args: T) => LogData;
        logResult?: (result: R) => LogData;
    }
) => {
    const logger = createLogger(serviceName);
    const perf = createPerformanceCollector();

    return async (...args: T): Promise<R> => {
        const opId = `${operationName}:${Date.now()}`;

        // Log operation start
        const argData = options?.logArgs ? options.logArgs(args) : {};
        logger.debug(`Starting ${operationName}`, { operation: operationName, ...argData });

        perf.start(opId);

        try {
            const result = await fn(...args);
            const perfData = perf.end(opId);

            const resultData = options?.logResult ? options.logResult(result) : {};
            logger.info(`${operationName} completed`, {
                ...resultData,
                ...perfData
            });

            return result;

        } catch (error) {
            const perfData = perf.end(opId);
            const errorData = collectErrorData(error);

            logger.error(`${operationName} failed`, {
                ...errorData,
                ...perfData
            });

            throw error;
        }
    };
};

/**
 * API Logger - automatically collects API-specific context
 */
export const createApiLogger = (serviceName: string) => {
    // Get log level for this service
    const runtimeLevel = getRuntimeLogLevel(serviceName);
    const configLevel = getServiceLogLevel(serviceName);
    const logLevel = runtimeLevel || configLevel;

    const config = getLoggerConfig();

    // Convert string log level to numeric for Consola
    const numericLevel = logLevelToNumeric(logLevel);

    const consola = createConsola({
        level: numericLevel,
        defaults: { tag: `${serviceName}:API` },
        reporters: config.enableConsoleOutput ? undefined : []
    });
    const contextCollector = createContextCollector();

    return {
        request: (endpoint: string, method: string, data?: LogData) => {
            const context = contextCollector.api(endpoint, method);
            consola.info(`API Request: ${method} ${endpoint}`, { ...context, ...data });
        },
        response: (endpoint: string, method: string, statusCode: number, duration: number, data?: LogData) => {
            const context = contextCollector.api(endpoint, method);
            consola.info(`API Response: ${method} ${endpoint}`, {
                ...context,
                statusCode,
                duration: `${duration.toFixed(2)}ms`,
                ...data
            });
        },
        error: (endpoint: string, method: string, error: unknown, duration: number, data?: LogData) => {
            const context = contextCollector.api(endpoint, method);
            const errorData = collectErrorData(error); // Safe error extraction
            consola.error(`API Error: ${method} ${endpoint}`, {
                ...context,
                ...errorData,
                duration: `${duration.toFixed(2)}ms`,
                ...data
            });
        }
    };
};

/**
 * Error collector - automatically extracts error details
 */
export const collectErrorData = (error: unknown): LogData => {
    if (error instanceof Error) {
        const errorData: LogData = {
            error: error.message,
            stack: error.stack,
            name: error.name
        };

        // Only add cause if it exists (ES2022+ feature)
        if ('cause' in error && error.cause !== undefined) {
            errorData.cause = String(error.cause);
        }

        return errorData;
    }

    return {
        error: String(error),
        type: typeof error
    };
};

/**
 * Performance collector - tracks timing and resource usage
 */
export const createPerformanceCollector = () => {
    const measurements = new Map<string, number>();

    return {
        start: (operationId: string) => {
            measurements.set(operationId, performance.now());
        },

        end: (operationId: string): PerformanceData => {
            const startTime = measurements.get(operationId);
            if (!startTime) {
                return {
                    error: `No start time found for operation: ${operationId}`,
                    operation: operationId,
                    durationMs: 0  // Always provide durationMs for consistent API
                };
            }

            const duration = performance.now() - startTime;
            measurements.delete(operationId);

            const result: PerformanceData = {
                operation: operationId,
                durationMs: Math.round(duration * 100) / 100  // Raw number, rounded to 2 decimals
            };

            // Add memory info if available (Chrome/Edge)
            if ((performance as any).memory) {
                const memory = (performance as any).memory;
                result.memoryUsedMB = Math.round(memory.usedJSHeapSize / 1024 / 1024);
                result.memoryTotalMB = Math.round(memory.totalJSHeapSize / 1024 / 1024);
            }

            return result;
        }
    };
};

/**
 * Batch logger - collects multiple log entries and flushes efficiently
 */
export const createBatchLogger = (serviceName: string, flushInterval: number = 1000) => {
    const consola = createConsola({
        defaults: { tag: `${serviceName}:Batch` }
    });

    const batch: Array<{ level: 'info' | 'warn' | 'error', message: string, data: any }> = [];

    const flush = () => {
        if (batch.length === 0) return;

        consola.info(`Batch flush: ${batch.length} entries`, {
            entries: batch.map(entry => ({
                level: entry.level,
                message: entry.message,
                timestamp: entry.data.timestamp
            }))
        });

        batch.length = 0; // Clear batch
    };

    // Auto-flush interval
    setInterval(flush, flushInterval);

    return {
        add: (level: 'info' | 'warn' | 'error', message: string, data?: LogData) => {
            const context = createContextCollector().component(serviceName);
            batch.push({ level, message, data: { ...context, ...data } });
        },
        flush,
        size: () => batch.length
    };
};

// ============ RUNTIME LOG LEVEL CONTROL ============

/**
 * Runtime debugging utilities - available in browser console
 */
export const LoggerDebug = {
    /**
     * Set log level for a specific service at runtime
     * Usage: LoggerDebug.setLevel('TransactionService', 'debug')
     */
    setLevel: (serviceName: string, level: 'silent' | 'error' | 'warn' | 'info' | 'debug' | 'trace') => {
        sessionStorage.setItem(`logLevel:${serviceName}`, level);
        console.log(`🔧 Log level for ${serviceName} set to: ${level}`);
        console.log('📝 Refresh the page or trigger new operations to see the effect');
    },

    /**
     * Get current log level for a service
     */
    getLevel: (serviceName: string) => {
        const runtime = getRuntimeLogLevel(serviceName);
        const config = getServiceLogLevel(serviceName);
        console.log(`📊 ${serviceName} log levels:`, {
            runtime: runtime || 'none',
            config,
            effective: runtime || config
        });
        return runtime || config;
    },

    /**
     * Clear runtime overrides for a service
     */
    clearLevel: (serviceName: string) => {
        sessionStorage.removeItem(`logLevel:${serviceName}`);
        console.log(`🧹 Cleared runtime log level for ${serviceName}`);
    },

    /**
     * Show all current log levels
     */
    showAll: () => {
        const config = getLoggerConfig();
        console.log('📋 Current logging configuration:', {
            globalLevel: config.globalLevel,
            environment: import.meta.env.MODE,
            serviceOverrides: config.serviceOverrides,
            enableConsoleOutput: config.enableConsoleOutput,
            enableRemoteLogging: config.enableRemoteLogging
        });

        // Show runtime overrides
        const runtimeOverrides: Record<string, string> = {};
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            if (key?.startsWith('logLevel:')) {
                const serviceName = key.replace('logLevel:', '');
                runtimeOverrides[serviceName] = sessionStorage.getItem(key) || '';
            }
        }

        if (Object.keys(runtimeOverrides).length > 0) {
            console.log('🔧 Runtime overrides:', runtimeOverrides);
        }
    },

    /**
     * Enable debug logging for all services (temporary)
     */
    enableDebugAll: () => {
        const services = ['TransactionService', 'AccountService', 'AuthService', 'CategoryService', 'AnalyticsService'];
        services.forEach(service => {
            sessionStorage.setItem(`logLevel:${service}`, 'debug');
        });
        console.log('🐛 Debug logging enabled for all services');
    },

    /**
     * Reset all logging to config defaults
     */
    reset: () => {
        // Clear all runtime overrides
        for (let i = sessionStorage.length - 1; i >= 0; i--) {
            const key = sessionStorage.key(i);
            if (key?.startsWith('logLevel:')) {
                sessionStorage.removeItem(key);
            }
        }
        console.log('🔄 All log levels reset to configuration defaults');
    }
};

// Make LoggerDebug available globally for browser console access
if (typeof window !== 'undefined') {
    (window as any).LoggerDebug = LoggerDebug;
}
