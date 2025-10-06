import React from 'react';
import BaseSidebarContent from '@/components/navigation/sidebar-content/BaseSidebarContent';
import { transfersConfig } from './transfersConfig';

interface TransfersSidebarContentProps {
    sidebarCollapsed: boolean;
}

const TransfersSidebarContent: React.FC<TransfersSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={transfersConfig}
        />
    );
};

export default TransfersSidebarContent;
