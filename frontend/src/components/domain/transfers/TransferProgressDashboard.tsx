import React from 'react';
import { ProgressBar, LoadingState } from '@/components/ui';
import Button from '@/components/ui/Button';
import { useLocale } from '@/hooks/useLocale';
import './TransferProgressDashboard.css';

interface DateRange {
    startDate: number;
    endDate: number;
}

interface TransferProgress {
    accountDateRange?: DateRange;
    checkedDateRange?: DateRange;
    progressPercentage?: number;
    totalDaysAvailable?: number;
    totalDaysChecked?: number;
    transferPairsFound?: number;
    averagePairsPerDay?: number;
    estimatedTimeRemaining?: string;
}

interface RecommendedRange {
    startDate: string;
    endDate: string;
    reasoning?: string;
    transactionDensity?: 'low' | 'medium' | 'high';
    priority?: number;
}

interface TransferProgressDashboardProps {
    progress: TransferProgress | null;
    recommendedRange: RecommendedRange | null;
    loading: boolean;
    onUseRecommendedRange: (range: { startDate: Date; endDate: Date }) => void;
    onRecalculateFromScratch: () => void;
    onContinueSystematic: () => void;
    totalConfirmedPairs: number;
    lastScanDate?: Date;
}

const TransferProgressDashboard: React.FC<TransferProgressDashboardProps> = ({
    progress,
    recommendedRange,
    loading,
    onUseRecommendedRange,
    onRecalculateFromScratch,
    onContinueSystematic,
    totalConfirmedPairs,
    lastScanDate
}) => {
    const { formatDate } = useLocale();

    const formatDateRange = (startMs: number | null, endMs: number | null): string => {
        if (!startMs || !endMs) return 'No data available';
        const start = formatDate(startMs, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
        const end = formatDate(endMs, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
        return `${start} - ${end}`;
    };

    const getTimelineSegments = () => {
        if (!progress?.accountDateRange) return [];

        const totalRange = progress.accountDateRange.endDate - progress.accountDateRange.startDate;
        const segments = [];

        // Add checked segment
        if (progress.checkedDateRange) {
            const checkedStart = Math.max(progress.checkedDateRange.startDate, progress.accountDateRange.startDate);
            const checkedEnd = Math.min(progress.checkedDateRange.endDate, progress.accountDateRange.endDate);
            const checkedOffset = ((checkedStart - progress.accountDateRange.startDate) / totalRange) * 100;
            const checkedWidth = ((checkedEnd - checkedStart) / totalRange) * 100;

            segments.push({
                type: 'checked',
                left: checkedOffset,
                width: checkedWidth,
                label: 'Checked'
            });
        }

        // Add recommended segment
        if (recommendedRange) {
            const recStart = new Date(recommendedRange.startDate).getTime();
            const recEnd = new Date(recommendedRange.endDate).getTime();
            const recOffset = ((recStart - progress.accountDateRange.startDate) / totalRange) * 100;
            const recWidth = ((recEnd - recStart) / totalRange) * 100;

            segments.push({
                type: 'recommended',
                left: recOffset,
                width: recWidth,
                label: 'Recommended'
            });
        }

        return segments;
    };

    const getDensityIcon = (density?: string) => {
        switch (density) {
            case 'high': return '🔥';
            case 'medium': return '📊';
            case 'low': return '📉';
            default: return '📈';
        }
    };

    const getPriorityColor = (priority?: number) => {
        if (!priority) return 'var(--color-blue-500)';
        if (priority >= 8) return 'var(--color-red-500)';
        if (priority >= 6) return 'var(--color-orange-500)';
        if (priority >= 4) return 'var(--color-yellow-500)';
        return 'var(--color-green-500)';
    };

    if (loading) {
        return (
            <div className="transfer-progress-dashboard">
                <LoadingState message="Loading transfer analysis..." size="small" />
            </div>
        );
    }

    return (
        <div className="transfer-progress-dashboard">
            <div className="dashboard-header">
                <h3>📈 Transfer Analysis Dashboard</h3>
                <div className="quick-stats">
                    <div className="stat-item">
                        <span className="stat-value">{totalConfirmedPairs}</span>
                        <span className="stat-label">Pairs Found</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-value">{progress?.progressPercentage || 0}%</span>
                        <span className="stat-label">Complete</span>
                    </div>
                    <div className="stat-item">
                        <span className="stat-value">{progress?.averagePairsPerDay?.toFixed(2) || '0.00'}</span>
                        <span className="stat-label">Pairs/Day</span>
                    </div>
                    {lastScanDate && (
                        <div className="stat-item">
                            <span className="stat-value">
                                {formatDate(lastScanDate.getTime(), {
                                    hour: 'numeric',
                                    minute: 'numeric'
                                })}
                            </span>
                            <span className="stat-label">Last Scan</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="dashboard-content">
                {/* Account Coverage Timeline */}
                <div className="coverage-section">
                    <h4>📅 Account Coverage Timeline</h4>
                    {progress?.accountDateRange ? (
                        <div className="timeline-container">
                            <div className="timeline-labels">
                                <span className="timeline-start">
                                    {formatDate(progress.accountDateRange.startDate, {
                                        year: 'numeric',
                                        month: 'short'
                                    })}
                                </span>
                                <span className="timeline-end">
                                    {formatDate(progress.accountDateRange.endDate, {
                                        year: 'numeric',
                                        month: 'short'
                                    })}
                                </span>
                            </div>
                            <div className="timeline-track">
                                <div className="timeline-background"></div>
                                {getTimelineSegments().map((segment) => (
                                    <div
                                        key={`${segment.type}-${segment.left}-${segment.width}`}
                                        className={`timeline-segment ${segment.type}`}
                                        style={{
                                            left: `${segment.left}%`,
                                            width: `${segment.width}%`
                                        }}
                                        title={segment.label}
                                    />
                                ))}
                            </div>
                            <div className="timeline-legend">
                                <div className="legend-item">
                                    <div className="legend-color checked"></div>
                                    <span>Checked ({progress.totalDaysChecked || 0} days)</span>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color unchecked"></div>
                                    <span>Unchecked ({(progress.totalDaysAvailable || 0) - (progress.totalDaysChecked || 0)} days)</span>
                                </div>
                                {recommendedRange && (
                                    <div className="legend-item">
                                        <div className="legend-color recommended"></div>
                                        <span>Recommended</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="no-data">No transaction data available</div>
                    )}
                </div>

                {/* Progress Metrics */}
                <div className="metrics-section">
                    <h4>📊 Progress Metrics</h4>
                    <div className="metrics-grid">
                        <div className="metric-card">
                            <div className="metric-header">
                                <span className="metric-title">Overall Progress</span>
                                <span className="metric-value">{progress?.progressPercentage || 0}%</span>
                            </div>
                            <ProgressBar
                                percentage={progress?.progressPercentage || 0}
                                size="medium"
                            />
                            <div className="metric-details">
                                {progress?.totalDaysChecked || 0} of {progress?.totalDaysAvailable || 0} days checked
                            </div>
                        </div>

                        <div className="metric-card">
                            <div className="metric-header">
                                <span className="metric-title">Transfer Pairs Found</span>
                                <span className="metric-value">{totalConfirmedPairs}</span>
                            </div>
                            <div className="metric-details">
                                Average: {progress?.averagePairsPerDay?.toFixed(2) || '0.00'} pairs per day scanned
                            </div>
                        </div>

                        {progress?.estimatedTimeRemaining && (
                            <div className="metric-card">
                                <div className="metric-header">
                                    <span className="metric-title">Estimated Time Remaining</span>
                                    <span className="metric-value">{progress.estimatedTimeRemaining}</span>
                                </div>
                                <div className="metric-details">
                                    Based on current scanning pace
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Smart Recommendations */}
                {recommendedRange && (
                    <div className="recommendations-section">
                        <h4>🎯 Smart Recommendations</h4>
                        <div className="recommendation-card">
                            <div className="recommendation-header">
                                <div className="recommendation-title">
                                    <span className="recommendation-icon">
                                        {getDensityIcon(recommendedRange.transactionDensity)}
                                    </span>
                                    <span>Suggested Next Range</span>
                                    {recommendedRange.priority && (
                                        <span
                                            className="priority-badge"
                                            style={{ backgroundColor: getPriorityColor(recommendedRange.priority) }}
                                        >
                                            Priority {recommendedRange.priority}/10
                                        </span>
                                    )}
                                </div>
                                <Button
                                    variant="primary"
                                    size="compact"
                                    onClick={() => onUseRecommendedRange({
                                        startDate: new Date(recommendedRange.startDate),
                                        endDate: new Date(recommendedRange.endDate)
                                    })}
                                >
                                    Use This Range
                                </Button>
                            </div>
                            <div className="recommendation-details">
                                <div className="recommendation-range">
                                    {formatDateRange(
                                        new Date(recommendedRange.startDate).getTime(),
                                        new Date(recommendedRange.endDate).getTime()
                                    )}
                                </div>
                                {recommendedRange.reasoning && (
                                    <div className="recommendation-reasoning">
                                        💡 {recommendedRange.reasoning}
                                    </div>
                                )}
                                {recommendedRange.transactionDensity && (
                                    <div className="recommendation-density">
                                        Transaction Density: <strong>{recommendedRange.transactionDensity}</strong>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Quick Actions */}
                <div className="actions-section">
                    <h4>⚡ Quick Actions</h4>
                    <div className="action-buttons">
                        <Button
                            variant="danger"
                            onClick={onRecalculateFromScratch}
                            className="action-button"
                        >
                            🔄 Recalculate from Scratch
                        </Button>
                        <Button
                            variant="secondary"
                            onClick={onContinueSystematic}
                            className="action-button"
                        >
                            ➡️ Continue Systematic Scan
                        </Button>
                    </div>
                    <div className="action-descriptions">
                        <div className="action-description">
                            <strong>Recalculate from Scratch:</strong> Clears all progress and starts fresh analysis
                        </div>
                        <div className="action-description">
                            <strong>Continue Systematic:</strong> Picks up scanning from where you left off
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TransferProgressDashboard;
