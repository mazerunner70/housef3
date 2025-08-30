import React, { useState } from 'react';
import { useFZIPBackups } from '../hooks/useFZIPBackups';
import FZIPBackupCreator from '../components/FZIPBackupCreator';
import FZIPBackupList from '../components/FZIPBackupList';
import Button from '../components/Button';
import './FZIPBackupView.css';

const FZIPBackupView: React.FC = () => {
  const {
    backups,
    isLoading,
    error,
    createBackup,
    refreshBackups,
    deleteBackup,
    downloadBackup,
    getBackupStatus,
    hasMore,
    loadMore
  } = useFZIPBackups();

  const [showCreator, setShowCreator] = useState(false);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const handleCreateBackup = async (request: any) => {
    try {
      const backupId = await createBackup(request);
      setNotification({
        type: 'success',
        message: `Backup created successfully! ID: ${backupId}`
      });
      setShowCreator(false);
      
      // Clear notification after 5 seconds
      setTimeout(() => setNotification(null), 5000);
      
      return backupId;
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to create backup'
      });
      setTimeout(() => setNotification(null), 5000);
      throw error;
    }
  };

  const handleDownload = async (backupId: string, filename?: string) => {
    try {
      await downloadBackup(backupId, filename);
      setNotification({
        type: 'success',
        message: 'Download started successfully'
      });
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Download failed'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleDelete = async (backupId: string) => {
    try {
      await deleteBackup(backupId);
      setNotification({
        type: 'success',
        message: 'Backup deleted successfully'
      });
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to delete backup'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshBackups();
      setNotification({
        type: 'success',
        message: 'Backup list refreshed'
      });
      setTimeout(() => setNotification(null), 2000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: 'Failed to refresh backup list'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  return (
    <div className="fzip-backup-view">
      {/* Header */}
      <div className="backup-view-header">
        <div className="header-content">
          <h1>Financial Profile Backups</h1>
          <p>Create and manage complete backups of your financial data using the FZIP format.</p>
        </div>
        
        <div className="header-actions">
          <Button
            variant="secondary"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
          
          <Button
            variant="primary"
            onClick={() => setShowCreator(true)}
            disabled={showCreator}
          >
            Create Backup
          </Button>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div className={`notification notification--${notification.type}`}>
          <div className="notification-content">
            <span className="notification-icon">
              {notification.type === 'success' ? '✓' : '⚠'}
            </span>
            <span className="notification-message">{notification.message}</span>
            <button
              className="notification-close"
              onClick={() => setNotification(null)}
              aria-label="Close notification"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Global Error */}
      {error && (
        <div className="global-error">
          <div className="error-content">
            <h3>Service Status</h3>
            <p>{error}</p>
            {error.includes('service may not be available') || error.includes('service is not available') ? (
              <div className="service-notice">
                <p><strong>Note:</strong> The backup and restore feature requires backend deployment. If you're a developer, make sure the FZIP endpoints are deployed.</p>
              </div>
            ) : (
              <Button
                variant="secondary"
                size="small"
                onClick={handleRefresh}
              >
                Try Again
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="backup-view-content">
        {/* Backup Creator */}
        {showCreator && (
          <div className="creator-section">
            <div className="section-header">
              <h2>Create New Backup</h2>
              <Button
                variant="secondary"
                size="small"
                onClick={() => setShowCreator(false)}
              >
                Cancel
              </Button>
            </div>
            
            <FZIPBackupCreator
              onCreateBackup={handleCreateBackup}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Backup List */}
        <div className="list-section">
          <div className="section-header">
            <h2>Your Backups</h2>
            <div className="section-info">
              {backups.length > 0 && (
                <span className="backup-count">
                  {backups.length} backup{backups.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
          
          <FZIPBackupList
            backups={backups}
            isLoading={isLoading}
            onDownload={handleDownload}
            onDelete={handleDelete}
            onRefreshStatus={getBackupStatus}
            hasMore={hasMore}
            onLoadMore={loadMore}
          />
        </div>
      </div>

      {/* Info Panel */}
      <div className="info-panel">
        <h3>About FZIP Backups</h3>
        <div className="info-content">
          <div className="info-item">
            <h4>Complete Financial Profile</h4>
            <p>FZIP backups contain your entire financial profile including accounts, transactions, categories, rules, and files.</p>
          </div>
          
          <div className="info-item">
            <h4>Portable Format</h4>
            <p>FZIP files are portable and can be restored to any empty financial profile, making them perfect for migration and recovery.</p>
          </div>
          
          <div className="info-item">
            <h4>Data Security</h4>
            <p>All backup data is encrypted in transit and at rest. Backup packages expire after 24 hours for security.</p>
          </div>
          
          <div className="info-item">
            <h4>Quality Validation</h4>
            <p>Each backup includes comprehensive validation to ensure data integrity and completeness.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FZIPBackupView;