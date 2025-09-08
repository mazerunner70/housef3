import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import SidebarSection, { SidebarSectionData } from '@/new-ui/components/navigation/SidebarSection';

interface TransactionsSidebarContentProps {
    sidebarCollapsed: boolean;
}

const TransactionsSidebarContent: React.FC<TransactionsSidebarContentProps> = ({ sidebarCollapsed }) => {
    const location = useLocation();

    // Generate sidebar sections for transactions page
    const sections = useMemo((): SidebarSectionData[] => {
        const searchParams = new URLSearchParams(location.search);
        const currentTab = searchParams.get('tab') || 'list';

        return [
            {
                type: 'navigation',
                title: 'Transaction Views',
                items: [
                    {
                        id: 'transactions-list',
                        label: 'All Transactions',
                        icon: '📋',
                        active: currentTab === 'list',
                        onClick: () => {
                            window.location.href = '/transactions?tab=list';
                        }
                    },
                    {
                        id: 'category-management',
                        label: 'Category Management',
                        icon: '🏷️',
                        active: currentTab === 'categories',
                        onClick: () => {
                            window.location.href = '/transactions?tab=categories';
                        }
                    },
                    {
                        id: 'imports',
                        label: 'Imports & Statements',
                        icon: '📥',
                        active: currentTab === 'imports',
                        onClick: () => {
                            window.location.href = '/transactions?tab=imports';
                        }
                    },
                    {
                        id: 'transfers',
                        label: 'Transfer Detection',
                        icon: '↔️',
                        active: currentTab === 'transfers',
                        onClick: () => {
                            window.location.href = '/transactions?tab=transfers';
                        }
                    }
                ],
                collapsible: false
            },
            {
                type: 'context',
                title: 'Quick Filters',
                items: [
                    {
                        id: 'recent',
                        label: 'Recent (30 days)',
                        icon: '🕒',
                        active: false,
                        onClick: () => {
                            window.location.href = '/transactions?filter=recent';
                        }
                    },
                    {
                        id: 'uncategorized',
                        label: 'Uncategorized',
                        icon: '❓',
                        active: false,
                        onClick: () => {
                            window.location.href = '/transactions?filter=uncategorized';
                        }
                    },
                    {
                        id: 'large-amounts',
                        label: 'Large Amounts',
                        icon: '💰',
                        active: false,
                        onClick: () => {
                            window.location.href = '/transactions?filter=large';
                        }
                    }
                ],
                collapsible: true,
                collapsed: true
            },
            {
                type: 'actions',
                title: 'Quick Actions',
                items: [
                    {
                        id: 'add-transaction',
                        label: 'Add Transaction',
                        icon: '➕',
                        active: false,
                        onClick: () => {
                            alert('Add Transaction functionality to be implemented');
                        }
                    },
                    {
                        id: 'export-data',
                        label: 'Export Data',
                        icon: '📤',
                        active: false,
                        onClick: () => {
                            alert('Export functionality to be implemented');
                        }
                    }
                ],
                collapsible: false
            }
        ];
    }, [location]);

    return (
        <>
            {sections.map((section, index) => (
                <SidebarSection
                    key={`${section.type}-${index}`}
                    section={section}
                    sidebarCollapsed={sidebarCollapsed}
                />
            ))}
        </>
    );
};

export default TransactionsSidebarContent;
