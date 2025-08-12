import React, { useState } from 'react';
import { useFZIPRestore } from '../hooks/useFZIPRestore';
import FZIPRestoreUpload from '../components/FZIPRestoreUpload';
import FZIPRestoreList from '../components/FZIPRestoreList';
import Button from '../components/Button';
import './FZIPRestoreView.css';

const FZIPRestoreView: React.FC = () => {
  const {
    restoreJobs,
    isLoading,
    error,
    // profileError and profileSummary are not used in simplified flow
    // but remain available for backward compatibility if needed
    profileError,
    profileSummary,
    refreshRestoreJobs,
    deleteRestoreJob,
    getRestoreStatus,
    startRestoreProcessing,
    cancelRestore,
    hasMore,
    loadMore,
    clearErrors
  } = useFZIPRestore();

  const [showUpload, setShowUpload] = useState(true);
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'warning';
    message: string;
  } | null>(null);

  const handleUploaded = async () => {
    console.log('handleUploaded called');
    setNotification({
      type: 'success',
      message: 'Uploaded; validation will start automatically.'
    });
    setShowUpload(false);
    setTimeout(() => setNotification(null), 5000);
    console.log('Calling refreshRestoreJobs...');
    await refreshRestoreJobs();
    console.log('refreshRestoreJobs completed');
  };

  const handleDelete = async (restoreId: string) => {
    try {
      await deleteRestoreJob(restoreId);
      setNotification({
        type: 'success',
        message: 'Restore job deleted successfully'
      });
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to delete restore job'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshRestoreJobs();
      setNotification({
        type: 'success',
        message: 'Restore jobs refreshed'
      });
      setTimeout(() => setNotification(null), 2000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: 'Failed to refresh restore jobs'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleClearErrors = () => {
    clearErrors();
    setNotification(null);
  };

  return (
    <div className="fzip-restore-view">
      {/* Header */}
      <div className="restore-view-header">
        <div className="header-content">
          <h1>Financial Profile Restore</h1>
          <p>Restore your complete financial profile from a FZIP backup file. Your current profile must be completely empty.</p>
        </div>
        
        <div className="header-actions">
          <Button
            variant="secondary"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
          
          {!showUpload && (
            <Button
              variant="primary"
              onClick={() => {
                setShowUpload(true);
                clearErrors();
              }}
            >
              New Restore
            </Button>
          )}
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <div className={`notification notification--${notification.type}`}>
          <div className="notification-content">
            <span className="notification-icon">
              {notification.type === 'success' ? '✓' : 
               notification.type === 'warning' ? '⚠' : '⚠'}
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
      {error && !profileError && (
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
      <div className="restore-view-content">
        {/* Restore Upload */}
        {showUpload && (
          <div className="upload-section">
            <div className="section-header">
              <h2>Upload FZIP Backup</h2>
              {restoreJobs.length > 0 && (
                <Button
                  variant="secondary"
                  size="small"
                  onClick={() => setShowUpload(false)}
                >
                  Hide Upload
                </Button>
              )}
            </div>
            
            <FZIPRestoreUpload
              onUploaded={handleUploaded}
              isLoading={isLoading}
              profileError={profileError}
              profileSummary={profileSummary}
              onClearErrors={handleClearErrors}
            />
          </div>
        )}

        {/* Restore Jobs List */}
        <div className="list-section">
          <div className="section-header">
            <h2>Restore Jobs</h2>
            <div className="section-info">
              {restoreJobs.length > 0 && (
                <span className="job-count">
                  {restoreJobs.length} job{restoreJobs.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
          
          <FZIPRestoreList
            restoreJobs={restoreJobs}
            isLoading={isLoading}
            onDelete={handleDelete}
            onRefreshStatus={getRestoreStatus}
            onStartRestore={startRestoreProcessing}
            onCancelRestore={cancelRestore}
            hasMore={hasMore}
            onLoadMore={loadMore}
          />
        </div>
      </div>

      {/* Info Panel */}
      <div className="info-panel">
        <h3>About FZIP Restore</h3>
        <div className="info-content">
          <div className="info-item">
            <h4>Empty Profile Required</h4>
            <p>Restore operations require a completely empty financial profile to ensure clean restoration without conflicts.</p>
          </div>
          
          <div className="info-item">
            <h4>Complete Restoration</h4>
            <p>All data from the backup is restored exactly as it was, including accounts, transactions, categories, and files.</p>
          </div>
          
          <div className="info-item">
            <h4>Data Validation</h4>
            <p>Every restore includes comprehensive validation to ensure data integrity and schema compatibility.</p>
          </div>
          
          <div className="info-item">
            <h4>Progress Tracking</h4>
            <p>Real-time progress updates show each phase of the restore process from validation to completion.</p>
          </div>
        </div>

        <div className="restore-phases">
          <h4>Restore Process:</h4>
          <ol>
            <li><strong>Upload:</strong> Upload your FZIP backup file</li>
            <li><strong>Validation:</strong> Verify file format and profile emptiness</li>
            <li><strong>Parsing:</strong> Extract and validate backup contents</li>
            <li><strong>Restoration:</strong> Restore accounts, categories, files, and transactions</li>
            <li><strong>Completion:</strong> Verify data integrity and finalize</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default FZIPRestoreView;