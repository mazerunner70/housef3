import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPortfolioInsights, formatDateRange, PortfolioInsights } from '@/services/PortfolioService';
import { useNavigationStore } from '@/stores/navigationStore';
import { Account } from '@/schemas/Account';
import './HomePage.css';

// Helper function to determine account update text
const getAccountUpdateText = (staleAccounts: number): string => {
    if (staleAccounts === 0) {
        return 'All accounts up to date!';
    }
    const accountText = staleAccounts > 1 ? 'accounts' : 'account';
    const needText = staleAccounts === 1 ? 'needs' : 'need';
    return `${staleAccounts} ${accountText} ${needText} new transactions`;
};

// Helper function to determine transfer progress class
const getTransferProgressClass = (transferScanProgress: PortfolioInsights['transferScanProgress']): string => {
    if (!transferScanProgress.hasData) return 'no-data';
    return transferScanProgress.isComplete ? 'complete' : 'in-progress';
};

// Loading component
const LoadingView: React.FC = () => (
    <div className="home-page">
        <div className="home-header">
            <h1>Portfolio Overview</h1>
            <p>Loading your portfolio insights...</p>
        </div>
        <div className="insights-grid loading">
            <div className="insight-card skeleton"></div>
            <div className="insight-card skeleton"></div>
            <div className="insight-card skeleton"></div>
            <div className="insight-card skeleton"></div>
        </div>
    </div>
);

// Error component
const ErrorView: React.FC<{ error: string | null }> = ({ error }) => (
    <div className="home-page">
        <div className="home-header">
            <h1>Portfolio Overview</h1>
            <p className="error-message">{error || 'Unable to load portfolio data'}</p>
        </div>
        <div className="insights-grid">
            <div className="insight-card error">
                <div className="card-content">
                    <h3>Error Loading Data</h3>
                    <p>Please try refreshing the page or check your connection.</p>
                    <button onClick={() => window.location.reload()} className="retry-button">
                        Retry
                    </button>
                </div>
            </div>
        </div>
    </div>
);

// Transfer Recommendation Section Component
interface TransferRecommendationProps {
    insights: PortfolioInsights;
    onUseRecommendedRange: () => void;
}

const TransferRecommendationSection: React.FC<TransferRecommendationProps> = ({ insights, onUseRecommendedRange }) => {
    if (!insights.transferScanProgress.hasData ||
        insights.transferScanProgress.isComplete ||
        !insights.transferScanProgress.recommendedRange) {
        return null;
    }

    return (
        <div className="transfer-recommendation-section">
            <h2>Continue Transfer Scanning</h2>
            <p>We recommend scanning this date range next to systematically check all your transaction data for transfers:</p>
            <div className="recommendation-card">
                <div className="recommendation-info">
                    <div className="recommended-range">
                        <strong>
                            {new Date(insights.transferScanProgress.recommendedRange.startDate).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric'
                            })} - {new Date(insights.transferScanProgress.recommendedRange.endDate).toLocaleDateString('en-US', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric'
                            })}
                        </strong>
                    </div>
                    <div className="recommendation-details">
                        This range provides optimal coverage with 3-day overlap for accurate transfer detection
                    </div>
                </div>
                <button
                    className="use-range-button"
                    onClick={onUseRecommendedRange}
                >
                    Scan This Range
                </button>
            </div>
        </div>
    );
};

// Stale Accounts Section Component
interface StaleAccountsSectionProps {
    insights: PortfolioInsights;
}

