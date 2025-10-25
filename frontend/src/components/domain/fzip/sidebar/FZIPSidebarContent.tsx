import React from 'react';
import BaseSidebarContent from '@/components/navigation/sidebar-content/BaseSidebarContent';
import { fzipConfig } from './fzipSidebarConfig';

interface FZIPSidebarContentProps {
    sidebarCollapsed: boolean;
}

/**
 * FZIPSidebarContent - Sidebar content for FZIP backup and restore pages
 * 
 * Provides navigation and context-specific actions for FZIP operations
 */
const FZIPSidebarContent: React.FC<FZIPSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={fzipConfig}
        />
    );
};

export default FZIPSidebarContent;



