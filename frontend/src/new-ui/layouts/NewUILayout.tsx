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
        <nav className="new-ui-navigation">
          <NavLink to="/dashboard">Dashboard</NavLink>
          <NavLink to="/transactions-header">Transactions</NavLink>
        </nav>
      </header>
      <div className="new-ui-layout-content">
        <nav className="new-ui-sidebar">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? "active" : ""}>Dashboard</NavLink>
          <NavLink to="/transactions" className={({ isActive }) => isActive ? "active" : ""}>Transactions</NavLink>
          <NavLink to="/accounts" className={({ isActive }) => isActive ? "active" : ""}>Accounts</NavLink>
          <NavLink to="/analytics" className={({ isActive }) => isActive ? "active" : ""}>Analytics</NavLink>
          <p onClick={onSignOut} className="sign-out-button">Sign Out</p>
        </nav>
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