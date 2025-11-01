/**
 * Import sidebar configuration for Stage 1 implementation
 * 
 * Provides navigation, context, and actions specific to the import workflow
 * Uses the established configuration-based approach with BaseSidebarContent
 */

import { SidebarContentConfig } from '@/components/navigation/sidebar-content/types';
import { createNavItem, createActionItem } from '@/components/navigation/sidebar-content/SidebarConfigFactory';

export const importSidebarConfig: SidebarContentConfig = {
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
                    (pathname) => pathname === '/import/upload' || pathname.startsWith('/import/upload/')
                ),
                createNavItem(
                    'import-history',
                    'Import History',
                    '/import/history',
                    '📊',
                    (pathname) => pathname === '/import/history' || pathname.startsWith('/import/history/')
                ),
                createNavItem(
                    'field-mappings',
                    'Field Mappings',
                    '/import/mappings',
                    '🗂️',
                    (pathname) => pathname === '/import/mappings' || pathname.startsWith('/import/mappings/')
                ),
                createNavItem(
                    'import-settings',
                    'Import Settings',
                    '/import/settings',
                    '⚙️',
                    (pathname) => pathname === '/import/settings' || pathname.startsWith('/import/settings/')
                )
            ]
        },

        // Actions Section - Import-Specific Quick Actions
        {
            type: 'actions',
            title: 'Quick Actions',
            items: [
                createNavItem(
                    'start-import',
                    'Start New Import',
                    '/import/upload',
                    '📤'
                ),
                createActionItem(
                    'download-template',
                    'Download Sample Template',
                    () => {
                        console.log('Download template clicked');
                        // TODO: Implement template download
                        alert('Sample CSV template download coming soon!');
                    },
                    '📄'
                ),
                createNavItem(
                    'view-history',
                    'View Import History',
                    '/import/history',
                    '📊'
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

