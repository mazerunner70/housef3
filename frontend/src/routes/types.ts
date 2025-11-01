/**
 * Route Handle Types
 * 
 * Extends React Router's handle property to include:
 * - breadcrumb: Function to render breadcrumb for this route
 * - sidebar: Key to identify which sidebar to use for this route
 */

import { UIMatch } from 'react-router-dom';

export interface RouteHandle {
    /**
     * Function to render breadcrumb for this route
     * Receives the route match which includes params, pathname, and loader data
     */
    breadcrumb?: (match: UIMatch) => React.ReactNode;

    /**
     * Sidebar key - identifies which sidebar to display for this route
     * This key is used to lookup the sidebar component from the registry
     * 
     * Examples: 'accounts', 'transactions', 'categories', 'import', etc.
     * 
     * If not specified, falls back to using the first path segment
     */
    sidebar?: string;
}

/**
 * Type guard to check if a route match has our extended handle
 */
export function hasRouteHandle(match: UIMatch): match is UIMatch & { handle: RouteHandle } {
    return match.handle !== undefined;
}

