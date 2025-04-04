import { useState, useEffect } from 'react';
import './App.css'
import Login from './components/Login';
import UserProfile from './components/UserProfile';
import { AuthUser, getCurrentUser, isAuthenticated } from './services/AuthService';

function App() {
  const [authenticated, setAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  // Check authentication status on component mount
  useEffect(() => {
    const checkAuth = () => {
      const isAuth = isAuthenticated();
      setAuthenticated(isAuth);
      
      if (isAuth) {
        const currentUser = getCurrentUser();
        setUser(currentUser);
      }
    };
    
    checkAuth();
  }, []);

  const handleLoginSuccess = () => {
    setAuthenticated(true);
    setUser(getCurrentUser());
  };

  const handleSignOut = () => {
    setAuthenticated(false);
    setUser(null);
  };

  return (
    <div className="app-container">
      <h1>Color Import Application</h1>
      
      {authenticated && user ? (
        <>
          <UserProfile user={user} onSignOut={handleSignOut} />
          <div className="content">
            <p>Welcome to the Color Import Application. You are now authenticated and can view your colors.</p>
            {/* Color list would go here in a future step */}
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
