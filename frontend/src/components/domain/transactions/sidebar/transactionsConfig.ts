/**
 * Configuration for Transactions page sidebar content
 * Replaces TransactionsSidebarContent.tsx with declarative configuration
 */

import { SidebarContentConfig } from '@/components/navigation/sidebar-content/types';
import { createNavItem, createFilterItem, createActionItem } from '@/components/navigation/sidebar-content/SidebarConfigFactory';

export const transactionsConfig: SidebarContentConfig = {
    sections: [
        {
            type: 'navigation',
            title: 'Transaction Views',
            items: [
                createNavItem(
                    'transactions-list',
                    'All Transactions',
                    '/transactions',
                    '📋'
                ),
                createNavItem(
                    'category-management',
                    'Category Management',
                    '/categories',
                    '🏷️'
                ),
                createNavItem(
                    'imports',
                    'Imports & Statements',
                    '/import',
                    '📥'
                ),
                createNavItem(
                    'transfers',
                    'Transfer Detection',
                    '/transfers',
                    '↔️'
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'Quick Filters',
            items: [
                createFilterItem(
                    'recent',
                    'Recent (30 days)',
                    '/transactions',
                    { filter: 'recent' },
                    '🕒'
                ),
                createFilterItem(
                    'uncategorized',
                    'Uncategorized',
                    '/transactions',
                    { filter: 'uncategorized' },
                    '❓'
                ),
                createFilterItem(
                    'large-amounts',
                    'Large Amounts',
                    '/transactions',
                    { filter: 'large' },
                    '💰'
                )
            ],
            collapsible: true,
            collapsed: true
        },
        {
            type: 'actions',
            title: 'Quick Actions',
            items: [
                createActionItem(
                    'add-transaction',
                    'Add Transaction',
                    () => alert('Add Transaction functionality to be implemented'),
                    '➕'
                ),
                createActionItem(
                    'export-data',
                    'Export Data',
                    () => alert('Export functionality to be implemented'),
                    '📤'
                )
            ],
            collapsible: false
        }
    ]
};

