import React from 'react';
import { useParams, useLocation } from 'react-router-dom';
import './PlaceholderPage.css';

interface PlaceholderPageProps {
    title: string;
    description?: string;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({ title, description }) => {
    const params = useParams();
    const location = useLocation();

    return (
        <div className="placeholder-page">
            <div className="placeholder-content">
                <div className="placeholder-header">
                    <h1>{title}</h1>
                    {description && <p className="placeholder-description">{description}</p>}
                </div>

                <div className="placeholder-info">
                    <div className="info-section">
                        <h3>Route Information</h3>
                        <div className="info-item">
                            <strong>Path:</strong> {location.pathname}
                        </div>
                        {location.search && (
                            <div className="info-item">
                                <strong>Query:</strong> {location.search}
                            </div>
                        )}
                    </div>

                    {Object.keys(params).length > 0 && (
                        <div className="info-section">
                            <h3>URL Parameters</h3>
                            {Object.entries(params).map(([key, value]) => (
                                <div key={key} className="info-item">
                                    <strong>{key}:</strong> {value}
                                </div>
                            ))}
                        </div>
                    )}

                    <div className="info-section">
                        <h3>Implementation Status</h3>
                        <div className="status-badge pending">
                            🚧 Placeholder - Implementation Pending
                        </div>
                    </div>
                </div>

                <div className="placeholder-actions">
                    <button
                        className="back-button"
                        onClick={() => window.history.back()}
                    >
                        ← Go Back
                    </button>
                    <button
                        className="home-button"
                        onClick={() => window.location.href = '/accounts'}
                    >
                        🏠 Go to Accounts
                    </button>
                </div>
            </div>
        </div>
    );
};

// Specific placeholder components for different entity types
export const CategoriesPage: React.FC = () => (
    <PlaceholderPage
        title="Categories"
        description="Browse and manage transaction categories across all accounts"
    />
);

export const CategoryDetailPage: React.FC = () => (
    <PlaceholderPage
        title="Category Detail"
        description="View detailed information and analytics for a specific category"
    />
);

export const CategoryTransactionsPage: React.FC = () => (
    <PlaceholderPage
        title="Category Transactions"
        description="View all transactions within this category"
    />
);

export const CategoryAccountsPage: React.FC = () => (
    <PlaceholderPage
        title="Category Accounts"
        description="View which accounts have transactions in this category"
    />
);

export const CategoryAnalyticsPage: React.FC = () => (
    <PlaceholderPage
        title="Category Analytics"
        description="Analytics and trends for this category"
    />
);

export const CategoryComparePage: React.FC = () => (
    <PlaceholderPage
        title="Compare Categories"
        description="Compare spending patterns across different categories"
    />
);

export const TransactionDetailPage: React.FC = () => (
    <PlaceholderPage
        title="Transaction Detail"
        description="View and edit detailed information for a specific transaction"
    />
);

export const TransactionEditPage: React.FC = () => (
    <PlaceholderPage
        title="Edit Transaction"
        description="Edit transaction details, category, and other properties"
    />
);

export const TransactionComparePage: React.FC = () => (
    <PlaceholderPage
        title="Compare Transactions"
        description="Compare multiple transactions side by side"
    />
);

export const FilesPage: React.FC = () => (
    <PlaceholderPage
        title="Transaction Files"
        description="Browse and manage imported transaction files"
    />
);

export const FileDetailPage: React.FC = () => (
    <PlaceholderPage
        title="File Detail"
        description="View detailed information about an imported transaction file"
    />
);

export const FileTransactionsPage: React.FC = () => (
    <PlaceholderPage
        title="File Transactions"
        description="View all transactions imported from this file"
    />
);

export const FileAccountsPage: React.FC = () => (
    <PlaceholderPage
        title="File Accounts"
        description="View which accounts are affected by this file"
    />
);

export const FileCategoriesPage: React.FC = () => (
    <PlaceholderPage
        title="File Categories"
        description="View transaction categories found in this file"
    />
);

export const FileSummaryPage: React.FC = () => (
    <PlaceholderPage
        title="File Import Summary"
        description="Summary of the file import process and results"
    />
);

export const FileProcessingLogPage: React.FC = () => (
    <PlaceholderPage
        title="File Processing Log"
        description="Detailed log of the file processing and import steps"
    />
);

export const FileComparePage: React.FC = () => (
    <PlaceholderPage
        title="Compare Files"
        description="Compare multiple transaction files and their contents"
    />
);

export default PlaceholderPage;
