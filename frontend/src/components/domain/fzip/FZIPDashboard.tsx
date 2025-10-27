import React, { useState } from 'react';
import { useFZIPBackups } from './hooks/useFZIPBackups';
import { useFZIPRestore } from './hooks/useFZIPRestore';
import { useFZIPRestoreStatus } from './hooks/useFZIPRestoreStatus';
import FZIPBackupCreator from './components/FZIPBackupCreator';
import FZIPBackupList from './components/FZIPBackupList';
import FZIPRestoreUpload from './components/FZIPRestoreUpload';
import FZIPRestoreList from './components/FZIPRestoreList';
import { FZIPRestoreSummary } from './components/FZIPRestoreSummary';
import { FZIPRestoreResults } from './components/FZIPRestoreResults';
import { FZIPRestoreError } from './components/FZIPRestoreError';
import { FZIPRestoreStatus, InitiateFZIPBackupRequest } from '@/services/FZIPService';
import Button from '@/components/ui/Button';
import './FZIPDashboard.css';

type TabType = 'backup' | 'restore';

// Constants for sticky notifications
const CONFIRMATION_READY_MESSAGE = 'Restore job ready for confirmation! Click "Start Restore" in the job list below.';

/**
 * FZIPDashboard - Main component for FZIP backup and restore management
 * 
 * Role: Provides tabbed interface for backup creation/management and restore operations
 * Features:
 * - Complete backup creation and management
 * - FZIP file upload and restore
 * - Real-time progress tracking
 * - Comprehensive error handling
 */
