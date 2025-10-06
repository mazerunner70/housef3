/**
 * Configuration for Categories page sidebar content
 * Replaces CategoriesSidebarContent.tsx with declarative configuration
 */

import { SidebarContentConfig } from '../types';
import { createNavItem, createFilterItem, createActionItem } from '../SidebarConfigFactory';

export const categoriesConfig: SidebarContentConfig = {
    sections: [
        {
            type: 'navigation',
            title: 'Category Views',
            items: [
                createNavItem(
                    'categories-list',
                    'All Categories',
                    '/categories',
                    '🏷️',
                    (pathname) => pathname === '/categories'
                ),
                createNavItem(
                    'category-compare',
                    'Compare Categories',
                    '/categories/compare',
                    '📊',
                    (pathname) => pathname.includes('/compare')
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'Category Types',
            items: [
                createFilterItem(
                    'income',
                    'Income',
                    '/categories',
                    { type: 'income' },
                    '💵'
                ),
                createFilterItem(
                    'expense',
                    'Expenses',
                    '/categories',
                    { type: 'expense' },
                    '💸'
                ),
                createFilterItem(
                    'transfer',
                    'Transfers',
                    '/categories',
                    { type: 'transfer' },
                    '↔️'
                )
            ],
            collapsible: true,
            collapsed: false
        },
        {
            type: 'actions',
            title: 'Quick Actions',
            items: [
                createActionItem(
                    'add-category',
                    'Add Category',
                    () => alert('Add Category functionality to be implemented'),
                    '➕'
                ),
                createActionItem(
                    'bulk-categorize',
                    'Bulk Categorize',
                    () => alert('Bulk categorize functionality to be implemented'),
                    '⚡'
                )
            ],
            collapsible: false
        }
    ]
};
