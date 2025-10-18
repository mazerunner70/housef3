import React, { useState, useEffect, useCallback } from 'react';
import {
    getTotalPairedTransfersCount,
    detectPotentialTransfers,
    bulkMarkTransfers,
    TransferPair,
    getTransferProgressAndRecommendation
} from '@/services/TransferService';
import { getAccounts } from '@/services/TransactionService';
import { updateTransferPreferences } from '@/services/UserPreferencesService';
import { AccountInfo } from '@/schemas/Transaction';
import {
    Alert,
    LoadingState
} from '@/components/ui';
import Button from '@/components/Button';
import CurrencyDisplay from '@/components/ui/CurrencyDisplay';
import DateCell from '@/components/ui/DateCell';

import { useLocale } from '@/hooks/useLocale';
import { useNavigationStore } from '@/stores/navigationStore';
import './TransfersDashboard.css';

// Helper function to generate unique keys for transfer pairs
const getTransferPairKey = (pair: TransferPair): string => {
    const outgoingId = pair.outgoingTransaction.transactionId || (pair.outgoingTransaction as any).id;
    const incomingId = pair.incomingTransaction.transactionId || (pair.incomingTransaction as any).id;
    return `${outgoingId}-${incomingId}`;
};

// Removed isEpochDate - no longer needed with simplified date range approach

// Removed isValidCheckedDateRange - no longer needed with simplified date range approach

interface TransfersDashboardProps { }

