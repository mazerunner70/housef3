import React from 'react';
import { useLocale } from '@/new-ui/hooks/useLocale';

/**
 * Debug component to test and display locale information
 * Use this component to verify locale detection is working correctly
 */
const LocaleDebugger: React.FC = () => {
    const { localeConfig, getLocaleInfo, updateLocale, resetToDefault } = useLocale();
    const localeInfo = getLocaleInfo();

    // Get raw browser information for debugging
    const getBrowserInfo = () => {
        if (typeof navigator === 'undefined') {
            return { error: 'Navigator not available (SSR?)' };
        }

        return {
            'navigator.language': navigator.language,
            'navigator.languages': navigator.languages,
            'userLanguage': (navigator as any).userLanguage,
            'browserLanguage': (navigator as any).browserLanguage,
            'systemLanguage': (navigator as any).systemLanguage,
            'detected timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
            'localStorage value': localStorage.getItem('user-locale-config')
        };
    };

    const browserInfo = getBrowserInfo();
    const testDate = new Date('2024-01-15T10:30:00');

    const testLocales = [
        'en-US', 'en-GB', 'de-DE', 'fr-FR', 'es-ES',
        'ja-JP', 'zh-CN', 'ar-SA', 'he-IL', 'ru-RU'
    ];

    return (
        <div style={{
            padding: '20px',
            fontFamily: 'monospace',
            backgroundColor: '#f5f5f5',
            border: '1px solid #ccc',
            borderRadius: '8px',
            margin: '20px'
        }}>
            <h2>🌍 Locale Debugger</h2>

            <div style={{ marginBottom: '20px' }}>
                <h3>Current Configuration</h3>
                <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <tbody>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Active Locale:</td>
                            <td style={{ padding: '4px', backgroundColor: '#e8f4fd' }}>{localeInfo.locale}</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Date Format:</td>
                            <td style={{ padding: '4px' }}>{localeInfo.dateFormat}</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Time Zone:</td>
                            <td style={{ padding: '4px' }}>{localeInfo.timeZone}</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Is RTL:</td>
                            <td style={{ padding: '4px' }}>{localeInfo.isRTL ? 'Yes' : 'No'}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div style={{ marginBottom: '20px' }}>
                <h3>Sample Formatting</h3>
                <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <tbody>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Sample Date:</td>
                            <td style={{ padding: '4px', backgroundColor: '#e8f4fd' }}>{localeInfo.sampleDate}</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Sample DateTime:</td>
                            <td style={{ padding: '4px' }}>{localeInfo.sampleDateTime}</td>
                        </tr>
                        <tr>
                            <td style={{ padding: '4px', fontWeight: 'bold' }}>Sample Currency:</td>
                            <td style={{ padding: '4px' }}>{localeInfo.currency}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div style={{ marginBottom: '20px' }}>
                <h3>Browser Detection Info</h3>
                <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <tbody>
                        {Object.entries(browserInfo).map(([key, value]) => (
                            <tr key={key}>
                                <td style={{ padding: '4px', fontWeight: 'bold' }}>{key}:</td>
                                <td style={{ padding: '4px' }}>
                                    {Array.isArray(value) ? JSON.stringify(value) : String(value || 'undefined')}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div style={{ marginBottom: '20px' }}>
                <h3>Test Different Locales</h3>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
                    {testLocales.map(locale => (
                        <button
                            key={locale}
                            onClick={() => updateLocale(locale)}
                            style={{
                                padding: '4px 8px',
                                backgroundColor: localeConfig.locale === locale ? '#007bff' : '#f8f9fa',
                                color: localeConfig.locale === locale ? 'white' : 'black',
                                border: '1px solid #ccc',
                                borderRadius: '4px',
                                cursor: 'pointer'
                            }}
                        >
                            {locale}
                        </button>
                    ))}
                </div>
                <button
                    onClick={resetToDefault}
                    style={{
                        padding: '8px 16px',
                        backgroundColor: '#28a745',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                    }}
                >
                    Reset to Browser Default
                </button>
            </div>

            <div>
                <h3>Locale Comparison</h3>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '12px' }}>
                    <thead>
                        <tr style={{ backgroundColor: '#f0f0f0' }}>
                            <th style={{ padding: '4px', border: '1px solid #ccc' }}>Locale</th>
                            <th style={{ padding: '4px', border: '1px solid #ccc' }}>Short Date</th>
                            <th style={{ padding: '4px', border: '1px solid #ccc' }}>Long Date</th>
                            <th style={{ padding: '4px', border: '1px solid #ccc' }}>Currency</th>
                        </tr>
                    </thead>
                    <tbody>
                        {testLocales.map(locale => {
                            const shortDate = testDate.toLocaleDateString(locale, {
                                year: 'numeric', month: 'short', day: 'numeric'
                            });
                            const longDate = testDate.toLocaleDateString(locale, {
                                year: 'numeric', month: 'long', day: 'numeric'
                            });
                            const currency = new Intl.NumberFormat(locale).format(1234.56);

                            return (
                                <tr key={locale} style={{
                                    backgroundColor: localeConfig.locale === locale ? '#e8f4fd' : 'white'
                                }}>
                                    <td style={{ padding: '4px', border: '1px solid #ccc', fontWeight: 'bold' }}>
                                        {locale}
                                    </td>
                                    <td style={{ padding: '4px', border: '1px solid #ccc' }}>{shortDate}</td>
                                    <td style={{ padding: '4px', border: '1px solid #ccc' }}>{longDate}</td>
                                    <td style={{ padding: '4px', border: '1px solid #ccc' }}>{currency}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default LocaleDebugger;

