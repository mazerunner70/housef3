/**
 * Shared navigation items used across multiple sidebar configurations
 * Eliminates duplication between different domain-specific sidebar configs
 */

import { SidebarSectionConfig } from '../types';
import { createNavItem } from '../SidebarConfigFactory';

/**
 * Main navigation section shared across all sidebar configurations
 * Contains primary app navigation links
 */
export const mainNavigationSection: SidebarSectionConfig = {
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
};

