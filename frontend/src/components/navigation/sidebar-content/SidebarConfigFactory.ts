/**
 * Factory functions to convert sidebar configurations to processed section data
 * Handles navigation logic, active state detection, and section generation
 */

import { SidebarSectionData } from '@/components/navigation/SidebarSection';
import { SidebarItemData } from '@/components/navigation/SidebarItem';
import {
    SidebarContentConfig,
    SidebarSectionConfig,
    SidebarItemConfig,
    SidebarContext
} from './types';

/**
 * Default navigation handler using React Router navigate
 */
const defaultNavigate = (href: string, navigate: (to: string) => void): void => {
    navigate(href);
};

/**
 * Default active state detection - checks if pathname starts with href
 */
const defaultIsActive = (href: string, pathname: string): boolean => {
    if (href === '/') {
        return pathname === '/' || pathname === '/home';
    }
    return pathname.startsWith(href);
};

/**
 * Converts a sidebar item configuration to processed item data
 */
const processItemConfig = (
    config: SidebarItemConfig,
    context: SidebarContext,
    level: number = 0
): SidebarItemData => {
    const { pathname, searchParams, navigate } = context;

    // Determine if item is active
    let isActive = false;
    if (config.isActive) {
        isActive = config.isActive(pathname, searchParams);
    } else if (config.href) {
        isActive = defaultIsActive(config.href, pathname);
    }

    // Create click handler
    let onClick: () => void;

    if (config.onClick) {
        onClick = config.onClick;
    } else if (config.filterParams && config.href) {
        // Handle filter navigation with React Router navigate
        onClick = () => {
            const newSearchParams = new URLSearchParams();

            // Add filter params to search
            Object.entries(config.filterParams!).forEach(([key, value]) => {
                newSearchParams.set(key, value);
            });

            const search = newSearchParams.toString();
            navigate({
                pathname: config.href!,
                search: search ? `?${search}` : ''
            });
        };
    } else if (config.href) {
        onClick = () => defaultNavigate(config.href!, navigate);
    } else {
        onClick = () => { };
    }

    // Process children if they exist
    const children = config.children?.map(child =>
        processItemConfig(child, context, level + 1)
    );

    return {
        id: config.id,
        label: config.label,
        icon: config.icon,
        active: isActive,
        onClick,
        children,
        level
    };
};

/**
 * Converts a sidebar section configuration to processed section data
 */
const processSectionConfig = (
    config: SidebarSectionConfig,
    context: SidebarContext
): SidebarSectionData => {
    return {
        type: config.type,
        title: config.title,
        items: config.items.map(item => processItemConfig(item, context)),
        collapsible: config.collapsible,
        collapsed: config.collapsed
    };
};

/**
 * Main factory function that converts a sidebar content configuration to processed sections
 */
export const createSidebarSections = (
    config: SidebarContentConfig,
    context: SidebarContext
): SidebarSectionData[] => {
    const { pathname, searchParams } = context;
    const sections: SidebarSectionData[] = [];

    // Process static sections
    for (const sectionConfig of config.sections) {
        sections.push(processSectionConfig(sectionConfig, context));
    }

    // Process dynamic sections if they exist
    if (config.dynamicSections) {
        const dynamicSections = config.dynamicSections({ pathname, searchParams });
        for (const dynamicSection of dynamicSections) {
            sections.push(processSectionConfig(dynamicSection, context));
        }
    }

    return sections;
};

/**
 * Helper function to create a basic navigation item configuration
 */
export const createNavItem = (
    id: string,
    label: string,
    href: string,
    icon?: string,
    isActive?: (pathname: string, searchParams: URLSearchParams) => boolean
): SidebarItemConfig => ({
    id,
    label,
    href,
    icon,
    isActive
});

/**
 * Helper function to create an action item configuration
 */
export const createActionItem = (
    id: string,
    label: string,
    onClick: () => void,
    icon?: string
): SidebarItemConfig => ({
    id,
    label,
    onClick,
    icon
});

/**
 * Helper function to create a filter item that modifies URL search params
 * Uses React Router navigate instead of full page reloads
 */
export const createFilterItem = (
    id: string,
    label: string,
    baseUrl: string,
    filterParams: Record<string, string>,
    icon?: string,
    isActive?: (pathname: string, searchParams: URLSearchParams) => boolean
): SidebarItemConfig => {
    return {
        id,
        label,
        icon,
        isActive: isActive || ((pathname, searchParams) => {
            if (pathname !== baseUrl.split('?')[0]) return false;

            // Check if all filter params match current search params
            return Object.entries(filterParams).every(([key, value]) =>
                searchParams.get(key) === value
            );
        }),
        onClick: () => {
            // This will be replaced in processItemConfig with actual navigate function
            // Storing the navigation data for the processor to handle
        },
        // Store navigation data for processing
        href: baseUrl,
        filterParams
    };
};
