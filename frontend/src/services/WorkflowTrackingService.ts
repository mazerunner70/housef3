/**
 * Workflow Tracking Service
 * Handles long-running, multi-step workflows with polling and state management
 */

import { ApiClient } from '@/utils/apiClient';
import { validateApiResponse } from '@/utils/zodErrorHandler';
import { z } from 'zod';

// Import efficient logging utilities
import {
    withApiLogging,
    withServiceLogging,
    createLogger
} from '@/utils/logger';

export enum WorkflowStatus {
    INITIATED = 'initiated',
    IN_PROGRESS = 'in_progress',
    WAITING_FOR_APPROVAL = 'waiting_for_approval',
    APPROVED = 'approved',
    EXECUTING = 'executing',
    COMPLETED = 'completed',
    FAILED = 'failed',
    CANCELLED = 'cancelled',
    DENIED = 'denied'
}

export enum WorkflowType {
    FILE_DELETION = 'file_deletion',
    FILE_UPLOAD = 'file_upload',
    ACCOUNT_MODIFICATION = 'account_modification',
    DATA_EXPORT = 'data_export',
    BULK_CATEGORIZATION = 'bulk_categorization',
    ACCOUNT_MIGRATION = 'account_migration'
}

export interface WorkflowStep {
    name: string;
    description: string;
}

export interface WorkflowProgress {
    operationId: string; // Keep as operationId for backend compatibility
    operationType: WorkflowType; // Keep as operationType for backend compatibility
    displayName: string;
    entityId: string;
    status: WorkflowStatus;
    progressPercentage: number;
    currentStep: number;
    totalSteps: number;
    currentStepDescription?: string;
    estimatedCompletion?: number; // Backend returns int timestamp
    timeRemaining?: string | null;
    createdAt: number; // Backend returns int timestamp
    updatedAt: number; // Backend returns int timestamp
    errorMessage?: string | null; // Backend can return null
    cancellable: boolean;
    context: Record<string, any>;
    steps: WorkflowStep[];
}

export interface WorkflowTracker {
    workflowId: string;
    onUpdate: (progress: WorkflowProgress) => void;
    onComplete: (progress: WorkflowProgress) => void;
    onError: (error: string) => void;
    intervalId?: NodeJS.Timeout;
}

// Response interfaces following naming conventions
export interface WorkflowListResponse {
    workflows: WorkflowProgress[];
    total: number;
}

export interface CancelWorkflowResponse {
    success: boolean;
    message: string;
}


// Zod schemas for response validation
const WorkflowStepSchema = z.object({
    name: z.string(),
    description: z.string()
});

const WorkflowProgressSchema = z.object({
    operationId: z.string(), // Backend still uses operationId
    operationType: z.enum(Object.values(WorkflowType) as [WorkflowType, ...WorkflowType[]]), // Backend uses operationType
    displayName: z.string(),
    entityId: z.string(),
    status: z.enum([WorkflowStatus.INITIATED, WorkflowStatus.IN_PROGRESS, WorkflowStatus.WAITING_FOR_APPROVAL, WorkflowStatus.APPROVED, WorkflowStatus.EXECUTING, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED, WorkflowStatus.DENIED]),
    progressPercentage: z.number(),
    currentStep: z.number(),
    totalSteps: z.number(),
    currentStepDescription: z.string().optional(),
    estimatedCompletion: z.number().optional(), // Backend returns int timestamp
    timeRemaining: z.string().nullable().optional(),
    createdAt: z.number(), // Backend returns int timestamp
    updatedAt: z.number(), // Backend returns int timestamp
    errorMessage: z.string().nullable().optional(), // Backend can return null
    cancellable: z.boolean(),
    context: z.record(z.string(), z.any()),
    steps: z.array(WorkflowStepSchema)
});

const WorkflowListResponseSchema = z.object({
    workflows: z.array(WorkflowProgressSchema),
    total: z.number()
});

const CancelWorkflowResponseSchema = z.object({
    success: z.boolean(),
    message: z.string()
});

// API endpoint path - ApiClient will handle the full URL construction
const API_ENDPOINT = '/workflows';

// Logger for workflow operations
const logger = createLogger('WorkflowTrackingService');

// Module-level state for tracking (replacing class state)
const activeTrackers = new Map<string, WorkflowTracker>();
const defaultPollingInterval = 2000; // 2 seconds

// ============ EFFICIENT LOGGING IMPLEMENTATIONS ============

/**
 * Get current status of a workflow
 */
