import React, { useState, useEffect } from 'react';
import { FZIPRestoreJob, FZIPRestoreStatus, formatRestoreStatus } from '../../services/FZIPService';
import Button from './Button';
import ConfirmationModal from './ConfirmationModal';
import StatusBadge from './ui/StatusBadge';
import './FZIPRestoreList.css';

interface FZIPRestoreListProps {
  restoreJobs: FZIPRestoreJob[];
  isLoading?: boolean;
  onDelete: (restoreId: string) => Promise<void>;
  onRefreshStatus: (restoreId: string) => Promise<FZIPRestoreJob>;
  onStartRestore: (restoreId: string) => Promise<void>;
  onCancelRestore?: (restoreId: string) => Promise<void>;
  hasMore?: boolean;
  onLoadMore?: () => Promise<void>;
}

const FZIPRestoreList: React.FC<FZIPRestoreListProps> = ({
  restoreJobs,
  isLoading = false,
  onDelete,
  onRefreshStatus,
  onStartRestore,
  onCancelRestore,
  hasMore = false,
  onLoadMore
}) => {
  const [processingJobs, setProcessingJobs] = useState<Set<string>>(new Set());
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    isOpen: boolean;
    restoreId: string;
  }>({ isOpen: false, restoreId: '' });
  const [cancelConfirmation, setCancelConfirmation] = useState<{
    isOpen: boolean;
    restoreId: string;
  }>({ isOpen: false, restoreId: '' });

  // Auto-refresh processing restore jobs
  useEffect(() => {
    const processingIds = restoreJobs
      .filter(job => 
        job.status === FZIPRestoreStatus.UPLOADED ||
        job.status === FZIPRestoreStatus.VALIDATING ||
        job.status === FZIPRestoreStatus.VALIDATION_PASSED ||
        job.status === FZIPRestoreStatus.PROCESSING
      )
      .map(job => job.jobId);

    setProcessingJobs(new Set(processingIds));

    if (processingIds.length > 0) {
      const interval = setInterval(async () => {
        for (const restoreId of processingIds) {
          try {
            const updatedJob = await onRefreshStatus(restoreId);
            if (updatedJob.status === FZIPRestoreStatus.COMPLETED || 
                updatedJob.status === FZIPRestoreStatus.FAILED ||
                updatedJob.status === FZIPRestoreStatus.VALIDATION_FAILED) {
              setProcessingJobs(prev => {
                const newSet = new Set(prev);
                newSet.delete(restoreId);
                return newSet;
              });
            }
          } catch (error) {
            console.error(`Failed to refresh status for restore ${restoreId}:`, error);
          }
        }
      }, 3000); // Refresh every 3 seconds

      return () => clearInterval(interval);
    }
  }, [restoreJobs, onRefreshStatus]);

  const handleDelete = async () => {
    try {
      await onDelete(deleteConfirmation.restoreId);
      setDeleteConfirmation({ isOpen: false, restoreId: '' });
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const handleCancel = async () => {
    if (!onCancelRestore) {
      setCancelConfirmation({ isOpen: false, restoreId: '' });
      return;
    }
    try {
      await onCancelRestore(cancelConfirmation.restoreId);
      setCancelConfirmation({ isOpen: false, restoreId: '' });
    } catch (error) {
      console.error('Cancel failed:', error);
    }
  };

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp).toLocaleString();
  };

  const getStatusVariant = (status: FZIPRestoreStatus): 'success' | 'error' | 'warning' | 'processing' => {
    switch (status) {
      case FZIPRestoreStatus.COMPLETED:
        return 'success';
      case FZIPRestoreStatus.FAILED:
      case FZIPRestoreStatus.VALIDATION_FAILED:
        return 'error';
      case FZIPRestoreStatus.UPLOADED:
      case FZIPRestoreStatus.VALIDATING:
      case FZIPRestoreStatus.VALIDATION_PASSED:
      case FZIPRestoreStatus.PROCESSING:
        return 'processing';
      default:
        return 'warning';
    }
  };

  const canStartRestore = (job: FZIPRestoreJob): boolean => {
    // Backend sets status to restore_validation_passed when ready; it may not include a
    // specific `ready` flag. Allow starting when status indicates validation passed.
    return job.status === FZIPRestoreStatus.VALIDATION_PASSED;
  };

  const renderValidationResults = (job: FZIPRestoreJob) => {
    if (!job.validationResults) return null;

    const { validationResults } = job;
    
    return (
      <div className="restore-validation">
        <h5>Validation Results:</h5>
        <div className="validation-checks">
          <div className={`validation-check ${validationResults.profileEmpty ? 'success' : 'error'}`}>
            <span className="check-icon">{validationResults.profileEmpty ? '✓' : '✗'}</span>
            <span>Profile Empty: {validationResults.profileEmpty ? 'Yes' : 'No'}</span>
          </div>
          <div className={`validation-check ${validationResults.schemaValid ? 'success' : 'error'}`}>
            <span className="check-icon">{validationResults.schemaValid ? '✓' : '✗'}</span>
            <span>Schema Valid: {validationResults.schemaValid ? 'Yes' : 'No'}</span>
          </div>
          <div className={`validation-check ${validationResults.ready ? 'success' : 'error'}`}>
            <span className="check-icon">{validationResults.ready ? '✓' : '✗'}</span>
            <span>Ready for Restore: {validationResults.ready ? 'Yes' : 'No'}</span>
          </div>
        </div>
      </div>
    );
  };

  const renderRestoreResults = (job: FZIPRestoreJob) => {
    if (!job.restoreResults || job.status !== FZIPRestoreStatus.COMPLETED) return null;

    const { restoreResults } = job;
    
    return (
      <div className="restore-results">
        <h5>Restore Results:</h5>
        <div className="results-grid">
          <div className="result-item">
            <span className="result-label">Accounts:</span>
            <span className="result-value">{restoreResults.accounts_restored}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Transactions:</span>
            <span className="result-value">{restoreResults.transactions_restored.toLocaleString()}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Categories:</span>
            <span className="result-value">{restoreResults.categories_restored}</span>
          </div>
          <div className="result-item">
            <span className="result-label">Files:</span>
            <span className="result-value">{restoreResults.files_restored}</span>
          </div>
        </div>
      </div>
    );
  };

  if (restoreJobs.length === 0 && !isLoading) {
    return (
      <div className="fzip-restore-list fzip-restore-list--empty">
        <div className="empty-state">
          <h3>No Restore Jobs</h3>
          <p>Upload a FZIP backup file to restore your financial profile.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fzip-restore-list">
      <div className="restore-list-header">
        <h3>Restore Jobs</h3>
        <p>Track your FZIP restore operations and their progress.</p>
      </div>

      <div className="restore-items">
        {restoreJobs.map((job) => (
          <div key={job.jobId} className="restore-item">
            <div className="restore-item__header">
              <div className="restore-info">
                <h4 className="restore-title">
                  Restore Job {job.jobId.slice(0, 8)}...
                </h4>
                <div className="restore-meta">
                  <span className="restore-date">
                    Uploaded: {formatDate(job.createdAt)}
                  </span>
                  {job.completedAt && (
                    <span className="restore-date">
                      Completed: {formatDate(job.completedAt)}
                    </span>
                  )}
                </div>
              </div>
              
              <div className="restore-status">
                <StatusBadge 
                  status={formatRestoreStatus(job.status)}
                  variant={getStatusVariant(job.status)}
                />
              </div>
            </div>

            {processingJobs.has(job.jobId) && (
              <div className="restore-progress">
                <div className="progress-info">
                  <span>
                    {job.currentPhase || 'Processing'}...
                  </span>
                  <span>{job.progress}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
              </div>
            )}

            {job.error && (
              <div className="restore-error">
                <strong>Error:</strong> {job.error}
              </div>
            )}

            {renderValidationResults(job)}
            {renderRestoreResults(job)}

            <div className="restore-item__details">
              <div className="restore-stats">
                {job.packageSize && (
                  <span>Package Size: {formatFileSize(job.packageSize)}</span>
                )}
                <span>Status: {formatRestoreStatus(job.status)}</span>
                {job.currentPhase && (
                  <span>Phase: {job.currentPhase}</span>
                )}
              </div>

              <div className="restore-actions">
                {canStartRestore(job) && (
                  <Button
                    variant="primary"
                    size="compact"
                    onClick={() => onStartRestore(job.jobId)}
                    disabled={processingJobs.has(job.jobId)}
                  >
                    Start Restore
                  </Button>
                )}
                {onCancelRestore && (
                  // Show Cancel for any non-terminal status (uploaded/validating/validation passed/processing)
                  [
                    FZIPRestoreStatus.UPLOADED,
                    FZIPRestoreStatus.VALIDATING,
                    FZIPRestoreStatus.VALIDATION_PASSED,
                    FZIPRestoreStatus.PROCESSING
                  ].includes(job.status) && (
                  <Button
                    variant="secondary"
                    size="compact"
                    onClick={() => setCancelConfirmation({ isOpen: true, restoreId: job.jobId })}
                  >
                    Cancel
                  </Button>
                  )
                )}
                <Button
                  variant="danger"
                  size="compact"
                  onClick={() => setDeleteConfirmation({
                    isOpen: true,
                    restoreId: job.jobId
                  })}
                  disabled={processingJobs.has(job.jobId)}
                >
                  Delete
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {hasMore && (
        <div className="restore-list-footer">
          <Button
            variant="secondary"
            onClick={onLoadMore}
            disabled={isLoading}
          >
            Load More Restore Jobs
          </Button>
        </div>
      )}

      <ConfirmationModal
        isOpen={deleteConfirmation.isOpen}
        title="Delete Restore Job"
        message="Are you sure you want to delete this restore job? This action cannot be undone."
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        onConfirm={handleDelete}
        onCancel={() => setDeleteConfirmation({ isOpen: false, restoreId: '' })}
        type="danger"
      />

      <ConfirmationModal
        isOpen={cancelConfirmation.isOpen}
        title="Cancel Restore"
        message="Are you sure you want to cancel this restore? It may stop mid-phase."
        confirmButtonText="Cancel Restore"
        cancelButtonText="Keep Running"
        onConfirm={handleCancel}
        onCancel={() => setCancelConfirmation({ isOpen: false, restoreId: '' })}
        type="warning"
      />
    </div>
  );
};

export default FZIPRestoreList;