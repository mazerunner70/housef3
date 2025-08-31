/**
 * Logger configuration for different environments and services
 */

export type LogLevel = 'silent' | 'error' | 'warn' | 'info' | 'debug' | 'trace';

export interface LoggerConfig {
    globalLevel: LogLevel;
    serviceOverrides: Record<string, LogLevel>;
    enableConsoleOutput: boolean;
    enableRemoteLogging: boolean;
    batchSize?: number;
    flushInterval?: number;
}

/**
 * Get environment-specific logger configuration - SIMPLIFIED for maximum logging
 */
export const getLoggerConfig = (): LoggerConfig => {
    // Always return maximum logging configuration regardless of environment
    return {
        globalLevel: 'debug', // Always debug level
        serviceOverrides: {}, // No service overrides - everything gets debug
        enableConsoleOutput: true, // Always enable console output
        enableRemoteLogging: false, // Disable remote logging for simplicity
        batchSize: 10,
        flushInterval: 5000
    };
};

/**
 * Get log level for a specific service
 */
export const getServiceLogLevel = (serviceName: string): LogLevel => {
    const config = getLoggerConfig();
    return config.serviceOverrides[serviceName] || config.globalLevel;
};

/**
 * Check if logging is enabled for a service at a specific level
 */
export const isLogLevelEnabled = (serviceName: string, level: LogLevel): boolean => {
    const serviceLevel = getServiceLogLevel(serviceName);
    const levels: LogLevel[] = ['silent', 'error', 'warn', 'info', 'debug', 'trace'];

    const serviceLevelIndex = levels.indexOf(serviceLevel);
    const requestedLevelIndex = levels.indexOf(level);

    return serviceLevelIndex >= requestedLevelIndex;
};

/**
 * Runtime log level control (for debugging)
 */
export const setServiceLogLevel = (serviceName: string, level: LogLevel): void => {
    const config = getLoggerConfig();
    config.serviceOverrides[serviceName] = level;

    // Store in sessionStorage for persistence during session
    sessionStorage.setItem(`logLevel:${serviceName}`, level);

    console.log(`🔧 Log level for ${serviceName} set to: ${level}`);
};

/**
 * Get log level from sessionStorage (for runtime overrides)
 */
export const getRuntimeLogLevel = (serviceName: string): LogLevel | null => {
    const stored = sessionStorage.getItem(`logLevel:${serviceName}`);
    return stored as LogLevel | null;
};
