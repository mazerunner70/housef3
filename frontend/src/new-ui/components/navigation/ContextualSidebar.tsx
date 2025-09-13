import React from 'react';
import { useLocation } from 'react-router-dom';
import { useNavigationStore } from '@/stores/navigationStore';
import AccountsSidebarContent from './sidebar-content/AccountsSidebarContent';
import TransactionsSidebarContent from './sidebar-content/TransactionsSidebarContent';
import CategoriesSidebarContent from './sidebar-content/CategoriesSidebarContent';
import ImportSidebarContent from './sidebar-content/ImportSidebarContent';
import DefaultSidebarContent from './sidebar-content/DefaultSidebarContent';
import './ContextualSidebar.css';

interface ContextualSidebarProps {
    className?: string;
}

const ContextualSidebar: React.FC<ContextualSidebarProps> = ({ className = '' }) => {
    const location = useLocation();
    const { sidebarCollapsed, toggleSidebar, breadcrumb } = useNavigationStore();

    // Determine which sidebar content to show based on current route
    const renderSidebarContent = () => {
        const pathSegments = location.pathname.split('/').filter(Boolean);
        const route = pathSegments[0];

        switch (route) {
            case 'accounts':
                return <AccountsSidebarContent sidebarCollapsed={sidebarCollapsed} />;
            case 'transactions':
                return <TransactionsSidebarContent sidebarCollapsed={sidebarCollapsed} />;
            case 'categories':
                return <CategoriesSidebarContent sidebarCollapsed={sidebarCollapsed} />;
            case 'import':
                return <ImportSidebarContent sidebarCollapsed={sidebarCollapsed} />;
            case 'files':
                // For now, files can use the default content, but could have its own component later
                return <DefaultSidebarContent sidebarCollapsed={sidebarCollapsed} />;
            default:
                // Home page and other routes
                return <DefaultSidebarContent sidebarCollapsed={sidebarCollapsed} />;
        }
    };

    return (
        <>
            <aside
                className={`contextual-sidebar ${sidebarCollapsed ? 'collapsed' : ''} ${className}`}
                role="navigation"
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
            </aside>
        </>
    );
};

export default ContextualSidebar;