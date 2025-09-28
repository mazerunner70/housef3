import React, { useState } from 'react';
import { TransferPair } from '@/services/TransferService';
import { AccountInfo } from '@/schemas/Transaction';
import {
    CurrencyDisplay,
    DateCell,
    LoadingState,
    Alert
} from '@/new-ui/components/ui';
import Button from '@/new-ui/components/Button';
import { useLocale } from '@/new-ui/hooks/useLocale';
import './TransferResultsDashboard.css';

type ViewMode = 'confirmed' | 'pending' | 'all';
type SortField = 'date' | 'amount' | 'account' | 'confidence';
type SortDirection = 'asc' | 'desc';

interface TransferResultsDashboardProps {
    confirmedTransfers: TransferPair[];
    pendingTransfers: TransferPair[];
    selectedPendingTransfers: Set<string>;
    accounts: AccountInfo[];
    loading: boolean;
    bulkMarkLoading: boolean;
    onTogglePendingTransfer: (pairKey: string) => void;
    onSelectAllPending: () => void;
    onBulkMarkTransfers: () => void;
    onExportTransfers: () => void;
    getTransferPairKey: (pair: TransferPair) => string;
    showSuccessMessage?: boolean;
}

const TransferResultsDashboard: React.FC<TransferResultsDashboardProps> = ({
    confirmedTransfers,
    pendingTransfers,
    selectedPendingTransfers,
    accounts,
    loading,
    bulkMarkLoading,
    onTogglePendingTransfer,
    onSelectAllPending,
    onBulkMarkTransfers,
    onExportTransfers,
    getTransferPairKey,
    showSuccessMessage = false
}) => {
    const { localeConfig } = useLocale();
    const [viewMode, setViewMode] = useState<ViewMode>('pending');
    const [sortField, setSortField] = useState<SortField>('date');
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
    const [searchTerm, setSearchTerm] = useState('');

    const getAccountName = (accountId: string | null | undefined): string => {
        if (!accountId) return 'Unknown Account';
        const account = accounts.find(acc => acc.accountId === accountId);
        return account ? (account.name as string) : `Account ${accountId}`;
    };

    const getConfidenceScore = (pair: TransferPair): number => {
        // Calculate confidence based on amount match and date proximity
        const amountDiff = Math.abs(
            Math.abs(Number(pair.outgoingTransaction.amount)) -
            Math.abs(Number(pair.incomingTransaction.amount))
        );
        const amountScore = Math.max(0, 100 - (amountDiff * 10));
        const dateScore = Math.max(0, 100 - (pair.dateDifference * 10));
        return Math.round((amountScore + dateScore) / 2);
    };

    const getConfidenceColor = (score: number): string => {
        if (score >= 90) return '#10b981'; // Green
        if (score >= 70) return '#f59e0b'; // Yellow
        if (score >= 50) return '#f97316'; // Orange
        return '#ef4444'; // Red
    };

    const sortTransfers = (transfers: TransferPair[]): TransferPair[] => {
        return [...transfers].sort((a, b) => {
            let aValue: any, bValue: any;

            switch (sortField) {
                case 'date':
                    aValue = new Date(a.outgoingTransaction.date).getTime();
                    bValue = new Date(b.outgoingTransaction.date).getTime();
                    break;
                case 'amount':
                    aValue = Math.abs(Number(a.outgoingTransaction.amount));
                    bValue = Math.abs(Number(b.outgoingTransaction.amount));
                    break;
                case 'account':
                    aValue = getAccountName(a.outgoingTransaction.accountId);
                    bValue = getAccountName(b.outgoingTransaction.accountId);
                    break;
                case 'confidence':
                    aValue = getConfidenceScore(a);
                    bValue = getConfidenceScore(b);
                    break;
                default:
                    return 0;
            }

            if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
            if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    };

    const filterTransfers = (transfers: TransferPair[]): TransferPair[] => {
        if (!searchTerm) return transfers;

        const term = searchTerm.toLowerCase();
        return transfers.filter(pair =>
            getAccountName(pair.outgoingTransaction.accountId).toLowerCase().includes(term) ||
            getAccountName(pair.incomingTransaction.accountId).toLowerCase().includes(term) ||
            pair.outgoingTransaction.amount.toString().includes(term) ||
            pair.incomingTransaction.amount.toString().includes(term)
        );
    };

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    const getSortIcon = (field: SortField): string => {
        if (sortField !== field) return '↕️';
        return sortDirection === 'asc' ? '⬆️' : '⬇️';
    };

    const getDisplayTransfers = (): TransferPair[] => {
        let transfers: TransferPair[];
        switch (viewMode) {
            case 'confirmed':
                transfers = confirmedTransfers;
                break;
            case 'pending':
                transfers = pendingTransfers;
                break;
            case 'all':
                transfers = [...confirmedTransfers, ...pendingTransfers];
                break;
        }
        return sortTransfers(filterTransfers(transfers));
    };

    const displayTransfers = getDisplayTransfers();

    if (loading) {
        return <LoadingState message="Loading transfer results..." />;
    }

    return (
        <div className="transfer-results-dashboard">
            <div className="results-header">
                <div className="results-title">
                    <h3>📋 Transfer Detection Results</h3>
                </div>
                <div className="results-actions">
                    <Button
                        variant="secondary"
                        onClick={onExportTransfers}
                        className="export-button"
                    >
                        📤 Export
                    </Button>
                </div>
            </div>

            {/* Success Message for New Detections */}
            {showSuccessMessage && pendingTransfers.length > 0 && (
                <Alert
                    variant="success"
                    title={`🎉 Detected ${pendingTransfers.length} Transfer Candidate${pendingTransfers.length !== 1 ? 's' : ''} - Confirmation Required!`}
                    className="detection-success-alert"
                >
                    <p>
                        <strong>These are potential transfers that need your confirmation.</strong> Review each candidate carefully,
                        check the boxes next to the ones that are actual transfers, then click "Confirm as Transfers" to verify them.
                    </p>
                </Alert>
            )}

            {/* View Controls */}
            <div className="view-controls">
                <div className="view-tabs">
                    {[
                        { key: 'pending', label: 'Pending Confirmation', count: pendingTransfers.length },
                        { key: 'confirmed', label: 'Confirmed in Range', count: confirmedTransfers.length },
                        { key: 'all', label: 'All Detection Results', count: (() => confirmedTransfers.length + pendingTransfers.length)() }
                    ].map(tab => (
                        <button
                            key={tab.key}
                            className={`view-tab ${viewMode === tab.key ? 'active' : ''}`}
                            onClick={() => setViewMode(tab.key as ViewMode)}
                        >
                            {tab.label}
                            <span className="tab-count">{tab.count}</span>
                        </button>
                    ))}
                </div>

                <div className="view-filters">
                    <input
                        type="text"
                        placeholder="Search transfers..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="search-input"
                    />
                </div>
            </div>

            {/* Pending Confirmation Actions */}
            {viewMode === 'pending' && pendingTransfers.length > 0 && (
                <div className="pending-actions">
                    <div className="confirmation-header">
                        <h4>⚠️ Confirmation Required</h4>
                        <p>Review these detected transfer candidates and confirm the ones that are actual transfers.</p>
                    </div>
                    <div className="selection-info">
                        <span>
                            {selectedPendingTransfers.size} of {pendingTransfers.length} candidates selected for confirmation
                        </span>
                    </div>
                    <div className="bulk-actions">
                        <Button
                            variant="secondary"
                            size="compact"
                            onClick={onSelectAllPending}
                        >
                            {selectedPendingTransfers.size === pendingTransfers.length ? 'Deselect All' : 'Select All Candidates'}
                        </Button>
                        <Button
                            variant="primary"
                            onClick={onBulkMarkTransfers}
                            disabled={bulkMarkLoading || selectedPendingTransfers.size === 0}
                        >
                            {(() => {
                                if (bulkMarkLoading) return 'Confirming...';
                                const count = selectedPendingTransfers.size;
                                const plural = count !== 1 ? 's' : '';
                                return `✅ Confirm ${count} as Transfer${plural}`;
                            })()}
                        </Button>
                    </div>
                </div>
            )}

            {/* Results Table */}
            {displayTransfers.length === 0 ? (
                <div className="no-results">
                    {viewMode === 'pending' && (
                        <div className="no-results-content">
                            <span className="no-results-icon">🔍</span>
                            <h4>No Transfer Candidates Pending Confirmation</h4>
                            <p>Run a scan to detect potential transfer pairs that need your confirmation.</p>
                        </div>
                    )}
                    {viewMode === 'confirmed' && (
                        <div className="no-results-content">
                            <span className="no-results-icon">✅</span>
                            <h4>No Confirmed Transfers</h4>
                            <p>Confirm detected transfer candidates to see them here as verified transfers.</p>
                        </div>
                    )}
                    {viewMode === 'all' && (
                        <div className="no-results-content">
                            <span className="no-results-icon">📋</span>
                            <h4>No Transfer Detection Results</h4>
                            <p>Start by scanning for transfers to detect candidates that need confirmation.</p>
                        </div>
                    )}
                </div>
            ) : (
                <div className="results-table-container">
                    <table className="results-table">
                        <thead>
                            <tr>
                                {viewMode === 'pending' && <th className="checkbox-column">
                                    <input
                                        type="checkbox"
                                        checked={selectedPendingTransfers.size === pendingTransfers.length && pendingTransfers.length > 0}
                                        onChange={onSelectAllPending}
                                    />
                                </th>}
                                <th
                                    className="sortable-header"
                                    onClick={() => handleSort('account')}
                                >
                                    Source Account {getSortIcon('account')}
                                </th>
                                <th
                                    className="sortable-header"
                                    onClick={() => handleSort('date')}
                                >
                                    Date {getSortIcon('date')}
                                </th>
                                <th
                                    className="sortable-header"
                                    onClick={() => handleSort('amount')}
                                >
                                    Amount {getSortIcon('amount')}
                                </th>
                                <th>Target Account</th>
                                <th>Target Date</th>
                                <th>Target Amount</th>
                                <th>Days Apart</th>
                                {viewMode === 'pending' && (
                                    <th
                                        className="sortable-header"
                                        onClick={() => handleSort('confidence')}
                                    >
                                        Confidence {getSortIcon('confidence')}
                                    </th>
                                )}
                                {viewMode === 'all' && <th>Status</th>}
                            </tr>
                        </thead>
                        <tbody>
                            {displayTransfers.map((pair) => {
                                const pairKey = getTransferPairKey(pair);
                                const isPending = pendingTransfers.includes(pair);
                                const confidence = getConfidenceScore(pair);

                                return (
                                    <tr
                                        key={pairKey}
                                        className={`
                                            ${isPending && selectedPendingTransfers.has(pairKey) ? 'selected' : ''}
                                            ${isPending ? 'pending-row' : 'confirmed-row'}
                                        `}
                                    >
                                        {viewMode === 'pending' && (
                                            <td className="checkbox-cell">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedPendingTransfers.has(pairKey)}
                                                    onChange={() => onTogglePendingTransfer(pairKey)}
                                                />
                                            </td>
                                        )}
                                        <td className="account-cell">
                                            {getAccountName(pair.outgoingTransaction.accountId)}
                                        </td>
                                        <td>
                                            <DateCell
                                                date={pair.outgoingTransaction.date}
                                                format="short"
                                                locale={localeConfig.locale}
                                            />
                                        </td>
                                        <td>
                                            <CurrencyDisplay
                                                amount={Math.abs(Number(pair.outgoingTransaction.amount))}
                                                currency={pair.outgoingTransaction.currency || 'USD'}
                                                className="currency-negative"
                                            />
                                        </td>
                                        <td className="account-cell">
                                            {getAccountName(pair.incomingTransaction.accountId)}
                                        </td>
                                        <td>
                                            <DateCell
                                                date={pair.incomingTransaction.date}
                                                format="short"
                                                locale={localeConfig.locale}
                                            />
                                        </td>
                                        <td>
                                            <CurrencyDisplay
                                                amount={Number(pair.incomingTransaction.amount)}
                                                currency={pair.incomingTransaction.currency || 'USD'}
                                                className="currency-positive"
                                            />
                                        </td>
                                        <td className="days-apart">
                                            <span className={`days-badge ${(() => {
                                                if (pair.dateDifference <= 1) return 'same-day';
                                                if (pair.dateDifference <= 3) return 'close';
                                                return 'distant';
                                            })()}`}>
                                                {pair.dateDifference} day{pair.dateDifference !== 1 ? 's' : ''}
                                            </span>
                                        </td>
                                        {viewMode === 'pending' && (
                                            <td className="confidence-cell">
                                                <div className="confidence-indicator">
                                                    <div
                                                        className="confidence-bar"
                                                        style={{
                                                            width: `${confidence}%`,
                                                            backgroundColor: getConfidenceColor(confidence)
                                                        }}
                                                    />
                                                    <span className="confidence-text">{confidence}%</span>
                                                </div>
                                            </td>
                                        )}
                                        {viewMode === 'all' && (
                                            <td className="status-cell">
                                                <span className={`status-badge ${isPending ? 'pending' : 'confirmed'}`}>
                                                    {isPending ? '⏳ Needs Confirmation' : '✅ Confirmed Transfer'}
                                                </span>
                                            </td>
                                        )}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Results Summary */}
            {displayTransfers.length > 0 && (
                <div className="results-footer">
                    <div className="results-stats">
                        <span>Showing {displayTransfers.length} transfer{displayTransfers.length !== 1 ? 's' : ''}</span>
                        {searchTerm && (
                            <span className="search-results">
                                {(() => {
                                    let totalCount: number;
                                    if (viewMode === 'all') {
                                        totalCount = confirmedTransfers.length + pendingTransfers.length;
                                    } else if (viewMode === 'confirmed') {
                                        totalCount = confirmedTransfers.length;
                                    } else {
                                        totalCount = pendingTransfers.length;
                                    }
                                    return `(filtered from ${totalCount})`;
                                })()}
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TransferResultsDashboard;
