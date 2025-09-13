import React from 'react';
import BaseSidebarContent from '@/new-ui/components/navigation/sidebar-content/BaseSidebarContent';
import { importConfig } from '@/new-ui/components/navigation/sidebar-content/configs/importConfig';

interface ImportSidebarContentProps {
    sidebarCollapsed: boolean;
}

/**
 * ImportSidebarContent - Contextual sidebar for import transactions workflow
 * 
 * Features:
 * - Import-specific navigation and tools
 * - Quick actions for account management
 * - Context-aware content based on import status
 * - Follows established sidebar patterns
 */
const ImportSidebarContent: React.FC<ImportSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={importConfig}
        />
    );
};

export default ImportSidebarContent;
