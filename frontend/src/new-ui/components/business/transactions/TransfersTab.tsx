import React, { useState, useEffect } from 'react';
import {
    getPairedTransfers,
    detectTransfers,
    bulkMarkTransfers,
    TransferPair,
    convertDaysToDateRange,
    formatDateForDisplay
} from '@/services/TransferService';
import { getAccounts } from '@/services/TransactionService';
import { AccountInfo } from '@/schemas/Transaction';
import CurrencyDisplay from '@/new-ui/components/ui/CurrencyDisplay';
import DateRangePicker, { DateRange } from '@/new-ui/components/ui/DateRangePicker';
import { useDateRangePreferences } from '@/new-ui/hooks/useTransferPreferences';
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

    // Date range management - use both new date range and legacy support
    const [currentDateRange, setCurrentDateRange] = useState<DateRange>(
        convertDaysToDateRange(7) // Default to 7 days
    );

    // Use preferences hook for legacy support and user preferences
    const {
        currentDateRange: dateRangeDays,
        quickRangeOptions,
        updateDateRange,
        autoExpandSuggestion,
        loading: preferencesLoading,
        error: preferencesError
    } = useDateRangePreferences();

    // Load initial data
    useEffect(() => {
        loadInitialData();
    }, []);

    const loadInitialData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [transfersData, accountsData] = await Promise.all([
                getPairedTransfers(currentDateRange.startDate, currentDateRange.endDate),
                getAccounts()
            ]);
            setPairedTransfers(transfersData);
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
            const detected = await detectTransfers(currentDateRange.startDate, currentDateRange.endDate);
            setDetectedTransfers(detected);
            setSelectedDetectedTransfers(new Set());

            // Calculate days for suggestion logic
            const daysDiff = Math.ceil((currentDateRange.endDate.getTime() - currentDateRange.startDate.getTime()) / (1000 * 60 * 60 * 24));

            // Show suggestion to expand date range if no matches found, current range is small, and user has auto-expand enabled
            if (detected.length === 0 && daysDiff < 30 && autoExpandSuggestion) {
                setShowDateRangeSuggestion(true);
            }
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
                const updatedTransfers = await getPairedTransfers(currentDateRange.startDate, currentDateRange.endDate);
                setPairedTransfers(updatedTransfers);

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

    const handleExpandDateRange = async (newDays: number) => {
        const newRange = convertDaysToDateRange(newDays);
        setCurrentDateRange(newRange);
        await updateDateRange(newDays);
        setShowDateRangeSuggestion(false);
        // Automatically trigger detection with new range
        setDetectLoading(true);
        setError(null);
        try {
            const detected = await detectTransfers(newRange.startDate, newRange.endDate);
            setDetectedTransfers(detected);
            setSelectedDetectedTransfers(new Set());
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to detect transfers');
        } finally {
            setDetectLoading(false);
        }
    };

    const handleDateRangeChange = async (newDays: number) => {
        const newRange = convertDaysToDateRange(newDays);
        setCurrentDateRange(newRange);
        await updateDateRange(newDays);

        // Reload paired transfers with new date range
        try {
            setLoading(true);
            const updatedTransfers = await getPairedTransfers(newRange.startDate, newRange.endDate);
            setPairedTransfers(updatedTransfers);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to reload transfers with new date range');
        } finally {
            setLoading(false);
        }
    };

    const handleDateRangePickerChange = async (newRange: DateRange) => {
        setCurrentDateRange(newRange);
        // Calculate days for legacy support
        const days = Math.ceil((newRange.endDate.getTime() - newRange.startDate.getTime()) / (1000 * 60 * 60 * 24));
        updateDateRange(days);

        // Reload paired transfers with new date range
        try {
            setLoading(true);
            const updatedTransfers = await getPairedTransfers(newRange.startDate, newRange.endDate);
            setPairedTransfers(updatedTransfers);
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

    if (loading || preferencesLoading) {
        return <div className="transfers-tab-loading">Loading transfer data...</div>;
    }

    return (
        <div className="transfers-tab">
            <div className="transfers-tab-header">
                <h2>Inter-Account Transfers</h2>
                <p>Manage transfers between your accounts</p>
            </div>

            {(error || preferencesError) && (
                <div className="transfers-tab-error">
                    {error || preferencesError}
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
                    <div className="transfers-detection-controls">
                        <div className="date-range-section">
                            <DateRangePicker
                                value={currentDateRange}
                                onChange={handleDateRangePickerChange}
                                quickRangeOptions={quickRangeOptions.map((days: number) => ({ label: `${days} days`, days }))}
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
                                    Scan 14 days
                                </button>
                                <button
                                    onClick={() => handleExpandDateRange(30)}
                                    className="suggestion-button"
                                    disabled={detectLoading}
                                >
                                    Scan 30 days
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
