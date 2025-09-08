/**
 * Base sidebar content component that eliminates code duplication
 * Uses configuration objects to generate dynamic sidebar sections
 */

import React, { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import SidebarSection from '@/new-ui/components/navigation/SidebarSection';
import { createSidebarSections } from './SidebarConfigFactory';
import { SidebarContentConfig, SidebarContext } from './types';

interface BaseSidebarContentProps {
    sidebarCollapsed: boolean;
    config: SidebarContentConfig;
}

/**
 * Reusable sidebar content component that processes configurations
 * Eliminates the 292 lines of duplication across sidebar components
 */
const BaseSidebarContent: React.FC<BaseSidebarContentProps> = ({
    sidebarCollapsed,
    config
}) => {
    const location = useLocation();
    const navigate = useNavigate();

    // Generate sidebar sections from configuration
    const sections = useMemo(() => {
        const searchParams = new URLSearchParams(location.search);
        const context: SidebarContext = {
            pathname: location.pathname,
            searchParams,
            sidebarCollapsed,
            navigate
        };

        return createSidebarSections(config, context);
    }, [location.search, sidebarCollapsed, config, navigate]);

    return (
        <>
            {sections.map((section, index) => (
                <SidebarSection
                    key={`${section.type}-${index}`}
                    section={section}
                    sidebarCollapsed={sidebarCollapsed}
                />
            ))}
        </>
    );
};

export default BaseSidebarContent;
