import React from 'react';
import './NewUILayout.css'; // We'll create this for basic styling
import { Outlet, NavLink } from 'react-router-dom';
import logoImage from '../assets/logo1.png'; // Import the logo

interface NewUILayoutProps {
  onSignOut: () => void;
}

const NewUILayout: React.FC<NewUILayoutProps> = ({ onSignOut }) => {
  return (
    <div className="new-ui-layout">
      <header className="new-ui-header">
        <NavLink to="/">
          <img src={logoImage} alt="App Logo" className="new-ui-logo" />
        </NavLink>
        <h1 className="new-ui-title">Modern Finance App</h1>
        <button onClick={onSignOut} className="header-sign-out-button">Sign Out</button>
      </header>
      <div className="new-ui-layout-content">
        <main className="new-ui-main-content">
          <Outlet />
        </main>
      </div>
      <footer className="new-ui-footer">
        <p>&copy; 2024 Your App Name</p>
      </footer>
    </div>
  );
};

export default NewUILayout; 