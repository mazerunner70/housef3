/**
 * Configuration for Default/Home page sidebar content
 * Replaces DefaultSidebarContent.tsx with declarative configuration
 */

import { SidebarContentConfig } from '../types';
import { createNavItem, createFilterItem, createActionItem } from '../SidebarConfigFactory';
import { mainNavigationSection } from './sharedNavigation';

export const defaultConfig: SidebarContentConfig = {
    sections: [
        mainNavigationSection,
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
