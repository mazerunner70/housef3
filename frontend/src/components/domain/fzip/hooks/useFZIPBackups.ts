import { useState, useEffect, useCallback } from 'react';
import {
  FZIPBackupJob,
  FZIPBackupStatus,
  FZIPBackupType,
  InitiateFZIPBackupRequest,
  initiateFZIPBackup,
  getFZIPBackupStatus,
  listFZIPBackups,
  deleteFZIPBackup,
  downloadFZIPBackup
} from '@/services/FZIPService';

export interface UseFZIPBackupsResult {
  backups: FZIPBackupJob[];
  isLoading: boolean;
  error: string | null;
  createBackup: (request?: InitiateFZIPBackupRequest) => Promise<string>;
  refreshBackups: () => Promise<void>;
  deleteBackup: (backupId: string) => Promise<void>;
  downloadBackup: (backupId: string, filename?: string) => Promise<void>;
  getBackupStatus: (backupId: string) => Promise<FZIPBackupJob>;
  hasMore: boolean;
  loadMore: () => Promise<void>;
}

export const useFZIPBackups = (): UseFZIPBackupsResult => {
  const [backups, setBackups] = useState<FZIPBackupJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadBackups = useCallback(async (reset: boolean = false) => {
    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      const currentOffset = reset ? 0 : offset;
      const response = await listFZIPBackups(limit, currentOffset);

      // Defensive check for response structure
      if (response && response.backups && Array.isArray(response.backups)) {
        if (reset) {
          setBackups(response.backups);
          setOffset(response.backups.length);
        } else {
          setBackups(prev => [...prev, ...response.backups]);
          setOffset(prev => prev + response.backups.length);
        }

        setHasMore(response.hasMore || false);
      } else {
        // Handle malformed response
        setBackups([]);
        setOffset(0);
        setHasMore(false);
        setError('Invalid response from backup service');
      }
    } catch (err) {
      // Ensure backups is always an array even when there's an error
      setBackups([]);
      setOffset(0);
      setHasMore(false);
      setError(err instanceof Error ? err.message : 'Failed to load backups - service may not be available');
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, offset, limit]);

  const refreshBackups = useCallback(async () => {
    setOffset(0);
    await loadBackups(true);
  }, [loadBackups]);

  const loadMore = useCallback(async () => {
    if (hasMore && !isLoading) {
      await loadBackups(false);
    }
  }, [hasMore, isLoading, loadBackups]);

  const createBackup = useCallback(async (request: InitiateFZIPBackupRequest = {}): Promise<string> => {
    setError(null);

    try {
      const response = await initiateFZIPBackup(request);

      // Defensive check for response
      if (!response || !response.backupId) {
        throw new Error('Invalid response from backup service');
      }

      // Add new backup to the beginning of the list with initial status
      const newBackup: FZIPBackupJob = {
        backupId: response.backupId,
        status: response.status || FZIPBackupStatus.INITIATED,
        backupType: request.backupType || FZIPBackupType.COMPLETE,
        requestedAt: Date.now(),
        progress: 0,
        description: request.description
      };

      setBackups(prev => [newBackup, ...prev]);
      return response.backupId;
    } catch (err) {
      let errorMessage = 'Failed to create backup';
      if (err instanceof Error) {
        if (err.message.includes('404') || err.message.includes('Not Found')) {
          errorMessage = 'Backup service is not available. Please contact support.';
        } else {
          errorMessage = err.message;
        }
      }
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const deleteBackup = useCallback(async (backupId: string): Promise<void> => {
    setError(null);

    try {
      await deleteFZIPBackup(backupId);
      setBackups(prev => prev.filter(backup => backup.backupId !== backupId));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete backup';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const downloadBackup = useCallback(async (backupId: string, filename?: string): Promise<void> => {
    setError(null);

    try {
      await downloadFZIPBackup(backupId, filename);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to download backup';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  const getBackupStatus = useCallback(async (backupId: string): Promise<FZIPBackupJob> => {
    setError(null);

    try {
      const updatedBackup = await getFZIPBackupStatus(backupId);

      // Update the backup in our local state
      setBackups(prev =>
        prev.map(backup =>
          backup.backupId === backupId ? updatedBackup : backup
        )
      );

      return updatedBackup;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get backup status';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  // Load initial backups
  useEffect(() => {
    loadBackups(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    backups,
    isLoading,
    error,
    createBackup,
    refreshBackups,
    deleteBackup,
    downloadBackup,
    getBackupStatus,
    hasMore,
    loadMore
  };
};