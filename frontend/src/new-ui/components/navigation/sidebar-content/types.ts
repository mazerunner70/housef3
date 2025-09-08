/**
 * Configuration types for the sidebar content system
 * Eliminates code duplication across sidebar content components
 */

import { SidebarSectionData } from '@/new-ui/components/navigation/SidebarSection';

// Raw configuration for a sidebar item before processing
export interface SidebarItemConfig {
    id: string;
    label: string;
    icon?: string;
    href?: string; // Navigation URL
    filterParams?: Record<string, string>; // URL search params for filter items
    isActive?: (pathname: string, searchParams: URLSearchParams) => boolean;
    onClick?: () => void; // Custom click handler (overrides href navigation)
    children?: SidebarItemConfig[];
}

// Raw configuration for a sidebar section before processing
export interface SidebarSectionConfig {
    type: 'navigation' | 'context' | 'actions';
    title?: string;
    items: SidebarItemConfig[];
    collapsible?: boolean;
    collapsed?: boolean;
}

// Configuration for an entire sidebar content component
export interface SidebarContentConfig {
    sections: SidebarSectionConfig[];
    // Function to generate dynamic sections based on context
    dynamicSections?: (context: { pathname: string; searchParams: URLSearchParams }) => SidebarSectionConfig[];
}

// Context passed to configuration functions
export interface SidebarContext {
    pathname: string;
    searchParams: URLSearchParams;
    sidebarCollapsed: boolean;
    navigate: (to: string | { pathname?: string; search?: string }) => void;
}

// Factory function type for generating sections
export type SidebarSectionFactory = (context: SidebarContext) => SidebarSectionData[];