export const getWorkflowStatus = (workflowId: string) => withApiLogging(
    'WorkflowTrackingService',
    `${API_ENDPOINT}/${workflowId}/status`,
    'GET',
    async (url) => {
        try {
            const result = await validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => {
                    // Extract workflow data from the nested response structure
                    const workflowData = rawData.workflow || rawData;
                    return WorkflowProgressSchema.parse(workflowData);
                },
                'workflow status data',
                `Failed to load workflow status for ${workflowId}. The workflow data format is invalid.`
            );
            return result;
        } catch (error) {
            // Handle 404 specifically - workflow not found
            if (error instanceof Error && error.message.includes('404')) {
                logger.info('Workflow not found (404), returning null', {
                    workflowId,
                    errorMessage: error.message
                });
                return null;
            }
            logger.error('Unexpected error in getWorkflowStatus', {
                workflowId,
                errorMessage: error instanceof Error ? error.message : 'Unknown error',
                errorType: typeof error
            });
            throw error;
        }
    },
    {
        operationName: `getWorkflowStatus:${workflowId}`,
        successData: (result) => result ? {
            workflowId,
            status: result.status,
            progress: result.progressPercentage,
            workflowType: result.operationType
        } : { workflowId, notFound: true }
    }
);

/**
 * List workflows for current user
 */
export const listUserWorkflows = (filters?: {
    status?: WorkflowStatus[];
    workflowType?: WorkflowType[];
    limit?: number;
}) => {
    const params = new URLSearchParams();

    if (filters?.status) {
        params.append('status', filters.status.join(','));
    }
    if (filters?.workflowType) {
        params.append('workflowType', filters.workflowType.join(','));
    }
    if (filters?.limit) {
        params.append('limit', filters.limit.toString());
    }

    return withApiLogging(
        'WorkflowTrackingService',
        API_ENDPOINT,
        'GET',
        async (url) => {
            return validateApiResponse(
                () => ApiClient.getJson<any>(url),
                (rawData) => WorkflowListResponseSchema.parse(rawData),
                'workflows list data',
                'Failed to load workflows list. The server response format is invalid.'
            );
        },
        {
            operationName: 'listUserWorkflows',
            queryParams: params.toString() ? params : undefined,
            successData: (result) => ({
                workflowCount: result.workflows.length,
                totalWorkflows: result.total,
                filters: filters ? Object.keys(filters).filter(key => filters[key as keyof typeof filters]) : []
            })
        }
    );
};

/**
 * Cancel a workflow
 */
export const cancelWorkflow = (workflowId: string, reason?: string) => withApiLogging(
    'WorkflowTrackingService',
    `${API_ENDPOINT}/${workflowId}/cancel`,
    'POST',
    async (url) => {
        return validateApiResponse(
            () => ApiClient.postJson<any>(url, {
                reason: reason || 'Cancelled by user'
            }),
            (rawData) => CancelWorkflowResponseSchema.parse(rawData),
            'cancel workflow response',
            `Failed to cancel workflow ${workflowId}. The server response format is invalid.`
        );
    },
    {
        operationName: `cancelWorkflow:${workflowId}`,
        successData: (result) => ({
            workflowId,
            success: result.success,
            reason: reason || 'Cancelled by user'
        })
    }
);


// ============ POLLING AND TRACKING FUNCTIONS ============

/**
 * Check if workflow status indicates completion
 */
export const isWorkflowComplete = (status: WorkflowStatus): boolean => {
    return [
        WorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED,
        WorkflowStatus.CANCELLED,
        WorkflowStatus.DENIED
    ].includes(status);
};

/**
 * Start tracking a long-running workflow
 * Note: Consider using a React hook (useWorkflowTracking) for component-based polling
 */
