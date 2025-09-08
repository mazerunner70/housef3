import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import SidebarSection, { SidebarSectionData } from '@/new-ui/components/navigation/SidebarSection';

interface DefaultSidebarContentProps {
    sidebarCollapsed: boolean;
}

const DefaultSidebarContent: React.FC<DefaultSidebarContentProps> = ({ sidebarCollapsed }) => {
    const location = useLocation();

    // Generate sidebar sections for home/default page
    const sections = useMemo((): SidebarSectionData[] => {
        return [
            {
                type: 'navigation',
                title: 'Main Navigation',
                items: [
                    {
                        id: 'home',
                        label: 'Portfolio Overview',
                        icon: '🏠',
                        active: location.pathname === '/' || location.pathname === '/home',
                        onClick: () => {
                            window.location.href = '/';
                        }
                    },
                    {
                        id: 'accounts',
                        label: 'Accounts',
                        icon: '🏦',
                        active: location.pathname.startsWith('/accounts'),
                        onClick: () => {
                            window.location.href = '/accounts';
                        }
                    },
                    {
                        id: 'transactions',
                        label: 'Transactions',
                        icon: '📋',
                        active: location.pathname.startsWith('/transactions'),
                        onClick: () => {
                            window.location.href = '/transactions';
                        }
                    },
                    {
                        id: 'categories',
                        label: 'Categories',
                        icon: '🏷️',
                        active: location.pathname.startsWith('/categories'),
                        onClick: () => {
                            window.location.href = '/categories';
                        }
                    },
                    {
                        id: 'files',
                        label: 'Files',
                        icon: '📁',
                        active: location.pathname.startsWith('/files'),
                        onClick: () => {
                            window.location.href = '/files';
                        }
                    }
                ],
                collapsible: false
            },
            {
                type: 'quick-stats',
                title: 'Quick Stats',
                items: [
                    {
                        id: 'total-accounts',
                        label: 'View All Accounts',
                        icon: '📊',
                        active: false,
                        onClick: () => {
                            window.location.href = '/accounts';
                        }
                    },
                    {
                        id: 'recent-transactions',
                        label: 'Recent Transactions',
                        icon: '🕒',
                        active: false,
                        onClick: () => {
                            window.location.href = '/transactions?filter=recent';
                        }
                    },
                    {
                        id: 'uncategorized',
                        label: 'Uncategorized Items',
                        icon: '❓',
                        active: false,
                        onClick: () => {
                            window.location.href = '/transactions?filter=uncategorized';
                        }
                    }
                ],
                collapsible: true,
                collapsed: false
            },
            {
                type: 'actions',
                title: 'Quick Actions',
                items: [
                    {
                        id: 'add-account',
                        label: 'Add Account',
                        icon: '➕',
                        active: false,
                        onClick: () => {
                            alert('Add Account functionality to be implemented');
                        }
                    },
                    {
                        id: 'import-file',
                        label: 'Import Transactions',
                        icon: '📥',
                        active: false,
                        onClick: () => {
                            window.location.href = '/transactions?tab=imports';
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

export default DefaultSidebarContent;
