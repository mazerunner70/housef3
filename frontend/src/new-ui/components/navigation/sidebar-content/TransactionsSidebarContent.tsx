import React from 'react';
import BaseSidebarContent from './BaseSidebarContent';
import { transactionsConfig } from './configs';

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