export const trackWorkflow = withServiceLogging(
    'WorkflowTrackingService',
    'trackWorkflow',
    async (
        workflowId: string,
        callbacks: {
            onUpdate?: (progress: WorkflowProgress) => void;
            onComplete?: (progress: WorkflowProgress) => void;
            onError?: (error: string) => void;
        },
        pollingInterval: number = defaultPollingInterval
    ): Promise<void> => {
        // Check if already tracking this workflow
        const existingTracker = activeTrackers.get(workflowId);
        if (existingTracker?.intervalId) {
            logger.warn('Workflow already being tracked, ignoring duplicate request', { workflowId });
            return; // Don't start a new tracker if one is already active
        }

        // Stop existing tracker if any (defensive cleanup)
        stopWorkflowTracking(workflowId);

        const tracker: WorkflowTracker = {
            workflowId,
            onUpdate: callbacks.onUpdate || (() => { }),
            onComplete: callbacks.onComplete || (() => { }),
            onError: callbacks.onError || (() => { })
        };

        activeTrackers.set(workflowId, tracker);
        logger.info('Started workflow tracking', { workflowId, pollingInterval });

        // Start polling with retry logic for initial 404s
        let retryCount = 0;
        const maxRetries = 5; // Allow up to 5 retries for initial 404s

        const poll = async () => {
            try {
                const progressFunc = getWorkflowStatus(workflowId);
                const progress = await progressFunc();

                if (!progress) {
                    // If workflow not found and we haven't exceeded retries, wait longer and try again
                    if (retryCount < maxRetries) {
                        retryCount++;
                        const backoffDelay = Math.min(pollingInterval * Math.pow(2, retryCount), 10000); // Max 10 seconds
                        tracker.intervalId = setTimeout(poll, backoffDelay);
                        return;
                    }

                    tracker.onError('Workflow not found after retries');
                    stopWorkflowTracking(workflowId);
                    return;
                }

                // Reset retry count once we successfully get a response
                retryCount = 0;

                // Call update callback
                tracker.onUpdate(progress);

                // Check if workflow is complete
                if (isWorkflowComplete(progress.status)) {
                    tracker.onComplete(progress);
                    stopWorkflowTracking(workflowId);
                    return;
                }

                // Schedule next poll
                tracker.intervalId = setTimeout(poll, pollingInterval);

            } catch (error) {
                tracker.onError(error instanceof Error ? error.message : 'Unknown error');
                stopWorkflowTracking(workflowId);
            }
        };

        // Wait a bit before first poll to let backend create the operation record
        tracker.intervalId = setTimeout(poll, 3000); // 3 second initial delay
    },
    {
        logArgs: ([workflowId, callbacks, pollingInterval]) => ({
            workflowId,
            hasOnUpdate: !!callbacks.onUpdate,
            hasOnComplete: !!callbacks.onComplete,
            hasOnError: !!callbacks.onError,
            pollingInterval: pollingInterval || defaultPollingInterval
        }),
        logResult: () => ({ trackingStarted: true })
    }
);

/**
 * Stop tracking a workflow
 */
export const stopWorkflowTracking = (workflowId: string): void => {
    logger.info('Stopping workflow tracking', { workflowId });

    const tracker = activeTrackers.get(workflowId);
    if (tracker?.intervalId) {
        clearTimeout(tracker.intervalId);
    }
    activeTrackers.delete(workflowId);

    logger.info('Workflow tracking stopped', {
        workflowId,
        activeTrackersCount: activeTrackers.size
    });
};

/**
 * Stop all active tracking
 */
export const stopAllWorkflowTracking = (): void => {
    logger.info('Stopping all workflow tracking', {
        activeTrackersCount: activeTrackers.size
    });

    for (const workflowId of activeTrackers.keys()) {
        stopWorkflowTracking(workflowId);
    }

    logger.info('All workflow tracking stopped');
};

/**
 * Get list of currently tracked workflows
 */
export const getActiveWorkflowTrackers = (): string[] => {
    return Array.from(activeTrackers.keys());
};


// ============ UTILITY FUNCTIONS ============

/**
 * Get human-readable status description
 */
export const getWorkflowStatusDescription = (status: WorkflowStatus): string => {
    const descriptions: Record<WorkflowStatus, string> = {
        [WorkflowStatus.INITIATED]: 'Starting...',
        [WorkflowStatus.IN_PROGRESS]: 'In Progress',
        [WorkflowStatus.WAITING_FOR_APPROVAL]: 'Waiting for Approval',
        [WorkflowStatus.APPROVED]: 'Approved',
        [WorkflowStatus.EXECUTING]: 'Executing',
        [WorkflowStatus.COMPLETED]: 'Completed',
        [WorkflowStatus.FAILED]: 'Failed',
        [WorkflowStatus.CANCELLED]: 'Cancelled',
        [WorkflowStatus.DENIED]: 'Denied'
    };

    return descriptions[status] || status;
};

/**
 * Get status color for UI
 */
export const getWorkflowStatusColor = (status: WorkflowStatus): string => {
    const colors: Record<WorkflowStatus, string> = {
        [WorkflowStatus.INITIATED]: 'blue',
        [WorkflowStatus.IN_PROGRESS]: 'blue',
        [WorkflowStatus.WAITING_FOR_APPROVAL]: 'orange',
        [WorkflowStatus.APPROVED]: 'green',
        [WorkflowStatus.EXECUTING]: 'blue',
        [WorkflowStatus.COMPLETED]: 'green',
        [WorkflowStatus.FAILED]: 'red',
        [WorkflowStatus.CANCELLED]: 'gray',
        [WorkflowStatus.DENIED]: 'red'
    };

    return colors[status] || 'gray';
};


// ============ CLEANUP ============

// Cleanup on page unload
if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', () => {
        stopAllWorkflowTracking();
    });
}
