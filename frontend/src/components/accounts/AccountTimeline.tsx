import React, { useMemo, useState } from 'react';
import { Account } from '../../schemas/Account';
import './AccountTimeline.css';

interface AccountTimelineProps {
    accounts: Account[];
    onAccountClick?: (accountId: string) => void;
}

type ZoomLevel = 'all' | 'year' | 'sixMonths' | 'month';

interface ZoomOption {
    key: ZoomLevel;
    label: string;
    days: number | null; // null means show all data
}

interface TimelineData {
    startDate: number;
    endDate: number;
    totalDays: number;
    accounts: Array<{
        id: string;
        name: string;
        startDate?: number;
        endDate?: number;
        leftPercent: number;
        widthPercent: number;
        hasData: boolean;
    }>;
}

// Static zoom options - moved outside component to prevent unnecessary re-renders
const zoomOptions: ZoomOption[] = [
    { key: 'all', label: 'All Time', days: null },
    { key: 'year', label: 'Last Year', days: 365 },
    { key: 'sixMonths', label: 'Last 6 Months', days: 180 },
    { key: 'month', label: 'Last 30 Days', days: 30 }
];

const AccountTimeline: React.FC<AccountTimelineProps> = ({ accounts, onAccountClick }) => {
    const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('all');

    const timelineData = useMemo((): TimelineData => {
        // Filter accounts that have import date data
        const accountsWithDates = accounts.filter(acc =>
            acc.importsStartDate != null && acc.importsEndDate != null
        );

        if (accountsWithDates.length === 0) {
            // Return empty timeline data
            const today = Date.now();
            return {
                startDate: today,
                endDate: today,
                totalDays: 1,
                accounts: accounts.map(acc => ({
                    id: acc.accountId,
                    name: acc.accountName,
                    leftPercent: 0,
                    widthPercent: 0,
                    hasData: false,
                })),
            };
        }

        // Find the earliest start date and latest end date
        const allStartDates = accountsWithDates.map(acc => acc.importsStartDate!);
        const allEndDates = accountsWithDates.map(acc => acc.importsEndDate!);

        let earliestStart = Math.min(...allStartDates);
        let latestEnd = Math.max(...allEndDates, Date.now()); // Include today

        // Apply zoom level filtering
        const selectedZoomOption = zoomOptions.find(option => option.key === zoomLevel);
        if (selectedZoomOption && selectedZoomOption.days !== null) {
            const zoomStartDate = Date.now() - (selectedZoomOption.days * 24 * 60 * 60 * 1000);
            earliestStart = Math.max(earliestStart, zoomStartDate);
            latestEnd = Date.now(); // For zoom modes, always end at today
        }

        const totalDays = Math.max(1, Math.ceil((latestEnd - earliestStart) / (1000 * 60 * 60 * 24)));

        // Create timeline data for all accounts
        const timelineAccounts = accounts.map(acc => {
            if (acc.importsStartDate == null || acc.importsEndDate == null) {
                return {
                    id: acc.accountId,
                    name: acc.accountName,
                    leftPercent: 0,
                    widthPercent: 0,
                    hasData: false,
                };
            }

            const startDays = Math.floor((acc.importsStartDate - earliestStart) / (1000 * 60 * 60 * 24));
            const duration = Math.ceil((acc.importsEndDate - acc.importsStartDate) / (1000 * 60 * 60 * 24));

            const leftPercent = (startDays / totalDays) * 100;
            const widthPercent = Math.max(0.5, (duration / totalDays) * 100); // Minimum 0.5% width for visibility

            return {
                id: acc.accountId,
                name: acc.accountName,
                startDate: acc.importsStartDate,
                endDate: acc.importsEndDate,
                leftPercent,
                widthPercent,
                hasData: true,
            };
        });

        return {
            startDate: earliestStart,
            endDate: latestEnd,
            totalDays,
            accounts: timelineAccounts,
        };
    }, [accounts, zoomLevel]);

    const formatDate = (timestamp: number) => {
        return new Date(timestamp).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    };

    const getTooltipText = (account: TimelineData['accounts'][0]) => {
        if (!account.hasData || !account.startDate || !account.endDate) {
            return `${account.name}: No import data available`;
        }
        return `${account.name}: ${formatDate(account.startDate)} - ${formatDate(account.endDate)}`;
    };

    if (accounts.length === 0) {
        return (
            <div className="account-timeline-container">
                <h3 className="timeline-title">Account Import Timeline</h3>
                <div className="timeline-empty">
                    No accounts to display
                </div>
            </div>
        );
    }

    return (
        <div className="account-timeline-container">
            <h3 className="timeline-title">Account Import Timeline</h3>

            {/* Timeline Header */}
            <div className="timeline-header">
                <div className="timeline-controls">
                    <div className="zoom-controls">
                        <span className="zoom-label">View:</span>
                        {zoomOptions.map((option) => (
                            <button
                                key={option.key}
                                className={`zoom-button ${zoomLevel === option.key ? 'active' : ''}`}
                                onClick={() => setZoomLevel(option.key)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault();
                                        setZoomLevel(option.key);
                                    }
                                }}
                                aria-label={`Zoom to ${option.label}`}
                                aria-pressed={zoomLevel === option.key}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="timeline-date-range">
                    <span className="start-date">{formatDate(timelineData.startDate)}</span>
                    <span className="end-date">{formatDate(timelineData.endDate)}</span>
                </div>
            </div>

            {/* Timeline Content */}
            <div className="timeline-content">
                <div className="timeline-axis">
                    <div className="timeline-line"></div>
                </div>

                <div className="timeline-accounts">
                    {timelineData.accounts.map((account, index) => (
                        <div key={account.id} className="timeline-account-row">
                            <div className="account-label">
                                <span
                                    className="account-name"
                                    style={{ color: account.hasData ? `hsl(${index * 40}, 70%, 50%)` : '#999' }}
                                >
                                    {account.name}
                                </span>
                            </div>
                            <div className="timeline-bar-container">
                                {account.hasData ? (
                                    <div
                                        className="timeline-bar"
                                        style={{
                                            left: `${account.leftPercent}%`,
                                            width: `${account.widthPercent}%`,
                                            backgroundColor: `hsl(${index * 40}, 70%, 50%)`,
                                        }}
                                        title={getTooltipText(account)}
                                        onClick={() => onAccountClick?.(account.id)}
                                        onKeyDown={(e) => {
                                            if ((e.key === 'Enter' || e.key === ' ') && onAccountClick) {
                                                e.preventDefault();
                                                onAccountClick(account.id);
                                            }
                                        }}
                                        tabIndex={0}
                                        role="button"
                                        aria-label={`Click to scroll to ${account.name} account details`}
                                    />
                                ) : (
                                    <div className="timeline-no-data" title={getTooltipText(account)}>
                                        <span>No data</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default AccountTimeline;
