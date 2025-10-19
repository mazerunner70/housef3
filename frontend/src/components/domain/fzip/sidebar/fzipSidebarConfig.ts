/**
 * Configuration for FZIP Backup & Restore sidebar content
 */

import { SidebarContentConfig } from '@/components/navigation/sidebar-content/types';
import { createNavItem } from '@/components/navigation/sidebar-content/SidebarConfigFactory';

export const fzipConfig: SidebarContentConfig = {
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
                ),
                createNavItem(
                    'fzip',
                    'Backup & Restore',
                    '/fzip',
                    '💾',
                    (pathname) => pathname.startsWith('/fzip') || pathname.startsWith('/backup')
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'FZIP Operations',
            items: [
                createNavItem(
                    'fzip-info',
                    'About FZIP',
                    '/fzip',
                    'ℹ️'
                )
            ],
            collapsible: true,
            collapsed: false
        }
    ]
};



