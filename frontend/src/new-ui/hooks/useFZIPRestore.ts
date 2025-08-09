import { useState, useEffect, useCallback } from 'react';
import {
  FZIPRestoreJob,
  FZIPRestoreStatus,
  CreateFZIPRestoreRequest,
  CreateFZIPRestoreResponse,
  createFZIPRestoreJob,
  getFZIPRestoreStatus,
  listFZIPRestoreJobs,
  deleteFZIPRestoreJob,
  uploadFZIPPackage,
  startFZIPRestoreProcessing
} from '../../services/FZIPService';

export interface UseFZIPRestoreResult {
  restoreJobs: FZIPRestoreJob[];
  isLoading: boolean;
  error: string | null;
  profileError: string | null;
  profileSummary: CreateFZIPRestoreResponse['profileSummary'] | null;
  createRestoreJob: (request?: CreateFZIPRestoreRequest) => Promise<CreateFZIPRestoreResponse>;
  uploadFile: (restoreId: string, file: File, uploadUrl: CreateFZIPRestoreResponse['uploadUrl']) => Promise<void>;
  refreshRestoreJobs: () => Promise<void>;
  deleteRestoreJob: (restoreId: string) => Promise<void>;
  getRestoreStatus: (restoreId: string) => Promise<FZIPRestoreJob>;
  startRestoreProcessing: (restoreId: string) => Promise<void>;
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

  const refreshRestoreJobs = useCallback(async () => {
    setLastEvaluatedKey(undefined);
    await loadRestoreJobs(true);
  }, [loadRestoreJobs]);

  const loadMore = useCallback(async () => {
    if (hasMore && !isLoading) {
      await loadRestoreJobs(false);
    }
  }, [hasMore, isLoading, loadRestoreJobs]);

  const createRestoreJob = useCallback(async (
    request: CreateFZIPRestoreRequest = {}
  ): Promise<CreateFZIPRestoreResponse> => {
    setError(null);
    setProfileError(null);
    setProfileSummary(null);
    
    try {
      const response = await createFZIPRestoreJob(request);
      
      // Defensive check for response
      if (!response || !response.restoreId) {
        throw new Error('Invalid response from restore service');
      }
      
      // Check for profile not empty error
      if (response.profileSummary) {
        setProfileError('Financial profile is not empty. Restore requires an empty profile.');
        setProfileSummary(response.profileSummary);
        throw new Error('PROFILE_NOT_EMPTY');
      }
      
      // Add new restore job to the beginning of the list
      const newRestoreJob: FZIPRestoreJob = {
        jobId: response.restoreId,
        status: response.status || FZIPRestoreStatus.UPLOADED,
        createdAt: Date.now(),
        progress: 0,
        currentPhase: ''
      };
      
      setRestoreJobs(prev => [newRestoreJob, ...prev]);
      return response;
    } catch (err) {
      if (err instanceof Error && err.message === 'PROFILE_NOT_EMPTY') {
        // Don't set error for profile not empty - it's handled separately
        throw err;
      }
      
      let errorMessage = 'Failed to create restore job';
      if (err instanceof Error) {
        if (err.message.includes('404') || err.message.includes('Not Found')) {
          errorMessage = 'Restore service is not available. Please contact support.';
        } else {
          errorMessage = err.message;
        }
      }
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const uploadFile = useCallback(async (
    restoreId: string,
    file: File,
    uploadUrl: CreateFZIPRestoreResponse['uploadUrl']
  ): Promise<void> => {
    setError(null);
    
    if (!uploadUrl) {
      throw new Error('No upload URL provided');
    }
    
    try {
      await uploadFZIPPackage(restoreId, file, uploadUrl);
      
      // Update restore job status
      setRestoreJobs(prev =>
        prev.map(job =>
          job.jobId === restoreId
            ? { ...job, status: FZIPRestoreStatus.VALIDATING, progress: 10, packageSize: file.size }
            : job
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload file';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
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
    hasMore,
    loadMore,
    clearErrors
  };
};