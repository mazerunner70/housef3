import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPortfolioInsights, formatDateRange, PortfolioInsights } from '@/services/PortfolioService';
import { Account } from '@/schemas/Account';
import './HomePage.css';

const HomePage: React.FC = () => {
    const [insights, setInsights] = useState<PortfolioInsights | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const navigate = useNavigate();

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
        // Navigate to accounts page with a filter or highlight for stale accounts
        navigate('/accounts?filter=stale');
    };

    if (loading) {
        return (
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
    }

    if (error || !insights) {
        return (
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
    }

    return (
        <div className="home-page">
            <div className="home-header">
                <h1>Portfolio Overview</h1>
                <p>Welcome back! Here's what's happening with your accounts.</p>
            </div>

            <div className="insights-grid">
                {/* Total Accounts Card */}
                <div
                    className="insight-card accounts-summary"
                    onClick={handleViewAccounts}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleViewAccounts();
                        }
                    }}
                    role="button"
                    tabIndex={0}
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
                </div>

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
                <div
                    className={`insight-card updates-needed ${insights.staleAccounts > 0 ? 'warning' : 'success'}`}
                    onClick={insights.staleAccounts > 0 ? handleViewStaleAccounts : undefined}
                    onKeyDown={insights.staleAccounts > 0 ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleViewStaleAccounts();
                        }
                    } : undefined}
                    role={insights.staleAccounts > 0 ? "button" : undefined}
                    tabIndex={insights.staleAccounts > 0 ? 0 : undefined}
                    aria-label={insights.staleAccounts > 0 ? "View accounts needing updates" : undefined}
                    style={{ cursor: insights.staleAccounts > 0 ? 'pointer' : 'default' }}
                >
                    <div className="card-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            {insights.staleAccounts > 0 ? (
                                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                            ) : (
                                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            )}
                            {insights.staleAccounts > 0 ? (
                                <path d="M12 9v4" />
                            ) : (
                                <polyline points="22,4 12,14.01 9,11.01" />
                            )}
                            {insights.staleAccounts > 0 && <path d="M12 17h.01" />}
                        </svg>
                    </div>
                    <div className="card-content">
                        <h3>Updates Needed</h3>
                        <div className="metric-value">{insights.staleAccounts}</div>
                        <div className="metric-detail">
                            {insights.staleAccounts === 0
                                ? 'All accounts up to date!'
                                : `${insights.staleAccounts} account${insights.staleAccounts > 1 ? 's' : ''} need${insights.staleAccounts === 1 ? 's' : ''} new transactions`
                            }
                        </div>
                    </div>
                    {insights.staleAccounts > 0 && (
                        <div className="card-action">
                            <span>Review</span>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="m9 18 6-6-6-6" />
                            </svg>
                        </div>
                    )}
                </div>

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

            {/* Stale Accounts List (if any) */}
            {insights.staleAccounts > 0 && (
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
                        {insights.accountsNeedingUpdate.length > 5 && (
                            <div className="more-accounts">
                                +{insights.accountsNeedingUpdate.length - 5} more accounts
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default HomePage;
