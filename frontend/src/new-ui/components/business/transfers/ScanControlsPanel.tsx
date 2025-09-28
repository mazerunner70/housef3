import React, { useState } from 'react';
import { DateRangePicker, Alert } from '@/new-ui/components/ui';
import Button from '@/new-ui/components/Button';
import { DateRange } from '@/new-ui/components/ui/DateRangePicker';
import './ScanControlsPanel.css';

type ScanStrategy = 'smart' | 'systematic' | 'custom';

interface ScanControlsPanelProps {
    currentDateRange: DateRange;
    onDateRangeChange: (range: DateRange) => void;
    onScanTransfers: () => void;
    onSmartScan: () => void;
    onSystematicScan: () => void;
    loading: boolean;
    className?: string;
}

const ScanControlsPanel: React.FC<ScanControlsPanelProps> = ({
    currentDateRange,
    onDateRangeChange,
    onScanTransfers,
    onSmartScan,
    onSystematicScan,
    loading,
    className = ''
}) => {
    const [selectedStrategy, setSelectedStrategy] = useState<ScanStrategy>('systematic');
    const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
    const [advancedSettings, setAdvancedSettings] = useState({
        amountTolerance: 0.01,
        dateTolerance: 3,
        selectedAccounts: [] as string[]
    });

    const handleStrategyChange = (strategy: ScanStrategy) => {
        setSelectedStrategy(strategy);
    };

    const handleScan = () => {
        switch (selectedStrategy) {
            case 'smart':
                onSmartScan();
                break;
            case 'systematic':
                onSystematicScan();
                break;
            case 'custom':
                onScanTransfers();
                break;
        }
    };

    const getStrategyDescription = (strategy: ScanStrategy): string => {
        switch (strategy) {
            case 'smart':
                return 'AI-powered scanning that automatically selects optimal date ranges based on transaction patterns and density.';
            case 'systematic':
                return 'Methodical chronological scanning that processes data in sequential chunks for comprehensive coverage.';
            case 'custom':
                return 'Manual date range selection for targeted scanning of specific time periods.';
        }
    };

    const getStrategyIcon = (strategy: ScanStrategy): string => {
        switch (strategy) {
            case 'smart': return '🤖';
            case 'systematic': return '📋';
            case 'custom': return '🎯';
        }
    };

    return (
        <div className={`scan-controls-panel ${className}`}>
            <div className="scan-controls-header">
                <h3>🔍 Scan Controls</h3>
                <div className="scan-status">
                    {loading && <span className="scanning-indicator">⚡ Scanning...</span>}
                </div>
            </div>

            {/* Strategy Selection */}
            <div className="strategy-section">
                <h4>Scanning Strategy</h4>
                <div className="strategy-options">
                    {(['smart', 'systematic', 'custom'] as ScanStrategy[]).map((strategy) => (
                        <button
                            key={strategy}
                            type="button"
                            className={`strategy-option ${selectedStrategy === strategy ? 'selected' : ''}`}
                            onClick={() => handleStrategyChange(strategy)}
                        >
                            <div className="strategy-header">
                                <span className="strategy-icon">{getStrategyIcon(strategy)}</span>
                                <span className="strategy-name">
                                    {strategy.charAt(0).toUpperCase() + strategy.slice(1)} Scan
                                </span>
                                <div className="strategy-radio">
                                    <input
                                        type="radio"
                                        name="strategy"
                                        checked={selectedStrategy === strategy}
                                        onChange={() => handleStrategyChange(strategy)}
                                    />
                                </div>
                            </div>
                            <div className="strategy-description">
                                {getStrategyDescription(strategy)}
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Date Range Controls */}
            {selectedStrategy === 'custom' && (
                <div className="date-range-section">
                    <h4>Date Range Selection</h4>
                    <DateRangePicker
                        value={currentDateRange}
                        onChange={onDateRangeChange}
                        quickRangeOptions={[
                            { label: '1 week', days: 7 },
                            { label: '2 weeks', days: 14 },
                            { label: '1 month', days: 30 },
                            { label: '3 months', days: 90 },
                            { label: '6 months', days: 180 },
                            { label: '1 year', days: 365 }
                        ]}
                        className="scan-date-picker"
                    />
                </div>
            )}

            {/* Advanced Options */}
            <div className="advanced-options-section">
                <button
                    className="advanced-toggle"
                    onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                >
                    <span>⚙️ Advanced Options</span>
                    <span className={`toggle-arrow ${showAdvancedOptions ? 'expanded' : ''}`}>
                        ▼
                    </span>
                </button>

                {showAdvancedOptions && (
                    <div className="advanced-options-content">
                        <div className="advanced-option">
                            <label htmlFor="amount-tolerance">
                                Amount Tolerance ($)
                                {' '}
                                <span className="option-help" title="Maximum difference in transfer amounts to consider a match">
                                    ❓
                                </span>
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
                                className="advanced-input"
                            />
                        </div>

                        <div className="advanced-option">
                            <label htmlFor="date-tolerance">
                                Date Tolerance (days)
                                {' '}
                                <span className="option-help" title="Maximum days between transactions to consider a match">
                                    ❓
                                </span>
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
                                className="advanced-input"
                            />
                        </div>

                        <div className="advanced-option">
                            <label htmlFor="account-filtering">Account Filtering</label>
                            <div className="account-filter-note">
                                <span className="note-icon">💡</span>
                                {' '}
                                <span>Account filtering will be available once accounts are loaded</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Scan Actions */}
            <div className="scan-actions">
                <Button
                    variant="primary"
                    size="standard"
                    onClick={handleScan}
                    disabled={loading}
                    className="primary-scan-button"
                >
                    {loading ? (
                        <>
                            <span className="loading-spinner">⚡</span>
                            {' '}
                            Scanning...
                        </>
                    ) : (
                        <>
                            {getStrategyIcon(selectedStrategy)}
                            {' '}
                            {selectedStrategy === 'smart' && 'Smart Scan'}
                            {selectedStrategy === 'systematic' && 'Systematic Scan'}
                            {selectedStrategy === 'custom' && 'Scan Range'}
                        </>
                    )}
                </Button>

                {selectedStrategy !== 'custom' && (
                    <div className="scan-info">
                        <Alert variant="info" className="strategy-info">
                            <strong>{selectedStrategy.charAt(0).toUpperCase() + selectedStrategy.slice(1)} Scan:</strong> {getStrategyDescription(selectedStrategy)}
                        </Alert>
                    </div>
                )}
            </div>

            {/* Batch Actions */}
            <div className="batch-actions">
                <h4>Batch Operations</h4>
                <div className="batch-buttons">
                    <Button
                        variant="secondary"
                        onClick={onSystematicScan}
                        disabled={loading}
                        className="batch-button"
                    >
                        📊 Continue from Last
                    </Button>
                    <Button
                        variant="secondary"
                        onClick={onSmartScan}
                        disabled={loading}
                        className="batch-button"
                    >
                        🎯 Scan High-Priority Areas
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default ScanControlsPanel;
