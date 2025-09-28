import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    listPairedTransfers,
    getTotalPairedTransfersCount,
    detectPotentialTransfers,
    bulkMarkTransfers,
    TransferPair,
    getTransferProgressAndRecommendation,
    resetTransferProgress
} from '@/services/TransferService';
import { getAccounts } from '@/services/TransactionService';
import { AccountInfo } from '@/schemas/Transaction';
import {
    Alert,
    LoadingState,
    DateRange
} from '@/new-ui/components/ui';
import Button from '@/new-ui/components/Button';

import { useLocale } from '@/new-ui/hooks/useLocale';
import ScanControlsPanel from '../transfers/ScanControlsPanel';
import TransferResultsDashboard from '../transfers/TransferResultsDashboard';
import './TransfersDashboard.css';

// Helper function to generate unique keys for transfer pairs
const getTransferPairKey = (pair: TransferPair): string => {
    const outgoingId = pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id;
    const incomingId = pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id;
    return `${outgoingId}-${incomingId}`;
};

// Helper function to check if a date is an epoch date (1970)
const isEpochDate = (date: Date): boolean => {
    return date.getFullYear() === 1970;
};

// Helper function to check if a checked date range is valid (not epoch)
const isValidCheckedDateRange = (checkedDateRange: any): boolean => {
    if (!checkedDateRange) return false;
    const startDate = new Date(checkedDateRange.startDate);
    const endDate = new Date(checkedDateRange.endDate);
    return !isEpochDate(startDate) && !isEpochDate(endDate);
};

interface TransfersDashboardProps { }

