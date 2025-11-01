/**
 * ImportSidebarContent - Contextual sidebar for import workflow
 * 
 * Stage 1 Implementation:
 * - Uses configuration-based approach with BaseSidebarContent
 * - Provides import-specific navigation and tools
 * - Dynamic sections for import status and recent activity
 * - Integration with existing navigation system
 * - Follows established sidebar conventions
 */

import React from 'react';
import BaseSidebarContent from '@/components/navigation/sidebar-content/BaseSidebarContent';
import { importSidebarConfig } from './importSidebarConfig';

interface ImportSidebarContentProps {
    sidebarCollapsed: boolean;
}

/**
 * Sidebar content component for import workflow pages
 * Leverages the established configuration-based approach to eliminate code duplication
 */
const ImportSidebarContent: React.FC<ImportSidebarContentProps> = ({
    sidebarCollapsed
}) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={importSidebarConfig}
        />
    );
};

export default ImportSidebarContent;

