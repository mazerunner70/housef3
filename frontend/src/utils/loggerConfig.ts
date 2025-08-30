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
 * Get environment-specific logger configuration
 */
export const getLoggerConfig = (): LoggerConfig => {
    const env = import.meta.env.MODE || 'development';
    const isDev = env === 'development';
    const isProd = env === 'production';
    const isTest = env === 'test';

    // Base configuration
    const baseConfig: LoggerConfig = {
        globalLevel: isDev ? 'debug' : isProd ? 'warn' : 'silent',
        serviceOverrides: {},
        enableConsoleOutput: !isProd,
        enableRemoteLogging: isProd,
        batchSize: 10,
        flushInterval: 5000
    };

    // Environment-specific overrides
    if (isDev) {
        return {
            ...baseConfig,
            globalLevel: 'debug',
            serviceOverrides: {
                'TransactionService': 'debug',
                'AccountService': 'info',
                'AuthService': 'debug',
                'ApiClient': 'info',
                'CategoryService': 'warn', // Less verbose for this service
                'AnalyticsService': 'error' // Only errors for analytics
            },
            enableConsoleOutput: true,
            enableRemoteLogging: false
        };
    }

    if (isProd) {
        return {
            ...baseConfig,
            globalLevel: 'warn',
            serviceOverrides: {
                'AuthService': 'error', // Only auth errors in prod
                'TransactionService': 'warn',
                'AccountService': 'warn',
                'ApiClient': 'error',
                'CategoryService': 'error',
                'AnalyticsService': 'silent' // No analytics logging in prod
            },
            enableConsoleOutput: true, // Temporarily enable console output in production
            enableRemoteLogging: true,
            batchSize: 50,
            flushInterval: 10000
        };
    }

    if (isTest) {
        return {
            ...baseConfig,
            globalLevel: 'silent',
            serviceOverrides: {},
            enableConsoleOutput: false,
            enableRemoteLogging: false
        };
    }

    return baseConfig;
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
