import React, { useState, useEffect } from 'react';
import { FZIPBackupJob, FZIPBackupStatus, formatBackupStatus } from '../../services/FZIPService';
import Button from './Button';
import ConfirmationModal from './ConfirmationModal';
import StatusBadge from './ui/StatusBadge';
import './FZIPBackupList.css';

interface FZIPBackupListProps {
  backups: FZIPBackupJob[];
  isLoading?: boolean;
  onDownload: (backupId: string, filename?: string) => Promise<void>;
  onDelete: (backupId: string) => Promise<void>;
  onRefreshStatus: (backupId: string) => Promise<FZIPBackupJob>;
  hasMore?: boolean;
  onLoadMore?: () => Promise<void>;
}

const FZIPBackupList: React.FC<FZIPBackupListProps> = ({
  backups,
  isLoading = false,
  onDownload,
  onDelete,
  onRefreshStatus,
  hasMore = false,
  onLoadMore
}) => {
  const [processingBackups, setProcessingBackups] = useState<Set<string>>(new Set());
  const [deleteConfirmation, setDeleteConfirmation] = useState<{
    isOpen: boolean;
    backupId: string;
    description?: string;
  }>({ isOpen: false, backupId: '' });

  // Auto-refresh processing backups
  useEffect(() => {
    const processingStatuses: string[] = [
      FZIPBackupStatus.INITIATED,
      FZIPBackupStatus.COLLECTING_DATA,
      FZIPBackupStatus.BUILDING_FZIP_PACKAGE,
      FZIPBackupStatus.UPLOADING
    ];
    
    const processingIds = backups
      .filter(backup => processingStatuses.includes(backup.status))
      .map(backup => backup.backupId);

    setProcessingBackups(new Set(processingIds));

    if (processingIds.length > 0) {
      const interval = setInterval(async () => {
        for (const backupId of processingIds) {
          try {
            const updatedBackup = await onRefreshStatus(backupId);
            if (updatedBackup.status === FZIPBackupStatus.COMPLETED || 
                updatedBackup.status === FZIPBackupStatus.FAILED) {
              setProcessingBackups(prev => {
                const newSet = new Set(prev);
                newSet.delete(backupId);
                return newSet;
              });
            }
          } catch (error) {
            console.error(`Failed to refresh status for backup ${backupId}:`, error);
          }
        }
      }, 3000); // Refresh every 3 seconds

      return () => clearInterval(interval);
    }
  }, [backups, onRefreshStatus]);

  const handleDownload = async (backup: FZIPBackupJob) => {
    try {
      const filename = `backup_${backup.backupId}_${new Date(backup.requestedAt).toISOString().split('T')[0]}.fzip`;
      await onDownload(backup.backupId, filename);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const handleDelete = async () => {
    try {
      await onDelete(deleteConfirmation.backupId);
      setDeleteConfirmation({ isOpen: false, backupId: '' });
    } catch (error) {
      console.error('Delete failed:', error);
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

  const getStatusVariant = (status: FZIPBackupStatus): 'success' | 'error' | 'warning' | 'processing' => {
    switch (status) {
      case FZIPBackupStatus.COMPLETED:
        return 'success';
      case FZIPBackupStatus.FAILED:
        return 'error';
      case FZIPBackupStatus.INITIATED:
      case FZIPBackupStatus.COLLECTING_DATA:
      case FZIPBackupStatus.BUILDING_FZIP_PACKAGE:
      case FZIPBackupStatus.UPLOADING:
        return 'processing';
      default:
        return 'warning';
    }
  };

  const renderValidationInfo = (backup: FZIPBackupJob) => {
    if (!backup.validation || backup.status !== FZIPBackupStatus.COMPLETED) {
      return null;
    }

    const { validation } = backup;
    const qualityColor = 
      validation.overall_quality === 'excellent' ? '#10b981' :
      validation.overall_quality === 'good' ? '#f59e0b' :
      validation.overall_quality === 'fair' ? '#f97316' : '#ef4444';

    return (
      <div className="backup-validation">
        <div className="validation-summary">
          <span 
            className="quality-badge"
            style={{ backgroundColor: qualityColor }}
          >
            {validation.overall_quality.toUpperCase()}
          </span>
          <span className="validation-scores">
            Integrity: {validation.data_integrity_score}% | 
            Completeness: {validation.completeness_score}%
          </span>
        </div>
        
        {validation.issues.length > 0 && (
          <div className="validation-issues">
            <strong>Issues:</strong>
            <ul>
              {validation.issues.map((issue, index) => (
                <li key={index}>{issue}</li>
              ))}
            </ul>
          </div>
        )}
        
        <div className="validation-details">
          <span>Files: {validation.files_processed - validation.files_failed}/{validation.files_processed}</span>
          <span>Compression: {validation.compression_ratio.toFixed(1)}%</span>
          <span>Time: {validation.processing_time_seconds.toFixed(1)}s</span>
        </div>
      </div>
    );
  };

  if (backups.length === 0 && !isLoading) {
    return (
      <div className="fzip-backup-list fzip-backup-list--empty">
        <div className="empty-state">
          <h3>No Backups Yet</h3>
          <p>Create your first backup to get started. Backups contain your complete financial profile.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fzip-backup-list">
      <div className="backup-list-header">
        <h3>Financial Profile Backups</h3>
        <p>Manage your FZIP backup packages. Backups expire after 24 hours.</p>
      </div>

      <div className="backup-items">
        {backups.map((backup) => (
          <div key={backup.backupId} className="backup-item">
            <div className="backup-item__header">
              <div className="backup-info">
                <h4 className="backup-title">
                  {backup.description || `${backup.backupType.replace('_', ' ')} Backup`}
                </h4>
                <div className="backup-meta">
                  <span className="backup-date">
                    Created: {formatDate(backup.requestedAt)}
                  </span>
                  {backup.completedAt && (
                    <span className="backup-date">
                      Completed: {formatDate(backup.completedAt)}
                    </span>
                  )}
                </div>
              </div>
              
              <div className="backup-status">
                <StatusBadge 
                  status={formatBackupStatus(backup.status)}
                  variant={getStatusVariant(backup.status)}
                />
              </div>
            </div>

            {processingBackups.has(backup.backupId) && (
              <div className="backup-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${backup.progress}%` }}
                  />
                </div>
                <span className="progress-text">{backup.progress}%</span>
              </div>
            )}

            {backup.error && (
              <div className="backup-error">
                <strong>Error:</strong> {backup.error}
              </div>
            )}

            {renderValidationInfo(backup)}

            <div className="backup-item__details">
              <div className="backup-stats">
                <span>Type: {backup.backupType.replace('_', ' ')}</span>
                {backup.packageSize && (
                  <span>Size: {formatFileSize(backup.packageSize)}</span>
                )}
                {backup.expiresAt && (
                  <span className={backup.expiresAt < Date.now() ? 'expired' : ''}>
                    Expires: {formatDate(backup.expiresAt)}
                  </span>
                )}
              </div>

              <div className="backup-actions">
                {backup.status === FZIPBackupStatus.COMPLETED && (
                  <Button
                    variant="secondary"
                    size="compact"
                    onClick={() => handleDownload(backup)}
                    disabled={backup.expiresAt ? backup.expiresAt < Date.now() : false}
                  >
                    Download
                  </Button>
                )}
                
                <Button
                  variant="danger"
                  size="compact"
                  onClick={() => setDeleteConfirmation({
                    isOpen: true,
                    backupId: backup.backupId,
                    description: backup.description
                  })}
                >
                  Delete
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {hasMore && (
        <div className="backup-list-footer">
          <Button
            variant="secondary"
            onClick={onLoadMore}
            disabled={isLoading}
          >
            {isLoading ? 'Loading...' : 'Load More Backups'}
          </Button>
        </div>
      )}

      <ConfirmationModal
        isOpen={deleteConfirmation.isOpen}
        title="Delete Backup"
        message={`Are you sure you want to delete this backup? ${
          deleteConfirmation.description ? `"${deleteConfirmation.description}"` : ''
        } This action cannot be undone.`}
        confirmButtonText="Delete"
        cancelButtonText="Cancel"
        onConfirm={handleDelete}
        onCancel={() => setDeleteConfirmation({ isOpen: false, backupId: '' })}
        type="danger"
      />
    </div>
  );
};

export default FZIPBackupList;