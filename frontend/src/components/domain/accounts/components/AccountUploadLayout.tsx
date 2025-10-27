import React from 'react';
import './AccountUploadLayout.css';

interface AccountUploadLayoutProps {
    children: React.ReactNode;
    className?: string;
}

/**
 * AccountUploadLayout - Provides overall page structure for account file upload
 * 
 * Features:
 * - Responsive layout with proper spacing
 * - Consistent styling with existing design system
 * - Optimized for file upload workflow
 * - Mobile-friendly responsive design
 * 
 * Layout Structure:
 * - Main container with proper margins and padding
 * - Responsive grid system
 * - Proper spacing between sections
 * - Accessibility considerations
 */
const AccountUploadLayout: React.FC<AccountUploadLayoutProps> = ({
    children,
    className = ''
}) => {
    return (
        <div className={`account-upload-layout ${className}`}>
            <div className="account-upload-content-wrapper">
                {children}
            </div>
        </div>
    );
};

export default AccountUploadLayout;