const StaleAccountsSection: React.FC<StaleAccountsSectionProps> = ({ insights }) => {
    if (insights.staleAccounts === 0) {
        return null;
    }

    return (
        <div className="stale-accounts-section">
            <h2>Accounts Needing Updates</h2>
            <p>These accounts haven't had new transactions in over 7 days:</p>
            <div className="stale-accounts-list">
                {insights.accountsNeedingUpdate.slice(0, 5).map((account: Account) => (
                    <div key={account.accountId} className="stale-account-item">
                        <div className="account-info">
                            <div className="account-name">{account.accountName}</div>
                            <div className="account-details">
                                {account.institution} • {account.accountType}
                            </div>
                        </div>
                        <div className="last-transaction">
                            {account.lastTransactionDate
                                ? `Last: ${new Date(account.lastTransactionDate).toLocaleDateString()}`
                                : 'No transactions'
                            }
                        </div>
                    </div>
                ))}
                {(() => {
                    const extra = insights.accountsNeedingUpdate.length - 5;
                    return extra > 0 && (
                        <div className="more-accounts">
                            +{extra} more account{extra === 1 ? '' : 's'}
                        </div>
                    );
                })()}
            </div>
        </div>
    );
};

// Insight Cards Components
interface InsightCardsProps {
    insights: PortfolioInsights;
    onViewAccounts: () => void;
    onViewStaleAccounts: () => void;
    onViewTransfers: () => void;
}

const InsightCards: React.FC<InsightCardsProps> = ({
    insights,
    onViewAccounts,
    onViewStaleAccounts,
    onViewTransfers
}) => (
    <div className="insights-grid">
        {/* Total Accounts Card */}
        <button
            className="insight-card accounts-summary"
            onClick={onViewAccounts}
            aria-label="View all accounts"
        >
            <div className="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                    <line x1="2" y1="9" x2="22" y2="9" />
                </svg>
            </div>
            <div className="card-content">
                <h3>Total Accounts</h3>
                <div className="metric-value">{insights.totalAccounts}</div>
                <div className="metric-detail">
                    {insights.activeAccounts} active • {insights.totalAccounts - insights.activeAccounts} inactive
                </div>
            </div>
            <div className="card-action">
                <span>View All</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m9 18 6-6-6-6" />
                </svg>
            </div>
        </button>

        {/* Date Range Coverage Card */}
        <div className="insight-card date-range">
            <div className="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
            </div>
            <div className="card-content">
                <h3>Data Coverage</h3>
                <div className="metric-value">
                    {insights.dateRange.totalDays ? `${Math.round(insights.dateRange.totalDays / 365 * 10) / 10}` : '0'}
                    <span className="metric-unit">years</span>
                </div>
                <div className="metric-detail">
                    {formatDateRange(insights.dateRange)}
                </div>
            </div>
        </div>

        {/* Accounts Needing Updates Card */}
        {insights.staleAccounts > 0 ? (
            <button
                className="insight-card updates-needed warning"
                onClick={onViewStaleAccounts}
                aria-label="View accounts needing updates"
            >
                <div className="card-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                        <path d="M12 9v4" />
                        <path d="M12 17h.01" />
                    </svg>
                </div>
                <div className="card-content">
                    <h3>Updates Needed</h3>
                    <div className="metric-value">{insights.staleAccounts}</div>
                    <div className="metric-detail">
                        {getAccountUpdateText(insights.staleAccounts)}
                    </div>
                </div>
                <div className="card-action">
                    <span>Review</span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="m9 18 6-6-6-6" />
                    </svg>
                </div>
            </button>
        ) : (
            <div className="insight-card updates-needed success">
                <div className="card-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                        <polyline points="22,4 12,14.01 9,11.01" />
                    </svg>
                </div>
                <div className="card-content">
                    <h3>Updates Needed</h3>
                    <div className="metric-value">{insights.staleAccounts}</div>
                    <div className="metric-detail">
                        {getAccountUpdateText(insights.staleAccounts)}
                    </div>
                </div>
            </div>
        )}

        {/* Transfer Scan Progress Card */}
        <button
            className={`insight-card transfer-progress ${getTransferProgressClass(insights.transferScanProgress)}`}
            onClick={onViewTransfers}
            aria-label="View transfer detection progress"
        >
            <div className="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M7 16.5L12 12l5 4.5" />
                    <path d="M7 7.5L12 3l5 4.5" />
                    <path d="M12 3v18" />
                </svg>
            </div>
            <div className="card-content">
                <h3>Transfer Scan Progress</h3>
                <div className="metric-value">
                    {insights.transferScanProgress.hasData ? insights.transferScanProgress.progressPercentage : 0}
                    <span className="metric-unit">%</span>
                </div>
                <div className="metric-detail">
                    {insights.transferScanProgress.hasData
                        ? `${insights.transferScanProgress.checkedDays} of ${insights.transferScanProgress.totalDays} days scanned`
                        : 'No transfer scanning data available'
                    }
                </div>
                {insights.transferScanProgress.hasData && !insights.transferScanProgress.isComplete && (
                    <div className="progress-bar">
                        <div
                            className="progress-fill"
                            style={{ width: `${insights.transferScanProgress.progressPercentage}%` }}
                        ></div>
                    </div>
                )}
            </div>
            <div className="card-action">
                <span>{insights.transferScanProgress.isComplete ? 'Complete' : 'Manage'}</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="m9 18 6-6-6-6" />
                </svg>
            </div>
        </button>

        {/* Recent Activity Card */}
        <div className="insight-card recent-activity">
            <div className="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 3v5h5" />
                    <path d="m3 8 9-5 9 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                    <path d="M9 21v-6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v6" />
                </svg>
            </div>
            <div className="card-content">
                <h3>Recent Activity</h3>
                <div className="metric-value">{insights.recentActivity.accountsWithRecentTransactions}</div>
                <div className="metric-detail">
                    accounts with transactions in the last 7 days
                </div>
            </div>
        </div>
    </div>
);

