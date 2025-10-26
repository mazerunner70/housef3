import { Account } from '@/schemas/Account';
import { listAccounts } from '../components/domain/accounts/services/AccountService';
import { getTransferProgressAndRecommendation } from './TransferService';
import { createLogger } from '@/utils/logger';

const logger = createLogger('PortfolioService');

export interface PortfolioInsights {
    totalAccounts: number;
    activeAccounts: number;
    staleAccounts: number;
    dateRange: {
        earliest: Date | null;
        latest: Date | null;
        totalDays: number | null;
    };
    accountsNeedingUpdate: Account[];
    recentActivity: {
        accountsWithRecentTransactions: number;
        accountsWithOldTransactions: number;
    };
    transferScanProgress: {
        totalDays: number;
        checkedDays: number;
        progressPercentage: number;
        isComplete: boolean;
        hasData: boolean;
        accountDateRange: {
            startDate: number | null;
            endDate: number | null;
        };
        checkedDateRange: {
            startDate: number | null;
            endDate: number | null;
        };
        recommendedRange: {
            startDate: number;
            endDate: number;
        } | null;
    };
}

/**
 * Calculate comprehensive portfolio insights from account data
 */
export const getPortfolioInsights = async (): Promise<PortfolioInsights> => {
    logger.info('Calculating portfolio insights');

    try {
        // Load accounts and transfer progress in parallel
        const [accountsResponse, transferProgressData] = await Promise.all([
            listAccounts(),
            getTransferProgressAndRecommendation()
        ]);
        const accounts = accountsResponse.accounts;

        // Calculate basic counts
        const totalAccounts = accounts.length;
        const activeAccounts = accounts.filter(account => account.isActive).length;

        // Calculate date range from imports
        const earliestTimestamp = accounts
            .map(account => account.importsStartDate)
            .filter((timestamp): timestamp is number => timestamp != null)
            .reduce((earliest, timestamp) =>
                earliest === null || timestamp < earliest ? timestamp : earliest, null as number | null);

        const latestTimestamp = accounts
            .map(account => account.importsEndDate)
            .filter((timestamp): timestamp is number => timestamp != null)
            .reduce((latest, timestamp) =>
                latest === null || timestamp > latest ? timestamp : latest, null as number | null);

        // Calculate total days covered
        const totalDays = earliestTimestamp && latestTimestamp
            ? Math.ceil((latestTimestamp - earliestTimestamp) / (1000 * 60 * 60 * 24))
            : null;

        // Find accounts needing updates (last transaction > 7 days ago)
        const sevenDaysAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
        const accountsNeedingUpdate = accounts.filter(account => {
            if (!account.lastTransactionDate) return true; // No transactions at all
            return account.lastTransactionDate < sevenDaysAgo;
        });

        const staleAccounts = accountsNeedingUpdate.length;

        // Calculate recent activity metrics
        const accountsWithRecentTransactions = accounts.filter(account =>
            account.lastTransactionDate && account.lastTransactionDate >= sevenDaysAgo
        ).length;

        const accountsWithOldTransactions = accounts.filter(account =>
            account.lastTransactionDate && account.lastTransactionDate < sevenDaysAgo
        ).length;

        // Guard against missing transfer progress data
        const progress = transferProgressData?.progress ?? {};
        const recommendedRange = transferProgressData?.recommendedRange ?? null;

        const insights: PortfolioInsights = {
            totalAccounts,
            activeAccounts,
            staleAccounts,
            dateRange: {
                earliest: earliestTimestamp ? new Date(earliestTimestamp) : null,
                latest: latestTimestamp ? new Date(latestTimestamp) : null,
                totalDays
            },
            accountsNeedingUpdate,
            recentActivity: {
                accountsWithRecentTransactions,
                accountsWithOldTransactions
            },
            transferScanProgress: {
                totalDays: progress.totalDays ?? 0,
                checkedDays: progress.checkedDays ?? 0,
                progressPercentage: progress.progressPercentage ?? 0,
                isComplete: progress.isComplete ?? false,
                hasData: progress.hasData ?? false,
                accountDateRange: {
                    startDate: progress.accountDateRange?.startDate ?? null,
                    endDate: progress.accountDateRange?.endDate ?? null
                },
                checkedDateRange: {
                    startDate: progress.checkedDateRange?.startDate ?? null,
                    endDate: progress.checkedDateRange?.endDate ?? null
                },
                recommendedRange: recommendedRange
            }
        };

        logger.info('Portfolio insights calculated', {
            totalAccounts,
            activeAccounts,
            staleAccounts,
            dateRangeDays: totalDays,
            accountsNeedingUpdate: accountsNeedingUpdate.length
        });

        return insights;

    } catch (error) {
        logger.error('Failed to calculate portfolio insights', { error: error instanceof Error ? error.message : 'Unknown error' });
        throw error;
    }
};

/**
 * Format date range for display
 */
export const formatDateRange = (dateRange: PortfolioInsights['dateRange']): string => {
    if (!dateRange.earliest || !dateRange.latest) {
        return 'No transaction data available';
    }

    const formatDate = (date: Date) => date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });

    if (dateRange.totalDays === null) {
        return 'Date range unavailable';
    }

    if (dateRange.totalDays < 30) {
        return `${dateRange.totalDays} days (${formatDate(dateRange.earliest)} - ${formatDate(dateRange.latest)})`;
    } else if (dateRange.totalDays < 365) {
        const months = Math.round(dateRange.totalDays / 30);
        return `${months} months (${formatDate(dateRange.earliest)} - ${formatDate(dateRange.latest)})`;
    } else {
        const years = Math.round(dateRange.totalDays / 365 * 10) / 10;
        return `${years} years (${formatDate(dateRange.earliest)} - ${formatDate(dateRange.latest)})`;
    }
};

export default {
    getPortfolioInsights,
    formatDateRange
};
