import { useState, useEffect, useCallback } from 'react';
import {
  FZIPRestoreJob,
  FZIPRestoreStatus,
  getFZIPRestoreStatus,
  confirmRestoreStart,
  retryRestore,
  deleteFZIPRestoreJob
} from '../services/FZIPService';

export interface UseFZIPRestoreStatusResult {
  status: FZIPRestoreJob | null;
  isPolling: boolean;
  error: string | null;
  confirmRestore: () => Promise<void>;
  retryRestore: () => Promise<void>;
  abortRestore: () => Promise<void>;
  clearError: () => void;
}

// Progressive polling intervals based on status
const getPollingInterval = (status: FZIPRestoreStatus, elapsedTime: number): number => {
  const intervals: Record<FZIPRestoreStatus, number> = {
    [FZIPRestoreStatus.UPLOADED]: 2000,              // Fast while validating
    [FZIPRestoreStatus.VALIDATING]: 1000,            // Fastest during validation
    [FZIPRestoreStatus.VALIDATION_PASSED]: 2000,     // Medium speed
    [FZIPRestoreStatus.VALIDATION_FAILED]: 0,        // Stop polling
    [FZIPRestoreStatus.AWAITING_CONFIRMATION]: 0,    // Stop polling - user action required
    [FZIPRestoreStatus.PROCESSING]: 500,             // Very fast during restore
    [FZIPRestoreStatus.COMPLETED]: 0,                // Stop polling
    [FZIPRestoreStatus.FAILED]: 0,                   // Stop polling
    [FZIPRestoreStatus.CANCELED]: 0                  // Stop polling
  };

  const baseInterval = intervals[status] || 5000;

  // Slow down after 1 minute of processing to avoid overwhelming the server
  if (status === FZIPRestoreStatus.PROCESSING && elapsedTime > 60000) {
    return Math.min(baseInterval * 2, 2000);
  }

  return baseInterval;
};

// Check if status requires polling
const shouldPoll = (status: FZIPRestoreStatus): boolean => {
  return getPollingInterval(status, 0) > 0;
};

export const useFZIPRestoreStatus = (restoreId: string | null): UseFZIPRestoreStatusResult => {
  const [status, setStatus] = useState<FZIPRestoreJob | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const fetchStatus = useCallback(async (jobId: string): Promise<FZIPRestoreJob | null> => {
    try {
      clearError();
      console.log(`🔄 FETCHING STATUS for job: ${jobId}`);
      const response = await getFZIPRestoreStatus(jobId);
      console.log(`📊 STATUS RESPONSE:`, {
        jobId: response.jobId,
        status: response.status,
        progress: response.progress,
        currentPhase: response.currentPhase,
        hasSummary: !!response.summary,
        hasValidationResults: !!response.validationResults,
        hasRestoreResults: !!response.restoreResults
      });
      setStatus(response);
      return response;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch restore status';
      console.error(`❌ ERROR FETCHING STATUS for ${jobId}:`, errorMessage);
      setError(errorMessage);
      setIsPolling(false);
      return null;
    }
  }, [clearError]);

  const confirmRestore = useCallback(async (): Promise<void> => {
    if (!restoreId) {
      setError('No restore ID available');
      return;
    }

    try {
      clearError();
      await confirmRestoreStart(restoreId);
      // Immediately fetch updated status
      await fetchStatus(restoreId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to confirm restore';
      setError(errorMessage);
    }
  }, [restoreId, clearError, fetchStatus]);

  const retryRestoreAction = useCallback(async (): Promise<void> => {
    if (!restoreId) {
      setError('No restore ID available');
      return;
    }

    try {
      clearError();
      await retryRestore(restoreId);
      // Immediately fetch updated status - polling will restart automatically via effect
      await fetchStatus(restoreId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to retry restore';
      setError(errorMessage);
    }
  }, [restoreId, clearError, fetchStatus]);

  const abortRestore = useCallback(async (): Promise<void> => {
    if (!restoreId) {
      setError('No restore ID available');
      return;
    }

    try {
      clearError();
      await deleteFZIPRestoreJob(restoreId);
      setStatus(null);
      setIsPolling(false);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to abort restore';
      setError(errorMessage);
    }
  }, [restoreId, clearError]);

  // Main polling effect - responsive to status transitions
  useEffect(() => {
    if (!restoreId) {
      setStatus(null);
      setIsPolling(false);
      return;
    }

    // Only start polling if status requires it
    if (status && !shouldPoll(status.status)) {
      setIsPolling(false);
      return;
    }

    let intervalId: number | null = null;
    let isMounted = true;
    const startTime = Date.now();

    const poll = async () => {
      if (!isMounted) return;

      try {
        const response = await fetchStatus(restoreId);
        if (!response || !isMounted) return;

        const elapsedTime = Date.now() - startTime;
        const nextInterval = getPollingInterval(response.status, elapsedTime);

        if (nextInterval > 0 && isMounted) {
          intervalId = window.setTimeout(poll, nextInterval);
        } else {
          setIsPolling(false);
        }
      } catch (error) {
        console.error('Polling error:', error);
        setIsPolling(false);
      }
    };

    // Start polling
    setIsPolling(true);
    poll();

    // Cleanup function
    return () => {
      isMounted = false;
      if (intervalId) {
        clearTimeout(intervalId);
      }
      setIsPolling(false);
    };
  }, [restoreId, fetchStatus, status]);

  return {
    status,
    isPolling,
    error,
    confirmRestore,
    retryRestore: retryRestoreAction,
    abortRestore,
    clearError
  };
};
