import React from 'react';
import BaseSidebarContent from './BaseSidebarContent';
import { defaultConfig } from './configs';

interface DefaultSidebarContentProps {
    sidebarCollapsed: boolean;
}

const DefaultSidebarContent: React.FC<DefaultSidebarContentProps> = ({ sidebarCollapsed }) => {
    return (
        <BaseSidebarContent
            sidebarCollapsed={sidebarCollapsed}
            config={defaultConfig}
        />
    );
};

export default DefaultSidebarContent;
