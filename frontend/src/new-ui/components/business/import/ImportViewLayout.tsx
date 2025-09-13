import React from 'react';
import './ImportViewLayout.css';

interface ImportViewLayoutProps {
    children: React.ReactNode;
    className?: string;
}

/**
 * ImportViewLayout - Provides the overall page structure and responsive layout for import pages
 * 
 * Features:
 * - Responsive grid layout
 * - Consistent spacing and structure
 * - Mobile-first design approach
 */
const ImportViewLayout: React.FC<ImportViewLayoutProps> = ({
    children,
    className = ''
}) => {
    return (
        <div className={`import-transactions-container ${className}`}>
            <div className="import-content-wrapper">
                {children}
            </div>
        </div>
    );
};

export default ImportViewLayout;
