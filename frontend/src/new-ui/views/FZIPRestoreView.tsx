import React, { useState } from 'react';
import { useFZIPRestore } from '../hooks/useFZIPRestore';
import { useFZIPRestoreStatus } from '../hooks/useFZIPRestoreStatus';
import FZIPRestoreUpload from '../components/FZIPRestoreUpload';
import FZIPRestoreList from '../components/FZIPRestoreList';
import { FZIPRestoreSummary } from '../components/fzip/FZIPRestoreSummary';
import { FZIPRestoreResults } from '../components/fzip/FZIPRestoreResults';
import { FZIPRestoreError } from '../components/fzip/FZIPRestoreError';
import { FZIPRestoreStatus } from '../../services/FZIPService';
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
  
  // Enhanced state management for individual restore jobs
  const [activeRestoreId, setActiveRestoreId] = useState<string | null>(null);
  const [showRestoreModal, setShowRestoreModal] = useState(false);
  
  // DIAGNOSTIC: Track state changes
  React.useEffect(() => {
    console.log('🔄 STATE CHANGE - activeRestoreId:', activeRestoreId);
  }, [activeRestoreId]);
  
  React.useEffect(() => {
    console.log('🔄 STATE CHANGE - showRestoreModal:', showRestoreModal);
  }, [showRestoreModal]);
  
  // Enhanced status polling for active restore
  const { 
    status: activeRestoreStatus, 
    confirmRestore, 
    retryRestore: retryActiveRestore, 
    abortRestore,
    clearError 
  } = useFZIPRestoreStatus(activeRestoreId);
  
  React.useEffect(() => {
    console.log('🔄 STATE CHANGE - activeRestoreStatus:', activeRestoreStatus?.status, 'for job:', activeRestoreStatus?.jobId);
  }, [activeRestoreStatus]);
  
  // DIAGNOSTIC: Track modal rendering
  React.useEffect(() => {
    if (showRestoreModal && activeRestoreStatus) {
      console.log(`🎭 MODAL RENDERING for job: ${activeRestoreId}`);
      console.log(`   Modal status: ${activeRestoreStatus.status}`);
      console.log(`   Has summary: ${!!activeRestoreStatus.summary}`);
      console.log(`   Summary data:`, activeRestoreStatus.summary);
      
      if (activeRestoreStatus.status === FZIPRestoreStatus.AWAITING_CONFIRMATION) {
        if (activeRestoreStatus.summary) {
          console.log('✅ SHOULD RENDER SUMMARY COMPONENT');
        } else {
          console.log('⚠️ STATUS IS AWAITING_CONFIRMATION BUT NO SUMMARY DATA');
        }
      } else if (activeRestoreStatus.status === FZIPRestoreStatus.VALIDATION_PASSED) {
        console.log('✅ SHOULD RENDER VALIDATION PASSED COMPONENT');
        console.log('   Validation results:', activeRestoreStatus.validationResults);
      }
    }
  }, [showRestoreModal, activeRestoreStatus, activeRestoreId]);

  const handleUploaded = async () => {
    console.log('handleUploaded called');
    setShowUpload(false);
    
    // Poll for the newly created restore job
    const maxAttempts = 15; // 30 seconds max wait time
    const pollInterval = 2000; // 2 seconds between polls
    let attempts = 0;
    let foundJob: any = null;
    
    // Get current job count for comparison
    const currentJobCount = restoreJobs.length;
    
    // Show initial success message
    setNotification({
      type: 'success',
      message: 'Upload successful. Creating restore job...'
    });
    
    while (attempts < maxAttempts && !foundJob) {
      attempts++;
      console.log(`Polling attempt ${attempts}/${maxAttempts} for new restore job...`);
      
      // Update notification with progress
      setNotification({
        type: 'success',
        message: `Looking for restore job... (${attempts}/${maxAttempts})`
      });
      
      try {
        const updatedJobs = await refreshRestoreJobs();
        
        // DIAGNOSTIC: Log all current jobs and their statuses
        console.log(`=== POLLING DIAGNOSTIC (attempt ${attempts}) ===`);
        console.log(`Current job count: ${currentJobCount}, Updated job count: ${updatedJobs.length}`);
        console.log('All jobs:');
        updatedJobs.forEach((job, index) => {
          console.log(`  [${index}] ${job.jobId}: ${job.status} (progress: ${job.progress}%, phase: ${job.currentPhase})`);
          if (job.summary) {
            console.log(`    - Has summary data`);
          }
          if (job.validationResults) {
            console.log(`    - Validation: ${JSON.stringify(job.validationResults)}`);
          }
        });
        console.log('=== END DIAGNOSTIC ===');
        
        // Check if we have a new job that's awaiting user confirmation
        const confirmationJob = updatedJobs.find(job => 
          job.status === FZIPRestoreStatus.AWAITING_CONFIRMATION
        );
        
        if (confirmationJob) {
          foundJob = confirmationJob;
          console.log(`🎯 FOUND CONFIRMATION-READY JOB: ${confirmationJob.jobId} with status: ${confirmationJob.status}`);
          console.log(`   Summary available: ${!!confirmationJob.summary}`);
          console.log(`   Validation results: ${JSON.stringify(confirmationJob.validationResults)}`);
          
          // Note: Jobs awaiting confirmation may or may not have summary data depending on the flow
          if (confirmationJob.status === FZIPRestoreStatus.AWAITING_CONFIRMATION && !confirmationJob.summary) {
            console.log('ℹ️ Job awaiting confirmation without summary data (simplified validation flow)');
          }
          break;
        }
        
        // Also check if we simply have more jobs than before (any status)
        if (updatedJobs.length > currentJobCount) {
          const latestJob = updatedJobs[0]; // Jobs should be sorted by creation date
          console.log(`🆕 FOUND NEW JOB: ${latestJob.jobId} with status: ${latestJob.status}`);
          console.log(`   Created at: ${new Date(latestJob.createdAt).toISOString()}`);
          console.log(`   Progress: ${latestJob.progress}%, Phase: ${latestJob.currentPhase}`);
          console.log(`   Summary available: ${!!latestJob.summary}`);
          console.log(`   Validation results: ${JSON.stringify(latestJob.validationResults)}`);
          foundJob = latestJob;
          break;
        }
        
        if (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
      } catch (error) {
        console.error(`Polling attempt ${attempts} failed:`, error);
        // Update notification to show error but continue polling
        setNotification({
          type: 'warning',
          message: `Checking for restore job... (${attempts}/${maxAttempts}) - retrying...`
        });
        
        if (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
      }
    }
    
    if (foundJob) {
      console.log(`🏁 POLLING COMPLETE - Found job: ${foundJob.jobId}`);
      console.log(`   Final status: ${foundJob.status}`);
      console.log(`   Has summary: ${!!foundJob.summary}`);
      console.log(`   Has validation results: ${!!foundJob.validationResults}`);
      
      // If the job is ready for user confirmation, show appropriate message without auto-opening modal
      if (foundJob.status === FZIPRestoreStatus.AWAITING_CONFIRMATION) {
        console.log('✅ JOB READY FOR USER ACTION:', foundJob.jobId);
        console.log('   Job status:', foundJob.status);
        console.log('   Not auto-opening modal - user can interact via main page');
        
        setNotification({
          type: 'success',
          message: 'Restore job ready for confirmation! Click "Start Restore" in the job list below.'
        });
      } else {
        // Job exists but isn't awaiting confirmation - show success message
        console.log(`📝 JOB EXISTS BUT NOT AWAITING CONFIRMATION: ${foundJob.status}`);
        setNotification({
          type: 'success',
          message: `Restore job created with status: ${foundJob.status}. Check the list below for updates.`
        });
      }
    } else {
      setNotification({
        type: 'warning',
        message: 'Upload completed but restore job creation is taking longer than expected. Please refresh to check status.'
      });
    }
    
    // Clear notification after 5 seconds (except for confirmation message)
    setTimeout(() => {
      if (notification?.message !== 'Restore job ready for confirmation! Review the backup contents below.') {
        setNotification(null);
      }
    }, 5000);
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

  // Enhanced handlers for new restore flow (kept for potential future use)
  // const handleRestoreJobSelect = (restoreId: string) => {
  //   setActiveRestoreId(restoreId);
  //   setShowRestoreModal(true);
  // };

  const handleConfirmRestore = async () => {
    console.log(`🔧 CONFIRM RESTORE CALLED for job: ${activeRestoreId}`);
    try {
      await confirmRestore();
      console.log('✅ CONFIRM RESTORE SUCCESS');
      setNotification({
        type: 'success',
        message: 'Restore confirmed and started'
      });
      setTimeout(() => setNotification(null), 3000);
    } catch (error) {
      console.error('❌ CONFIRM RESTORE FAILED:', error);
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
    refreshRestoreJobs().catch(console.error);
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
                  <h3>✅ Restore File Validated</h3>
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
                  <h3>Restore in Progress</h3>
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
              className="modal-close-overlay" 
              onClick={handleCloseModal}
              aria-label="Close modal"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default FZIPRestoreView;