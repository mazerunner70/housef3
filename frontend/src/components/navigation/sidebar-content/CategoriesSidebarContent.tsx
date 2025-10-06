import React from 'react';
import BaseSidebarContent from './BaseSidebarContent';
import { categoriesConfig } from './configs';

interface CategoriesSidebarContentProps {
    sidebarCollapsed: boolean;
}

const CategoriesSidebarContent: React.FC<CategoriesSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={categoriesConfig}
        />
    );
};

export default CategoriesSidebarContent;
