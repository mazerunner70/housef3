import React, { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import SidebarSection, { SidebarSectionData } from '@/new-ui/components/navigation/SidebarSection';

interface CategoriesSidebarContentProps {
    sidebarCollapsed: boolean;
}

const CategoriesSidebarContent: React.FC<CategoriesSidebarContentProps> = ({ sidebarCollapsed }) => {
    const location = useLocation();

    // Generate sidebar sections for categories page
    const sections = useMemo((): SidebarSectionData[] => {
        const pathSegments = location.pathname.split('/').filter(Boolean);
        const categoryId = pathSegments[1];

        return [
            {
                type: 'navigation',
                title: 'Category Views',
                items: [
                    {
                        id: 'categories-list',
                        label: 'All Categories',
                        icon: '🏷️',
                        active: !categoryId,
                        onClick: () => {
                            window.location.href = '/categories';
                        }
                    },
                    {
                        id: 'category-compare',
                        label: 'Compare Categories',
                        icon: '📊',
                        active: pathSegments.includes('compare'),
                        onClick: () => {
                            window.location.href = '/categories/compare';
                        }
                    }
                ],
                collapsible: false
            },
            {
                type: 'context',
                title: 'Category Types',
                items: [
                    {
                        id: 'income',
                        label: 'Income',
                        icon: '💵',
                        active: false,
                        onClick: () => {
                            window.location.href = '/categories?type=income';
                        }
                    },
                    {
                        id: 'expense',
                        label: 'Expenses',
                        icon: '💸',
                        active: false,
                        onClick: () => {
                            window.location.href = '/categories?type=expense';
                        }
                    },
                    {
                        id: 'transfer',
                        label: 'Transfers',
                        icon: '↔️',
                        active: false,
                        onClick: () => {
                            window.location.href = '/categories?type=transfer';
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
                        id: 'add-category',
                        label: 'Add Category',
                        icon: '➕',
                        active: false,
                        onClick: () => {
                            alert('Add Category functionality to be implemented');
                        }
                    },
                    {
                        id: 'bulk-categorize',
                        label: 'Bulk Categorize',
                        icon: '⚡',
                        active: false,
                        onClick: () => {
                            alert('Bulk categorize functionality to be implemented');
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

export default CategoriesSidebarContent;
