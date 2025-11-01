import React from 'react';
import HomeDashboard from './HomeDashboard';

/**
 * HomePage - Entry point for the home/portfolio overview domain
 * 
 * Role: Routing jump off point that renders main component
 * Route: /home, /
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const HomePage: React.FC = () => {
    return <HomeDashboard />;
};

export default HomePage;

