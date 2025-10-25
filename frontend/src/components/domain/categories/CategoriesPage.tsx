import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import CategoriesDashboard from './CategoriesDashboard';
import './CategoriesPage.css';

/**
 * CategoriesPage - Entry point for the categories domain
 * 
 * Role: Routing jump off point that sets up context and renders main component
 * Route: /categories
 */
const CategoriesPage: React.FC = () => {
    const { goToCategories } = useNavigationStore();

    // Set up breadcrumbs/navigation context
    useEffect(() => {
        goToCategories();
    }, [goToCategories]);

    return (
        <div className="categories-page">
            <CategoriesDashboard />
        </div>
    );
};

export default CategoriesPage;


