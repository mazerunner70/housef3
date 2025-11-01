import React from 'react';
import CategoriesDashboard from './CategoriesDashboard';
import './CategoriesPage.css';

/**
 * CategoriesPage - Entry point for the categories domain
 * 
 * Role: Routing jump off point that renders main component
 * Route: /categories
 * 
 * Note: Breadcrumbs are automatically managed by useBreadcrumbSync hook in Layout
 */
const CategoriesPage: React.FC = () => {
    return (
        <div className="categories-page">
            <CategoriesDashboard />
        </div>
    );
};

export default CategoriesPage;


