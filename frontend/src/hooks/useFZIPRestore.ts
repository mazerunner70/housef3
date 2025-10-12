import { useState, useEffect, useCallback } from 'react';
import {
  FZIPRestoreJob,
  FZIPRestoreStatus,
  CreateFZIPRestoreRequest,
  CreateFZIPRestoreResponse,
  getFZIPRestoreStatus,
  listFZIPRestoreJobs,
  deleteFZIPRestoreJob,
  startFZIPRestoreProcessing,
  getFZIPRestoreUploadUrl,
  cancelFZIPRestore
} from '../services/FZIPService';

export interface UseFZIPRestoreResult {
  restoreJobs: FZIPRestoreJob[];
  isLoading: boolean;
  error: string | null;
  profileError: string | null;
  profileSummary: CreateFZIPRestoreResponse['profileSummary'] | null;
  // Backward compat types remain but functions are no-ops in simplified flow
  createRestoreJob: (request?: CreateFZIPRestoreRequest) => Promise<CreateFZIPRestoreResponse>;
  uploadFile: (restoreId: string, file: File, uploadUrl: CreateFZIPRestoreResponse['uploadUrl']) => Promise<void>;
  refreshRestoreJobs: () => Promise<FZIPRestoreJob[]>;
  deleteRestoreJob: (restoreId: string) => Promise<void>;
  getRestoreStatus: (restoreId: string) => Promise<FZIPRestoreJob>;
  startRestoreProcessing: (restoreId: string) => Promise<void>;
  cancelRestore: (restoreId: string) => Promise<void>;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  clearErrors: () => void;
}

