import { useState, useEffect } from 'react';
import Login from './components/Login';
import UserProfile from './components/UserProfile';
import { ColorDisplay } from './components/ColorDisplay';
import FileManager from './components/FileManager';
import AccountManager from './components/AccountManager';
import { AuthUser, getCurrentUser, isAuthenticated, refreshToken } from './services/AuthService';
import './App.css'

function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeSection, setActiveSection] = useState<'colors' | 'files' | 'accounts'>('files');

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

  const handleSectionChange = (section: 'colors' | 'files' | 'accounts') => {
    setActiveSection(section);
  };

  if (loading) {
    return <div className="loading-auth">Checking authentication...</div>;
  }

  return (
    <div className="app-container">
      <h1>House F3 Application</h1>
      
      {authenticated && user ? (
        <>
          <UserProfile user={user} onSignOut={handleSignOut} />
          
          <div className="section-tabs">
            <button 
              className={`section-button ${activeSection === 'files' ? 'active' : ''}`}
              onClick={() => handleSectionChange('files')}
            >
              File Manager
            </button>
            <button 
              className={`section-button ${activeSection === 'accounts' ? 'active' : ''}`}
              onClick={() => handleSectionChange('accounts')}
            >
              Accounts
            </button>
            <button 
              className={`section-button ${activeSection === 'colors' ? 'active' : ''}`}
              onClick={() => handleSectionChange('colors')}
            >
              Colors
            </button>
          </div>
          
          <div className="content">
            {activeSection === 'files' && (
              <>
                <h2>File Management</h2>
                <FileManager />
              </>
            )}
            
            {activeSection === 'accounts' && (
              <>
                <h2>Account Management</h2>
                <AccountManager />
              </>
            )}
            
            {activeSection === 'colors' && (
              <>
                <h2>Color Import</h2>
                <ColorDisplay />
              </>
            )}
          </div>
        </>
      ) : (
        <>
          <p>Please sign in to access the application</p>
          <Login onLoginSuccess={handleLoginSuccess} />
        </>
      )}
    </div>
  )
}

export default App
