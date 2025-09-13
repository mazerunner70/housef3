/**
 * Import sidebar configuration for Stage 1 implementation
 * 
 * Provides navigation, context, and actions specific to the import workflow
 * Uses the established configuration-based approach with BaseSidebarContent
 */

import { SidebarContentConfig } from '../types';
import { createNavItem, createActionItem } from '../SidebarConfigFactory';

export const importConfig: SidebarContentConfig = {
    sections: [
        // Navigation Section - Import Tools
        {
            type: 'navigation',
            title: 'Import Tools',
            items: [
                createNavItem(
                    'upload-file',
                    'Upload File',
                    '/import/upload',
                    '📤',
                    // Custom active check for upload functionality
                    (pathname) => pathname.includes('/import/upload')
                ),
                createNavItem(
                    'import-history',
                    'Import History',
                    '/import/history',
                    '📊',
                    (pathname) => pathname.includes('/import/history')
                ),
                createNavItem(
                    'field-mappings',
                    'Field Mappings',
                    '/import/mappings',
                    '🗂️',
                    (pathname) => pathname.includes('/import/mappings')
                ),
                createNavItem(
                    'import-settings',
                    'Import Settings',
                    '/import/settings',
                    '⚙️',
                    (pathname) => pathname.includes('/import/settings')
                )
            ]
        },

        // Actions Section - Quick Actions
        {
            type: 'actions',
            title: 'Quick Actions',
            items: [
                createActionItem(
                    'add-account',
                    'Add New Account',
                    () => {
                        console.log('Add new account clicked');
                        // TODO: Implement account creation dialog
                        alert('Account creation functionality coming soon!');
                    },
                    '🏦'
                ),
                createActionItem(
                    'refresh-accounts',
                    'Refresh Account Data',
                    () => {
                        console.log('Refresh accounts clicked');
                        // TODO: Implement account data refresh
                        window.location.reload();
                    },
                    '🔄'
                ),
                createNavItem(
                    'view-accounts',
                    'View All Accounts',
                    '/accounts',
                    '📈'
                )
            ]
        }
    ],

    // Dynamic sections for import status and recent activity
    dynamicSections: () => {
        const sections = [];

        // Context Section - Import Status & Recent Activity
        // This will be enhanced in Stage 2 with real import status data
        const contextItems = [];

        // Placeholder for import status (Stage 1)
        contextItems.push({
            id: 'import-status-placeholder',
            label: 'No Active Imports',
            icon: '⏸️',
            onClick: () => {
                console.log('Import status clicked');
            }
        });

        // Placeholder for recent imports (Stage 1)
        contextItems.push({
            id: 'recent-imports-placeholder',
            label: 'View Recent Imports',
            icon: '📋',
            onClick: () => {
                console.log('Recent imports clicked');
                // TODO: Navigate to import history
            }
        });

        // Add help and documentation
        contextItems.push({
            id: 'import-help',
            label: 'Import Help & Guide',
            icon: '❓',
            onClick: () => {
                console.log('Import help clicked');
                // TODO: Open help documentation
                alert('Import help documentation coming soon!');
            }
        });

        sections.push({
            type: 'context' as const,
            title: 'Import Status',
            items: contextItems
        });

        return sections;
    }
};

export default importConfig;