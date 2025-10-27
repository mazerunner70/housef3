import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import ImportDashboard from './ImportDashboard';

/**
 * ImportPage - Entry point for the import domain
 * 
 * Role: Routing jump off point that sets up context and renders main component
 * Route: /import
 * 
 * This follows the domain conventions:
 * - Thin entry point (5-20 lines typical)
 * - Sets up breadcrumbs/navigation context
 * - Renders main domain component
 * - No business logic
 */
const ImportPage: React.FC = () => {
    const { goToImport } = useNavigationStore();

    // Set up breadcrumbs/navigation context
    useEffect(() => {
        goToImport?.();
    }, [goToImport]);

    return <ImportDashboard />;
};

export default ImportPage;
