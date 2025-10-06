/**
 * Domain: Transfers
 * 
 * This module contains all transfer-related components, organized according to the
 * component organization strategy. These are domain-specific components that handle
 * transfer detection, management, and analytics.
 */

// Main components
export { default as TransfersPage } from './TransfersPage';
export { default as TransfersDashboard } from './TransfersDashboard';

// Transfer management components
export { default as TransferResultsDashboard } from './TransferResultsDashboard';
export { default as TransferAnalyticsDashboard } from './TransferAnalyticsDashboard';
export { default as TransferProgressDashboard } from './TransferProgressDashboard';
export { default as ScanControlsPanel } from './ScanControlsPanel';

// Sidebar components
export { default as TransfersSidebarContent } from './sidebar/TransfersSidebarContent';
export { transfersConfig } from './sidebar/transfersConfig';

// Hooks
export * from './hooks/useTransferPreferences';
