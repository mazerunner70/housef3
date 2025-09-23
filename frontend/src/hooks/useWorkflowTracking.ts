/**
 * React hooks for tracking long-running workflows
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    trackWorkflow,
    stopWorkflowTracking as stopTrackingService,
    cancelWorkflow as cancelWorkflowService,
    listUserWorkflows,
    isWorkflowComplete,
    getWorkflowStatusColor,
    getWorkflowStatusDescription,
    WorkflowProgress,
    WorkflowStatus,
    WorkflowType
} from '../services/WorkflowTrackingService';

export interface UseWorkflowTrackingOptions {
    pollingInterval?: number;
    onComplete: (progress: WorkflowProgress) => void; // Required - always needed for completion handling
    enabled: boolean; // Controls whether the hook should be active
}

export interface UseWorkflowTrackingReturn {
    // State
    progress: WorkflowProgress | null;
    isTracking: boolean;
    error: string | null;

    // Actions
    startTracking: (workflowId: string) => Promise<void>;
    stopTracking: () => void;
    cancelWorkflow: (reason?: string) => Promise<boolean>;

    // Computed values
    isComplete: boolean;
    isInProgress: boolean;
    canCancel: boolean;
    statusColor: string;
    statusDescription: string;
}

export function useWorkflowTracking(
    options: UseWorkflowTrackingOptions
): UseWorkflowTrackingReturn {
    // Generate unique hook instance ID for logging - only once per hook instance
    const hookInstanceId = useRef<string | null>(null);
    const isFirstRender = useRef(true);
    // Using Math.random() for non-security debugging ID generation - safe for this context
    if (!hookInstanceId.current) {
        hookInstanceId.current = `hook_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    const [progress, setProgress] = useState<WorkflowProgress | null>(null);
    const [isTracking, setIsTracking] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const currentWorkflowId = useRef<string | null>(null);
    const optionsRef = useRef(options);
    const enabled = options.enabled;

    // Update options ref when options change
    useEffect(() => {
        optionsRef.current = options;
    }, [options]);

    // Single consolidated render log
    if (isFirstRender.current) {
        console.log(`🔧 useWorkflowTracking INITIALIZED (FIRST TIME)`, {
            hookInstanceId: hookInstanceId.current,
            enabled,
            isTracking,
            currentWorkflowId: currentWorkflowId.current,
            timestamp: new Date().toISOString()
        });
        isFirstRender.current = false;
    } else {
        console.log(`🔧 useWorkflowTracking RE-RENDER`, {
            hookInstanceId: hookInstanceId.current,
            enabled,
            isTracking,
            currentWorkflowId: currentWorkflowId.current,
            timestamp: new Date().toISOString()
        });
    }

    const stopTracking = useCallback(() => {
        console.log(`🛑 useWorkflowTracking STOP TRACKING`, {
            hookInstanceId: hookInstanceId.current,
            workflowId: currentWorkflowId.current,
            timestamp: new Date().toISOString()
        });

        if (currentWorkflowId.current) {
            stopTrackingService(currentWorkflowId.current);
            currentWorkflowId.current = null;
        }
        setIsTracking(false);
    }, []);

    // Stop tracking when disabled
    useEffect(() => {
        console.log(`🔄 useWorkflowTracking EFFECT (stop when disabled)`, {
            hookInstanceId: hookInstanceId.current,
            enabled,
            isTracking,
            willStop: !enabled && isTracking,
            timestamp: new Date().toISOString()
        });

        if (!enabled && isTracking) {
            console.log(`🛑 Stopping tracking because hook is disabled`, {
                hookInstanceId: hookInstanceId.current
            });

            // Stop tracking without using the callback to avoid dependency loop
            if (currentWorkflowId.current) {
                stopTrackingService(currentWorkflowId.current);
                currentWorkflowId.current = null;
            }
            setIsTracking(false);
        }
    }, [enabled, isTracking]); // Removed stopTracking dependency to prevent loop

    const startTracking = useCallback(async (workflowId: string) => {
        console.log(`🚀 useWorkflowTracking START TRACKING CALLED`, {
            hookInstanceId: hookInstanceId.current,
            workflowId,
            enabled,
            isTracking,
            currentWorkflowId: currentWorkflowId.current,
            timestamp: new Date().toISOString()
        });

        if (!enabled) {
            console.warn(`❌ Cannot start tracking: hook is disabled`, {
                hookInstanceId: hookInstanceId.current,
                workflowId
            });
            return;
        }

        if (currentWorkflowId.current === workflowId && isTracking) {
            console.log(`⚠️ Already tracking this workflow`, {
                hookInstanceId: hookInstanceId.current,
                workflowId
            });
            return; // Already tracking this workflow
        }

        // Stop any existing tracking
        if (currentWorkflowId.current) {
            console.log(`🔄 Stopping existing tracking before starting new one`, {
                hookInstanceId: hookInstanceId.current,
                oldWorkflowId: currentWorkflowId.current,
                newWorkflowId: workflowId
            });
            stopTrackingService(currentWorkflowId.current);
        }

        currentWorkflowId.current = workflowId;
        setIsTracking(true);
        setError(null);

        console.log(`✅ Starting workflow tracking`, {
            hookInstanceId: hookInstanceId.current,
            workflowId,
            timestamp: new Date().toISOString()
        });

        try {
            await trackWorkflow(
                workflowId,
                {
                    onUpdate: (newProgress: WorkflowProgress) => {
                        setProgress(newProgress);
                    },
                    onComplete: (finalProgress: WorkflowProgress) => {
                        setProgress(finalProgress);
                        setIsTracking(false);
                        // Call onComplete from current options (not from closure)
                        const currentOptions = optionsRef.current;
                        if (currentOptions?.onComplete) {
                            currentOptions.onComplete(finalProgress);
                        }
                    },
                    onError: (errorMessage: string) => {
                        setError(errorMessage);
                        setIsTracking(false);
                        // Error handling is internal - no external callback needed
                    }
                },
                optionsRef.current?.pollingInterval
            );
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to start tracking');
            setIsTracking(false);
        }
    }, [enabled, isTracking]); // Removed options dependency to prevent recreation

    const cancelWorkflow = useCallback(async (reason?: string): Promise<boolean> => {
        if (!currentWorkflowId.current) {
            return false;
        }

        try {
            const cancelFunc = cancelWorkflowService(currentWorkflowId.current, reason);
            const result = await cancelFunc();

            if (result.success) {
                stopTracking();
            }

            return result.success;
        } catch (err) {
            console.error('Failed to cancel workflow:', err);
            return false;
        }
    }, [stopTracking]);

    // Cleanup on unmount only
    useEffect(() => {
        console.log(`🔄 useWorkflowTracking MOUNT EFFECT`, {
            hookInstanceId: hookInstanceId.current,
            timestamp: new Date().toISOString()
        });

        return () => {
            console.log(`🧹 useWorkflowTracking CLEANUP (unmount)`, {
                hookInstanceId: hookInstanceId.current,
                timestamp: new Date().toISOString()
            });
            stopTracking();
        };
    }, []); // No dependencies - just cleanup on unmount

    // Computed values
    const isComplete = progress ? isWorkflowComplete(progress.status) : false;
    const isInProgress = isTracking && !isComplete;
    const canCancel = progress?.cancellable ?? false;
    const statusColor = progress ? getWorkflowStatusColor(progress.status) : 'gray';
    const statusDescription = progress ? getWorkflowStatusDescription(progress.status) : '';

    return {
        // State
        progress,
        isTracking,
        error,

        // Actions
        startTracking,
        stopTracking,
        cancelWorkflow,

        // Computed values
        isComplete,
        isInProgress,
        canCancel,
        statusColor,
        statusDescription
    };
}

/**
 * Hook for tracking multiple workflows
 */
export function useWorkflowList(filters?: {
    status?: WorkflowStatus[];
    workflowType?: WorkflowType[];
    limit?: number;
}) {
    const [workflows, setWorkflows] = useState<WorkflowProgress[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadWorkflows = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const listFunc = listUserWorkflows(filters);
            const result = await listFunc();
            setWorkflows(result.workflows);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load workflows');
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        loadWorkflows();
    }, [loadWorkflows]);

    return {
        workflows,
        loading,
        error,
        refresh: loadWorkflows
    };
}

