/**
 * Examples of how to use the configurable logging system
 * 
 * This file demonstrates various logging patterns and runtime controls
 */

import { createLogger, withApiLogging, LoggerDebug } from './logger';

// ============ BASIC USAGE EXAMPLES ============

/**
 * Example 1: Basic service logger
 * Log level controlled by configuration and runtime overrides
 */
const exampleServiceLogger = createLogger('ExampleService');

export const exampleBasicLogging = () => {
    exampleServiceLogger.info('Service started', { version: '1.0.0' });
    exampleServiceLogger.warn('This is a warning', { retryCount: 3 });
    exampleServiceLogger.error('Something went wrong', { errorCode: 'E001' });
};

/**
 * Example 2: API operation with automatic logging
 * Log level controlled by service configuration
 */
export const exampleApiOperation = withApiLogging(
    'ExampleService',
    '/api/example',
    'GET',
    async () => {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 100));
        return { data: 'example response' };
    },
    {
        successData: (result) => ({ responseSize: JSON.stringify(result).length })
    }
);

// ============ RUNTIME CONTROL EXAMPLES ============

/**
 * Example 3: Runtime log level control
 * These functions can be called from browser console or programmatically
 */
export const demonstrateRuntimeControls = () => {
    console.log('=== Logger Runtime Control Demo ===');

    // Show current configuration
    LoggerDebug.showAll();

    // Set specific service to debug level
    LoggerDebug.setLevel('ExampleService', 'debug');

    // Test logging at different levels
    exampleServiceLogger.info('This should now appear (info level)');
    exampleServiceLogger.error('This should definitely appear (error level)');

    // Reset to defaults
    LoggerDebug.clearLevel('ExampleService');

    console.log('=== Demo Complete ===');
};

// ============ ENVIRONMENT-SPECIFIC EXAMPLES ============

/**
 * Example 4: Different behavior based on environment
 */
export const exampleEnvironmentAwareLogging = () => {
    const logger = createLogger('EnvironmentExample');

    // This will behave differently based on:
    // - Development: debug level, console output enabled
    // - Production: warn level, console output disabled, remote logging enabled
    // - Test: silent level, no output

    logger.debug('Debug info (only in development)');
    logger.info('General info (development only)');
    logger.warn('Warning (development and production)');
    logger.error('Error (all environments)');
};

// ============ BROWSER CONSOLE USAGE GUIDE ============

/**
 * Browser Console Usage Examples:
 * 
 * // Show current logging configuration
 * LoggerDebug.showAll()
 * 
 * // Enable debug logging for TransactionService
 * LoggerDebug.setLevel('TransactionService', 'debug')
 * 
 * // Enable debug for all services (temporary)
 * LoggerDebug.enableDebugAll()
 * 
 * // Check current level for a service
 * LoggerDebug.getLevel('TransactionService')
 * 
 * // Clear runtime override for a service
 * LoggerDebug.clearLevel('TransactionService')
 * 
 * // Reset all services to configuration defaults
 * LoggerDebug.reset()
 * 
 * // The LoggerDebug object is automatically available in browser console
 * // when this module is imported anywhere in your app
 */
