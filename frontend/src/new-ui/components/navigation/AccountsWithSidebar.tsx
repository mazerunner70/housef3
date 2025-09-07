import React from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import ContextualSidebar from '@/new-ui/components/navigation/ContextualSidebar';
import MainContent from '@/new-ui/components/navigation/MainContent';
import './AccountsWithSidebar.css';

interface AccountsWithSidebarProps {
    className?: string;
}

const AccountsWithSidebar: React.FC<AccountsWithSidebarProps> = ({ className = '' }) => {
    const { sidebarCollapsed, setSidebarCollapsed } = useNavigationStore();

    // Handle responsive sidebar behavior
    React.useEffect(() => {
        const handleResize = () => {
            const isMobile = window.innerWidth < 768;
            const isTablet = window.innerWidth >= 768 && window.innerWidth < 1200;

            if (isMobile || isTablet) {
                // On mobile/tablet, sidebar should be collapsed by default
                setSidebarCollapsed(true);
            }
        };

        // Set initial state
        handleResize();

        // Listen for resize events
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [setSidebarCollapsed]);

    return (
        <div className={`accounts-layout ${className}`}>
            <ContextualSidebar />
            <MainContent />

            {/* Mobile overlay when sidebar is open */}
            {!sidebarCollapsed && (
                <div
                    className="sidebar-overlay"
                    onClick={() => setSidebarCollapsed(true)}
                    aria-hidden="true"
                />
            )}
        </div>
    );
};

export default AccountsWithSidebar;
