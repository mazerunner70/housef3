import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    listPairedTransfers,
    detectPotentialTransfers,
    bulkMarkTransfers,
    TransferPair,
    getTransferProgressAndRecommendation
} from '@/services/TransferService';
import { getAccounts } from '@/services/TransactionService';
import { AccountInfo } from '@/schemas/Transaction';
import {
    CurrencyDisplay,
    DateRangePicker,
    DateCell,
    ProgressBar,
    Alert,
    LoadingState
} from '@/new-ui/components/ui';
import Button from '@/new-ui/components/Button';
import { DateRange } from '@/new-ui/components/ui/DateRangePicker';

import { useLocale } from '@/new-ui/hooks/useLocale';
import './TransfersTab.css';

// Helper function to generate unique keys for transfer pairs
const getTransferPairKey = (pair: TransferPair): string => {
    const outgoingId = pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id;
    const incomingId = pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id;
    return `${outgoingId}-${incomingId}`;
};

interface TransfersTabProps { }

const TransfersTab: React.FC<TransfersTabProps> = () => {
    const { localeConfig, formatDate } = useLocale();
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

            // Refresh progress after detection
            loadTransferProgress();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to detect transfers');
        } finally {
            setDetectLoading(false);
        }
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

    const getAccountName = (accountId: string | undefined): string => {
        if (!accountId) return 'Unknown Account';
        const account = accounts.find(acc => acc.accountId === accountId);
        return account ? (account.name as string) : `Account ${accountId}`;
    };



    const formatDateRange = (startMs: number | null, endMs: number | null): string => {
        if (!startMs || !endMs) return 'No data available';
        const start = formatDate(startMs, {
            year: 'numeric',
            month: 'numeric',
            day: 'numeric'
        });
        const end = formatDate(endMs, {
            year: 'numeric',
            month: 'numeric',
            day: 'numeric'
        });
        return `${start} - ${end}`;
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
        <div className="transfers-tab">
            <div className="transfers-tab-header">
                <h2>Inter-Account Transfers</h2>
                <p>Manage transfers between your accounts</p>
            </div>

            {error && (
                <Alert variant="error" dismissible onDismiss={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Existing Paired Transfers Section */}
            <section className="transfers-section">
                <h3>Existing Transfer Pairs ({pairedTransfers.length})</h3>
                {pairedTransfers.length === 0 ? (
                    <div className="transfers-empty-state">
                        No transfer pairs found. Use the detection feature below to find potential transfers.
                    </div>
                ) : (
                    <div className="transfers-table-container">
                        <table className="transfers-table">
                            <thead>
                                <tr>
                                    <th>Source Account</th>
                                    <th>Date</th>
                                    <th>Source Amount</th>
                                    <th>Target Account</th>
                                    <th>Date</th>
                                    <th>Target Amount</th>
                                    <th>Days Apart</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pairedTransfers.map((pair) => (
                                    <tr key={getTransferPairKey(pair)}>
                                        <td>{getAccountName(pair.outgoingTransaction.accountId || undefined)}</td>
                                        <td><DateCell date={pair.outgoingTransaction.date} format="short" locale={localeConfig.locale} /></td>
                                        <td>
                                            <CurrencyDisplay
                                                amount={Math.abs(Number(pair.outgoingTransaction.amount))}
                                                currency={pair.outgoingTransaction.currency || 'USD'}
                                                className="currency-negative"
                                            />
                                        </td>
                                        <td>{getAccountName(pair.incomingTransaction.accountId || undefined)}</td>
                                        <td><DateCell date={pair.incomingTransaction.date} format="short" locale={localeConfig.locale} /></td>
                                        <td>
                                            <CurrencyDisplay
                                                amount={Number(pair.incomingTransaction.amount)}
                                                currency={pair.incomingTransaction.currency || 'USD'}
                                                className="currency-positive"
                                            />
                                        </td>
                                        <td>{pair.dateDifference}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

            {/* Transfer Detection Section */}
            <section className="transfers-section">
                <div className="transfers-detection-header">
                    <h3>Detect New Transfers</h3>

                    {/* Date Range Information Panel */}
                    <div className="date-range-info-panel">
                        {progressLoading ? (
                            <LoadingState message="Loading date range information..." size="small" />
                        ) : (
                            <>
                                {/* Overall Account Date Range */}
                                <div className="date-range-info-section">
                                    <h4>Account Data Range</h4>
                                    <div className="date-range-display">
                                        {transferProgress?.accountDateRange ? (
                                            <span className="date-range-text">
                                                {formatDateRange(
                                                    transferProgress.accountDateRange.startDate,
                                                    transferProgress.accountDateRange.endDate
                                                )}
                                            </span>
                                        ) : (
                                            <span className="date-range-text no-data">No transaction data available</span>
                                        )}
                                    </div>
                                </div>

                                {/* Checked Date Range */}
                                <div className="date-range-info-section">
                                    <h4>Checked So Far</h4>
                                    <div className="date-range-display">
                                        {transferProgress?.checkedDateRange?.startDate && transferProgress?.checkedDateRange?.endDate ? (
                                            <>
                                                <span className="date-range-text">
                                                    {formatDateRange(
                                                        transferProgress.checkedDateRange.startDate,
                                                        transferProgress.checkedDateRange.endDate
                                                    )}
                                                </span>
                                                <ProgressBar
                                                    percentage={transferProgress.progressPercentage || 0}
                                                    size="small"
                                                />
                                            </>
                                        ) : (
                                            <span className="date-range-text no-data">No transfers checked yet</span>
                                        )}
                                    </div>
                                </div>

                                {/* Recommended Next Range */}
                                {recommendedRange && (
                                    <div className="date-range-info-section recommended">
                                        <h4>Suggested Next Range</h4>
                                        <div className="date-range-display">
                                            <span className="date-range-text recommended-text">
                                                {formatDateRange(
                                                    new Date(recommendedRange.startDate).getTime(),
                                                    new Date(recommendedRange.endDate).getTime()
                                                )}
                                            </span>
                                            <Button
                                                variant="secondary"
                                                size="compact"
                                                onClick={() => {
                                                    const newRange = {
                                                        startDate: new Date(recommendedRange.startDate),
                                                        endDate: new Date(recommendedRange.endDate)
                                                    };
                                                    setCurrentDateRange(newRange);
                                                    handleDateRangePickerChange(newRange);
                                                }}
                                                disabled={detectLoading}
                                            >
                                                Use This Range
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    <div className="transfers-detection-controls">
                        <div className="date-range-section">
                            <DateRangePicker
                                value={currentDateRange}
                                onChange={handleDateRangePickerChange}
                                quickRangeOptions={[
                                    { label: '7 days', days: 7 },
                                    { label: '14 days', days: 14 },
                                    { label: '30 days', days: 30 },
                                    { label: '90 days', days: 90 }
                                ]}
                                className="transfers-date-picker"
                            />
                        </div>
                        <Button
                            variant="primary"
                            onClick={handleDetectTransfers}
                            disabled={detectLoading}
                        >
                            {detectLoading ? 'Detecting...' : 'Scan for Transfers'}
                        </Button>
                    </div>
                </div>

                {detectedTransfers.length > 0 && (
                    <div className="detected-transfers">
                        <div className="detected-transfers-header">
                            <h4>Potential Transfer Matches ({detectedTransfers.length})</h4>
                            <div className="bulk-actions">
                                <Button
                                    variant="secondary"
                                    size="compact"
                                    onClick={selectAllDetected}
                                >
                                    {selectedDetectedTransfers.size === detectedTransfers.length ? 'Deselect All' : 'Select All'}
                                </Button>
                                <Button
                                    variant="primary"
                                    onClick={handleBulkMarkTransfers}
                                    disabled={bulkMarkLoading || selectedDetectedTransfers.size === 0}
                                >
                                    {bulkMarkLoading ? 'Marking...' : `Mark ${selectedDetectedTransfers.size} as Transfers`}
                                </Button>
                            </div>
                        </div>

                        <div className="transfers-table-container">
                            <table className="transfers-table detected-table">
                                <thead>
                                    <tr>
                                        <th>
                                            <input
                                                type="checkbox"
                                                checked={selectedDetectedTransfers.size === detectedTransfers.length && detectedTransfers.length > 0}
                                                onChange={selectAllDetected}
                                            />
                                        </th>
                                        <th>Source Account</th>
                                        <th>Date</th>
                                        <th>Source Amount</th>
                                        <th>Target Account</th>
                                        <th>Date</th>
                                        <th>Target Amount</th>
                                        <th>Days Apart</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {detectedTransfers.map((pair) => {
                                        const pairKey = getTransferPairKey(pair);
                                        return (
                                            <tr key={pairKey} className={selectedDetectedTransfers.has(pairKey) ? 'selected' : ''}>
                                                <td>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedDetectedTransfers.has(pairKey)}
                                                        onChange={() => toggleDetectedTransfer(pairKey)}
                                                    />
                                                </td>
                                                <td>{getAccountName(pair.outgoingTransaction.accountId || undefined)}</td>
                                                <td><DateCell date={pair.outgoingTransaction.date} format="short" locale={localeConfig.locale} /></td>
                                                <td>
                                                    <CurrencyDisplay
                                                        amount={Math.abs(Number(pair.outgoingTransaction.amount))}
                                                        currency={pair.outgoingTransaction.currency || 'USD'}
                                                        className="currency-negative"
                                                    />
                                                </td>
                                                <td>{getAccountName(pair.incomingTransaction.accountId || undefined)}</td>
                                                <td><DateCell date={pair.incomingTransaction.date} format="short" locale={localeConfig.locale} /></td>
                                                <td>
                                                    <CurrencyDisplay
                                                        amount={Number(pair.incomingTransaction.amount)}
                                                        currency={pair.incomingTransaction.currency || 'USD'}
                                                        className="currency-positive"
                                                    />
                                                </td>
                                                <td>{pair.dateDifference}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {detectedTransfers.length === 0 && !detectLoading && !showDateRangeSuggestion && (
                    <div className="no-detected-transfers">
                        Click "Scan for Transfers" to detect potential transfer pairs.
                    </div>
                )}

                {showDateRangeSuggestion && (
                    <div className="date-range-suggestion">
                        <div className="suggestion-content">
                            <h4>No transfers found in current date range</h4>
                            <p>Try expanding the date range to find more potential matches:</p>
                            <div className="suggestion-buttons">
                                <Button
                                    variant="secondary"
                                    onClick={() => handleExpandDateRange(14)}
                                    disabled={detectLoading}
                                >
                                    Scan Last 2 Weeks
                                </Button>
                                <Button
                                    variant="secondary"
                                    onClick={() => handleExpandDateRange(30)}
                                    disabled={detectLoading}
                                >
                                    Scan Last Month
                                </Button>
                                <Button
                                    variant="tertiary"
                                    onClick={() => setShowDateRangeSuggestion(false)}
                                >
                                    Cancel
                                </Button>
                            </div>
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
};

export default TransfersTab;