const FZIPDashboard: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TabType>('backup');

    // Backup state and operations
    const {
        backups,
        isLoading: isBackupLoading,
        error: backupError,
        createBackup,
        refreshBackups,
        deleteBackup,
        downloadBackup,
        getBackupStatus,
        hasMore: hasMoreBackups,
        loadMore: loadMoreBackups
    } = useFZIPBackups();

    // Restore state and operations
    const {
        restoreJobs,
        isLoading: isRestoreLoading,
        error: restoreError,
        profileError,
        profileSummary,
        refreshRestoreJobs,
        deleteRestoreJob,
        getRestoreStatus,
        startRestoreProcessing,
        cancelRestore,
        hasMore: hasMoreRestores,
        loadMore: loadMoreRestores,
        clearErrors
    } = useFZIPRestore();

    // Backup UI state
    const [showBackupCreator, setShowBackupCreator] = useState(false);

    // Restore UI state
    const [showRestoreUpload, setShowRestoreUpload] = useState(true);
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

    // Notification state
    const [notification, setNotification] = useState<{
        type: 'success' | 'error' | 'warning';
        message: string;
    } | null>(null);

    // ========================================
    // Backup Handlers
    // ========================================

    const handleCreateBackup = async (request: InitiateFZIPBackupRequest) => {
        try {
            const backupId = await createBackup(request);
            setNotification({
                type: 'success',
                message: `Backup created successfully! ID: ${backupId}`
            });
            setShowBackupCreator(false);
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

    const handleDownloadBackup = async (backupId: string, filename?: string) => {
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

    const handleDeleteBackup = async (backupId: string) => {
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

    const handleRefreshBackups = async () => {
        try {
            await refreshBackups();
            setNotification({
                type: 'success',
                message: 'Backup list refreshed'
            });
            setTimeout(() => setNotification(null), 2000);
        } catch (error) {
            console.error('Error refreshing backups:', error);
            setNotification({
                type: 'error',
                message: 'Failed to refresh backup list'
            });
            setTimeout(() => setNotification(null), 5000);
        }
    };

    // ========================================
    // Restore Handlers
    // ========================================

    // Helper functions for restore upload polling
    const findNewRestoreJob = (updatedJobs: any[], currentJobCount: number) => {
        const confirmationJob = updatedJobs.find(job =>
            job.status === FZIPRestoreStatus.AWAITING_CONFIRMATION
        );
        if (confirmationJob) return confirmationJob;
        if (updatedJobs.length > currentJobCount) return updatedJobs[0];
        return null;
    };

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

    const handleRestoreUploaded = async () => {
        setShowRestoreUpload(false);
        const maxAttempts = 15;
        const pollInterval = 2000;
        const currentJobCount = restoreJobs.length;

        setNotification({
            type: 'success',
            message: 'Upload successful. Creating restore job...'
        });

        let foundJob: any = null;
        for (let attempts = 1; attempts <= maxAttempts && !foundJob; attempts++) {
            const result = await performPollingAttempt(attempts, maxAttempts, currentJobCount);
            if (result.success && result.job) {
                foundJob = result.job;
                break;
            }
            if (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, pollInterval));
            }
        }

        if (foundJob) {
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
        } else {
            setNotification({
                type: 'warning',
                message: 'Upload completed but restore job creation is taking longer than expected. Please refresh to check status.'
            });
        }

        setTimeout(() => {
            setNotification(currentNotification => {
                if (currentNotification?.message !== CONFIRMATION_READY_MESSAGE) {
                    return null;
                }
                return currentNotification;
            });
        }, 5000);
    };

    const handleDeleteRestore = async (restoreId: string) => {
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

    const handleRefreshRestores = async () => {
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
            // Handle refresh error silently
        });
    };

    // ========================================
    // Render
    // ========================================

    return (
        <div className="fzip-dashboard">
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

            {/* Tab Content */}
            <div className="tab-content">
                {/* Backup Tab */}
                {activeTab === 'backup' && (
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
                                    onClick={handleRefreshBackups}
                                    disabled={isBackupLoading}
                                >
                                    Refresh
                                </Button>

                                <Button
                                    variant="primary"
                                    onClick={() => setShowBackupCreator(true)}
                                    disabled={showBackupCreator}
                                >
                                    Create Backup
                                </Button>
                            </div>
                        </div>

                        {/* Global Error */}
                        {backupError && (
                            <div className="global-error">
                                <div className="error-content">
                                    <h3>Service Status</h3>
                                    <p>{backupError}</p>
                                    {backupError.includes('service may not be available') || backupError.includes('service is not available') ? (
                                        <div className="service-notice">
                                            <p><strong>Note:</strong> The backup and restore feature requires backend deployment. If you're a developer, make sure the FZIP endpoints are deployed.</p>
                                        </div>
                                    ) : (
                                        <Button
                                            variant="secondary"
                                            size="compact"
                                            onClick={handleRefreshBackups}
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
                            {showBackupCreator && (
                                <div className="creator-section">
                                    <div className="section-header">
                                        <h2>Create New Backup</h2>
                                        <Button
                                            variant="secondary"
                                            size="compact"
                                            onClick={() => setShowBackupCreator(false)}
                                        >
                                            Cancel
                                        </Button>
                                    </div>

                                    <FZIPBackupCreator
                                        onCreateBackup={handleCreateBackup}
                                        isLoading={isBackupLoading}
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
                                                {backups.length} {backups.length === 1 ? 'backup' : 'backups'}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <FZIPBackupList
                                    backups={backups}
                                    isLoading={isBackupLoading}
                                    onDownload={handleDownloadBackup}
                                    onDelete={handleDeleteBackup}
                                    onRefreshStatus={getBackupStatus}
                                    hasMore={hasMoreBackups}
                                    onLoadMore={loadMoreBackups}
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
                )}

                {/* Restore Tab */}
                {activeTab === 'restore' && (
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
                                    onClick={handleRefreshRestores}
                                    disabled={isRestoreLoading}
                                >
                                    Refresh
                                </Button>

                                {!showRestoreUpload && (
                                    <Button
                                        variant="primary"
                                        onClick={() => {
                                            setShowRestoreUpload(true);
                                            clearErrors();
                                        }}
                                    >
                                        New Restore
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Global Error */}
                        {restoreError && !profileError && (
                            <div className="global-error">
                                <div className="error-content">
                                    <h3>Service Status</h3>
                                    <p>{restoreError}</p>
                                    {restoreError.includes('service may not be available') || restoreError.includes('service is not available') ? (
                                        <div className="service-notice">
                                            <p><strong>Note:</strong> The backup and restore feature requires backend deployment. If you're a developer, make sure the FZIP endpoints are deployed.</p>
                                        </div>
                                    ) : (
                                        <Button
                                            variant="secondary"
                                            size="compact"
                                            onClick={handleRefreshRestores}
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
                            {showRestoreUpload && (
                                <div className="upload-section">
                                    <div className="section-header">
                                        <h2>Upload FZIP Backup</h2>
                                        {restoreJobs.length > 0 && (
                                            <Button
                                                variant="secondary"
                                                size="compact"
                                                onClick={() => setShowRestoreUpload(false)}
                                            >
                                                Hide Upload
                                            </Button>
                                        )}
                                    </div>

                                    <FZIPRestoreUpload
                                        onUploaded={handleRestoreUploaded}
                                        isLoading={isRestoreLoading}
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
                                                {restoreJobs.length} {restoreJobs.length === 1 ? 'job' : 'jobs'}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <FZIPRestoreList
                                    restoreJobs={restoreJobs}
                                    isLoading={isRestoreLoading}
                                    onDelete={handleDeleteRestore}
                                    onRefreshStatus={getRestoreStatus}
                                    onStartRestore={startRestoreProcessing}
                                    onCancelRestore={cancelRestore}
                                    hasMore={hasMoreRestores}
                                    onLoadMore={loadMoreRestores}
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
                )}
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

            {/* Enhanced Restore Modal */}
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

                            {/* Validation Passed View */}
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
                                        <Button variant="primary" onClick={handleConfirmRestore}>
                                            Start Restore
                                        </Button>
                                        <Button variant="secondary" onClick={handleCloseModal}>
                                            Cancel
                                        </Button>
                                    </div>
                                </div>
                            )}

                            {/* Loading/Progress View */}
                            {(activeRestoreStatus.status !== FZIPRestoreStatus.AWAITING_CONFIRMATION &&
                                activeRestoreStatus.status !== FZIPRestoreStatus.VALIDATION_PASSED &&
                                activeRestoreStatus.status !== FZIPRestoreStatus.COMPLETED &&
                                activeRestoreStatus.status !== FZIPRestoreStatus.FAILED) && (
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

                            {/* Close button */}
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

export default FZIPDashboard;

