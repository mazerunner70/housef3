import { RouteObject, Link, UIMatch, Navigate } from 'react-router-dom';
import { RouteHandle } from './types';
import {
    HomePage,
    AccountsPage,
    TransactionsPage,
    TransfersPage,
    CategoriesPage,
    ImportPage,
    AccountFileUploadPage,
    AnalyticsView,
    FZIPPage,
    CategoryDetailPage,
    CategoryTransactionsPage,
    CategoryAccountsPage,
    CategoryAnalyticsPage,
    CategoryComparePage,
    TransactionDetailPage,
    TransactionEditPage,
    TransactionComparePage,
    FilesPage,
    FileDetailPage,
    FileTransactionsPage,
    FileAccountsPage,
    FileCategoriesPage,
    FileSummaryPage,
    FileProcessingLogPage,
    FileComparePage
} from '@/pages';

/**
 * Application Route Configuration
 * 
 * This file centralizes all route definitions to keep App.tsx clean.
 * Routes are organized by feature domain for easy navigation and maintenance.
 * 
 * Each route should export a `handle` property with:
 * - breadcrumb: Function to render breadcrumb for this route
 * - sidebar: Key identifying which sidebar to use (e.g., 'accounts', 'transactions')
 * 
 * The breadcrumb function receives the route match and can access:
 * - match.pathname - the matched URL path
 * - match.params - URL parameters (e.g., accountId, categoryId)
 * - match.data - data from the route's loader (if defined)
 * 
 * The sidebar key is used to lookup the sidebar component from the registry.
 * If not specified, the system falls back to using the first path segment.
 * 
 * Route Organization:
 * - Home/Landing
 * - Accounts (with session support via query params)
 * - Categories (with sub-routes)
 * - Transactions (with sub-routes)
 * - Transfers
 * - Import
 * - Files (with sub-routes)
 * - Other (Analytics, FZIP, etc.)
 */

