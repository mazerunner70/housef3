import React from 'react';
import BaseSidebarContent from '@/components/navigation/sidebar-content/BaseSidebarContent';
import { transactionsConfig } from './transactionsConfig';

interface TransactionsSidebarContentProps {
    sidebarCollapsed: boolean;
}

const TransactionsSidebarContent: React.FC<TransactionsSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={transactionsConfig}
        />
    );
};

export default TransactionsSidebarContent;

