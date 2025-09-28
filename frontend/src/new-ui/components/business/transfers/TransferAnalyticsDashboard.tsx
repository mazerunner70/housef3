import React, { useState, useMemo } from 'react';
import { TransferPair } from '@/services/TransferService';
import { AccountInfo } from '@/schemas/Transaction';
import { CurrencyDisplay } from '@/new-ui/components/ui';
import { useLocale } from '@/new-ui/hooks/useLocale';
import './TransferAnalyticsDashboard.css';

interface TransferAnalyticsDashboardProps {
    confirmedTransfers: TransferPair[];
    accounts: AccountInfo[];
    scanningStats?: {
        totalScansRun: number;
        totalTimeSpent: number; // in minutes
        averageScanTime: number; // in minutes
        lastScanDate?: Date;
    };
}

interface TransferPattern {
    amount: number;
    frequency: number;
    accounts: string[];
    averageDays: number;
}

interface AccountActivity {
    accountId: string;
    accountName: string;
    outgoingCount: number;
    incomingCount: number;
    totalOutgoing: number;
    totalIncoming: number;
    netTransfer: number;
}

const TransferAnalyticsDashboard: React.FC<TransferAnalyticsDashboardProps> = ({
    confirmedTransfers,
    accounts,
    scanningStats
}) => {
    const { formatDate } = useLocale();
    const [isExpanded, setIsExpanded] = useState(false);

    const getAccountName = (accountId: string | undefined): string => {
        if (!accountId) return 'Unknown Account';
        const account = accounts.find(acc => acc.accountId === accountId);
        return account ? (account.name as string) : `Account ${accountId}`;
    };

    // Calculate transfer patterns
    const transferPatterns = useMemo((): TransferPattern[] => {
        const amountGroups = new Map<number, TransferPair[]>();

        // Group transfers by rounded amount (to nearest $10)
        confirmedTransfers.forEach(transfer => {
            const amount = Math.round(Math.abs(Number(transfer.outgoingTransaction.amount)) / 10) * 10;
            if (!amountGroups.has(amount)) {
                amountGroups.set(amount, []);
            }
            amountGroups.get(amount)!.push(transfer);
        });

        // Convert to patterns and sort by frequency
        return Array.from(amountGroups.entries())
            .map(([amount, transfers]) => {
                const accounts = Array.from(new Set(
                    transfers.flatMap(t => [
                        getAccountName(t.outgoingTransaction.accountId),
                        getAccountName(t.incomingTransaction.accountId)
                    ])
                ));
                const averageDays = transfers.reduce((sum, t) => sum + t.dateDifference, 0) / transfers.length;

                return {
                    amount,
                    frequency: transfers.length,
                    accounts,
                    averageDays: Math.round(averageDays * 10) / 10
                };
            })
            .filter(pattern => pattern.frequency > 1) // Only show recurring patterns
            .sort((a, b) => b.frequency - a.frequency)
            .slice(0, 5); // Top 5 patterns
    }, [confirmedTransfers, accounts]);

    // Calculate account activity
    const accountActivity = useMemo((): AccountActivity[] => {
        const activityMap = new Map<string, AccountActivity>();

        // Initialize all accounts
        accounts.forEach(account => {
            activityMap.set(account.accountId, {
                accountId: account.accountId,
                accountName: account.name as string,
                outgoingCount: 0,
                incomingCount: 0,
                totalOutgoing: 0,
                totalIncoming: 0,
                netTransfer: 0
            });
        });

        // Process transfers
        confirmedTransfers.forEach(transfer => {
            const outgoingId = transfer.outgoingTransaction.accountId;
            const incomingId = transfer.incomingTransaction.accountId;
            const amount = Math.abs(Number(transfer.outgoingTransaction.amount));

            if (outgoingId && activityMap.has(outgoingId)) {
                const activity = activityMap.get(outgoingId)!;
                activity.outgoingCount++;
                activity.totalOutgoing += amount;
                activity.netTransfer -= amount;
            }

            if (incomingId && activityMap.has(incomingId)) {
                const activity = activityMap.get(incomingId)!;
                activity.incomingCount++;
                activity.totalIncoming += amount;
                activity.netTransfer += amount;
            }
        });

        return Array.from(activityMap.values())
            .filter(activity => activity.outgoingCount > 0 || activity.incomingCount > 0)
            .sort((a, b) => (b.outgoingCount + b.incomingCount) - (a.outgoingCount + a.incomingCount));
    }, [confirmedTransfers, accounts]);

    // Calculate scanning efficiency
    const scanningEfficiency = useMemo(() => {
        if (!scanningStats || scanningStats.totalScansRun === 0) return null;

        const transfersPerScan = confirmedTransfers.length / scanningStats.totalScansRun;
        const transfersPerMinute = scanningStats.totalTimeSpent > 0 ?
            confirmedTransfers.length / scanningStats.totalTimeSpent : 0;

        return {
            transfersPerScan: Math.round(transfersPerScan * 100) / 100,
            transfersPerMinute: Math.round(transfersPerMinute * 100) / 100,
            efficiency: transfersPerScan > 1 ? 'High' : transfersPerScan > 0.5 ? 'Medium' : 'Low'
        };
    }, [confirmedTransfers.length, scanningStats]);

    // Calculate time-based insights
    const timeInsights = useMemo(() => {
        if (confirmedTransfers.length === 0) return null;

        const dayOfWeekCounts = new Array(7).fill(0);
        const hourCounts = new Array(24).fill(0);

        confirmedTransfers.forEach(transfer => {
            const date = new Date(transfer.outgoingTransaction.date);
            dayOfWeekCounts[date.getDay()]++;
            hourCounts[date.getHours()]++;
        });

        const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const mostActiveDayIndex = dayOfWeekCounts.indexOf(Math.max(...dayOfWeekCounts));
        const mostActiveHour = hourCounts.indexOf(Math.max(...hourCounts));

        return {
            mostActiveDay: dayNames[mostActiveDayIndex],
            mostActiveHour: `${mostActiveHour}:00`,
            weekdayVsWeekend: {
                weekday: dayOfWeekCounts.slice(1, 6).reduce((sum, count) => sum + count, 0),
                weekend: dayOfWeekCounts[0] + dayOfWeekCounts[6]
            }
        };
    }, [confirmedTransfers]);

    if (confirmedTransfers.length === 0) {
        return (
            <div className="transfer-analytics-dashboard collapsed">
                <button
                    className="analytics-toggle"
                    onClick={() => setIsExpanded(!isExpanded)}
                >
                    <span>📊 Analytics & Insights</span>
                    <span className="toggle-note">(Available after transfers are found)</span>
                </button>
            </div>
        );
    }

    return (
        <div className={`transfer-analytics-dashboard ${isExpanded ? 'expanded' : 'collapsed'}`}>
            <button
                className="analytics-toggle"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <span>📊 Analytics & Insights</span>
                <span className={`toggle-arrow ${isExpanded ? 'expanded' : ''}`}>
                    ▼
                </span>
            </button>

            {isExpanded && (
                <div className="analytics-content">
                    {/* Overview Stats */}
                    <div className="analytics-section overview-stats">
                        <h4>📈 Overview</h4>
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-value">{confirmedTransfers.length}</div>
                                <div className="stat-label">Total Transfers</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">
                                    <CurrencyDisplay
                                        amount={confirmedTransfers.reduce((sum, t) =>
                                            sum + Math.abs(Number(t.outgoingTransaction.amount)), 0
                                        )}
                                        currency="USD"
                                        showSymbol={false}
                                    />
                                </div>
                                <div className="stat-label">Total Volume</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">
                                    <CurrencyDisplay
                                        amount={confirmedTransfers.reduce((sum, t) =>
                                            sum + Math.abs(Number(t.outgoingTransaction.amount)), 0
                                        ) / confirmedTransfers.length}
                                        currency="USD"
                                        showSymbol={false}
                                    />
                                </div>
                                <div className="stat-label">Average Amount</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">
                                    {Math.round(
                                        confirmedTransfers.reduce((sum, t) => sum + t.dateDifference, 0) /
                                        confirmedTransfers.length * 10
                                    ) / 10}
                                </div>
                                <div className="stat-label">Avg Days Apart</div>
                            </div>
                        </div>
                    </div>

                    {/* Transfer Patterns */}
                    {transferPatterns.length > 0 && (
                        <div className="analytics-section">
                            <h4>🔄 Common Transfer Patterns</h4>
                            <div className="patterns-list">
                                {transferPatterns.map((pattern) => (
                                    <div key={`pattern-${pattern.amount}-${pattern.frequency}`} className="pattern-card">
                                        <div className="pattern-header">
                                            <div className="pattern-amount">
                                                <CurrencyDisplay
                                                    amount={pattern.amount}
                                                    currency="USD"
                                                />
                                            </div>
                                            <div className="pattern-frequency">
                                                {pattern.frequency}x
                                            </div>
                                        </div>
                                        <div className="pattern-details">
                                            <div className="pattern-accounts">
                                                {pattern.accounts.slice(0, 2).join(' ↔ ')}
                                                {pattern.accounts.length > 2 && ` +${pattern.accounts.length - 2} more`}
                                            </div>
                                            <div className="pattern-timing">
                                                Avg {pattern.averageDays} days apart
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Account Activity */}
                    <div className="analytics-section">
                        <h4>🏦 Account Activity</h4>
                        <div className="activity-table-container">
                            <table className="activity-table">
                                <thead>
                                    <tr>
                                        <th>Account</th>
                                        <th>Outgoing</th>
                                        <th>Incoming</th>
                                        <th>Net Transfer</th>
                                        <th>Total Transfers</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {accountActivity.map((activity) => (
                                        <tr key={activity.accountId}>
                                            <td className="account-name">{activity.accountName}</td>
                                            <td className="outgoing-cell">
                                                <div className="transfer-count">{activity.outgoingCount}</div>
                                                <div className="transfer-amount">
                                                    <CurrencyDisplay
                                                        amount={activity.totalOutgoing}
                                                        currency="USD"
                                                        className="currency-negative"
                                                    />
                                                </div>
                                            </td>
                                            <td className="incoming-cell">
                                                <div className="transfer-count">{activity.incomingCount}</div>
                                                <div className="transfer-amount">
                                                    <CurrencyDisplay
                                                        amount={activity.totalIncoming}
                                                        currency="USD"
                                                        className="currency-positive"
                                                    />
                                                </div>
                                            </td>
                                            <td className="net-transfer-cell">
                                                <CurrencyDisplay
                                                    amount={activity.netTransfer}
                                                    currency="USD"
                                                    className={activity.netTransfer >= 0 ? 'currency-positive' : 'currency-negative'}
                                                />
                                            </td>
                                            <td className="total-transfers">
                                                {activity.outgoingCount + activity.incomingCount}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Time Insights */}
                    {timeInsights && (
                        <div className="analytics-section">
                            <h4>⏰ Timing Insights</h4>
                            <div className="insights-grid">
                                <div className="insight-card">
                                    <div className="insight-label">Most Active Day</div>
                                    <div className="insight-value">{timeInsights.mostActiveDay}</div>
                                </div>
                                <div className="insight-card">
                                    <div className="insight-label">Most Active Hour</div>
                                    <div className="insight-value">{timeInsights.mostActiveHour}</div>
                                </div>
                                <div className="insight-card">
                                    <div className="insight-label">Weekday vs Weekend</div>
                                    <div className="insight-value">
                                        {(() => {
                                            const total = timeInsights.weekdayVsWeekend.weekday + timeInsights.weekdayVsWeekend.weekend;
                                            const percentage = total > 0 ? Math.round((timeInsights.weekdayVsWeekend.weekday / total) * 100) : 0;
                                            return `${percentage}% weekdays`;
                                        })()}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Scanning Efficiency */}
                    {scanningEfficiency && (
                        <div className="analytics-section">
                            <h4>🔍 Scanning Efficiency</h4>
                            <div className="efficiency-grid">
                                <div className="efficiency-card">
                                    <div className="efficiency-label">Transfers per Scan</div>
                                    <div className="efficiency-value">{scanningEfficiency.transfersPerScan}</div>
                                </div>
                                <div className="efficiency-card">
                                    <div className="efficiency-label">Transfers per Minute</div>
                                    <div className="efficiency-value">{scanningEfficiency.transfersPerMinute}</div>
                                </div>
                                <div className="efficiency-card">
                                    <div className="efficiency-label">Efficiency Rating</div>
                                    <div className={`efficiency-value ${scanningEfficiency.efficiency.toLowerCase()}`}>
                                        {scanningEfficiency.efficiency}
                                    </div>
                                </div>
                                {scanningStats?.lastScanDate && (
                                    <div className="efficiency-card">
                                        <div className="efficiency-label">Last Scan</div>
                                        <div className="efficiency-value">
                                            {formatDate(scanningStats.lastScanDate.getTime(), {
                                                month: 'short',
                                                day: 'numeric',
                                                hour: 'numeric',
                                                minute: 'numeric'
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default TransferAnalyticsDashboard;
