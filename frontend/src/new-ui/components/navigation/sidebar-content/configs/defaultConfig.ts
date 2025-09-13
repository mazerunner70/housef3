/**
 * Configuration for Default/Home page sidebar content
 * Replaces DefaultSidebarContent.tsx with declarative configuration
 */

import { SidebarContentConfig } from '../types';
import { createNavItem, createFilterItem, createActionItem } from '../SidebarConfigFactory';

export const defaultConfig: SidebarContentConfig = {
    sections: [
        {
            type: 'navigation',
            title: 'Main Navigation',
            items: [
                createNavItem(
                    'home',
                    'Portfolio Overview',
                    '/',
                    '🏠',
                    (pathname) => pathname === '/' || pathname === '/home'
                ),
                createNavItem(
                    'accounts',
                    'Accounts',
                    '/accounts',
                    '🏦',
                    (pathname) => pathname.startsWith('/accounts')
                ),
                createNavItem(
                    'transactions',
                    'Transactions',
                    '/transactions',
                    '📋',
                    (pathname) => pathname.startsWith('/transactions')
                ),
                createNavItem(
                    'categories',
                    'Categories',
                    '/categories',
                    '🏷️',
                    (pathname) => pathname.startsWith('/categories')
                ),
                createNavItem(
                    'files',
                    'Files',
                    '/files',
                    '📁',
                    (pathname) => pathname.startsWith('/files')
                ),
                createNavItem(
                    'import',
                    'Import Transactions',
                    '/import',
                    '📥',
                    (pathname) => pathname.startsWith('/import')
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'Quick Stats',
            items: [
                createNavItem(
                    'total-accounts',
                    'View All Accounts',
                    '/accounts',
                    '📊'
                ),
                createFilterItem(
                    'recent-transactions',
                    'Recent Transactions',
                    '/transactions',
                    { filter: 'recent' },
                    '🕒'
                ),
                createFilterItem(
                    'uncategorized',
                    'Uncategorized Items',
                    '/transactions',
                    { filter: 'uncategorized' },
                    '❓'
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
                    'add-account',
                    'Add Account',
                    () => alert('Add Account functionality to be implemented'),
                    '➕'
                ),
                createNavItem(
                    'import-transactions',
                    'Import Transactions',
                    '/import',
                    '📥',
                    (pathname) => pathname.startsWith('/import')
                )
            ],
            collapsible: false
        }
    ]
};
