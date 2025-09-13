/**
 * Configuration for Import Transactions page sidebar content
 * Provides import-specific navigation and tools
 */

import { SidebarContentConfig } from '../types';
import { createNavItem, createActionItem } from '../SidebarConfigFactory';

export const importConfig: SidebarContentConfig = {
    sections: [
        {
            type: 'navigation',
            title: 'Import Tools',
            items: [
                createNavItem(
                    'import-overview',
                    'Import Overview',
                    '/import',
                    '📤',
                    (pathname) => pathname === '/import'
                ),
                createNavItem(
                    'import-history',
                    'Import History',
                    '/import/history',
                    '📊'
                ),
                createNavItem(
                    'field-mappings',
                    'Field Mappings',
                    '/import/mappings',
                    '🗂️'
                ),
                createNavItem(
                    'import-settings',
                    'Import Settings',
                    '/import/settings',
                    '⚙️'
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'Account Management',
            items: [
                createNavItem(
                    'view-accounts',
                    'View All Accounts',
                    '/accounts',
                    '🏦'
                ),
                createNavItem(
                    'stale-accounts',
                    'Accounts Needing Updates',
                    '/accounts?filter=stale',
                    '⚠️'
                ),
                createNavItem(
                    'recent-imports',
                    'Recent Imports',
                    '/files?filter=recent',
                    '📁'
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
                    'Add New Account',
                    () => {
                        // TODO: Implement add account modal/dialog
                        alert('Add Account functionality coming soon!');
                    },
                    '➕'
                ),
                createActionItem(
                    'refresh-accounts',
                    'Refresh Account Data',
                    () => {
                        // TODO: Implement account refresh
                        window.location.reload();
                    },
                    '🔄'
                ),
                createNavItem(
                    'help-import',
                    'Import Help & Guides',
                    '/help/import',
                    '❓'
                )
            ],
            collapsible: false
        }
    ]
};
