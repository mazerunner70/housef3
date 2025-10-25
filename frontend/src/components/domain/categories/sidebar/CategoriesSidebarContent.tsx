import React from 'react';
import BaseSidebarContent from '@/components/navigation/sidebar-content/BaseSidebarContent';
import { categoriesSidebarConfig } from './categoriesSidebarConfig';

interface CategoriesSidebarContentProps {
    sidebarCollapsed: boolean;
}

const CategoriesSidebarContent: React.FC<CategoriesSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={categoriesSidebarConfig}
        />
    );
};

export default CategoriesSidebarContent;
