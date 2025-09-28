import React from 'react';
import BaseSidebarContent from './BaseSidebarContent';
import { transfersConfig } from './configs';

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