export const useFZIPRestore = (): UseFZIPRestoreResult => {
  const [restoreJobs, setRestoreJobs] = useState<FZIPRestoreJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSummary, setProfileSummary] = useState<CreateFZIPRestoreResponse['profileSummary'] | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [lastEvaluatedKey, setLastEvaluatedKey] = useState<string | undefined>(undefined);
  const limit = 20;

  const loadRestoreJobs = useCallback(async (reset: boolean = false) => {
    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const currentKey = reset ? undefined : lastEvaluatedKey;
      const response = await listFZIPRestoreJobs(limit, currentKey);

      // Defensive check for response structure
      if (response && response.restoreJobs && Array.isArray(response.restoreJobs)) {
        if (reset) {
          setRestoreJobs(response.restoreJobs);
        } else {
          setRestoreJobs(prev => [...prev, ...response.restoreJobs]);
        }

        setLastEvaluatedKey(response.nextEvaluatedKey);
        setHasMore(!!response.nextEvaluatedKey);
      } else {
        // Handle malformed response
        setRestoreJobs([]);
        setLastEvaluatedKey(undefined);
        setHasMore(false);
        setError('Invalid response from restore service');
      }
    } catch (err) {
      // Ensure restoreJobs is always an array even when there's an error
      setRestoreJobs([]);
      setLastEvaluatedKey(undefined);
      setHasMore(false);
      setError(err instanceof Error ? err.message : 'Failed to load restore jobs - service may not be available');
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, lastEvaluatedKey, limit]);

  const refreshRestoreJobs = useCallback(async (): Promise<FZIPRestoreJob[]> => {
    if (isLoading) return restoreJobs;

    setIsLoading(true);
    setError(null);
    setLastEvaluatedKey(undefined);

    try {
      const response = await listFZIPRestoreJobs(limit, undefined);

      // Defensive check for response structure
      if (response && response.restoreJobs && Array.isArray(response.restoreJobs)) {
        setRestoreJobs(response.restoreJobs);
        setLastEvaluatedKey(response.nextEvaluatedKey);
        setHasMore(!!response.nextEvaluatedKey);
        return response.restoreJobs;
      } else {
        // Handle malformed response
        setRestoreJobs([]);
        setLastEvaluatedKey(undefined);
        setHasMore(false);
        setError('Invalid response from restore service');
        return [];
      }
    } catch (err) {
      // Ensure restoreJobs is always an array even when there's an error
      setRestoreJobs([]);
      setLastEvaluatedKey(undefined);
      setHasMore(false);
      setError(err instanceof Error ? err.message : 'Failed to load restore jobs - service may not be available');
      return [];
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, restoreJobs, limit]);

  const loadMore = useCallback(async () => {
    if (hasMore && !isLoading) {
      await loadRestoreJobs(false);
    }
  }, [hasMore, isLoading, loadRestoreJobs]);

  const createRestoreJob = useCallback(async (
    _request: CreateFZIPRestoreRequest = {}
  ): Promise<CreateFZIPRestoreResponse> => {
    // New flow: directly get upload URL; backend creates job on S3 event
    setError(null);
    try {
      const { restoreId, url, fields, expiresIn } = await getFZIPRestoreUploadUrl();
      // Optimistically add job placeholder
      const placeholderJob: FZIPRestoreJob = {
        jobId: restoreId,
        status: FZIPRestoreStatus.UPLOADED,
        createdAt: Date.now(),
        progress: 0,
        currentPhase: 'awaiting_upload'
      };
      setRestoreJobs(prev => [placeholderJob, ...prev]);
      return {
        restoreId,
        status: FZIPRestoreStatus.UPLOADED,
        message: 'Upload URL generated',
        uploadUrl: { url, fields },
        suggestion: `Upload URL expires in ${expiresIn} seconds`
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get upload URL';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Not used in simplified flow; kept for compatibility if older UI calls it
  const uploadFile = useCallback(async (
    _restoreId: string,
    _file: File,
    _uploadUrl: CreateFZIPRestoreResponse['uploadUrl']
  ): Promise<void> => {
    return Promise.resolve();
  }, []);

  const deleteRestoreJob = useCallback(async (restoreId: string): Promise<void> => {
    setError(null);

    try {
      await deleteFZIPRestoreJob(restoreId);
      setRestoreJobs(prev => prev.filter(job => job.jobId !== restoreId));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete restore job';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const getRestoreStatus = useCallback(async (restoreId: string): Promise<FZIPRestoreJob> => {
    setError(null);

    try {
      const updatedJob = await getFZIPRestoreStatus(restoreId);

      // Update the restore job in our local state
      setRestoreJobs(prev =>
        prev.map(job =>
          job.jobId === restoreId ? updatedJob : job
        )
      );

      return updatedJob;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get restore status';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const startRestoreProcessing = useCallback(async (restoreId: string): Promise<void> => {
    setError(null);

    try {
      await startFZIPRestoreProcessing(restoreId);

      // Update the restore job status to processing
      setRestoreJobs(prev =>
        prev.map(job =>
          job.jobId === restoreId
            ? { ...job, status: FZIPRestoreStatus.PROCESSING, progress: 50, currentPhase: 'Starting restore...' }
            : job
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start restore processing';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const cancelRestore = useCallback(async (restoreId: string): Promise<void> => {
    setError(null);
    try {
      await cancelFZIPRestore(restoreId);
      setRestoreJobs(prev =>
        prev.map(job =>
          job.jobId === restoreId
            ? { ...job, status: FZIPRestoreStatus.CANCELED, currentPhase: 'canceled', progress: job.progress }
            : job
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to cancel restore';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const clearErrors = useCallback(() => {
    setError(null);
    setProfileError(null);
    setProfileSummary(null);
  }, []);

  // Load initial restore jobs
  useEffect(() => {
    loadRestoreJobs(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    restoreJobs,
    isLoading,
    error,
    profileError,
    profileSummary,
    createRestoreJob,
    uploadFile,
    refreshRestoreJobs,
    deleteRestoreJob,
    getRestoreStatus,
    startRestoreProcessing,
    cancelRestore,
    hasMore,
    loadMore,
    clearErrors
  };
};