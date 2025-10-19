import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import Login from '@/components/Login';
import NewUILayout from '@/layouts/NewUILayout';
import HomePage from '@/pages/HomePage';
import AccountsPage from '@/pages/AccountsPage';
import TransactionsPage from '@/pages/TransactionsPage';
import TransfersPage from '@/components/domain/transfers/TransfersPage';
import ImportTransactionsPage from '@/pages/ImportTransactionsPage';
import AccountFileUploadPage from '@/pages/AccountFileUploadPage';
import AnalyticsView from '@/views/AnalyticsView';
import FZIPPage from '@/components/domain/fzip/FZIPPage';
import {
  CategoriesPage,
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
} from '@/pages/PlaceholderPage';
import { getCurrentUser, isAuthenticated, refreshToken } from './services/AuthService';
import './App.css'

function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  // Check authentication status on component mount
  useEffect(() => {
    const checkAuth = async () => {
      setLoading(true);

      try {
        // Get current user
        const currentUser = getCurrentUser();

        // Check if user is authenticated
        if (currentUser) {
          // If token expired, try to refresh
          if (!isAuthenticated() && currentUser.refreshToken) {
            try {
              await refreshToken(currentUser.refreshToken);
              setAuthenticated(true);
              return;
            } catch (error) {
              console.error('Failed to refresh token:', error);
              setAuthenticated(false);
              return;
            }
          }

          // Token still valid
          if (isAuthenticated()) {
            setAuthenticated(true);
            return;
          }
        }

        // No user or invalid token
        setAuthenticated(false);
      } catch (error) {
        console.error('Authentication check error:', error);
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLoginSuccess = () => {
    setAuthenticated(true);
  };

  const handleSignOut = () => {
    setAuthenticated(false);
  };

  if (loading) {
    return <div className="loading-auth">Checking authentication...</div>;
  }

  if (!authenticated) {
    return (
      <div className="app-container">
        <h1>House F3 Application</h1>
        <p>Please sign in to access the application</p>
        <Login onLoginSuccess={handleLoginSuccess} />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/*" element={<NewUILayout onSignOut={handleSignOut} />}>
        <Route index element={<HomePage />} />
        <Route path="home" element={<HomePage />} />
        {/* 
          Session URL Strategy: All session URLs use /accounts?s=sessionId
          React Router sees this as the base /accounts route with query parameters
          No new routes needed - sessions are handled via query params!
        */}
        {/* Account-based routes (for account-centric navigation) */}
        <Route path="accounts" element={<AccountsPage />} />
        <Route path="accounts/:accountId" element={<AccountsPage />} />

        {/* Entity-based branching routes */}

        {/* Categories */}
        <Route path="categories" element={<CategoriesPage />} />
        <Route path="categories/:categoryId" element={<CategoryDetailPage />} />
        <Route path="categories/:categoryId/transactions" element={<CategoryTransactionsPage />} />
        <Route path="categories/:categoryId/accounts" element={<CategoryAccountsPage />} />
        <Route path="categories/:categoryId/analytics" element={<CategoryAnalyticsPage />} />
        <Route path="categories/compare" element={<CategoryComparePage />} />

        {/* Transactions */}
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="transactions/:transactionId" element={<TransactionDetailPage />} />
        <Route path="transactions/:transactionId/edit" element={<TransactionEditPage />} />
        <Route path="transactions/compare" element={<TransactionComparePage />} />

        {/* Transfers */}
        <Route path="transfers" element={<TransfersPage />} />

        {/* Import */}
        <Route path="import" element={<ImportTransactionsPage />} />
        <Route path="import/account/:accountId" element={<AccountFileUploadPage />} />

        {/* Files */}
        <Route path="files" element={<FilesPage />} />
        <Route path="files/:fileId" element={<FileDetailPage />} />
        <Route path="files/:fileId/transactions" element={<FileTransactionsPage />} />
        <Route path="files/:fileId/accounts" element={<FileAccountsPage />} />
        <Route path="files/:fileId/categories" element={<FileCategoriesPage />} />
        <Route path="files/:fileId/summary" element={<FileSummaryPage />} />
        <Route path="files/:fileId/log" element={<FileProcessingLogPage />} />
        <Route path="files/compare" element={<FileComparePage />} />

        {/* Other routes */}
        <Route path="analytics" element={<AnalyticsView />} />
        <Route path="fzip" element={<FZIPPage />} />
        <Route path="backup" element={<FZIPPage />} /> {/* Legacy route - redirects to /fzip */}
        <Route path="*" element={<div><p>Page Not Found</p></div>} />
      </Route>
    </Routes>
  );
}

export default App
