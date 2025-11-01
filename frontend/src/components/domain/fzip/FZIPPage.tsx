import React from 'react';
import FZIPDashboard from './FZIPDashboard';
import './FZIPPage.css';

/**
 * FZIPPage - Entry point for the FZIP backup and restore domain
 * 
 * Role: Routing jump off point that renders main component
 * Route: /fzip
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const FZIPPage: React.FC = () => {
    return (
        <div className="fzip-page">
            <FZIPDashboard />
        </div>
    );
};

export default FZIPPage;

