import React, { useState } from 'react';
import { DateRangePicker, DateRange, DateCell } from '@/new-ui/components/ui';
import Button from '@/new-ui/components/Button';
import './ScanControlsPanel.css';


interface ScanControlsPanelProps {
    currentDateRange: DateRange;
    onDateRangeChange: (range: DateRange) => void;
    onScanTransfers: () => void;
    onSmartScan: () => void;
    onSystematicScan: () => void;
    loading: boolean;
    className?: string;
    recommendedRange?: {
        startDate: Date;
        endDate: Date;
    } | null;
    pairedTransfersCount?: number;
    detectedTransfersCount?: number;
}

const ScanControlsPanel: React.FC<ScanControlsPanelProps> = ({
    currentDateRange,
    onDateRangeChange,
    onScanTransfers,
    onSmartScan,
    onSystematicScan,
    loading,
    className = '',
    recommendedRange,
    pairedTransfersCount = 0,
    detectedTransfersCount = 0
}) => {
    const [showStrategyOptions, setShowStrategyOptions] = useState(false);
    const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
    const [advancedSettings, setAdvancedSettings] = useState({
        amountTolerance: 0.01,
        dateTolerance: 3,
        selectedAccounts: [] as string[]
    });

    // Determine the primary scan action based on recommended range
    const getPrimaryScanAction = () => {
        if (recommendedRange) {
            return {
                action: onSmartScan, // This will use the recommended range from the dashboard
                label: 'Scan Next Chunk',
                startDate: new Date(Math.min(recommendedRange.startDate.getTime(), recommendedRange.endDate.getTime())),
                endDate: new Date(Math.max(recommendedRange.startDate.getTime(), recommendedRange.endDate.getTime())),
                icon: '🎯'
            };
        } else {
            return {
                action: onSystematicScan,
                label: 'Continue Scanning',
                startDate: new Date(Math.min(currentDateRange.startDate.getTime(), currentDateRange.endDate.getTime())),
                endDate: new Date(Math.max(currentDateRange.startDate.getTime(), currentDateRange.endDate.getTime())),
                icon: '📋'
            };
        }
    };

    const primaryScan = getPrimaryScanAction();

    return (
        <div className={`scan-controls-panel ${className}`}>
            <div className="scan-controls-header">
                <h3>🔍 Scan Controls</h3>
                {loading && <span className="scanning-indicator">⚡ Scanning...</span>}
            </div>

            {/* Primary Scan Action */}
            <div className="primary-scan-section">
                <Button
                    variant="primary"
                    size="standard"
                    onClick={primaryScan.action}
                    disabled={loading || detectedTransfersCount > 0}
                    className="primary-scan-button"
                    title={detectedTransfersCount > 0 ? "Evaluate pending candidates before scanning next range" : undefined}
                >
                    {(() => {
                        if (loading) {
                            return (
                                <>
                                    <span className="loading-spinner">⚡</span>
                                    {' '}
                                    Scanning...
                                </>
                            );
                        }

                        if (detectedTransfersCount > 0) {
                            return (
                                <>
                                    <span className="scan-icon">⏸️</span>
                                    <div className="scan-button-content">
                                        <div className="scan-label">Evaluate Pending First</div>
                                        <div className="scan-date-range">
                                            {detectedTransfersCount} candidates awaiting review
                                        </div>
                                    </div>
                                </>
                            );
                        }

                        return (
                            <>
                                <span className="scan-icon">{primaryScan.icon}</span>
                                <div className="scan-button-content">
                                    <div className="scan-label">{primaryScan.label}</div>
                                    <div className="scan-date-range">
                                        <DateCell date={primaryScan.startDate} format="short" locale="en-GB" /> - <DateCell date={primaryScan.endDate} format="short" locale="en-GB" />
                                    </div>
                                </div>
                            </>
                        );
                    })()}
                </Button>

                {/* Scan Results Summary Panel */}
                {(pairedTransfersCount > 0 || detectedTransfersCount > 0) && (
                    <button
                        className="scan-results-panel"
                        aria-label="Click to scroll to transfer detection results"
                        onClick={() => {
                            const resultsPanel = document.querySelector('.transfer-results-dashboard');
                            if (resultsPanel) {
                                resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }
                        }}
                    >
                        <div className="scan-results-content">
                            <span className="scan-results-label">📊 Scan Results:</span>
                            <span className="scan-results-range">
                                <DateCell date={currentDateRange.startDate} format="short" locale="en-GB" /> - <DateCell date={currentDateRange.endDate} format="short" locale="en-GB" />
                            </span>
                            <span className="scan-results-stats">
                                {pairedTransfersCount} pairs found, {detectedTransfersCount} candidates pending review
                            </span>
                        </div>
                    </button>
                )}
            </div>

            {/* Secondary Actions */}
            <div className="secondary-actions">
                <div className="action-group">
                    <h4>Scan Strategy</h4>
                    <div className="strategy-buttons">
                        <Button
                            variant="secondary"
                            size="compact"
                            onClick={() => setShowStrategyOptions(!showStrategyOptions)}
                            className="strategy-toggle"
                        >
                            📋 Strategy Options
                            {' '}
                            <span className={`toggle-arrow ${showStrategyOptions ? 'expanded' : ''}`}>▼</span>
                        </Button>
                    </div>

                    {showStrategyOptions && (
                        <div className="strategy-options-expanded">
                            <div className="strategy-option-item">
                                <Button
                                    variant="secondary"
                                    size="compact"
                                    onClick={onSmartScan}
                                    disabled={loading}
                                    className="strategy-button"
                                >
                                    🤖 Smart Scan
                                </Button>
                                <span className="strategy-description">AI-powered optimal range selection</span>
                            </div>

                            <div className="strategy-option-item">
                                <Button
                                    variant="secondary"
                                    size="compact"
                                    onClick={onSystematicScan}
                                    disabled={loading}
                                    className="strategy-button"
                                >
                                    📋 Systematic Scan
                                </Button>
                                <span className="strategy-description">Sequential chronological processing</span>
                            </div>

                            <div className="strategy-option-item">
                                <Button
                                    variant="secondary"
                                    size="compact"
                                    onClick={onScanTransfers}
                                    disabled={loading}
                                    className="strategy-button"
                                >
                                    🎯 Custom Range
                                </Button>
                                <span className="strategy-description">Manual date range selection</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="action-group">
                    <h4>Advanced Options</h4>
                    <div className="advanced-buttons">
                        <Button
                            variant="secondary"
                            size="compact"
                            onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                            className="advanced-toggle"
                        >
                            ⚙️ Advanced Settings
                            {' '}
                            <span className={`toggle-arrow ${showAdvancedOptions ? 'expanded' : ''}`}>▼</span>
                        </Button>
                    </div>

                    {showAdvancedOptions && (
                        <div className="advanced-options-expanded">
                            <div className="date-range-section">
                                <label htmlFor="custom-date-range">Custom Date Range</label>
                                <DateRangePicker
                                    value={currentDateRange}
                                    onChange={onDateRangeChange}
                                    quickRangeOptions={[
                                        { label: '1 week', days: 7 },
                                        { label: '2 weeks', days: 14 },
                                        { label: '1 month', days: 30 },
                                        { label: '3 months', days: 90 }
                                    ]}
                                    className="scan-date-picker"
                                />
                            </div>

                            <div className="tolerance-settings">
                                <div className="tolerance-option">
                                    <label htmlFor="amount-tolerance">
                                        Amount Tolerance ($)
                                        {' '}
                                        <span className="option-help" title="Maximum difference in transfer amounts">❓</span>
                                    </label>
                                    <input
                                        id="amount-tolerance"
                                        type="number"
                                        min="0"
                                        step="0.01"
                                        value={advancedSettings.amountTolerance}
                                        onChange={(e) => setAdvancedSettings(prev => ({
                                            ...prev,
                                            amountTolerance: parseFloat(e.target.value) || 0
                                        }))}
                                        className="tolerance-input"
                                    />
                                </div>

                                <div className="tolerance-option">
                                    <label htmlFor="date-tolerance">
                                        Date Tolerance (days)
                                        {' '}
                                        <span className="option-help" title="Maximum days between transactions">❓</span>
                                    </label>
                                    <input
                                        id="date-tolerance"
                                        type="number"
                                        min="0"
                                        max="30"
                                        value={advancedSettings.dateTolerance}
                                        onChange={(e) => setAdvancedSettings(prev => ({
                                            ...prev,
                                            dateTolerance: parseInt(e.target.value) || 0
                                        }))}
                                        className="tolerance-input"
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ScanControlsPanel;
