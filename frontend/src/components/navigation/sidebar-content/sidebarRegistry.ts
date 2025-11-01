/**
 * Sidebar Registry
 * 
 * Provides a decoupled way for domain-specific sidebars to register themselves
 * without ContextualSidebar needing to know about all implementations.
 */

import React from 'react';

interface SidebarContentProps {
    sidebarCollapsed: boolean;
}

type SidebarComponent = React.ComponentType<SidebarContentProps>;

interface SidebarRegistryEntry {
    component: SidebarComponent;
    routes: string[]; // Route patterns this sidebar handles
}

class SidebarRegistry {
    private registry: Map<string, SidebarComponent> = new Map();

    /**
     * Register a sidebar component for specific routes
     */
    register(routes: string | string[], component: SidebarComponent): void {
        const routeArray = Array.isArray(routes) ? routes : [routes];
        routeArray.forEach(route => {
            this.registry.set(route, component);
        });
    }

    /**
     * Get the sidebar component for a specific route
     */
    get(route: string): SidebarComponent | undefined {
        return this.registry.get(route);
    }

    /**
     * Check if a sidebar is registered for a route
     */
    has(route: string): boolean {
        return this.registry.has(route);
    }
}

// Export singleton instance
export const sidebarRegistry = new SidebarRegistry();

