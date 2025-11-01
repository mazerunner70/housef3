import React from 'react';
import { useLocation, useMatches } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import { sidebarRegistry } from './sidebar-content/sidebarRegistry';
import { hasRouteHandle } from '@/routes/types';
import './ContextualSidebar.css';

interface ContextualSidebarProps {
    className?: string;
}

/**
 * ContextualSidebar - Generic sidebar container
 * 
 * Uses a registry pattern to decouple from domain-specific implementations.
 * Sidebars are registered in registerSidebars.ts which is called at app initialization.
 * 
 * Sidebar Selection Logic:
 * 1. Check if current route specifies a sidebar in its handle
 * 2. If not, fall back to first path segment
 * 3. If still not found, use 'default' sidebar
 */
const ContextualSidebar: React.FC<ContextualSidebarProps> = ({ className = '' }) => {
    const location = useLocation();
    const matches = useMatches();
    const { sidebarCollapsed, toggleSidebar } = useNavigationStore();

    // Determine which sidebar content to show based on current route
    const renderSidebarContent = () => {
        let sidebarKey: string | undefined;

        // Strategy 1: Check if route explicitly specifies a sidebar in its handle
        // Look through matches in reverse order (most specific route first)
        for (let i = matches.length - 1; i >= 0; i--) {
            const match = matches[i];
            if (hasRouteHandle(match) && match.handle.sidebar) {
                sidebarKey = match.handle.sidebar;
                break;
            }
        }

        // Strategy 2: Fall back to path-based lookup (first segment)
        if (!sidebarKey) {
            const pathSegments = location.pathname.split('/').filter(Boolean);
            sidebarKey = pathSegments[0] || 'default';
        }

        // Get the sidebar component from the registry
        const SidebarComponent = sidebarRegistry.get(sidebarKey) || sidebarRegistry.get('default');

        if (!SidebarComponent) {
            console.warn(`No sidebar registered for key: ${sidebarKey}`);
            return null;
        }

        return <SidebarComponent sidebarCollapsed={sidebarCollapsed} />;
    };

    return (
        <nav
            className={`contextual-sidebar ${sidebarCollapsed ? 'collapsed' : ''} ${className}`}
            aria-label="Contextual navigation"
        >
            {/* Sidebar header with toggle */}
            <div className="sidebar-header">
                <button
                    className="sidebar-toggle"
                    onClick={toggleSidebar}
                    aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                >
                    {sidebarCollapsed ? '☰' : '×'}
                </button>
                {!sidebarCollapsed && (
                    <h2 className="sidebar-title">Navigation</h2>
                )}
            </div>

            {/* Sidebar content - route-aware */}
            <div className="sidebar-content">
                {renderSidebarContent()}
            </div>
        </nav>
    );
};

export default ContextualSidebar;