import { Account } from '@/schemas/Account';
import { listAccounts } from './AccountService';
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
}

/**
 * Calculate comprehensive portfolio insights from account data
 */
export const getPortfolioInsights = async (): Promise<PortfolioInsights> => {
    logger.info('Calculating portfolio insights');

    try {
        const accountsResponse = await listAccounts();
        const accounts = accountsResponse.accounts;

        // Calculate basic counts
        const totalAccounts = accounts.length;
        const activeAccounts = accounts.filter(account => account.isActive).length;

        // Calculate date range from imports
        const earliestDate = accounts
            .map(account => account.importsStartDate)
            .filter((date): date is number => date != null)
            .map(timestamp => new Date(timestamp))
            .reduce((earliest, date) =>
                !earliest || date < earliest ? date : earliest, null as Date | null);

        const latestDate = accounts
            .map(account => account.importsEndDate)
            .filter((date): date is number => date != null)
            .map(timestamp => new Date(timestamp))
            .reduce((latest, date) =>
                !latest || date > latest ? date : latest, null as Date | null);

        // Calculate total days covered
        const totalDays = earliestDate && latestDate
            ? Math.ceil((latestDate.getTime() - earliestDate.getTime()) / (1000 * 60 * 60 * 24))
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

        const insights: PortfolioInsights = {
            totalAccounts,
            activeAccounts,
            staleAccounts,
            dateRange: {
                earliest: earliestDate,
                latest: latestDate,
                totalDays
            },
            accountsNeedingUpdate,
            recentActivity: {
                accountsWithRecentTransactions,
                accountsWithOldTransactions
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
