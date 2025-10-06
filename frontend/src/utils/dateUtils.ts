/**
 * Centralized date utilities for consistent epoch/Date object conversion
 * 
 * PATTERN:
 * - Storage/API: Always use milliseconds since epoch (number)
 * - Application Logic: Always use Date objects
 * - Display: Always use formatted strings from Date objects
 */

// Type helpers for clarity
export type DateRange = { startDate: Date; endDate: Date };
export type EpochDateRange = { startDate: number; endDate: number }; // milliseconds since epoch

// === BOUNDARY LAYER: API ↔ APPLICATION ===

/**
 * Convert epoch timestamp to Date object
 * Use this immediately after receiving data from API
 */
export const epochToDate = (timestamp: number): Date => {
    return new Date(timestamp);
};

/**
 * Convert Date object to epoch timestamp (milliseconds since epoch)
 * Use this immediately before sending to API
 */
export const dateToEpoch = (date: Date): number => {
    return date.getTime();
};

/**
 * Convert epoch date range to Date objects
 * Use in service layer after receiving API responses
 */
export const epochRangeToDateRange = (epochRange: EpochDateRange): DateRange => {
    return {
        startDate: epochToDate(epochRange.startDate),
        endDate: epochToDate(epochRange.endDate)
    };
};

/**
 * Convert Date range to epoch timestamps  
 * Use in service layer before API requests
 */
export const dateRangeToEpochRange = (dateRange: DateRange): EpochDateRange => {
    return {
        startDate: dateToEpoch(dateRange.startDate),
        endDate: dateToEpoch(dateRange.endDate)
    };
};

// === APPLICATION LAYER: Date object operations ===

/**
 * Calculate days between two dates (ignoring time component)
 * Always use this instead of manual getTime() calculations
 */
export const daysBetween = (startDate: Date, endDate: Date): number => {
    // Strip time component by creating new dates with only date part
    const startDateOnly = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
    const endDateOnly = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate());

    return Math.ceil(
        (endDateOnly.getTime() - startDateOnly.getTime()) / MS_PER_DAY
    );
};

/**
 * Add days to a date
 */
export const addDays = (date: Date, days: number): Date => {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
};

/**
 * Subtract days from a date
 */
export const subtractDays = (date: Date, days: number): Date => {
    return addDays(date, -days);
};

/**
 * Create a date range from number of days back from today
 */
export const createDateRangeFromDays = (days: number, endDate: Date = new Date()): DateRange => {
    return {
        startDate: subtractDays(endDate, days),
        endDate: endDate
    };
};

/**
 * Check if two dates are the same day (ignoring time)
 * @param date1 first date
 * @param date2 second date
 * @returns true if the two dates are the same day, false otherwise
 */
export const isSameDay = (date1: Date, date2: Date): boolean => {
    return date1.getFullYear() === date2.getFullYear() &&
        date1.getMonth() === date2.getMonth() &&
        date1.getDate() === date2.getDate();
};

/**
 * Check if a date is today
 */
export const isToday = (date: Date): boolean => {
    return isSameDay(date, new Date());
};

/**
 * Clamp a date to be within a range
 */
export const clampDate = (date: Date, minDate: Date, maxDate: Date): Date => {
    return new Date(Math.max(minDate.getTime(), Math.min(date.getTime(), maxDate.getTime())));
};

// === DISPLAY LAYER: Formatting ===

/**
 * Format date for display (e.g., "Jan 15, 2024")
 */
export const formatDisplayDate = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
};

/**
 * Format date for forms (YYYY-MM-DD)
 */
export const formatInputDate = (date: Date): string => {
    return date.toISOString().split('T')[0];
};

/**
 * Format date with time for display
 */
export const formatDateTime = (date: Date): string => {
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

/**
 * Format relative time (e.g., "2 days ago", "today")
 */
export const formatRelativeDate = (date: Date): string => {
    const now = new Date();
    const days = daysBetween(date, now);

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    if (days < 365) return `${Math.floor(days / 30)} months ago`;
    return `${Math.floor(days / 365)} years ago`;
};

// === VALIDATION ===

/**
 * Check if a value is a valid epoch timestamp (milliseconds since epoch)
 */
export const isValidEpochTimestamp = (value: unknown): value is number => {
    return typeof value === 'number' &&
        value > 0 &&
        value < 4102444800000 && // Year 2100
        !isNaN(value);
};

/**
 * Parse date safely from various input types
 */
export const parseDate = (input: string | number | Date): Date | null => {
    try {
        if (input instanceof Date) {
            return isNaN(input.getTime()) ? null : input;
        }

        if (typeof input === 'number' && isValidEpochTimestamp(input)) {
            return new Date(input);
        }

        if (typeof input === 'string') {
            const parsed = new Date(input);
            return isNaN(parsed.getTime()) ? null : parsed;
        }

        return null;
    } catch {
        return null;
    }
};

// === CONSTANTS ===

export const MS_PER_SECOND = 1000;
export const MS_PER_MINUTE = MS_PER_SECOND * 60;
export const MS_PER_HOUR = MS_PER_MINUTE * 60;
export const MS_PER_DAY = MS_PER_HOUR * 24;
export const MS_PER_WEEK = MS_PER_DAY * 7;

// Common date ranges
export const getCommonDateRanges = () => {
    const now = new Date();
    return {
        today: { startDate: now, endDate: now },
        yesterday: (() => {
            const yesterday = subtractDays(now, 1);
            return { startDate: yesterday, endDate: yesterday };
        })(),
        last7Days: createDateRangeFromDays(7, now),
        last30Days: createDateRangeFromDays(30, now),
        last90Days: createDateRangeFromDays(90, now),
        thisMonth: (() => {
            const start = new Date(now.getFullYear(), now.getMonth(), 1);
            const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
            return { startDate: start, endDate: end };
        })(),
        lastMonth: (() => {
            const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const end = new Date(now.getFullYear(), now.getMonth(), 0);
            return { startDate: start, endDate: end };
        })()
    };
};
