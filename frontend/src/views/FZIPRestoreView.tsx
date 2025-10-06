import React, { useState } from 'react';
import { useFZIPRestore } from '../hooks/useFZIPRestore';
import { useFZIPRestoreStatus } from '../hooks/useFZIPRestoreStatus';
import FZIPRestoreUpload from '../components/FZIPRestoreUpload';
import FZIPRestoreList from '../components/FZIPRestoreList';
import { FZIPRestoreSummary } from '../components/fzip/FZIPRestoreSummary';
import { FZIPRestoreResults } from '../components/fzip/FZIPRestoreResults';
import { FZIPRestoreError } from '../components/fzip/FZIPRestoreError';
import { FZIPRestoreStatus } from '../services/FZIPService';
import Button from '../components/Button';
import './FZIPRestoreView.css';

// Constants for sticky notifications
const CONFIRMATION_READY_MESSAGE = 'Restore job ready for confirmation! Click "Start Restore" in the job list below.';

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

  // Enhanced state management for individual restore jobs
  const [activeRestoreId, setActiveRestoreId] = useState<string | null>(null);
  const [showRestoreModal, setShowRestoreModal] = useState(false);

  // Enhanced status polling for active restore
  const {
    status: activeRestoreStatus,
    confirmRestore,
    retryRestore: retryActiveRestore,
    abortRestore,
    clearError
  } = useFZIPRestoreStatus(activeRestoreId);

  // Helper function to find new restore job
  const findNewRestoreJob = (updatedJobs: any[], currentJobCount: number) => {
    // Check if we have a new job that's awaiting user confirmation
    const confirmationJob = updatedJobs.find(job =>
      job.status === FZIPRestoreStatus.AWAITING_CONFIRMATION
    );

    if (confirmationJob) {
      return confirmationJob;
    }

    // Also check if we simply have more jobs than before (any status)
    if (updatedJobs.length > currentJobCount) {
      return updatedJobs[0]; // Jobs should be sorted by creation date
    }

    return null;
  };

  // Helper function to perform a single polling attempt
  const performPollingAttempt = async (attempts: number, maxAttempts: number, currentJobCount: number) => {
    setNotification({
      type: 'success',
      message: `Looking for restore job... (${attempts}/${maxAttempts})`
    });

    try {
      const updatedJobs = await refreshRestoreJobs();
      return { success: true, job: findNewRestoreJob(updatedJobs, currentJobCount) };
    } catch (error) {
      console.error('Error checking restore job:', error);
      setNotification({
        type: 'warning',
        message: `Checking for restore job... (${attempts}/${maxAttempts}) - retrying...`
      });
      return { success: false, job: null };
    }
  };

  // Helper function to handle successful job discovery
  const handleJobFound = (foundJob: any) => {
    if (foundJob.status === FZIPRestoreStatus.AWAITING_CONFIRMATION) {
      setNotification({
        type: 'success',
        message: CONFIRMATION_READY_MESSAGE
      });
    } else {
      setNotification({
        type: 'success',
        message: `Restore job created with status: ${foundJob.status}. Check the list below for updates.`
      });
    }
  };

  // Helper function to handle polling failure
  const handlePollingFailure = () => {
    setNotification({
      type: 'warning',
      message: 'Upload completed but restore job creation is taking longer than expected. Please refresh to check status.'
    });
  };

  // Helper function to schedule notification cleanup
  const scheduleNotificationCleanup = () => {
    setTimeout(() => {
      setNotification(currentNotification => {
        if (currentNotification?.message !== CONFIRMATION_READY_MESSAGE) {
          return null;
        }
        return currentNotification;
      });
    }, 5000);
  };

  const handleUploaded = async () => {
    setShowUpload(false);

    const maxAttempts = 15; // 30 seconds max wait time
    const pollInterval = 2000; // 2 seconds between polls
    const currentJobCount = restoreJobs.length;

    // Show initial success message
    setNotification({
      type: 'success',
      message: 'Upload successful. Creating restore job...'
    });

    // Poll for the newly created restore job
    let foundJob: any = null;
    for (let attempts = 1; attempts <= maxAttempts && !foundJob; attempts++) {
      const result = await performPollingAttempt(attempts, maxAttempts, currentJobCount);

      if (result.success && result.job) {
        foundJob = result.job;
        break;
      }

      // Wait before next attempt (except on last attempt)
      if (attempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
      }
    }

    // Handle the result
    if (foundJob) {
      handleJobFound(foundJob);
    } else {
      handlePollingFailure();
    }

    // Schedule notification cleanup
    scheduleNotificationCleanup();
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
      console.error('Error refreshing restore jobs:', error);
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

  // Enhanced handlers for new restore flow (kept for potential future use)
  // const handleRestoreJobSelect = (restoreId: string) => {
  //   setActiveRestoreId(restoreId);
  //   setShowRestoreModal(true);
  // };

  const handleConfirmRestore = async () => {
    try {
      await confirmRestore();
      setNotification({
        type: 'success',
        message: 'Restore confirmed and started'
      });
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to confirm restore'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleRetryRestore = async () => {
    try {
      await retryActiveRestore();
      setNotification({
        type: 'success',
        message: 'Restore retry initiated'
      });
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to retry restore'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleAbortRestore = async () => {
    try {
      await abortRestore();
      setNotification({
        type: 'success',
        message: 'Restore aborted successfully'
      });
      setTimeout(() => setNotification(null), 3000);
      setShowRestoreModal(false);
      setActiveRestoreId(null);
      await refreshRestoreJobs();
    } catch (error) {
      setNotification({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to abort restore'
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleCloseModal = () => {
    setShowRestoreModal(false);
    setActiveRestoreId(null);
    clearError();
    refreshRestoreJobs().catch(() => {
      // Handle refresh error silently - user will see stale data
    });
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
              {(() => {
                if (notification.type === 'success') return '✓';
                if (notification.type === 'warning') return '⚠';
                return '⚠';
              })()}
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
                size="compact"
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
                  size="compact"
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

      {/* Enhanced Restore Status Modal */}
      {showRestoreModal && activeRestoreStatus && (
        <div className="restore-modal-overlay">
          <dialog
            className="restore-modal"
            open
            aria-labelledby="restore-modal-title"
          >
            <div className="restore-modal">
              {/* Summary View - for awaiting confirmation */}
              {activeRestoreStatus.status === FZIPRestoreStatus.AWAITING_CONFIRMATION &&
                activeRestoreStatus.summary && (
                  <FZIPRestoreSummary
                    summary={activeRestoreStatus.summary}
                    onConfirm={handleConfirmRestore}
                    onCancel={handleCloseModal}
                    isConfirming={false}
                  />
                )}

              {/* Results View - for completed restores */}
              {activeRestoreStatus.status === FZIPRestoreStatus.COMPLETED &&
                activeRestoreStatus.restoreResults && (
                  <FZIPRestoreResults
                    results={activeRestoreStatus.restoreResults}
                    onClose={handleCloseModal}
                  />
                )}

              {/* Error View - for failed restores */}
              {activeRestoreStatus.status === FZIPRestoreStatus.FAILED &&
                activeRestoreStatus.error && (
                  <FZIPRestoreError
                    error={activeRestoreStatus.error}
                    onRetry={handleRetryRestore}
                    onAbort={handleAbortRestore}
                    isRetrying={false}
                  />
                )}

              {/* Validation Passed View - ready to start restore */}
              {activeRestoreStatus.status === FZIPRestoreStatus.VALIDATION_PASSED && (
                <div className="restore-validation-passed-modal">
                  <div className="validation-header">
                    <h3 id="validation-modal-title">✅ Restore File Validated</h3>
                    <p>Your backup file has been validated and is ready to restore.</p>
                  </div>

                  <div className="validation-content">
                    <div className="validation-info">
                      <p><strong>Phase:</strong> {activeRestoreStatus.currentPhase}</p>
                      <p><strong>Progress:</strong> {activeRestoreStatus.progress}%</p>
                      {activeRestoreStatus.validationResults && (
                        <div className="validation-results">
                          <p><strong>Validation Results:</strong></p>
                          <ul>
                            <li>Profile Empty: {activeRestoreStatus.validationResults.profileEmpty ? '✅' : '❌'}</li>
                            <li>Schema Valid: {activeRestoreStatus.validationResults.schemaValid ? '✅' : '❌'}</li>
                            <li>Ready to Restore: {activeRestoreStatus.validationResults.ready ? '✅' : '❌'}</li>
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="validation-actions">
                    <Button
                      variant="primary"
                      onClick={handleConfirmRestore}
                    >
                      Start Restore
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={handleCloseModal}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Loading/Progress View - for other statuses */}
              {![FZIPRestoreStatus.AWAITING_CONFIRMATION, FZIPRestoreStatus.VALIDATION_PASSED, FZIPRestoreStatus.COMPLETED, FZIPRestoreStatus.FAILED].includes(activeRestoreStatus.status) && (
                <div className="restore-progress-modal">
                  <div className="progress-header">
                    <h3 id="progress-modal-title">Restore in Progress</h3>
                    <p>Status: {activeRestoreStatus.status.replace('restore_', '').replace('_', ' ')}</p>
                  </div>

                  <div className="progress-content">
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${activeRestoreStatus.progress}%` }}
                      />
                    </div>
                    <span className="progress-text">{activeRestoreStatus.progress}%</span>

                    {activeRestoreStatus.currentPhase && (
                      <p className="current-phase">
                        Current phase: {activeRestoreStatus.currentPhase}
                      </p>
                    )}
                  </div>

                  <div className="progress-actions">
                    <Button variant="secondary" onClick={handleCloseModal}>
                      Close
                    </Button>
                  </div>
                </div>
              )}

              {/* Close button for modal overlay */}
              <button
                type="button"
                className="modal-close-overlay"
                onClick={handleCloseModal}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') {
                    handleCloseModal();
                  }
                }}
                aria-label="Close modal"
                tabIndex={0}
              />
            </div>
          </dialog>
        </div>
      )}
    </div>
  );
};

export default FZIPRestoreView;