import React from 'react';
import ImportDashboard from './ImportDashboard';

/**
 * ImportPage - Entry point for the import domain
 * 
 * Role: Routing jump off point that renders main component
 * Route: /import
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 * 
 * This follows the domain conventions:
 * - Thin entry point (5-20 lines typical)
 * - Renders main domain component
 * - No business logic
 */
const ImportPage: React.FC = () => {
    return <ImportDashboard />;
};

export default ImportPage;
