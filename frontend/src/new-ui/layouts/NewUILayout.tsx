import React from 'react';
import './NewUILayout.css'; // We'll create this for basic styling
import { Outlet, NavLink } from 'react-router-dom';
import logoImage from '../assets/logo1.png'; // Import the logo
import ContextualSidebar from '@/new-ui/components/navigation/ContextualSidebar';
import { useNavigationStore } from '@/stores/navigationStore';

interface NewUILayoutProps {
  onSignOut: () => void;
}

const NewUILayout: React.FC<NewUILayoutProps> = ({ onSignOut }) => {
  const { sidebarCollapsed, setSidebarCollapsed } = useNavigationStore();
  const [isMobileView, setIsMobileView] = React.useState(false);

  // Handle responsive sidebar behavior
  React.useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 768;
      const isTablet = window.innerWidth >= 768 && window.innerWidth < 1200;
      const isSmallScreen = isMobile || isTablet;

      setIsMobileView(isSmallScreen);

      if (isSmallScreen) {
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
    <div className="new-ui-layout">
      <header className="new-ui-header">
        <NavLink to="/">
          <img src={logoImage} alt="App Logo" className="new-ui-logo" />
        </NavLink>
        <h1 className="new-ui-title">Modern Finance App</h1>
        <button onClick={onSignOut} className="header-sign-out-button">Sign Out</button>
      </header>
      <div className="new-ui-layout-content">
        <ContextualSidebar />
        <main className="new-ui-main-content">
          <Outlet />
        </main>

        {/* Mobile overlay when sidebar is open on small screens */}
        {!sidebarCollapsed && isMobileView && (
          <div
            className="sidebar-overlay"
            role="button"
            tabIndex={0}
            aria-label="Close sidebar overlay"
            onClick={() => setSidebarCollapsed(true)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setSidebarCollapsed(true);
              } else if (e.key === 'Escape') {
                e.preventDefault();
                setSidebarCollapsed(true);
              }
            }}
          />
        )}
      </div>
      <footer className="new-ui-footer">
        <p>&copy; 2024 Your App Name</p>
      </footer>
    </div>
  );
};

export default NewUILayout; 