const TransfersDashboard: React.FC<TransfersDashboardProps> = () => {
    const { formatDate } = useLocale();
    const { urlContext, updateUrlContext } = useNavigationStore();
    const [detectedTransfers, setDetectedTransfers] = useState<TransferPair[]>([]);
    const [totalPairedTransfersCount, setTotalPairedTransfersCount] = useState<number>(0);
    const [accounts, setAccounts] = useState<AccountInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [detectLoading, setDetectLoading] = useState(false);
    const [bulkMarkLoading, setBulkMarkLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedDetectedTransfers, setSelectedDetectedTransfers] = useState<Set<string>>(new Set());
    const [ignoredTransfers, setIgnoredTransfers] = useState<Set<string>>(new Set());
    const [hadTransfersToProcess, setHadTransfersToProcess] = useState(false);

    // Transfer progress and date range tracking
    const [transferProgress, setTransferProgress] = useState<any>(null);
    const [recommendedRange, setRecommendedRange] = useState<any>(null);

    // Date range management - will be set from preferences in loadAllInitialData
    // Removed currentDateRange - now only use recommendedRange and checked range from backend


    // Load initial data
    useEffect(() => {
        loadAllInitialData();
    }, []);

    // Auto-scan if URL parameter is present
    useEffect(() => {
        const autoScan = urlContext.autoScan;
        if (autoScan === 'true' && !detectLoading && !loading) {
            // Clear the autoScan parameter to prevent repeated scans
            updateUrlContext({ autoScan: undefined });

            // Trigger scan after a short delay to ensure data is loaded
            const timer: NodeJS.Timeout = setTimeout(() => {
                handleDetectTransfers();
            }, 500);

            // Cleanup function to clear timeout if component unmounts or dependencies change
            return () => {
                clearTimeout(timer);
            };
        }
    }, [urlContext.autoScan, detectLoading, loading]);


    // Removed URL and preference date range functions - scanning now only uses recommendedRange from the intelligent algorithm

    // Removed getFallbackDateRange - no fallback needed, use only recommendedRange

    const loadAllInitialData = async () => {
        setLoading(true);
        setError(null);
        try {
            // First load progress to get checked range
            const progressAndRecommendation = await getTransferProgressAndRecommendation();
            setTransferProgress(progressAndRecommendation.progress);
            setRecommendedRange(progressAndRecommendation.recommendedRange);

            // Note: Scanning always uses recommendedRange from the intelligent algorithm
            // URL params and preferences are only used for specific user-requested ranges

            // Load remaining data in parallel
            const [totalCount, accountsData] = await Promise.all([
                getTotalPairedTransfersCount()(),
                getAccounts()
            ]);

            setTotalPairedTransfersCount(totalCount);
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
        try {
            // Only scan if we have a recommended range from the algorithm
            // No fallback - if no recommendation, all data has been processed
            if (!recommendedRange) {
                setError('No more date ranges to scan. All available data has been processed.');
                return;
            }

            const scanRange = {
                startDate: recommendedRange.startDate,
                endDate: recommendedRange.endDate
            };

            // Use date range API with DateRange object
            const detected = await detectPotentialTransfers({
                startDate: new Date(scanRange.startDate),
                endDate: new Date(scanRange.endDate)
            })();
            setDetectedTransfers(detected.transfers);

            // Smart pre-selection: Auto-select high-confidence matches (dateDifference <= 1)
            const highConfidencePairs = detected.transfers
                .filter(pair => pair.dateDifference <= 1)
                .map(pair => getTransferPairKey(pair));
            setSelectedDetectedTransfers(new Set(highConfidencePairs));

            // Clear ignored transfers when new detection is run
            setIgnoredTransfers(new Set());
            // Track if we had transfers to process
            setHadTransfersToProcess(detected.transfers.length > 0);

            // No need to update any state - the scanned range is already tracked in recommendedRange

            // If no candidates were found, immediately complete the review cycle
            // to update the checked range via API and auto-load the next chunk
            if (detected.transfers.length === 0) {
                await completeReviewCycle();
                return;
            }

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to detect transfers');
        } finally {
            setDetectLoading(false);
        }
    };

    const handleBulkIgnoreTransfers = () => {
        if (selectedDetectedTransfers.size === 0) {
            setError('Please select at least one transfer pair to ignore');
            return;
        }

        // Add selected transfers to ignored set
        setIgnoredTransfers(prev => {
            const newIgnored = new Set(prev);
            selectedDetectedTransfers.forEach(pairKey => newIgnored.add(pairKey));
            return newIgnored;
        });

        // Clear selection
        setSelectedDetectedTransfers(new Set());

        // Clear any existing error
        setError(null);

        // Check if all candidates processed - if so, complete review cycle
        // Use setTimeout to ensure state updates are processed first
        setTimeout(async () => {
            if (areAllTransfersProcessed()) {
                await completeReviewCycle();
            }
        }, 0);
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

            // Mark transfers
            const result = await bulkMarkTransfers(selectedPairs);

            if (result.successCount > 0) {
                // Optimistic update: increment total count locally
                setTotalPairedTransfersCount(prev => prev + result.successCount);

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

                // Remove from selection
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

            // Check if all candidates processed - if so, complete review cycle
            // Use setTimeout to ensure state updates are processed first
            setTimeout(async () => {
                if (areAllTransfersProcessed()) {
                    await completeReviewCycle();
                }
            }, 0);
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

    /**
     * Check if all detected transfers have been processed (marked or ignored)
     * This should be called when we have processed some transfers and want to check
     * if there are any remaining unprocessed transfers
     */
    const areAllTransfersProcessed = (): boolean => {
        // Only consider it "all processed" if we had transfers to process initially
        if (!hadTransfersToProcess) {
            return false;
        }

        // Check if all remaining detected transfers are ignored
        const remainingUnprocessed = detectedTransfers.filter(transfer => {
            const pairKey = getTransferPairKey(transfer);
            return !ignoredTransfers.has(pairKey);
        });

        // All transfers are processed if there are no remaining unprocessed transfers
        return remainingUnprocessed.length === 0;
    };

    /**
     * Helper: Calculate number of days checked
     */
    const calculateCheckedDays = (checkedRange: any, accountRange: any): number => {
        if (!accountRange?.startDate || !accountRange?.endDate) return 0;
        if (!checkedRange?.checkedDateRangeStart || !checkedRange?.checkedDateRangeEnd) return 0;

        const checkedStart = new Date(Math.max(checkedRange.checkedDateRangeStart, accountRange.startDate));
        const checkedEnd = new Date(Math.min(checkedRange.checkedDateRangeEnd, accountRange.endDate));

        return Math.max(0, Math.ceil((checkedEnd.getTime() - checkedStart.getTime()) / (1000 * 60 * 60 * 24)));
    };

    /**
     * Helper: Calculate progress percentage
     */
    const calculateProgressPercentage = (checkedRange: any, accountRange: any): number => {
        if (!accountRange?.startDate || !accountRange?.endDate) return 0;

        const totalDays = Math.ceil((accountRange.endDate - accountRange.startDate) / (1000 * 60 * 60 * 24));
        if (totalDays === 0) return 0;

        const checkedDays = calculateCheckedDays(checkedRange, accountRange);
        return Math.round((checkedDays / totalDays) * 100);
    };

    /**
     * Complete the review cycle and advance to next chunk
     * This is called when all candidates in current range have been processed
     * Updates checked range and loads next chunk
     */
    const completeReviewCycle = useCallback(async () => {
        try {
            // Only complete review cycle if we have a recommended range that was scanned
            if (!recommendedRange) {
                console.log('No recommended range to complete - all data processed');
                return;
            }

            console.log('Completing review cycle for range:', {
                start: new Date(recommendedRange.startDate).toISOString().split('T')[0],
                end: new Date(recommendedRange.endDate).toISOString().split('T')[0]
            });

            // 1. Update checked range to include the range that was just scanned
            const scannedStartMs = recommendedRange.startDate;
            const scannedEndMs = recommendedRange.endDate;

            // Validate scanned date range
            if (scannedStartMs === scannedEndMs) {
                console.error('BUG DETECTED: scanned range has same start and end timestamp:', {
                    startMs: scannedStartMs,
                    endMs: scannedEndMs,
                    startDate: new Date(scannedStartMs).toISOString(),
                    endDate: new Date(scannedEndMs).toISOString()
                });
                // Don't update preferences with invalid range
                return;
            }

            const updateData = {
                checkedDateRangeStart: transferProgress?.checkedDateRange?.startDate
                    ? Math.min(transferProgress.checkedDateRange.startDate, scannedStartMs)
                    : scannedStartMs,
                checkedDateRangeEnd: transferProgress?.checkedDateRange?.endDate
                    ? Math.max(transferProgress.checkedDateRange.endDate, scannedEndMs)
                    : scannedEndMs
            };

            await updateTransferPreferences(updateData);

            // 2. Update local progress state
            setTransferProgress((prev: any) => {
                if (!prev) return prev;
                return {
                    ...prev,
                    checkedDateRange: {
                        startDate: updateData.checkedDateRangeStart,
                        endDate: updateData.checkedDateRangeEnd
                    },
                    totalDaysChecked: calculateCheckedDays(updateData, prev.accountDateRange),
                    progressPercentage: calculateProgressPercentage(updateData, prev.accountDateRange)
                };
            });

            // 3. Load recommended range for next chunk
            const progressAndRecommendation = await getTransferProgressAndRecommendation();
            setTransferProgress(progressAndRecommendation.progress);
            setRecommendedRange(progressAndRecommendation.recommendedRange);

            // 4. If there's a next range, auto-scan it
            if (progressAndRecommendation.recommendedRange) {
                // Auto-scan next chunk
                const nextChunk = await detectPotentialTransfers({
                    startDate: new Date(progressAndRecommendation.recommendedRange.startDate),
                    endDate: new Date(progressAndRecommendation.recommendedRange.endDate)
                })();

                setDetectedTransfers(nextChunk.transfers);
                setIgnoredTransfers(new Set());
                setSelectedDetectedTransfers(new Set());
                setHadTransfersToProcess(nextChunk.transfers.length > 0);

                console.log('Review cycle completed, moved to next chunk:', {
                    nextRange: `${new Date(progressAndRecommendation.recommendedRange.startDate).toISOString().split('T')[0]} to ${new Date(progressAndRecommendation.recommendedRange.endDate).toISOString().split('T')[0]}`,
                    candidatesFound: nextChunk.transfers.length
                });
            } else {
                // No more chunks to process
                setDetectedTransfers([]);
                setIgnoredTransfers(new Set());
                setSelectedDetectedTransfers(new Set());
                setHadTransfersToProcess(false);

                console.log('Review cycle completed, no more chunks to process');
            }
        } catch (error) {
            console.error('Failed to complete review cycle:', error);
            setError(error instanceof Error ? error.message : 'Failed to complete review cycle');
        }
    }, [recommendedRange, transferProgress]);

    // Watch for completion of transfer processing
    useEffect(() => {
        // Check completion status directly without intermediate function call
        // Only consider it "all processed" if we had transfers to process initially
        if (!hadTransfersToProcess) {
            return;
        }

        // Check if all remaining detected transfers are ignored
        const remainingUnprocessed = detectedTransfers.filter(transfer => {
            const pairKey = getTransferPairKey(transfer);
            return !ignoredTransfers.has(pairKey);
        });

        // All transfers are processed if there are no remaining unprocessed transfers
        const allProcessed = remainingUnprocessed.length === 0;

        if (allProcessed) {
            const processCompletion = async () => {
                await completeReviewCycle();
                // Reset the flag after processing
                setHadTransfersToProcess(false);
            };
            processCompletion();
        }
    }, [detectedTransfers, ignoredTransfers, hadTransfersToProcess, completeReviewCycle]);


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
        // Only work with visible (non-ignored) transfers
        const visibleTransfers = detectedTransfers.filter(pair => !ignoredTransfers.has(getTransferPairKey(pair)));
        const visibleKeys = visibleTransfers.map(pair => getTransferPairKey(pair));

        if (selectedDetectedTransfers.size === visibleKeys.length) {
            setSelectedDetectedTransfers(new Set());
        } else {
            setSelectedDetectedTransfers(new Set(visibleKeys));
        }
    };

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Only handle when we have visible transfers
            const visibleTransfers = detectedTransfers.filter(pair => !ignoredTransfers.has(getTransferPairKey(pair)));
            if (visibleTransfers.length === 0) return;

            // Don't trigger if user is typing in an input
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
                return;
            }

            if (e.key === 'Enter' && selectedDetectedTransfers.size > 0) {
                e.preventDefault();
                handleBulkMarkTransfers();
            } else if (e.key === 'Backspace' && selectedDetectedTransfers.size > 0) {
                e.preventDefault();
                handleBulkIgnoreTransfers();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [detectedTransfers, ignoredTransfers, selectedDetectedTransfers, handleBulkMarkTransfers, handleBulkIgnoreTransfers]);

    if (loading) {
        return <LoadingState message="Loading transfer data..." />;
    }

    // Calculate visible transfers (non-ignored)
    const visibleDetectedTransfers = detectedTransfers.filter(pair => !ignoredTransfers.has(getTransferPairKey(pair)));

    return (
        <div className="transfers-dashboard-compact">
            {/* Compact Header with Mini Progress */}
            <div className="compact-header">
                <div className="progress-section">
                    <span className="chunk-indicator">Chunk {transferProgress?.progressPercentage || 0}%</span>
                    <div className="progress-bar-mini">
                        <div
                            className="progress-fill"
                            style={{ width: `${transferProgress?.progressPercentage || 0}%` }}
                        ></div>
                    </div>
                    <span className="quick-stats">
                        {totalPairedTransfersCount} pairs | {accounts.length} accounts
                    </span>
                </div>
            </div>

            {error && (
                <Alert variant="error" dismissible onDismiss={() => setError(null)}>
                    {error}
                </Alert>
            )}

            {/* Compact Single-Screen Review */}
            <div className="review-container">
                {/* Current Range & Scan Button */}
                <div className="scan-section">
                    <div className="range-display">
                        <span className="range-label">Scanning:</span>
                        <span className="range-dates">
                            {recommendedRange ? (
                                `${formatDate(recommendedRange.startDate, { month: 'short', day: 'numeric' })} - ${formatDate(recommendedRange.endDate, { month: 'short', day: 'numeric', year: 'numeric' })}`
                            ) : (
                                '✅ All data processed'
                            )}
                        </span>
                    </div>
                    <Button
                        variant="primary"
                        onClick={handleDetectTransfers}
                        disabled={detectLoading || visibleDetectedTransfers.length > 0 || !recommendedRange}
                        className="scan-button-compact"
                    >
                        {(() => {
                            if (detectLoading) return '⚡ Scanning...';
                            if (visibleDetectedTransfers.length > 0) return '⏸️ Review Pending';
                            if (!recommendedRange) return '✅ Complete';
                            return '🎯 Scan Next Chunk';
                        })()}
                    </Button>
                </div>

                {/* Compact Transfer Table */}
                {visibleDetectedTransfers.length > 0 ? (
                    <div className="compact-table-section">
                        <div className="table-header-compact">
                            <span className="candidates-count">{visibleDetectedTransfers.length} candidates pending</span>
                            <button
                                className="select-all-link"
                                onClick={selectAllDetected}
                            >
                                {selectedDetectedTransfers.size === visibleDetectedTransfers.length ? 'Deselect All' : 'Select All'}
                            </button>
                        </div>

                        <div className="transfer-table-compact">
                            {visibleDetectedTransfers.map((pair) => {
                                const pairKey = getTransferPairKey(pair);
                                const isSelected = selectedDetectedTransfers.has(pairKey);
                                const confidence = Math.round(
                                    100 - (pair.dateDifference * 5) // Simple confidence: lower days = higher confidence
                                );
                                let confidenceClass = 'low';
                                if (confidence >= 90) confidenceClass = 'high';
                                else if (confidence >= 70) confidenceClass = 'medium';

                                return (
                                    <label
                                        key={pairKey}
                                        className={`transfer-row-compact ${isSelected ? 'selected' : ''} confidence-${confidenceClass}`}
                                    >
                                        <div className="row-checkbox">
                                            <input
                                                type="checkbox"
                                                checked={isSelected}
                                                onChange={() => toggleDetectedTransfer(pairKey)}
                                            />
                                        </div>
                                        <div className="row-flow">
                                            <span className="account-from">{getAccountName(pair.outgoingTransaction.accountId)}</span>
                                            <span className="flow-arrow">→</span>
                                            <span className="account-to">{getAccountName(pair.incomingTransaction.accountId)}</span>
                                        </div>
                                        <div className="row-amount">
                                            <CurrencyDisplay
                                                amount={Math.abs(Number(pair.amount))}
                                                currency={pair.outgoingTransaction.currency || 'USD'}
                                            />
                                        </div>
                                        <div className="row-date">
                                            <DateCell
                                                date={pair.outgoingTransaction.date}
                                                format="short"
                                                locale="en-GB"
                                            />
                                            {pair.dateDifference > 0 && (
                                                <span className="days-diff">+{pair.dateDifference}d</span>
                                            )}
                                        </div>
                                        <div className={`row-confidence ${confidenceClass}`}>
                                            {(() => {
                                                if (confidence >= 90) return '✓✓';
                                                if (confidence >= 70) return '✓';
                                                return '~';
                                            })()}
                                        </div>
                                    </label>
                                );
                            })}
                        </div>
                    </div>
                ) : (() => {
                    if (detectedTransfers.length > 0) {
                        return (
                            <div className="all-processed-message">
                                ✓ All candidates processed! Auto-advancing...
                            </div>
                        );
                    }
                    if (detectLoading) {
                        return (
                            <div className="scanning-message">
                                ⚡ Scanning for transfer candidates...
                            </div>
                        );
                    }
                    return (
                        <div className="no-candidates-message">
                            No candidates found. Click "Scan Next Chunk" to begin.
                        </div>
                    );
                })()}

                {/* Fixed Action Bar at Bottom */}
                {visibleDetectedTransfers.length > 0 && (
                    <div className="action-bar-fixed">
                        <div className="selection-info">
                            <span className="selected-count">{selectedDetectedTransfers.size}</span>
                            <span className="selected-label">of {visibleDetectedTransfers.length} selected</span>
                        </div>

                        <div className="primary-actions-compact">
                            <Button
                                variant="primary"
                                onClick={handleBulkMarkTransfers}
                                disabled={bulkMarkLoading || selectedDetectedTransfers.size === 0}
                                className="btn-confirm-compact"
                            >
                                ✓ Confirm {selectedDetectedTransfers.size > 0 && `(${selectedDetectedTransfers.size})`}
                            </Button>

                            <Button
                                variant="danger"
                                onClick={handleBulkIgnoreTransfers}
                                disabled={selectedDetectedTransfers.size === 0}
                                className="btn-ignore-compact"
                            >
                                ✗ Ignore {selectedDetectedTransfers.size > 0 && `(${selectedDetectedTransfers.size})`}
                            </Button>
                        </div>

                        <div className="keyboard-hints-compact">
                            <span className="hint">Enter: Confirm | Backspace: Ignore</span>
                        </div>
                    </div>
                )}
            </div>

        </div>
    );
};

export default TransfersDashboard;
