import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './new-ui/components/Login';
import NewUILayout from './new-ui/layouts/NewUILayout';
import AccountsPage from './new-ui/pages/AccountsPage';
import TransactionsPage from '@/new-ui/pages/TransactionsPage';
import AnalyticsView from './new-ui/views/AnalyticsView';
import FZIPManagementView from './new-ui/views/FZIPManagementView';
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
        <Route index element={<Navigate to="accounts" replace />} />
        <Route path="accounts" element={<AccountsPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="analytics" element={<AnalyticsView />} />
        <Route path="backup" element={<FZIPManagementView />} />
        <Route path="*" element={<div><p>Page Not Found</p></div>} />
      </Route>
    </Routes>
  );
}

export default App