export const appRoutes: RouteObject[] = [
    // Home/Landing
    {
        index: true,
        element: <HomePage />,
        handle: {
            breadcrumb: () => <Link to="/">Home</Link>,
            sidebar: 'default'
        } as RouteHandle
    },
    {
        path: 'home',
        element: <HomePage />,
        handle: {
            breadcrumb: () => <Link to="/home">Home</Link>,
            sidebar: 'default'
        } as RouteHandle
    },

    // Accounts
    // Note: Session URLs use /accounts?s=sessionId (query params, not routes)
    {
        path: 'accounts',
        element: <AccountsPage />,
        handle: {
            breadcrumb: () => <Link to="/accounts">Accounts</Link>,
            sidebar: 'accounts'
        } as RouteHandle
    },
    {
        path: 'accounts/:accountId',
        element: <AccountsPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                // In the future, match.data can provide account name from loader
                // For now, we'll show the ID or fetch it
                const accountId = match.params.accountId as string;
                return <Link to={`/accounts/${accountId}`}>Account {accountId?.slice(0, 8)}</Link>;
            },
            sidebar: 'accounts'
        } as RouteHandle
    },

    // Categories
    {
        path: 'categories',
        element: <CategoriesPage />,
        handle: {
            breadcrumb: () => <Link to="/categories">Categories</Link>,
            sidebar: 'categories'
        } as RouteHandle
    },
    {
        path: 'categories/:categoryId',
        element: <CategoryDetailPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const categoryId = match.params.categoryId as string;
                return <Link to={`/categories/${categoryId}`}>Category {categoryId?.slice(0, 8)}</Link>;
            },
            sidebar: 'categories'
        } as RouteHandle
    },
    {
        path: 'categories/:categoryId/transactions',
        element: <CategoryTransactionsPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const categoryId = match.params.categoryId as string;
                return <Link to={`/categories/${categoryId}/transactions`}>Transactions</Link>;
            },
            sidebar: 'categories'
        } as RouteHandle
    },
    {
        path: 'categories/:categoryId/accounts',
        element: <CategoryAccountsPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const categoryId = match.params.categoryId as string;
                return <Link to={`/categories/${categoryId}/accounts`}>Accounts</Link>;
            },
            sidebar: 'categories'
        } as RouteHandle
    },
    {
        path: 'categories/:categoryId/analytics',
        element: <CategoryAnalyticsPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const categoryId = match.params.categoryId as string;
                return <Link to={`/categories/${categoryId}/analytics`}>Analytics</Link>;
            },
            sidebar: 'categories'
        } as RouteHandle
    },
    {
        path: 'categories/compare',
        element: <CategoryComparePage />,
        handle: {
            breadcrumb: () => <Link to="/categories/compare">Compare Categories</Link>,
            sidebar: 'categories'
        } as RouteHandle
    },

    // Transactions
    {
        path: 'transactions',
        element: <TransactionsPage />,
        handle: {
            breadcrumb: () => <Link to="/transactions">Transactions</Link>,
            sidebar: 'transactions'
        } as RouteHandle
    },
    {
        path: 'transactions/:transactionId',
        element: <TransactionDetailPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const transactionId = match.params.transactionId as string;
                return <Link to={`/transactions/${transactionId}`}>Transaction {transactionId?.slice(-6)}</Link>;
            },
            sidebar: 'transactions'
        } as RouteHandle
    },
    {
        path: 'transactions/:transactionId/edit',
        element: <TransactionEditPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const transactionId = match.params.transactionId as string;
                return <Link to={`/transactions/${transactionId}/edit`}>Edit</Link>;
            },
            sidebar: 'transactions'
        } as RouteHandle
    },
    {
        path: 'transactions/compare',
        element: <TransactionComparePage />,
        handle: {
            breadcrumb: () => <Link to="/transactions/compare">Compare Transactions</Link>,
            sidebar: 'transactions'
        } as RouteHandle
    },

    // Transfers
    {
        path: 'transfers',
        element: <TransfersPage />,
        handle: {
            breadcrumb: () => <Link to="/transfers">Transfers</Link>,
            sidebar: 'transfers'
        } as RouteHandle
    },

    // Import
    {
        path: 'import',
        element: <ImportPage />,
        handle: {
            breadcrumb: () => <Link to="/import">Import</Link>,
            sidebar: 'import'
        } as RouteHandle
    },
    {
        path: 'import/account/:accountId',
        element: <AccountFileUploadPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const accountId = match.params.accountId as string;
                return <Link to={`/import/account/${accountId}`}>Upload File</Link>;
            },
            sidebar: 'import'
        } as RouteHandle
    },

    // Files
    {
        path: 'files',
        element: <FilesPage />,
        handle: {
            breadcrumb: () => <Link to="/files">Files</Link>,
            sidebar: 'files'
        } as RouteHandle
    },
    {
        path: 'files/:fileId',
        element: <FileDetailPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const fileId = match.params.fileId as string;
                return <Link to={`/files/${fileId}`}>File {fileId?.slice(0, 8)}</Link>;
            }
        }
    },
    {
        path: 'files/:fileId/transactions',
        element: <FileTransactionsPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const fileId = match.params.fileId as string;
                return <Link to={`/files/${fileId}/transactions`}>Transactions</Link>;
            }
        }
    },
    {
        path: 'files/:fileId/accounts',
        element: <FileAccountsPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const fileId = match.params.fileId as string;
                return <Link to={`/files/${fileId}/accounts`}>Accounts</Link>;
            }
        }
    },
    {
        path: 'files/:fileId/categories',
        element: <FileCategoriesPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const fileId = match.params.fileId as string;
                return <Link to={`/files/${fileId}/categories`}>Categories</Link>;
            }
        }
    },
    {
        path: 'files/:fileId/summary',
        element: <FileSummaryPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const fileId = match.params.fileId as string;
                return <Link to={`/files/${fileId}/summary`}>Summary</Link>;
            }
        }
    },
    {
        path: 'files/:fileId/log',
        element: <FileProcessingLogPage />,
        handle: {
            breadcrumb: (match: UIMatch) => {
                const fileId = match.params.fileId as string;
                return <Link to={`/files/${fileId}/log`}>Processing Log</Link>;
            }
        }
    },
    {
        path: 'files/compare',
        element: <FileComparePage />,
        handle: {
            breadcrumb: () => <Link to="/files/compare">Compare Files</Link>
        }
    },

    // Other Routes
    {
        path: 'analytics',
        element: <AnalyticsView />,
        handle: {
            breadcrumb: () => <Link to="/analytics">Analytics</Link>
        }
    },
    {
        path: 'fzip',
        element: <FZIPPage />,
        handle: {
            breadcrumb: () => <Link to="/fzip">Backup & Restore</Link>,
            sidebar: 'fzip'
        } as RouteHandle
    },
    {
        path: 'backup',
        element: <Navigate to="/fzip" replace />, // Legacy route - redirects to /fzip
        handle: {
            breadcrumb: () => <Link to="/backup">Backup & Restore</Link>
        }
    },

    // 404 Fallback
    {
        path: '*',
        element: <div><p>Page Not Found</p></div>
    }
];