const TransfersDashboard: React.FC<TransfersDashboardProps> = () => {
    const { formatDate } = useLocale();
    const [searchParams, setSearchParams] = useSearchParams();
    const [pairedTransfers, setPairedTransfers] = useState<TransferPair[]>([]);
    const [detectedTransfers, setDetectedTransfers] = useState<TransferPair[]>([]);
    const [totalPairedTransfersCount, setTotalPairedTransfersCount] = useState<number>(0);
    const [accounts, setAccounts] = useState<AccountInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [detectLoading, setDetectLoading] = useState(false);
    const [bulkMarkLoading, setBulkMarkLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDetectedTransfers, setSelectedDetectedTransfers] = useState<Set<string>>(new Set());
    const [showDateRangeSuggestion, setShowDateRangeSuggestion] = useState(false);
    const [showDetectionSuccess, setShowDetectionSuccess] = useState(false);

    // Transfer progress and date range tracking
    const [transferProgress, setTransferProgress] = useState<any>(null);
    const [recommendedRange, setRecommendedRange] = useState<any>(null);
    const [recalculateLoading, setRecalculateLoading] = useState(false);

    // Scanning statistics for analytics
    const [scanningStats, setScanningStats] = useState({
        totalScansRun: 0,
        totalTimeSpent: 0,
        averageScanTime: 0,
        lastScanDate: undefined as Date | undefined
    });

    // Date range management - will be set from preferences in loadAllInitialData
    const [currentDateRange, setCurrentDateRange] = useState<DateRange>(() => {
        // Initialize with a default range, but this will be overridden by preferences
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - 7);
        return { startDate, endDate };
    });

    // Simple auto-expand suggestion state
    const [autoExpandSuggestion] = useState(true);

    // Load initial data
    useEffect(() => {
        loadAllInitialData();
    }, []);

    // Auto-scan if URL parameter is present
    useEffect(() => {
        const autoScan = searchParams.get('autoScan');
        if (autoScan === 'true' && !detectLoading && !loading) {
            // Clear the autoScan parameter to prevent repeated scans
            const newParams = new URLSearchParams(searchParams);
            newParams.delete('autoScan');
            setSearchParams(newParams, { replace: true });

            // Trigger scan after a short delay to ensure data is loaded
            const timer: NodeJS.Timeout = setTimeout(() => {
                handleDetectTransfers();
            }, 500);

            // Cleanup function to clear timeout if component unmounts or dependencies change
            return () => {
                clearTimeout(timer);
            };
        }
    }, [searchParams, detectLoading, loading]);

    const loadAllInitialData = async () => {
        setLoading(true);
        setError(null);
        try {
            // First load progress to get checked range
            const progressAndRecommendation = await getTransferProgressAndRecommendation();
            setTransferProgress(progressAndRecommendation.progress);
            setRecommendedRange(progressAndRecommendation.recommendedRange);

            // Determine the date range to use - prioritize checked range from preferences
            const startDateParam = searchParams.get('startDate');
            const endDateParam = searchParams.get('endDate');

            let dateRangeToUse: DateRange;
            let rangeToUseForAPI: { startDate: number; endDate: number };

            if (startDateParam && endDateParam) {
                // URL parameters take precedence (for direct navigation)
                const startDate = new Date(startDateParam);
                const endDate = new Date(endDateParam);
                if (!isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
                    dateRangeToUse = { startDate, endDate };
                    rangeToUseForAPI = {
                        startDate: startDate.getTime(),
                        endDate: endDate.getTime()
                    };
                } else {
                    // Invalid URL params, fall back to checked range or default
                    if (isValidCheckedDateRange(progressAndRecommendation.progress?.checkedDateRange)) {
                        dateRangeToUse = {
                            startDate: new Date(progressAndRecommendation.progress.checkedDateRange.startDate),
                            endDate: new Date(progressAndRecommendation.progress.checkedDateRange.endDate)
                        };
                    } else {
                        dateRangeToUse = currentDateRange;
                    }

                    rangeToUseForAPI = {
                        startDate: dateRangeToUse.startDate.getTime(),
                        endDate: dateRangeToUse.endDate.getTime()
                    };
                }
            } else if (isValidCheckedDateRange(progressAndRecommendation.progress?.checkedDateRange)) {
                // Use checked range from preferences (most common case)
                dateRangeToUse = {
                    startDate: new Date(progressAndRecommendation.progress.checkedDateRange.startDate),
                    endDate: new Date(progressAndRecommendation.progress.checkedDateRange.endDate)
                };
                rangeToUseForAPI = {
                    startDate: progressAndRecommendation.progress.checkedDateRange.startDate,
                    endDate: progressAndRecommendation.progress.checkedDateRange.endDate
                };
            } else {
                // No preferences or URL params, use current default range
                dateRangeToUse = currentDateRange;
                rangeToUseForAPI = {
                    startDate: currentDateRange.startDate.getTime(),
                    endDate: currentDateRange.endDate.getTime()
                };
            }

            // Update the current date range state
            setCurrentDateRange(dateRangeToUse);

            // Load remaining data in parallel
            const [transfersData, totalCount, accountsData] = await Promise.all([
                listPairedTransfers(rangeToUseForAPI)(),
                getTotalPairedTransfersCount()(),
                getAccounts()
            ]);

            setPairedTransfers(transfersData.pairedTransfers);
            setTotalPairedTransfersCount(totalCount);
            setAccounts(accountsData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load transfer data');
        } finally {
            setLoading(false);
        }
    };

    const loadTransferProgress = async () => {
        try {
            const progressAndRecommendation = await getTransferProgressAndRecommendation();
            setTransferProgress(progressAndRecommendation.progress);
            setRecommendedRange(progressAndRecommendation.recommendedRange);
        } catch (err) {
            console.warn('Failed to load transfer progress:', err);
        }
    };



    const handleDetectTransfers = async () => {
        const startTime = Date.now();
        setDetectLoading(true);
        setError(null);
        setShowDateRangeSuggestion(false);
        setShowDetectionSuccess(false);
        try {
            // Use recommended range if available, otherwise fall back to current range
            const scanRange = recommendedRange ? {
                startDate: recommendedRange.startDate,
                endDate: recommendedRange.endDate
            } : {
                startDate: currentDateRange.startDate.getTime(),
                endDate: currentDateRange.endDate.getTime()
            };

            // Use date range API
            const detected = await detectPotentialTransfers(
                scanRange.startDate,
                scanRange.endDate
            )();
            setDetectedTransfers(detected.transfers);
            setSelectedDetectedTransfers(new Set());

            // Update current date range to match what was actually scanned
            if (recommendedRange) {
                const newRange = {
                    startDate: new Date(recommendedRange.startDate),
                    endDate: new Date(recommendedRange.endDate)
                };
                setCurrentDateRange(newRange);
            }

            // Show success message with clear next steps
            if (detected.transfers.length > 0) {
                setError(null); // Clear any previous errors
                setShowDetectionSuccess(true);
                // Auto-hide success message after 10 seconds
                setTimeout(() => setShowDetectionSuccess(false), 10000);
            } else if (autoExpandSuggestion) {
                setShowDateRangeSuggestion(true);
            }

            // Update scanning stats
            const scanTime = (Date.now() - startTime) / 1000 / 60; // Convert to minutes
            setScanningStats(prev => ({
                totalScansRun: prev.totalScansRun + 1,
                totalTimeSpent: prev.totalTimeSpent + scanTime,
                averageScanTime: (prev.totalTimeSpent + scanTime) / (prev.totalScansRun + 1),
                lastScanDate: new Date()
            }));

            // Refresh progress after detection
            loadTransferProgress();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to detect transfers');
        } finally {
            setDetectLoading(false);
        }
    };

    const handleSmartScan = async () => {
        // For now, smart scan uses the recommended range if available
        if (recommendedRange) {
            const newRange = {
                startDate: new Date(recommendedRange.startDate),
                endDate: new Date(recommendedRange.endDate)
            };
            setCurrentDateRange(newRange);
            await handleDateRangePickerChange(newRange);
            await handleDetectTransfers();
        } else {
            // Fallback to regular scan
            await handleDetectTransfers();
        }
    };

    const handleSystematicScan = async () => {
        // Systematic scan continues from the last checked date
        if (transferProgress?.checkedDateRange?.endDate) {
            const lastCheckedDate = new Date(transferProgress.checkedDateRange.endDate);
            const endDate = new Date(lastCheckedDate);
            endDate.setDate(endDate.getDate() + 30); // Scan next 30 days

            const newRange = {
                startDate: lastCheckedDate,
                endDate: Math.min(endDate.getTime(), Date.now()) > endDate.getTime() ? new Date() : endDate
            };

            setCurrentDateRange(newRange);
            await handleDateRangePickerChange(newRange);
            await handleDetectTransfers();
        } else {
            // If no previous progress, start from the beginning
            await handleDetectTransfers();
        }
    };

    const handleRecalculateFromScratch = async () => {
        if (!confirm('This will clear all transfer detection progress and start fresh. Are you sure?')) {
            return;
        }

        setRecalculateLoading(true);
        setError(null);
        try {
            // Reset progress on the backend
            await resetTransferProgress();

            // Clear local state
            setTransferProgress(null);
            setRecommendedRange(null);
            setDetectedTransfers([]);
            setSelectedDetectedTransfers(new Set());
            setScanningStats({
                totalScansRun: 0,
                totalTimeSpent: 0,
                averageScanTime: 0,
                lastScanDate: undefined
            });

            // Reload fresh data
            await loadAllInitialData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to reset transfer progress');
        } finally {
            setRecalculateLoading(false);
        }
    };

    const handleExportTransfers = () => {
        // Create CSV content
        const csvContent = [
            ['Source Account', 'Source Date', 'Source Amount', 'Target Account', 'Target Date', 'Target Amount', 'Days Apart', 'Status'].join(','),
            ...pairedTransfers.map(pair => [
                getAccountName(pair.outgoingTransaction.accountId || undefined),
                pair.outgoingTransaction.date,
                Math.abs(Number(pair.outgoingTransaction.amount)),
                getAccountName(pair.incomingTransaction.accountId || undefined),
                pair.incomingTransaction.date,
                Number(pair.incomingTransaction.amount),
                pair.dateDifference,
                'Confirmed'
            ].join(',')),
            ...detectedTransfers.map(pair => [
                getAccountName(pair.outgoingTransaction.accountId || undefined),
                pair.outgoingTransaction.date,
                Math.abs(Number(pair.outgoingTransaction.amount)),
                getAccountName(pair.incomingTransaction.accountId || undefined),
                pair.incomingTransaction.date,
                Number(pair.incomingTransaction.amount),
                pair.dateDifference,
                'Pending'
            ].join(','))
        ].join('\n');

        // Download CSV
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transfers-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    };

    const handleBulkMarkTransfers = async () => {
        if (selectedDetectedTransfers.size === 0) {
            setError('Please select at least one transfer pair to mark');
            return;
        }

        setBulkMarkLoading(true);
        setError(null);
        try {
            const selectedPairs = detectedTransfers
                .filter(pair => selectedDetectedTransfers.has(getTransferPairKey(pair)))
                .map(pair => ({
                    outgoingTransactionId: (pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id) as string,
                    incomingTransactionId: (pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id) as string,
                    amount: pair.amount,
                    dateDifference: pair.dateDifference
                }));

            // Pass the current date range so the backend can update the checked range in preferences
            const scannedDateRange = {
                startDate: currentDateRange.startDate.getTime(),
                endDate: currentDateRange.endDate.getTime()
            };

            const result = await bulkMarkTransfers(selectedPairs, scannedDateRange);

            if (result.successCount > 0) {
                // Reload paired transfers and total count to show the newly marked ones
                const [updatedTransfers, updatedTotalCount] = await Promise.all([
                    listPairedTransfers({
                        startDate: currentDateRange.startDate.getTime(),
                        endDate: currentDateRange.endDate.getTime()
                    })(),
                    getTotalPairedTransfersCount()()
                ]);
                setPairedTransfers(updatedTransfers.pairedTransfers);
                setTotalPairedTransfersCount(updatedTotalCount);

                // Refresh transfer progress to get updated checked date range
                await loadTransferProgress();

                // Remove successfully marked transfers from detected list
                const successfulIds = new Set(
                    result.successful.flatMap(s => [s.outgoingTransactionId, s.incomingTransactionId])
                );
                setDetectedTransfers(prev =>
                    prev.filter(pair =>
                        !successfulIds.has((pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id) as string) &&
                        !successfulIds.has((pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id) as string)
                    )
                );

                // Remove successful pairs from selection
                setSelectedDetectedTransfers(prev => {
                    const newSelected = new Set(prev);
                    detectedTransfers.forEach(pair => {
                        const outgoingId = (pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id) as string;
                        const incomingId = (pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id) as string;
                        if (successfulIds.has(outgoingId) || successfulIds.has(incomingId)) {
                            newSelected.delete(getTransferPairKey(pair));
                        }
                    });
                    return newSelected;
                });
            }

            if (result.failureCount > 0) {
                setError(`${result.successCount} transfers marked successfully, ${result.failureCount} failed`);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to mark transfers');
        } finally {
            setBulkMarkLoading(false);
        }
    };

    const getAccountName = (accountId: string | null | undefined): string => {
        if (!accountId) return 'Unknown Account';
        const account = accounts.find(acc => acc.accountId === accountId);
        return account ? (account.name as string) : `Account ${accountId}`;
    };



    const handleExpandDateRange = async (days: number) => {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - days);

        const newRange = { startDate, endDate };
        setCurrentDateRange(newRange);
        setShowDateRangeSuggestion(false);

        // Automatically trigger detection with new range
        setDetectLoading(true);
        setError(null);
        try {
            const detected = await detectPotentialTransfers(
                newRange.startDate.getTime(),
                newRange.endDate.getTime()
            )();
            setDetectedTransfers(detected.transfers);
            setSelectedDetectedTransfers(new Set());
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to detect transfers');
        } finally {
            setDetectLoading(false);
        }
    };

    const handleDateRangePickerChange = async (newRange: DateRange) => {
        setCurrentDateRange(newRange);

        // Reload paired transfers with new date range
        try {
            setLoading(true);
            const updatedTransfers = await listPairedTransfers({
                startDate: newRange.startDate.getTime(),
                endDate: newRange.endDate.getTime()
            })();
            setPairedTransfers(updatedTransfers.pairedTransfers);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to reload transfers with new date range');
        } finally {
            setLoading(false);
        }
    };

    const toggleDetectedTransfer = (pairKey: string) => {
        const newSelected = new Set(selectedDetectedTransfers);
        if (newSelected.has(pairKey)) {
            newSelected.delete(pairKey);
        } else {
            newSelected.add(pairKey);
        }
        setSelectedDetectedTransfers(newSelected);
    };

    const selectAllDetected = () => {
        if (selectedDetectedTransfers.size === detectedTransfers.length) {
            setSelectedDetectedTransfers(new Set());
        } else {
            setSelectedDetectedTransfers(new Set(detectedTransfers.map(pair => getTransferPairKey(pair))));
        }
    };

    if (loading) {
        return <LoadingState message="Loading transfer data..." />;
    }

    return (
        <div className="transfers-dashboard">
            {/* Overall Status Header with Account Coverage Timeline */}
            <div className="transfers-dashboard-header">
                <div className="header-content">
                    <div className="header-text">
                        <h2>📊 Inter-Account Transfers Dashboard</h2>
                        <p>Detect and manage transfers between your accounts with advanced analytics</p>
                    </div>
                    <div className="quick-stats-bar">
                        <div className="quick-stat">
                            <span className="stat-value">🏦 {accounts.length}</span>
                            <span className="stat-label">Accounts</span>
                        </div>
                        <div className="quick-stat">
                            <span className="stat-value">🔄 {totalPairedTransfersCount}</span>
                            <span className="stat-label">Pairs Found</span>
                        </div>
                        {scanningStats.lastScanDate && (
                            <div className="quick-stat">
                                <span className="stat-value">📅 {formatDate(scanningStats.lastScanDate.getTime(), { hour: 'numeric', minute: 'numeric' })}</span>
                                <span className="stat-label">Last Scan</span>
                            </div>
                        )}
                        <div className="quick-stat">
                            <span className="stat-value">📈 {transferProgress?.progressPercentage || 0}%</span>
                            <span className="stat-label">Complete</span>
                        </div>
                    </div>
                </div>

                {/* Account Coverage Timeline - Moved from Progress Dashboard */}
                <div className="header-timeline-section">
                    <h4>📅 Account Coverage Timeline</h4>
                    {transferProgress?.accountDateRange ? (
                        <div className="timeline-container">
                            <div className="timeline-labels">
                                <span className="timeline-start">
                                    {formatDate(transferProgress.accountDateRange.startDate, {
                                        year: 'numeric',
                                        month: 'short'
                                    })}
                                </span>
                                <span className="timeline-end">
                                    {formatDate(transferProgress.accountDateRange.endDate, {
                                        year: 'numeric',
                                        month: 'short'
                                    })}
                                </span>
                            </div>
                            <div className="timeline-track">
                                <div className="timeline-background"></div>
                                {(() => {
                                    if (!transferProgress?.accountDateRange) return [];

                                    const totalRange = transferProgress.accountDateRange.endDate - transferProgress.accountDateRange.startDate;
                                    const segments = [];

                                    // Add checked segment
                                    if (transferProgress.checkedDateRange) {
                                        const checkedStart = Math.max(transferProgress.checkedDateRange.startDate, transferProgress.accountDateRange.startDate);
                                        const checkedEnd = Math.min(transferProgress.checkedDateRange.endDate, transferProgress.accountDateRange.endDate);
                                        const checkedOffset = ((checkedStart - transferProgress.accountDateRange.startDate) / totalRange) * 100;
                                        const checkedWidth = ((checkedEnd - checkedStart) / totalRange) * 100;

                                        segments.push({
                                            type: 'checked',
                                            left: checkedOffset,
                                            width: checkedWidth,
                                            label: `Checked: ${formatDate(checkedStart, { year: 'numeric', month: 'short', day: 'numeric' })} - ${formatDate(checkedEnd, { year: 'numeric', month: 'short', day: 'numeric' })}`
                                        });
                                    }

                                    // Add recommended segment
                                    if (recommendedRange) {
                                        const recStart = new Date(recommendedRange.startDate).getTime();
                                        const recEnd = new Date(recommendedRange.endDate).getTime();
                                        const recOffset = ((recStart - transferProgress.accountDateRange.startDate) / totalRange) * 100;
                                        const recWidth = ((recEnd - recStart) / totalRange) * 100;

                                        segments.push({
                                            type: 'recommended',
                                            left: recOffset,
                                            width: recWidth,
                                            label: `Recommended: ${formatDate(recStart, { year: 'numeric', month: 'short', day: 'numeric' })} - ${formatDate(recEnd, { year: 'numeric', month: 'short', day: 'numeric' })}`
                                        });
                                    }

                                    return segments;
                                })().map((segment) => (
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
                                    <span>Checked ({transferProgress.totalDaysChecked || 0} days)</span>
                                </div>
                                <div className="legend-item">
                                    <div className="legend-color unchecked"></div>
                                    <span>Unchecked ({(transferProgress.totalDaysAvailable || 0) - (transferProgress.totalDaysChecked || 0)} days)</span>
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
            </div>

            {error && (
                <Alert variant="error" dismissible onDismiss={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Current Analysis Panel - Focus on Date Range Analysis */}
            <div className="current-analysis-panel">
                <div className="analysis-header">
                    <h3>🔍 Current Analysis</h3>
                    <div className="analysis-stats">
                        <div className="stat-item">
                            <span className="stat-value">{pairedTransfers.length}</span>
                            <span className="stat-label">Pairs Found</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">{detectedTransfers.length}</span>
                            <span className="stat-label">Pending Review</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-value">
                                {(() => {
                                    // If we have no URL params and have a valid checked range, show the checked range
                                    // This ensures consistency with the timeline display
                                    const startDateParam = searchParams.get('startDate');
                                    const endDateParam = searchParams.get('endDate');

                                    if (!startDateParam && !endDateParam && isValidCheckedDateRange(transferProgress?.checkedDateRange)) {
                                        const checkedStart = new Date(transferProgress.checkedDateRange.startDate);
                                        const checkedEnd = new Date(transferProgress.checkedDateRange.endDate);
                                        return `${checkedStart.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })} - ${checkedEnd.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}`;
                                    }

                                    // Otherwise show the current selected range
                                    return `${currentDateRange.startDate.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })} - ${currentDateRange.endDate.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}`;
                                })()}
                            </span>
                            <span className="stat-label">
                                {(() => {
                                    const startDateParam = searchParams.get('startDate');
                                    const endDateParam = searchParams.get('endDate');

                                    if (!startDateParam && !endDateParam && isValidCheckedDateRange(transferProgress?.checkedDateRange)) {
                                        return 'Checked Range';
                                    }

                                    return 'Current Range';
                                })()}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Scan Controls */}
                <ScanControlsPanel
                    currentDateRange={currentDateRange}
                    onDateRangeChange={handleDateRangePickerChange}
                    onScanTransfers={handleDetectTransfers}
                    onSmartScan={handleSmartScan}
                    onSystematicScan={handleSystematicScan}
                    loading={detectLoading}
                    recommendedRange={recommendedRange ? {
                        startDate: new Date(recommendedRange.startDate),
                        endDate: new Date(recommendedRange.endDate)
                    } : null}
                    pairedTransfersCount={pairedTransfers.length}
                    detectedTransfersCount={detectedTransfers.length}
                />

                {/* Quick Actions */}
                <div className="quick-actions">
                    <Button
                        variant="danger"
                        size="compact"
                        onClick={handleRecalculateFromScratch}
                        disabled={recalculateLoading}
                    >
                        🔄 Reset Progress
                    </Button>
                    <Button
                        variant="secondary"
                        size="compact"
                        onClick={handleSystematicScan}
                        disabled={detectLoading}
                    >
                        ➡️ Continue Systematic
                    </Button>
                </div>
            </div>

            {/* Transfer Candidate Approval Panel */}
            <TransferResultsDashboard
                confirmedTransfers={pairedTransfers}
                pendingTransfers={detectedTransfers}
                selectedPendingTransfers={selectedDetectedTransfers}
                accounts={accounts}
                loading={loading}
                bulkMarkLoading={bulkMarkLoading}
                onTogglePendingTransfer={toggleDetectedTransfer}
                onSelectAllPending={selectAllDetected}
                onBulkMarkTransfers={handleBulkMarkTransfers}
                onExportTransfers={handleExportTransfers}
                getTransferPairKey={getTransferPairKey}
                showSuccessMessage={showDetectionSuccess}
            />


            {/* Legacy Date Range Suggestion (keep for backward compatibility) */}
            {showDateRangeSuggestion && (
                <div className="date-range-suggestion">
                    <div className="suggestion-content">
                        <h4>No transfer candidates found in current date range</h4>
                        <p>Try expanding the date range to find more potential transfer pairs for review:</p>
                        <div className="suggestion-buttons">
                            <button
                                className="suggestion-button"
                                onClick={() => handleExpandDateRange(14)}
                                disabled={detectLoading}
                            >
                                Scan Last 2 Weeks
                            </button>
                            <button
                                className="suggestion-button"
                                onClick={() => handleExpandDateRange(30)}
                                disabled={detectLoading}
                            >
                                Scan Last Month
                            </button>
                            <button
                                className="suggestion-button secondary"
                                onClick={() => setShowDateRangeSuggestion(false)}
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default TransfersDashboard;
