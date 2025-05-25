import React, { useState } from 'react';
import './NewUILayout.css'; // We'll create this for basic styling
import TransactionsView from '../views/TransactionsView'; // Import TransactionsView

interface NewUILayoutProps {
  onSignOut: () => void;
}

// Define possible view types
type ActiveView = 'Dashboard' | 'Transactions' | 'Accounts' | 'Analytics';

const NewUILayout: React.FC<NewUILayoutProps> = ({ onSignOut }) => {
  const [activeView, setActiveView] = useState<ActiveView>('Dashboard'); // Default to Dashboard

  const renderMainContent = () => {
    switch (activeView) {
      case 'Dashboard':
        return <p>Welcome to the Dashboard! Content will appear here.</p>;
      case 'Transactions':
        return <TransactionsView />;
      case 'Accounts':
        return <p>Accounts Management will appear here.</p>;
      case 'Analytics':
        return <p>Analytics & Reports will appear here.</p>;
      default:
        return <p>Welcome to the new UI! Content will appear here.</p>;
    }
  };

  return (
    <div className="new-ui-container">
      <header className="new-ui-header">
        <div className="new-ui-logo">APP LOGO</div>
        <h1 className="new-ui-title">Modern Finance App</h1>
      </header>
      <div className="new-ui-layout-content">
        <nav className="new-ui-sidebar">
          <p onClick={() => setActiveView('Dashboard')} className={activeView === 'Dashboard' ? 'active' : ''}>Dashboard</p>
          <p onClick={() => setActiveView('Transactions')} className={activeView === 'Transactions' ? 'active' : ''}>Transactions</p>
          <p onClick={() => setActiveView('Accounts')} className={activeView === 'Accounts' ? 'active' : ''}>Accounts</p>
          <p onClick={() => setActiveView('Analytics')} className={activeView === 'Analytics' ? 'active' : ''}>Analytics</p>
          <p onClick={onSignOut} className="sign-out-button">Sign Out</p>
        </nav>
        <main className="new-ui-main-content">
          {renderMainContent()} {/* Render dynamic content here */}
        </main>
      </div>
    </div>
  );
};

export default NewUILayout; 