/**
 * Barrel export for shared sidebar configurations
 * Domain-specific configs are now located in their respective domain folders
 */

export { defaultConfig } from './defaultConfig';

// Domain-specific configs are now exported from their respective domains:
// - transactionsConfig: @/components/domain/transactions/sidebar/transactionsConfig
// - transfersConfig: @/components/domain/transfers/sidebar/transfersConfig
// - categoriesConfig: @/components/domain/categories/sidebar/categoriesSidebarConfig
// - importSidebarConfig: @/components/domain/import/sidebar/importSidebarConfig
