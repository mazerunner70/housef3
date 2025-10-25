import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import FZIPDashboard from './FZIPDashboard';
import './FZIPPage.css';

/**
 * FZIPPage - Entry point for the FZIP backup and restore domain
 * 
 * Role: Routing jump off point that sets up context and renders main component
 * Route: /fzip
 */
const FZIPPage: React.FC = () => {
    const { setBreadcrumb, goToHome } = useNavigationStore();

    // Set up breadcrumbs/navigation context
    useEffect(() => {
        setBreadcrumb([
            { label: 'Home', action: () => goToHome(), level: 0 },
            { label: 'Backup & Restore', action: () => { }, level: 1 }
        ]);
    }, [setBreadcrumb, goToHome]);

    return (
        <div className="fzip-page">
            <FZIPDashboard />
        </div>
    );
};

export default FZIPPage;