const HomePage: React.FC = () => {
    const [insights, setInsights] = useState<PortfolioInsights | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();
    const { goToHome } = useNavigationStore();

    // Set up correct breadcrumb for home page
    useEffect(() => {
        goToHome();
    }, [goToHome]);

    useEffect(() => {
        const loadInsights = async () => {
            try {
                setLoading(true);
                const portfolioInsights = await getPortfolioInsights();
                setInsights(portfolioInsights);
                setError(null);
            } catch (err) {
                console.error('Failed to load portfolio insights:', err);
                setError('Failed to load portfolio insights');
            } finally {
                setLoading(false);
            }
        };

        loadInsights();
    }, []);

    const handleViewAccounts = () => {
        navigate('/accounts');
    };

    const handleViewStaleAccounts = () => {
        // Navigate to import page to help users update their accounts
        navigate('/import');
    };

    const handleViewTransfers = () => {
        navigate('/transfers');
    };

    const handleUseRecommendedRange = () => {
        if (insights?.transferScanProgress.recommendedRange) {
            const startDate = new Date(insights.transferScanProgress.recommendedRange.startDate).toISOString().split('T')[0];
            const endDate = new Date(insights.transferScanProgress.recommendedRange.endDate).toISOString().split('T')[0];
            navigate(`/transfers?startDate=${startDate}&endDate=${endDate}&autoScan=true`);
        }
    };

    if (loading) {
        return <LoadingView />;
    }

    if (error || !insights) {
        return <ErrorView error={error} />;
    }

    return (
        <div className="home-page">
            <div className="home-header">
                <h1>Portfolio Overview</h1>
                <p>Welcome back! Here's what's happening with your accounts.</p>
            </div>

            <InsightCards
                insights={insights}
                onViewAccounts={handleViewAccounts}
                onViewStaleAccounts={handleViewStaleAccounts}
                onViewTransfers={handleViewTransfers}
            />

            <TransferRecommendationSection
                insights={insights}
                onUseRecommendedRange={handleUseRecommendedRange}
            />

            <StaleAccountsSection insights={insights} />
        </div >
    );
};

export default HomePage;
