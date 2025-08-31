import React, { useState, useEffect } from 'react';
import {
    listPairedTransfers,
    detectPotentialTransfers,
    bulkMarkTransfers,
    TransferPair,
    getTransferCheckingProgress,
    getRecommendedTransferDateRange
} from '@/services/TransferService';
import { getAccounts } from '@/services/TransactionService';
import { AccountInfo } from '@/schemas/Transaction';
import CurrencyDisplay from '@/new-ui/components/ui/CurrencyDisplay';
import DateRangePicker, { DateRange } from '@/new-ui/components/ui/DateRangePicker';
import './TransfersTab.css';

interface TransfersTabProps { }

const TransfersTab: React.FC<TransfersTabProps> = () => {
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

    // Date range management - default to last 7 days
    const [currentDateRange, setCurrentDateRange] = useState<DateRange>(() => {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - 7);
        return { startDate, endDate };
    });

    // Simple auto-expand suggestion state
    const [autoExpandSuggestion] = useState(true);

    // Load initial data
    useEffect(() => {
        loadInitialData();
        loadTransferProgress();
    }, []);

    const loadTransferProgress = async () => {
        setProgressLoading(true);
        try {
            const [progress, recommended] = await Promise.all([
                getTransferCheckingProgress(),
                getRecommendedTransferDateRange()
            ]);
            setTransferProgress(progress);
            setRecommendedRange(recommended);
        } catch (err) {
            console.warn('Failed to load transfer progress:', err);
        } finally {
            setProgressLoading(false);
        }
    };

    const loadInitialData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [transfersData, accountsData] = await Promise.all([
                listPairedTransfers({
                    startDate: currentDateRange.startDate.getTime().toString(),
                    endDate: currentDateRange.endDate.getTime().toString()
                })(),
                getAccounts()
            ]);
            setPairedTransfers(transfersData.pairedTransfers);
            setAccounts(accountsData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load transfer data');
        } finally {
            setLoading(false);
        }
    };

    const handleDetectTransfers = async () => {
        setDetectLoading(true);
        setError(null);
        setShowDateRangeSuggestion(false);
        try {
            // Use date range API
            const detected = await detectPotentialTransfers(
                currentDateRange.startDate.toISOString().split('T')[0],
                currentDateRange.endDate.toISOString().split('T')[0]
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
                .filter((_, index) => selectedDetectedTransfers.has(index.toString()))
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
                    startDate: currentDateRange.startDate.getTime().toString(),
                    endDate: currentDateRange.endDate.getTime().toString()
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
                setSelectedDetectedTransfers(new Set());
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

    const formatDate = (timestamp: number): string => {
        return new Date(timestamp).toLocaleDateString();
    };

    const formatDateRange = (startMs: number | null, endMs: number | null): string => {
        if (!startMs || !endMs) return 'No data available';
        const start = new Date(startMs).toLocaleDateString();
        const end = new Date(endMs).toLocaleDateString();
        return `${start} - ${end}`;
    };

    const formatProgressPercentage = (percentage: number): string => {
        return `${Math.round(percentage)}%`;
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
                newRange.startDate.toISOString().split('T')[0],
                newRange.endDate.toISOString().split('T')[0]
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
                startDate: newRange.startDate.getTime().toString(),
                endDate: newRange.endDate.getTime().toString()
            })();
            setPairedTransfers(updatedTransfers.pairedTransfers);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to reload transfers with new date range');
        } finally {
            setLoading(false);
        }
    };

    const toggleDetectedTransfer = (index: string) => {
        const newSelected = new Set(selectedDetectedTransfers);
        if (newSelected.has(index)) {
            newSelected.delete(index);
        } else {
            newSelected.add(index);
        }
        setSelectedDetectedTransfers(newSelected);
    };

    const selectAllDetected = () => {
        if (selectedDetectedTransfers.size === detectedTransfers.length) {
            setSelectedDetectedTransfers(new Set());
        } else {
            setSelectedDetectedTransfers(new Set(detectedTransfers.map((_, index) => index.toString())));
        }
    };

    if (loading) {
        return <div className="transfers-tab-loading">Loading transfer data...</div>;
    }

    return (
        <div className="transfers-tab">
            <div className="transfers-tab-header">
                <h2>Inter-Account Transfers</h2>
                <p>Manage transfers between your accounts</p>
            </div>

            {error && (
                <div className="transfers-tab-error">
                    {error}
                </div>
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
                                {pairedTransfers.map((pair, index) => (
                                    <tr key={index}>
                                        <td>{getAccountName(pair.outgoingTransaction.accountId)}</td>
                                        <td>{formatDate(pair.outgoingTransaction.date)}</td>
                                        <td>
                                            <CurrencyDisplay
                                                amount={Math.abs(Number(pair.outgoingTransaction.amount))}
                                                currency={pair.outgoingTransaction.currency || 'USD'}
                                                className="currency-negative"
                                            />
                                        </td>
                                        <td>{getAccountName(pair.incomingTransaction.accountId)}</td>
                                        <td>{formatDate(pair.incomingTransaction.date)}</td>
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
                            <div className="date-range-loading">Loading date range information...</div>
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
                                                <div className="progress-indicator">
                                                    <div className="progress-bar">
                                                        <div
                                                            className="progress-fill"
                                                            style={{ width: `${transferProgress.progressPercentage || 0}%` }}
                                                        ></div>
                                                    </div>
                                                    <span className="progress-text">
                                                        {formatProgressPercentage(transferProgress.progressPercentage || 0)} complete
                                                    </span>
                                                </div>
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
                                            <button
                                                onClick={() => {
                                                    const newRange = {
                                                        startDate: new Date(recommendedRange.startDate),
                                                        endDate: new Date(recommendedRange.endDate)
                                                    };
                                                    setCurrentDateRange(newRange);
                                                    handleDateRangePickerChange(newRange);
                                                }}
                                                className="use-suggested-range-button"
                                                disabled={detectLoading}
                                            >
                                                Use This Range
                                            </button>
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
                        <button
                            onClick={handleDetectTransfers}
                            disabled={detectLoading}
                            className="detect-button"
                        >
                            {detectLoading ? 'Detecting...' : 'Scan for Transfers'}
                        </button>
                    </div>
                </div>

                {detectedTransfers.length > 0 && (
                    <div className="detected-transfers">
                        <div className="detected-transfers-header">
                            <h4>Potential Transfer Matches ({detectedTransfers.length})</h4>
                            <div className="bulk-actions">
                                <button
                                    onClick={selectAllDetected}
                                    className="select-all-button"
                                >
                                    {selectedDetectedTransfers.size === detectedTransfers.length ? 'Deselect All' : 'Select All'}
                                </button>
                                <button
                                    onClick={handleBulkMarkTransfers}
                                    disabled={bulkMarkLoading || selectedDetectedTransfers.size === 0}
                                    className="bulk-mark-button"
                                >
                                    {bulkMarkLoading ? 'Marking...' : `Mark ${selectedDetectedTransfers.size} as Transfers`}
                                </button>
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
                                    {detectedTransfers.map((pair, index) => (
                                        <tr key={index} className={selectedDetectedTransfers.has(index.toString()) ? 'selected' : ''}>
                                            <td>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedDetectedTransfers.has(index.toString())}
                                                    onChange={() => toggleDetectedTransfer(index.toString())}
                                                />
                                            </td>
                                            <td>{getAccountName(pair.outgoingTransaction.accountId)}</td>
                                            <td>{formatDate(pair.outgoingTransaction.date)}</td>
                                            <td>
                                                <CurrencyDisplay
                                                    amount={Math.abs(Number(pair.outgoingTransaction.amount))}
                                                    currency={pair.outgoingTransaction.currency || 'USD'}
                                                    className="currency-negative"
                                                />
                                            </td>
                                            <td>{getAccountName(pair.incomingTransaction.accountId)}</td>
                                            <td>{formatDate(pair.incomingTransaction.date)}</td>
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
                                <button
                                    onClick={() => handleExpandDateRange(14)}
                                    className="suggestion-button"
                                    disabled={detectLoading}
                                >
                                    Scan Last 2 Weeks
                                </button>
                                <button
                                    onClick={() => handleExpandDateRange(30)}
                                    className="suggestion-button"
                                    disabled={detectLoading}
                                >
                                    Scan Last Month
                                </button>
                                <button
                                    onClick={() => setShowDateRangeSuggestion(false)}
                                    className="suggestion-button secondary"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
};

export default TransfersTab;
