import React, { useState } from 'react';
import './DateRangePicker.css';

export interface DateRange {
    startDate: Date;
    endDate: Date;
}

interface DateRangePickerProps {
    value?: DateRange;
    onChange: (range: DateRange) => void;
    quickRangeOptions?: Array<{ label: string; days: number }>;
    className?: string;
}

// Constants
const MILLISECONDS_PER_DAY = 1000 * 60 * 60 * 24;

const DEFAULT_QUICK_RANGES = [
    { label: '7 days', days: 7 },
    { label: '14 days', days: 14 },
    { label: '30 days', days: 30 },
    { label: '90 days', days: 90 }
];

const DateRangePicker: React.FC<DateRangePickerProps> = ({
    value,
    onChange,
    quickRangeOptions = DEFAULT_QUICK_RANGES,
    className = ''
}) => {
    const [mode, setMode] = useState<'quick' | 'custom'>('quick');
    const [customRange, setCustomRange] = useState<DateRange>(
        value || {
            startDate: new Date(Date.now() - 7 * MILLISECONDS_PER_DAY),
            endDate: new Date()
        }
    );

    const handleQuickRangeSelect = (days: number) => {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - days);

        const range = { startDate, endDate };
        setCustomRange(range);
        onChange(range);
    };

    const handleCustomDateChange = (field: 'startDate' | 'endDate', dateStr: string) => {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return;

        const newRange = {
            ...customRange,
            [field]: date
        };

        // Ensure start date is not after end date
        if (field === 'startDate' && date > customRange.endDate) {
            newRange.endDate = date;
        } else if (field === 'endDate' && date < customRange.startDate) {
            newRange.startDate = date;
        }

        setCustomRange(newRange);
        if (mode === 'custom') {
            onChange(newRange);
        }
    };

    const handleApplyCustom = () => {
        onChange(customRange);
    };

    const formatDateForInput = (date: Date): string => {
        return date.toISOString().split('T')[0];
    };

    const formatDateForDisplay = (date: Date): string => {
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const getCurrentRange = (): DateRange => {
        return value || customRange;
    };

    const isQuickRangeActive = (days: number): boolean => {
        if (!value) return false;

        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - days);

        // Check if current range matches this quick range (within 1 day tolerance)
        const daysDiff = Math.abs(value.endDate.getTime() - endDate.getTime()) / MILLISECONDS_PER_DAY;
        const startDiff = Math.abs(value.startDate.getTime() - startDate.getTime()) / MILLISECONDS_PER_DAY;

        return daysDiff < 1 && startDiff < 1;
    };

    return (
        <div className={`date-range-picker ${className}`}>
            <div className="date-range-picker-header">
                <button
                    type="button"
                    className={`mode-toggle ${mode === 'quick' ? 'active' : ''}`}
                    onClick={() => setMode('quick')}
                >
                    Quick Select
                </button>
                <button
                    type="button"
                    className={`mode-toggle ${mode === 'custom' ? 'active' : ''}`}
                    onClick={() => setMode('custom')}
                >
                    Custom Range
                </button>
            </div>

            {mode === 'quick' && (
                <div className="quick-ranges">
                    {quickRangeOptions.map(option => (
                        <button
                            key={option.days}
                            type="button"
                            className={`quick-range-btn ${isQuickRangeActive(option.days) ? 'active' : ''}`}
                            onClick={() => handleQuickRangeSelect(option.days)}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            )}

            {mode === 'custom' && (
                <div className="custom-range">
                    <div className="date-inputs">
                        <div className="date-input-group">
                            <label htmlFor="start-date">Start Date</label>
                            <input
                                id="start-date"
                                type="date"
                                value={formatDateForInput(customRange.startDate)}
                                onChange={(e) => handleCustomDateChange('startDate', e.target.value)}
                            />
                        </div>
                        <div className="date-input-group">
                            <label htmlFor="end-date">End Date</label>
                            <input
                                id="end-date"
                                type="date"
                                value={formatDateForInput(customRange.endDate)}
                                onChange={(e) => handleCustomDateChange('endDate', e.target.value)}
                            />
                        </div>
                    </div>
                    <button
                        type="button"
                        className="apply-custom-btn"
                        onClick={handleApplyCustom}
                    >
                        Apply Range
                    </button>
                </div>
            )}

            <div className="current-range-display">
                <span className="range-label">Current range:</span>
                <span className="range-dates">
                    {formatDateForDisplay(getCurrentRange().startDate)} - {formatDateForDisplay(getCurrentRange().endDate)}
                </span>
            </div>
        </div>
    );
};

export default DateRangePicker;
