/**
 * Sidebar Registration
 * 
 * This file imports and registers all sidebar components.
 * Import this file once in your app entry point to register all sidebars.
 */

import { sidebarRegistry } from './sidebarRegistry';

// Import shared sidebars
import DefaultSidebarContent from './DefaultSidebarContent';

// Import domain-specific sidebars
import AccountsSidebarContent from '@/components/domain/accounts/sidebar/AccountsSidebarContent';
import TransactionsSidebarContent from '@/components/domain/transactions/sidebar/TransactionsSidebarContent';
import CategoriesSidebarContent from '@/components/domain/categories/sidebar/CategoriesSidebarContent';
import TransfersSidebarContent from '@/components/domain/transfers/sidebar/TransfersSidebarContent';
import ImportSidebarContent from '@/components/domain/import/sidebar/ImportSidebarContent';
import FZIPSidebarContent from '@/components/domain/fzip/sidebar/FZIPSidebarContent';

/**
 * Register all sidebars
 * This function should be called once during app initialization
 */
export function registerAllSidebars(): void {
    // Register domain-specific sidebars
    sidebarRegistry.register('accounts', AccountsSidebarContent);
    sidebarRegistry.register('transactions', TransactionsSidebarContent);
    sidebarRegistry.register('categories', CategoriesSidebarContent);
    sidebarRegistry.register('transfers', TransfersSidebarContent);
    sidebarRegistry.register('import', ImportSidebarContent);
    sidebarRegistry.register(['fzip', 'backup'], FZIPSidebarContent);
    sidebarRegistry.register('files', DefaultSidebarContent);

    // Register default sidebar for unmatched routes
    sidebarRegistry.register('default', DefaultSidebarContent);
}

