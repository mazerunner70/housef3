/**
 * Generic Workflow Progress Modal
 * Can display progress for any long-running workflow
 */

import React, { useMemo, useCallback, useEffect, useRef } from 'react';
import { useWorkflowTracking } from '../../../hooks/useWorkflowTracking';
import { WorkflowStatus } from '../../../services/WorkflowTrackingService';
import './WorkflowProgressModal.css';

interface WorkflowProgressModalProps {
  workflowId: string;
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
  title?: string;
  mode?: 'full' | 'percent'; // New mode prop
}

export const WorkflowProgressModal: React.FC<WorkflowProgressModalProps> = ({
  workflowId,
  isOpen,
  onClose,
  onComplete,
  title,
  mode = 'full' // Default to full mode
}) => {
  // Generate unique modal instance ID for logging - only once per component instance
  const modalInstanceId = useRef<string | null>(null);
  if (!modalInstanceId.current) {
    modalInstanceId.current = `modal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    console.log(`🎭 WorkflowProgressModal INITIALIZED (FIRST TIME)`, {
      modalInstanceId: modalInstanceId.current,
      workflowId,
      isOpen,
      title,
      timestamp: new Date().toISOString()
    });
  } else {
    console.log(`🎭 WorkflowProgressModal RE-RENDER (existing instance)`, {
      modalInstanceId: modalInstanceId.current,
      workflowId,
      isOpen,
      title,
      timestamp: new Date().toISOString()
    });
  }

  // Memoize the onComplete callback to prevent recreation on every render
  const memoizedOnComplete = useCallback((finalProgress: any) => {
    console.log(`🎯 WorkflowProgressModal onComplete callback`, {
      modalInstanceId: modalInstanceId.current,
      workflowId,
      status: finalProgress.status,
      timestamp: new Date().toISOString()
    });

    if (finalProgress.status === WorkflowStatus.COMPLETED) {
      onComplete?.();
    }
    // Auto-close after 2 seconds for completed operations
    setTimeout(() => {
      onClose();
    }, 2000);
  }, [onComplete, onClose]);

  // Memoize the options object - use enabled to control when hook is active
  const trackingOptions = useMemo(() => {
    console.log(`🔧 WorkflowProgressModal creating trackingOptions`, {
      modalInstanceId: modalInstanceId.current,
      enabled: isOpen,
      timestamp: new Date().toISOString()
    });

    return {
      onComplete: memoizedOnComplete,
      enabled: isOpen // Only enable hook when modal is open
    };
  }, [memoizedOnComplete, isOpen]);

  const {
    progress,
    isTracking,
    error,
    cancelWorkflow,
    canCancel,
    statusColor,
    statusDescription,
    startTracking
  } = useWorkflowTracking(trackingOptions);

  // Start tracking when modal opens and workflowId is available
  // Use ref to track if we've already started to prevent duplicate calls
  const hasStartedTracking = useRef(false);

  useEffect(() => {
    console.log(`🔄 WorkflowProgressModal useEffect (start tracking)`, {
      modalInstanceId: modalInstanceId.current,
      isOpen,
      workflowId,
      hasStartedTracking: hasStartedTracking.current,
      willStartTracking: isOpen && workflowId && !hasStartedTracking.current,
      timestamp: new Date().toISOString()
    });

    if (isOpen && workflowId && !hasStartedTracking.current) {
      console.log(`🚀 WorkflowProgressModal calling startTracking`, {
        modalInstanceId: modalInstanceId.current,
        workflowId,
        timestamp: new Date().toISOString()
      });
      hasStartedTracking.current = true;
      startTracking(workflowId);
    }

    // Reset when modal closes or workflowId changes
    if (!isOpen || !workflowId) {
      hasStartedTracking.current = false;
    }
  }, [isOpen, workflowId]); // Removed startTracking dependency

  if (!isOpen) return null;

  const handleCancel = async () => {
    const success = await cancelWorkflow('Cancelled by user');
    if (success) {
      onClose();
    }
  };

  const getProgressBarColor = () => {
    switch (progress?.status) {
      case WorkflowStatus.COMPLETED:
        return 'var(--success-color)';
      case WorkflowStatus.FAILED:
      case WorkflowStatus.DENIED:
        return 'var(--error-color)';
      case WorkflowStatus.CANCELLED:
        return 'var(--warning-color)';
      default:
        return 'var(--primary-color)';
    }
  };

  const renderStepIndicator = () => {
    if (!progress?.steps || progress.steps.length === 0) {
      return null;
    }

    return (
      <div className="step-indicator">
        {progress.steps.map((step, index) => {
          const isActive = index === progress.currentStep;
          const isCompleted = index < progress.currentStep;
          const isFailed = progress.status === WorkflowStatus.FAILED && isActive;

          return (
            <div
              key={index}
              className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isFailed ? 'failed' : ''}`}
            >
              <div className="step-number">
                {isCompleted ? '✓' : index + 1}
              </div>
              <div className="step-description">
                {step.description}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // Render percent mode - simplified view
  const renderPercentMode = () => (
    <div className="modal-overlay">
      <div className={`operation-progress-modal ${mode === 'percent' ? 'percent-mode' : ''}`}>
        <div className="modal-header">
          <h3>{title || progress?.displayName || 'Operation in Progress'}</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {error ? (
            <div className="error-state">
              <div className="error-icon">⚠️</div>
              <p>{error}</p>
              <button className="retry-button" onClick={onClose}>Close</button>
            </div>
          ) : (
            <>
              {/* Simple Progress Circle */}
              <div className="percent-progress-container">
                <div className="progress-circle">
                  <svg className="progress-ring" width="120" height="120">
                    <circle
                      className="progress-ring-background"
                      stroke="#e5e7eb"
                      strokeWidth="8"
                      fill="transparent"
                      r="52"
                      cx="60"
                      cy="60"
                    />
                    <circle
                      className="progress-ring-progress"
                      stroke={getProgressBarColor()}
                      strokeWidth="8"
                      fill="transparent"
                      r="52"
                      cx="60"
                      cy="60"
                      strokeDasharray={`${2 * Math.PI * 52}`}
                      strokeDashoffset={`${2 * Math.PI * 52 * (1 - (progress?.progressPercentage || 0) / 100)}`}
                      transform="rotate(-90 60 60)"
                    />
                  </svg>
                  <div className="progress-text-center">
                    <span className="progress-percentage">{progress?.progressPercentage || 0}%</span>
                    <span className="progress-status">{statusDescription}</span>
                  </div>
                </div>
              </div>

              {/* Time Remaining */}
              {progress?.timeRemaining && (
                <div className="time-remaining-simple">
                  {progress.timeRemaining} remaining
                </div>
              )}

              {/* Final Status Messages */}
              {progress?.status === WorkflowStatus.COMPLETED && (
                <div className="success-message-simple">
                  <span className="success-icon">✅</span>
                  <span>Completed Successfully!</span>
                </div>
              )}

              {progress?.status === WorkflowStatus.FAILED && (
                <div className="error-message-simple">
                  <span className="error-icon">❌</span>
                  <span>{progress.errorMessage || 'Operation Failed'}</span>
                </div>
              )}

              {progress?.status === WorkflowStatus.DENIED && (
                <div className="denied-message-simple">
                  <span className="denied-icon">🚫</span>
                  <span>{progress.errorMessage || 'Operation Denied'}</span>
                </div>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          {canCancel && isTracking && (
            <button className="cancel-button" onClick={handleCancel}>
              Cancel
            </button>
          )}
          {!isTracking && (
            <button className="close-button-footer" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );

  // Return appropriate mode
  if (mode === 'percent') {
    return renderPercentMode();
  }

  return (
    <div className="modal-overlay">
      <div className="operation-progress-modal">
        <div className="modal-header">
          <h3>{title || progress?.displayName || 'Operation in Progress'}</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {error ? (
            <div className="error-state">
              <div className="error-icon">⚠️</div>
              <h4>Operation Error</h4>
              <p>{error}</p>
              <button className="retry-button" onClick={onClose}>
                Close
              </button>
            </div>
          ) : (
            <>
              {/* Progress Bar */}
              <div className="progress-section">
                <div className="progress-bar-container">
                  <div
                    className="progress-bar"
                    style={{
                      width: `${progress?.progressPercentage || 0}%`,
                      backgroundColor: getProgressBarColor()
                    }}
                  />
                </div>
                <div className="progress-text">
                  {progress?.progressPercentage || 0}% Complete
                </div>
              </div>

              {/* Current Status */}
              <div className="status-section">
                <div className={`status-badge ${statusColor}`}>
                  {statusDescription}
                </div>
                {progress?.currentStepDescription && (
                  <p className="step-description">
                    {progress.currentStepDescription}
                  </p>
                )}
              </div>

              {/* Time Remaining */}
              {progress?.timeRemaining && (
                <div className="time-section">
                  <span className="time-label">Estimated time remaining:</span>
                  <span className="time-value">{progress.timeRemaining}</span>
                </div>
              )}

              {/* Step Indicator */}
              {renderStepIndicator()}

              {/* Success/Failure Messages */}
              {progress?.status === WorkflowStatus.COMPLETED && (
                <div className="success-message">
                  <div className="success-icon">✅</div>
                  <h4>Operation Completed Successfully!</h4>
                  <p>The operation has finished successfully.</p>
                </div>
              )}

              {progress?.status === WorkflowStatus.FAILED && (
                <div className="error-message">
                  <div className="error-icon">❌</div>
                  <h4>Operation Failed</h4>
                  <p>{progress.errorMessage || 'The operation encountered an error.'}</p>
                </div>
              )}

              {progress?.status === WorkflowStatus.DENIED && (
                <div className="denied-message">
                  <div className="denied-icon">🚫</div>
                  <h4>Operation Denied</h4>
                  <p>{progress.errorMessage || 'The operation was not approved.'}</p>
                </div>
              )}

              {progress?.status === WorkflowStatus.CANCELLED && (
                <div className="cancelled-message">
                  <div className="cancelled-icon">⏹️</div>
                  <h4>Operation Cancelled</h4>
                  <p>The operation was cancelled.</p>
                </div>
              )}
            </>
          )}
        </div>

        <div className="modal-footer">
          {canCancel && isTracking && (
            <button className="cancel-button" onClick={handleCancel}>
              Cancel Operation
            </button>
          )}

          {!isTracking && (
            <button className="close-button-footer" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowProgressModal;
