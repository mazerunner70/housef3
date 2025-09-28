import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    listPairedTransfers,
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
    LoadingState
} from '@/new-ui/components/ui';
import { DateRange } from '@/new-ui/components/ui/DateRangePicker';

import { useLocale } from '@/new-ui/hooks/useLocale';
import TransferProgressDashboard from '../transfers/TransferProgressDashboard';
import ScanControlsPanel from '../transfers/ScanControlsPanel';
import TransferResultsDashboard from '../transfers/TransferResultsDashboard';
import TransferAnalyticsDashboard from '../transfers/TransferAnalyticsDashboard';
import './TransfersDashboard.css';

// Helper function to generate unique keys for transfer pairs
const getTransferPairKey = (pair: TransferPair): string => {
    const outgoingId = pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id;
    const incomingId = pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id;
    return `${outgoingId}-${incomingId}`;
};

interface TransfersDashboardProps { }

const TransfersDashboard: React.FC<TransfersDashboardProps> = () => {
    const { formatDate } = useLocale();
    const [searchParams, setSearchParams] = useSearchParams();
    const [pairedTransfers, setPairedTransfers] = useState<TransferPair[]>([]);
    const [detectedTransfers, setDetectedTransfers] = useState<TransferPair[]>([]);
    const [accounts, setAccounts] = useState<AccountInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [detectLoading, setDetectLoading] = useState(false);
    const [bulkMarkLoading, setBulkMarkLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDetectedTransfers, setSelectedDetectedTransfers] = useState<Set<string>>(new Set());
    const [showDateRangeSuggestion, setShowDateRangeSuggestion] = useState(false);

    // Transfer progress and date range tracking
    const [transferProgress, setTransferProgress] = useState<any>(null);
    const [recommendedRange, setRecommendedRange] = useState<any>(null);
    const [progressLoading, setProgressLoading] = useState(false);
    const [recalculateLoading, setRecalculateLoading] = useState(false);

    // Scanning statistics for analytics
    const [scanningStats, setScanningStats] = useState({
        totalScansRun: 0,
        totalTimeSpent: 0,
        averageScanTime: 0,
        lastScanDate: undefined as Date | undefined
    });

    // Date range management - check URL params first, then default to last 7 days
    const [currentDateRange, setCurrentDateRange] = useState<DateRange>(() => {
        const startDateParam = searchParams.get('startDate');
        const endDateParam = searchParams.get('endDate');

        if (startDateParam && endDateParam) {
            // Parse and validate dates from URL parameters
            const startDate = new Date(startDateParam);
            const endDate = new Date(endDateParam);

            // Check if both dates are valid (not NaN)
            if (!isNaN(startDate.getTime()) && !isNaN(endDate.getTime())) {
                return { startDate, endDate };
            }
        }

        // Fall back to default 7-day range if URL params are missing or invalid
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
        setProgressLoading(true);
        setError(null);
        try {
            // Load all data in parallel with optimized progress/recommendation call
            const [transfersData, accountsData, progressAndRecommendation] = await Promise.all([
                listPairedTransfers({
                    startDate: currentDateRange.startDate.getTime(),
                    endDate: currentDateRange.endDate.getTime()
                })(),
                getAccounts(),
                getTransferProgressAndRecommendation()
            ]);

            setPairedTransfers(transfersData.pairedTransfers);
            setAccounts(accountsData);
            setTransferProgress(progressAndRecommendation.progress);
            setRecommendedRange(progressAndRecommendation.recommendedRange);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load transfer data');
        } finally {
            setLoading(false);
            setProgressLoading(false);
        }
    };

    const loadTransferProgress = async () => {
        setProgressLoading(true);
        try {
            const progressAndRecommendation = await getTransferProgressAndRecommendation();
            setTransferProgress(progressAndRecommendation.progress);
            setRecommendedRange(progressAndRecommendation.recommendedRange);
        } catch (err) {
            console.warn('Failed to load transfer progress:', err);
        } finally {
            setProgressLoading(false);
        }
    };



    const handleDetectTransfers = async () => {
        const startTime = Date.now();
        setDetectLoading(true);
        setError(null);
        setShowDateRangeSuggestion(false);
        try {
            // Use date range API
            const detected = await detectPotentialTransfers(
                currentDateRange.startDate.getTime(),
                currentDateRange.endDate.getTime()
            )();
            setDetectedTransfers(detected.transfers);
            setSelectedDetectedTransfers(new Set());

            // Show suggestion to expand date range if no matches found and user has auto-expand enabled
            if (detected.transfers.length === 0 && autoExpandSuggestion) {
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

            const result = await bulkMarkTransfers(selectedPairs);

            if (result.successCount > 0) {
                // Reload paired transfers to show the newly marked ones
                const updatedTransfers = await listPairedTransfers({
                    startDate: currentDateRange.startDate.getTime(),
                    endDate: currentDateRange.endDate.getTime()
                })();
                setPairedTransfers(updatedTransfers.pairedTransfers);

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
            {/* Enhanced Header with Quick Stats */}
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
                            <span className="stat-value">🔄 {pairedTransfers.length}</span>
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
            </div>

            {error && (
                <Alert variant="error" dismissible onDismiss={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Enhanced Progress Dashboard */}
            <TransferProgressDashboard
                progress={transferProgress}
                recommendedRange={recommendedRange}
                loading={progressLoading || recalculateLoading}
                onUseRecommendedRange={(range) => {
                    setCurrentDateRange(range);
                    handleDateRangePickerChange(range);
                }}
                onRecalculateFromScratch={handleRecalculateFromScratch}
                onContinueSystematic={handleSystematicScan}
                totalConfirmedPairs={pairedTransfers.length}
                lastScanDate={scanningStats.lastScanDate}
            />

            {/* Enhanced Scan Controls */}
            <ScanControlsPanel
                currentDateRange={currentDateRange}
                onDateRangeChange={handleDateRangePickerChange}
                onScanTransfers={handleDetectTransfers}
                onSmartScan={handleSmartScan}
                onSystematicScan={handleSystematicScan}
                loading={detectLoading}
            />

            {/* Enhanced Results Dashboard */}
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
            />

            {/* Analytics Dashboard */}
            <TransferAnalyticsDashboard
                confirmedTransfers={pairedTransfers}
                accounts={accounts}
                scanningStats={scanningStats}
            />

            {/* Legacy Date Range Suggestion (keep for backward compatibility) */}
            {showDateRangeSuggestion && (
                <div className="date-range-suggestion">
                    <div className="suggestion-content">
                        <h4>No transfers found in current date range</h4>
                        <p>Try expanding the date range to find more potential matches:</p>
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
