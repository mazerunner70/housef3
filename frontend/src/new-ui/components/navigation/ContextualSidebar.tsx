import React, { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import SidebarSection, { SidebarSectionData } from '@/new-ui/components/navigation/SidebarSection';
import useAccountsWithStore from '@/stores/useAccountsStore';
import './ContextualSidebar.css';

interface ContextualSidebarProps {
    className?: string;
}

const ContextualSidebar: React.FC<ContextualSidebarProps> = ({ className = '' }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const {
        currentView,
        selectedAccount,
        selectedFile,
        sidebarCollapsed,
        toggleSidebar
    } = useNavigationStore();

    const { accounts } = useAccountsWithStore();

    // Determine current route context
    const routeContext = useMemo(() => {
        const pathSegments = location.pathname.split('/').filter(Boolean);
        const searchParams = new URLSearchParams(location.search);

        return {
            isAccountsRoute: pathSegments[0] === 'accounts',
            isCategoriesRoute: pathSegments[0] === 'categories',
            isTransactionsRoute: pathSegments[0] === 'transactions',
            isFilesRoute: pathSegments[0] === 'files',
            entityId: pathSegments[1],
            subRoute: pathSegments[2],
            searchParams
        };
    }, [location]);

    // Generate sidebar sections based on current route and view
    const sections = useMemo((): SidebarSectionData[] => {
        const sectionList: SidebarSectionData[] = [];

        // Handle different route contexts
        if (routeContext.isAccountsRoute || currentView === 'account-list') {
            // Navigation section with all accounts
            sectionList.push({
                type: 'navigation',
                title: '🏦 Accounts',
                items: accounts.map(account => ({
                    id: account.accountId,
                    label: `${account.accountName} - ${account.accountType}`,
                    icon: getAccountIcon(account.accountType),
                    active: routeContext.entityId === account.accountId,
                    onClick: () => navigate(`/accounts/${account.accountId}`)
                }))
            });

            // Entity navigation section
            sectionList.push({
                type: 'context',
                title: '📈 Browse',
                items: [
                    {
                        id: 'all-transactions',
                        label: 'All Transactions',
                        icon: '📊',
                        active: routeContext.isTransactionsRoute && !routeContext.entityId,
                        onClick: () => navigate('/transactions')
                    },
                    {
                        id: 'all-categories',
                        label: 'All Categories',
                        icon: '🏷️',
                        active: routeContext.isCategoriesRoute && !routeContext.entityId,
                        onClick: () => navigate('/categories')
                    },
                    {
                        id: 'all-files',
                        label: 'All Files',
                        icon: '📁',
                        active: routeContext.isFilesRoute && !routeContext.entityId,
                        onClick: () => navigate('/files')
                    }
                ]
            });

            // Actions section
            sectionList.push({
                type: 'actions',
                title: '⚙️ Actions',
                items: [
                    {
                        id: 'add-account',
                        label: 'Add Account',
                        icon: '➕',
                        active: false,
                        onClick: () => {
                            console.log('Add new account');
                        }
                    },
                    {
                        id: 'import-transactions',
                        label: 'Import Transactions',
                        icon: '📥',
                        active: false,
                        onClick: () => {
                            console.log('Import transactions');
                        }
                    }
                ]
            });
        }

        // Categories route context
        else if (routeContext.isCategoriesRoute) {
            // Back navigation
            sectionList.push({
                type: 'navigation',
                items: [
                    {
                        id: 'back-to-accounts',
                        label: 'Back to Accounts',
                        icon: '←',
                        active: false,
                        onClick: () => navigate('/accounts')
                    }
                ]
            });

            // Category-specific navigation
            if (routeContext.entityId) {
                sectionList.push({
                    type: 'context',
                    title: `🏷️ Category: ${routeContext.entityId}`,
                    items: [
                        {
                            id: 'category-overview',
                            label: 'Overview',
                            icon: '📋',
                            active: !routeContext.subRoute,
                            onClick: () => navigate(`/categories/${routeContext.entityId}`)
                        },
                        {
                            id: 'category-transactions',
                            label: 'Transactions',
                            icon: '📊',
                            active: routeContext.subRoute === 'transactions',
                            onClick: () => navigate(`/categories/${routeContext.entityId}/transactions`)
                        },
                        {
                            id: 'category-accounts',
                            label: 'Accounts',
                            icon: '🏦',
                            active: routeContext.subRoute === 'accounts',
                            onClick: () => navigate(`/categories/${routeContext.entityId}/accounts`)
                        },
                        {
                            id: 'category-analytics',
                            label: 'Analytics',
                            icon: '📈',
                            active: routeContext.subRoute === 'analytics',
                            onClick: () => navigate(`/categories/${routeContext.entityId}/analytics`)
                        }
                    ]
                });
            }

            // Category actions
            sectionList.push({
                type: 'actions',
                title: '⚙️ Actions',
                items: [
                    {
                        id: 'compare-categories',
                        label: 'Compare Categories',
                        icon: '⚖️',
                        active: false,
                        onClick: () => navigate('/categories/compare')
                    }
                ]
            });
        }

        // Transactions route context
        else if (routeContext.isTransactionsRoute) {
            // Back navigation
            sectionList.push({
                type: 'navigation',
                items: [
                    {
                        id: 'back-to-accounts',
                        label: 'Back to Accounts',
                        icon: '←',
                        active: false,
                        onClick: () => navigate('/accounts')
                    }
                ]
            });

            // Transaction-specific navigation
            if (routeContext.entityId) {
                sectionList.push({
                    type: 'context',
                    title: `📊 Transaction: ${routeContext.entityId.slice(-6)}`,
                    items: [
                        {
                            id: 'transaction-detail',
                            label: 'Details',
                            icon: '📋',
                            active: !routeContext.subRoute,
                            onClick: () => navigate(`/transactions/${routeContext.entityId}`)
                        },
                        {
                            id: 'transaction-edit',
                            label: 'Edit',
                            icon: '✏️',
                            active: routeContext.subRoute === 'edit',
                            onClick: () => navigate(`/transactions/${routeContext.entityId}/edit`)
                        }
                    ]
                });
            }

            // Transaction actions
            sectionList.push({
                type: 'actions',
                title: '⚙️ Actions',
                items: [
                    {
                        id: 'compare-transactions',
                        label: 'Compare Transactions',
                        icon: '⚖️',
                        active: false,
                        onClick: () => navigate('/transactions/compare')
                    }
                ]
            });
        }

        // Files route context
        else if (routeContext.isFilesRoute) {
            // Back navigation
            sectionList.push({
                type: 'navigation',
                items: [
                    {
                        id: 'back-to-accounts',
                        label: 'Back to Accounts',
                        icon: '←',
                        active: false,
                        onClick: () => navigate('/accounts')
                    }
                ]
            });

            // File-specific navigation
            if (routeContext.entityId) {
                sectionList.push({
                    type: 'context',
                    title: `📁 File: ${routeContext.entityId}`,
                    items: [
                        {
                            id: 'file-overview',
                            label: 'Overview',
                            icon: '📋',
                            active: !routeContext.subRoute,
                            onClick: () => navigate(`/files/${routeContext.entityId}`)
                        },
                        {
                            id: 'file-transactions',
                            label: 'Transactions',
                            icon: '📊',
                            active: routeContext.subRoute === 'transactions',
                            onClick: () => navigate(`/files/${routeContext.entityId}/transactions`)
                        },
                        {
                            id: 'file-summary',
                            label: 'Import Summary',
                            icon: '📈',
                            active: routeContext.subRoute === 'summary',
                            onClick: () => navigate(`/files/${routeContext.entityId}/summary`)
                        },
                        {
                            id: 'file-log',
                            label: 'Processing Log',
                            icon: '📜',
                            active: routeContext.subRoute === 'log',
                            onClick: () => navigate(`/files/${routeContext.entityId}/log`)
                        }
                    ]
                });
            }

            // File actions
            sectionList.push({
                type: 'actions',
                title: '⚙️ Actions',
                items: [
                    {
                        id: 'compare-files',
                        label: 'Compare Files',
                        icon: '⚖️',
                        active: false,
                        onClick: () => navigate('/files/compare')
                    }
                ]
            });
        }

        // Fallback for account detail view
        else if (currentView === 'account-detail' && selectedAccount) {
            // Back navigation
            sectionList.push({
                type: 'navigation',
                items: [
                    {
                        id: 'back-to-accounts',
                        label: 'All Accounts',
                        icon: '←',
                        active: false,
                        onClick: () => navigate('/accounts')
                    }
                ]
            });

            // Current account context
            sectionList.push({
                type: 'context',
                title: `🏦 ${selectedAccount.accountName}`,
                items: [
                    {
                        id: 'account-overview',
                        label: 'Overview',
                        icon: '📋',
                        active: true,
                        onClick: () => navigate(`/accounts/${selectedAccount.accountId}`)
                    },
                    {
                        id: 'account-transactions',
                        label: 'Transactions',
                        icon: '📊',
                        active: false,
                        onClick: () => navigate(`/transactions?account=${selectedAccount.accountId}`)
                    },
                    {
                        id: 'account-files',
                        label: 'Files',
                        icon: '📁',
                        active: false,
                        onClick: () => navigate(`/files?account=${selectedAccount.accountId}`)
                    },
                    {
                        id: 'account-categories',
                        label: 'Categories',
                        icon: '🏷️',
                        active: false,
                        onClick: () => navigate(`/categories?account=${selectedAccount.accountId}`)
                    }
                ]
            });

            // Quick switch to other accounts
            const otherAccounts = accounts.filter(acc => acc.accountId !== selectedAccount.accountId);
            if (otherAccounts.length > 0) {
                sectionList.push({
                    type: 'navigation',
                    title: '🔄 Quick Switch',
                    items: otherAccounts.map(account => ({
                        id: `switch-${account.accountId}`,
                        label: account.accountName,
                        icon: getAccountIcon(account.accountType),
                        active: false,
                        onClick: () => navigate(`/accounts/${account.accountId}`)
                    }))
                });
            }

            // Account actions
            sectionList.push({
                type: 'actions',
                title: '⚙️ Actions',
                items: [
                    {
                        id: 'edit-account',
                        label: 'Edit Account',
                        icon: '✏️',
                        active: false,
                        onClick: () => {
                            console.log('Edit account');
                        }
                    },
                    {
                        id: 'import-file',
                        label: 'Import File',
                        icon: '📥',
                        active: false,
                        onClick: () => {
                            console.log('Import file');
                        }
                    }
                ]
            });
        }

        return sectionList;
    }, [currentView, selectedAccount, selectedFile, accounts, routeContext, navigate]);

    // Helper function to get account type icon
    function getAccountIcon(accountType: string): string {
        switch (accountType.toLowerCase()) {
            case 'checking':
                return '💳';
            case 'savings':
                return '💰';
            case 'credit':
                return '💳';
            case 'investment':
                return '📈';
            default:
                return '🏦';
        }
    }

    return (
        <aside
            className={`contextual-sidebar ${sidebarCollapsed ? 'collapsed' : ''} ${className}`}
            role="navigation"
            aria-label="Account navigation"
        >
            {/* Sidebar header with toggle */}
            <div className="sidebar-header">
                <button
                    className="sidebar-toggle"
                    onClick={toggleSidebar}
                    aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                >
                    {sidebarCollapsed ? '→' : '←'}
                </button>
                {!sidebarCollapsed && (
                    <h2 className="sidebar-title">Navigation</h2>
                )}
            </div>

            {/* Sidebar content */}
            <div className="sidebar-content">
                {sections.map((section, index) => (
                    <SidebarSection
                        key={`${section.type}-${index}`}
                        section={section}
                        sidebarCollapsed={sidebarCollapsed}
                    />
                ))}
            </div>
        </aside>
    );
};

export default ContextualSidebar;
