import { useState, useEffect, useCallback } from 'react';
import { listFilesByAccount, type FileMetadata } from '@/services/FileService';

/**
 * Enhanced hook for managing uploaded files for a specific account
 * 
 * Features:
 * - Account-specific file fetching via dedicated API endpoint
 * - Real-time updates for processing status
 * - File metadata management
 * - Loading and error states
 * - Automatic refresh capabilities
 * 
 * Data Structure:
 * - Uses GET /files/account/{accountId} API endpoint
 * - Sorts by upload date (newest first)
 * - Provides rich metadata for display
 */

export interface UploadedFile extends Omit<FileMetadata, 'dateRange'> {
    // All fields from FileMetadata are available
    // Key fields for display:
    // - fileId, fileName, fileSize, uploadDate
    // - transactionCount, startDate, endDate
    // - processingStatus, errorMessage
    // - accountId, accountName

    // Override dateRange to use our preferred camelCase format
    dateRange?: {
        startDate: number;
        endDate: number;
    };

    // Ensure these are always available (mapped from API response)
    startDate: number;
    endDate: number;
}

interface UseUploadedFilesReturn {
    files: UploadedFile[];
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
    fileCount: number;
    totalTransactions: number;
    lastUpdated: number | null;
}

const useUploadedFiles = (accountId: string): UseUploadedFilesReturn => {
    const [files, setFiles] = useState<UploadedFile[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdated, setLastUpdated] = useState<number | null>(null);

    const fetchFiles = useCallback(async () => {
        try {
            setIsLoading(true);
            setError(null);

            const response = await listFilesByAccount(accountId);

            // Transform to UploadedFile format (no filtering needed since API is account-specific)
            const accountFiles: UploadedFile[] = response.files
                .map(file => ({
                    ...file,
                    // Map the API's dateRange.start_date/end_date to our expected format
                    startDate: file.dateRange?.start_date || file.startDate || 0,
                    endDate: file.dateRange?.end_date || file.endDate || 0,
                    dateRange: (file.dateRange?.start_date && file.dateRange?.end_date) ? {
                        startDate: file.dateRange.start_date,
                        endDate: file.dateRange.end_date
                    } : undefined
                }))
                .sort((a, b) => {
                    // Sort by upload date (newest first)
                    const aDate = new Date(a.uploadDate).getTime();
                    const bDate = new Date(b.uploadDate).getTime();
                    return bDate - aDate;
                });

            setFiles(accountFiles);
            setLastUpdated(Date.now());

        } catch (fetchError: any) {
            console.error('Error fetching uploaded files for account:', accountId, fetchError);
            setError(fetchError.message || 'Failed to load uploaded files');
        } finally {
            setIsLoading(false);
        }
    }, [accountId]);

    // Initial fetch
    useEffect(() => {
        fetchFiles();
    }, [fetchFiles]);

    // Auto-refresh for files that are still processing
    useEffect(() => {
        const processingFiles = files.filter(file =>
            file.processingStatus === 'PENDING' || file.processingStatus === 'PROCESSING'
        );

        if (processingFiles.length === 0) {
            return; // No files processing, no need to poll
        }

        const pollInterval = setInterval(() => {
            console.log(`Polling for ${processingFiles.length} processing files...`);
            fetchFiles();
        }, 3000); // Poll every 3 seconds

        return () => clearInterval(pollInterval);
    }, [files, fetchFiles]);

    const refetch = useCallback(async () => {
        await fetchFiles();
    }, [fetchFiles]);

    // Calculate derived values
    const fileCount = files.length;
    const totalTransactions = files.reduce((sum, file) => sum + (file.transactionCount || 0), 0);

    return {
        files,
        isLoading,
        error,
        refetch,
        fileCount,
        totalTransactions,
        lastUpdated
    };
};

export default useUploadedFiles;
