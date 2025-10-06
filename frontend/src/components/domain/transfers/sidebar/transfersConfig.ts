/**
 * Configuration for Transfers page sidebar content
 * Provides contextual navigation and actions for transfer detection and management
 */

import { SidebarContentConfig } from '@/components/navigation/sidebar-content/types';
import { createNavItem, createFilterItem, createActionItem } from '@/components/navigation/sidebar-content/SidebarConfigFactory';

export const transfersConfig: SidebarContentConfig = {
    sections: [
        {
            type: 'navigation',
            title: 'Transfer Management',
            items: [
                createNavItem(
                    'transfers-overview',
                    'Transfer Overview',
                    '/transfers',
                    '🏠'
                ),
                createNavItem(
                    'all-transactions',
                    'All Transactions',
                    '/transactions',
                    '📋'
                ),
                createNavItem(
                    'accounts',
                    'Account Overview',
                    '/accounts',
                    '🏦'
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'Transfer Detection',
            items: [
                createFilterItem(
                    'recent-transfers',
                    'Recent Transfers (7 days)',
                    '/transfers',
                    { range: '7d' },
                    '🕒'
                ),
                createFilterItem(
                    'monthly-transfers',
                    'Monthly Transfers (30 days)',
                    '/transfers',
                    { range: '30d' },
                    '📅'
                ),
                createFilterItem(
                    'quarterly-transfers',
                    'Quarterly Transfers (90 days)',
                    '/transfers',
                    { range: '90d' },
                    '📊'
                ),
                createFilterItem(
                    'auto-scan',
                    'Auto-Scan Mode',
                    '/transfers',
                    { autoScan: 'true' },
                    '🔍'
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
                    'scan-transfers',
                    'Scan for Transfers',
                    () => {
                        // Trigger transfer scan - this will be handled by the TransfersDashboard component
                        const event = new CustomEvent('triggerTransferScan');
                        window.dispatchEvent(event);
                    },
                    '🔍'
                ),
                createActionItem(
                    'view-progress',
                    'View Scan Progress',
                    () => {
                        // Scroll to progress section
                        const progressSection = document.querySelector('.date-range-info-panel');
                        if (progressSection) {
                            progressSection.scrollIntoView({ behavior: 'smooth' });
                        }
                    },
                    '📈'
                ),
                createActionItem(
                    'export-transfers',
                    'Export Transfer Data',
                    () => alert('Export transfer data functionality to be implemented'),
                    '📤'
                )
            ],
            collapsible: false
        },
        {
            type: 'context',
            title: 'Help & Tips',
            items: [
                createActionItem(
                    'transfer-help',
                    'How Transfer Detection Works',
                    () => {
                        // Could open a help modal or navigate to documentation
                        alert('Transfer detection matches outgoing and incoming transactions of similar amounts within a few days of each other across different accounts.');
                    },
                    '❓'
                ),
                createActionItem(
                    'best-practices',
                    'Best Practices',
                    () => {
                        alert('For best results: 1) Ensure all accounts are up to date, 2) Scan systematically using recommended date ranges, 3) Review matches carefully before marking as transfers.');
                    },
                    '💡'
                )
            ],
            collapsible: true,
            collapsed: true
        }
    ]
};
