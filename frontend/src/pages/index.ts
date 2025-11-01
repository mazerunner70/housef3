/**
 * Central barrel export for all page components
 * Consolidates imports from different locations (pages/, domain/, views/)
 * Makes App.tsx and route configuration cleaner
 */

// App-level and multi-feature pages (from pages/)
export { default as TransactionsPage } from './TransactionsPage';
export * from './PlaceholderPage';

// Domain pages (from components/domain/)
export { default as HomePage } from '@/components/domain/home/HomePage';
export { default as AccountsPage } from '@/components/domain/accounts/AccountsPage';
export { default as TransfersPage } from '@/components/domain/transfers/TransfersPage';
export { default as CategoriesPage } from '@/components/domain/categories/CategoriesPage';
export { default as ImportPage } from '@/components/domain/import/ImportPage';
export { default as AccountFileUploadPage } from '@/components/domain/accounts/AccountFileUploadPage';
export { default as FZIPPage } from '@/components/domain/fzip/FZIPPage';

// Views
export { default as AnalyticsView } from '@/views/AnalyticsView';

