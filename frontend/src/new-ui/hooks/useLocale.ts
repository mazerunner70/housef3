import { useState, useEffect } from 'react';

export interface LocaleConfig {
    locale: string;
    dateFormat: 'short' | 'long' | 'iso' | 'relative';
    timeZone?: string;
}

// Helper function to detect RTL locales
const isRTLLocale = (locale: string): boolean => {
    const rtlLocales = ['ar', 'he', 'fa', 'ur', 'ku', 'dv'];
    const languageCode = locale.split('-')[0].toLowerCase();
    return rtlLocales.includes(languageCode);
};

// Helper function to get browser locale with fallbacks
const getBrowserLocale = (): string => {
    // Try multiple sources for locale detection
    if (typeof navigator !== 'undefined') {
        // Check navigator.language first
        if (navigator.language) {
            return navigator.language;
        }

        // Check navigator.languages array
        if (navigator.languages && navigator.languages.length > 0) {
            return navigator.languages[0];
        }

        // Legacy browser support
        const legacyLocale = (navigator as any).userLanguage ||
            (navigator as any).browserLanguage ||
            (navigator as any).systemLanguage;
        if (legacyLocale) {
            return legacyLocale;
        }
    }

    // Final fallback
    return 'en-US';
};

const DEFAULT_LOCALE_CONFIG: LocaleConfig = {
    locale: 'en-US',
    dateFormat: 'short'
};

/**
 * Hook for managing locale preferences across the application
 * 
 * Features:
 * - Automatically detects browser locale
 * - Persists locale preference in localStorage
 * - Provides methods to update locale settings
 * - Returns formatted locale configuration for components
 */
export const useLocale = () => {
    const [localeConfig, setLocaleConfig] = useState<LocaleConfig>(() => {
        // Try to load from localStorage first
        const stored = localStorage.getItem('user-locale-config');
        if (stored) {
            try {
                return { ...DEFAULT_LOCALE_CONFIG, ...JSON.parse(stored) };
            } catch {
                // Fall through to default behavior
            }
        }

        // Detect browser locale using improved detection
        const browserLocale = getBrowserLocale();

        return {
            ...DEFAULT_LOCALE_CONFIG,
            locale: browserLocale
        };
    });

    // Persist changes to localStorage
    useEffect(() => {
        localStorage.setItem('user-locale-config', JSON.stringify(localeConfig));
    }, [localeConfig]);

    const updateLocale = (newLocale: string) => {
        setLocaleConfig(prev => ({ ...prev, locale: newLocale }));
    };

    const updateDateFormat = (format: LocaleConfig['dateFormat']) => {
        setLocaleConfig(prev => ({ ...prev, dateFormat: format }));
    };

    const updateTimeZone = (timeZone: string) => {
        setLocaleConfig(prev => ({ ...prev, timeZone }));
    };

    const resetToDefault = () => {
        const browserLocale = getBrowserLocale();
        setLocaleConfig({
            ...DEFAULT_LOCALE_CONFIG,
            locale: browserLocale
        });
    };

    // Helper function to format dates consistently
    const formatDate = (date: Date | number | string, options?: Intl.DateTimeFormatOptions) => {
        const dateObj = new Date(date);
        const formatOptions: Intl.DateTimeFormatOptions = {
            timeZone: localeConfig.timeZone,
            ...options
        };

        return dateObj.toLocaleDateString(localeConfig.locale, formatOptions);
    };

    // Helper function to format date and time
    const formatDateTime = (date: Date | number | string, options?: Intl.DateTimeFormatOptions) => {
        const dateObj = new Date(date);
        const formatOptions: Intl.DateTimeFormatOptions = {
            timeZone: localeConfig.timeZone,
            ...options
        };

        return dateObj.toLocaleString(localeConfig.locale, formatOptions);
    };

    // Get common locale information
    const getLocaleInfo = () => {
        const testDate = new Date('2024-01-15T10:30:00');

        return {
            locale: localeConfig.locale,
            dateFormat: localeConfig.dateFormat,
            timeZone: localeConfig.timeZone || Intl.DateTimeFormat().resolvedOptions().timeZone,
            sampleDate: formatDate(testDate),
            sampleDateTime: formatDateTime(testDate),
            currency: new Intl.NumberFormat(localeConfig.locale).format(1234.56),
            isRTL: isRTLLocale(localeConfig.locale)
        };
    };

    return {
        localeConfig,
        updateLocale,
        updateDateFormat,
        updateTimeZone,
        resetToDefault,
        formatDate,
        formatDateTime,
        getLocaleInfo
    };
};

export default useLocale;
