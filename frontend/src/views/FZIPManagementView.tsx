import React, { useState } from 'react';
import FZIPBackupView from './FZIPBackupView';
import FZIPRestoreView from './FZIPRestoreView';
import './FZIPManagementView.css';

type TabType = 'backup' | 'restore';

const FZIPManagementView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('backup');

  return (
    <div className="fzip-management-view">
      {/* Navigation Tabs */}
      <div className="management-tabs">
        <div className="tabs-container">
          <button
            className={`tab-button ${activeTab === 'backup' ? 'active' : ''}`}
            onClick={() => setActiveTab('backup')}
          >
            <span className="tab-icon">💾</span>
            <span className="tab-label">Backup</span>
            <span className="tab-description">Create & manage backups</span>
          </button>
          
          <button
            className={`tab-button ${activeTab === 'restore' ? 'active' : ''}`}
            onClick={() => setActiveTab('restore')}
          >
            <span className="tab-icon">📂</span>
            <span className="tab-label">Restore</span>
            <span className="tab-description">Upload & restore backups</span>
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'backup' && <FZIPBackupView />}
        {activeTab === 'restore' && <FZIPRestoreView />}
      </div>

      {/* Overview Panel */}
      <div className="overview-panel">
        <h3>FZIP Backup & Restore System</h3>
        <div className="overview-content">
          <div className="overview-section">
            <h4>What is FZIP?</h4>
            <p>
              FZIP (Financial ZIP) is a specialized backup format that contains your complete financial profile 
              including accounts, transactions, categories, rules, file mappings, and original transaction files.
            </p>
          </div>
          
          <div className="overview-section">
            <h4>Use Cases</h4>
            <ul>
              <li><strong>Data Migration:</strong> Move your financial profile to a new environment</li>
              <li><strong>Disaster Recovery:</strong> Restore your complete financial data after system issues</li>
              <li><strong>Regular Backups:</strong> Create periodic backups for data protection</li>
              <li><strong>Development/Testing:</strong> Create clean datasets for testing environments</li>
            </ul>
          </div>
          
          <div className="overview-section">
            <h4>Key Features</h4>
            <div className="features-grid">
              <div className="feature-item">
                <div className="feature-icon">🔒</div>
                <div className="feature-content">
                  <h5>Secure</h5>
                  <p>All data encrypted in transit and at rest</p>
                </div>
              </div>
              
              <div className="feature-item">
                <div className="feature-icon">✅</div>
                <div className="feature-content">
                  <h5>Validated</h5>
                  <p>Comprehensive validation ensures data integrity</p>
                </div>
              </div>
              
              <div className="feature-item">
                <div className="feature-icon">📦</div>
                <div className="feature-content">
                  <h5>Complete</h5>
                  <p>Includes all financial data and relationships</p>
                </div>
              </div>
              
              <div className="feature-item">
                <div className="feature-icon">🚀</div>
                <div className="feature-content">
                  <h5>Portable</h5>
                  <p>Works across different environments</p>
                </div>
              </div>
            </div>
          </div>

          <div className="overview-section">
            <h4>Important Notes</h4>
            <div className="notes-list">
              <div className="note-item note-item--warning">
                <span className="note-icon">⚠️</span>
                <div className="note-content">
                  <strong>Empty Profile Required:</strong> Restore operations require a completely empty financial profile
                </div>
              </div>
              
              <div className="note-item note-item--info">
                <span className="note-icon">⏰</span>
                <div className="note-content">
                  <strong>Backup Expiration:</strong> Backup packages expire after 24 hours for security
                </div>
              </div>
              
              <div className="note-item note-item--success">
                <span className="note-icon">🔄</span>
                <div className="note-content">
                  <strong>Real-time Progress:</strong> Both backup and restore operations provide live progress updates
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FZIPManagementView;