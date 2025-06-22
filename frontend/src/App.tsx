import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Login from './components-old/Login';
import NewUILayout from './new-ui/layouts/NewUILayout';
import AccountsView from './new-ui/views/AccountsView';
import TransactionsView from './new-ui/views/TransactionsView';
import AnalyticsView from './new-ui/views/AnalyticsView';
import { AuthUser, getCurrentUser, isAuthenticated, refreshToken } from './services/AuthService';
import './App.css'

function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<AuthUser | null>(null);
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
              const refreshedUser = await refreshToken(currentUser.refreshToken);
              setUser(refreshedUser);
              setAuthenticated(true);
              return;
            } catch (error) {
              console.error('Failed to refresh token:', error);
              setUser(null);
              setAuthenticated(false);
              return;
            }
          }
          
          // Token still valid
          if (isAuthenticated()) {
            setUser(currentUser);
            setAuthenticated(true);
            return;
          }
        }
        
        // No user or invalid token
        setUser(null);
        setAuthenticated(false);
      } catch (error) {
        console.error('Authentication check error:', error);
        setUser(null);
        setAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
  }, []);

  const handleLoginSuccess = () => {
    setUser(getCurrentUser());
    setAuthenticated(true);
  };

  const handleSignOut = () => {
    setAuthenticated(false);
    setUser(null);
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
        <Route path="accounts" element={<AccountsView />} />
        <Route path="transactions" element={<TransactionsView />} />
        <Route path="analytics" element={<AnalyticsView />} />
        <Route path="*" element={<div><p>Page Not Found</p></div>} />
      </Route>
    </Routes>
  );
}

export default App
