import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import HomeDashboard from './HomeDashboard';

/**
 * HomePage - Entry point for the home/portfolio overview domain
 * 
 * Role: Routing jump off point that sets up context and renders main component
 * Route: /home, /
 */
const HomePage: React.FC = () => {
    const { goToHome } = useNavigationStore();

    // Set up breadcrumbs/navigation context
    useEffect(() => {
        goToHome();
    }, [goToHome]);

    return <HomeDashboard />;
};

export default HomePage;

