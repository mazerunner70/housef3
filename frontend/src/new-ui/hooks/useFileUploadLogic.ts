import { useState, useCallback } from 'react';
import { getCurrentUser } from '@/services/AuthService';
import {
    getUploadUrl,
    uploadFileToS3,
    waitForFileProcessing,
    deleteFile,
    getDownloadUrl,
    parseFileWithPolling,
    type FileMetadata
} from '@/services/FileService';

/**
 * Enhanced file upload logic hook for Stage 2
 * 
 * Features:
 * - Account-specific file upload workflow
 * - Progress tracking and status updates
 * - Error handling with retry capabilities
 * - File operations (view, download, delete)
 * - Integration with existing FileService APIs
 * 
 * Workflow:
 * 1. File validation (handled by DragDropUploadPanel)
 * 2. Get presigned upload URL
 * 3. Upload to S3 with progress tracking
 * 4. Wait for backend processing
 * 5. Update UI with results
 */

interface UseFileUploadLogicReturn {
    // Upload state
    isUploading: boolean;
    uploadProgress: number;
    error: string | null;

    // Upload actions
    handleFileUpload: (file: File) => Promise<void>;
    clearError: () => void;

    // File operations
    viewFile: (fileId: string) => Promise<void>;
    downloadFile: (fileId: string) => Promise<void>;
    deleteFile: (fileId: string) => Promise<string | null>;
    retryProcessing: (fileId: string) => Promise<void>;
}

const useFileUploadLogic = (accountId: string): UseFileUploadLogicReturn => {
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);

    const clearError = useCallback(() => {
        setError(null);
    }, []);

    const handleFileUpload = useCallback(async (file: File) => {
        const currentUser = getCurrentUser();
        if (!currentUser) {
            setError('User not authenticated');
            return;
        }

        setIsUploading(true);
        setUploadProgress(0);
        setError(null);

        try {
            // Step 1: Get presigned upload URL (10% progress)
            setUploadProgress(10);
            const uploadData = await getUploadUrl(
                file.name,
                file.type || 'application/octet-stream',
                file.size,
                currentUser.id,
                accountId
            );

            // Step 2: Upload to S3 (10% -> 70% progress)
            setUploadProgress(20);
            await uploadFileToS3(uploadData, file, accountId);
            setUploadProgress(70);

            // Step 3: Wait for backend processing (70% -> 90% progress)
            setUploadProgress(75);
            const metadata = await waitForFileProcessing(
                uploadData.fileId,
                30000, // 30 second timeout
                1000   // 1 second polling interval
            );

            // Step 4: Complete (90% -> 100% progress)
            setUploadProgress(90);

            if (metadata.processingStatus === 'ERROR') {
                throw new Error(metadata.errorMessage || 'File processing failed');
            }

            setUploadProgress(100);

            // Brief delay to show completion
            setTimeout(() => {
                setIsUploading(false);
                setUploadProgress(0);
            }, 1000);

        } catch (uploadError: any) {
            console.error('File upload failed:', uploadError);
            setError(uploadError.message || 'File upload failed');
            setIsUploading(false);
            setUploadProgress(0);
        }
    }, [accountId]);

    const viewFile = useCallback(async (fileId: string) => {
        try {
            setError(null);

            // Parse file to get preview data
            const parseResult = await parseFileWithPolling(fileId);

            if (parseResult.error) {
                setError(`Cannot preview file: ${parseResult.error}`);
                return;
            }

            // For now, just log the data - in a full implementation,
            // this would open a modal or navigate to a preview page
            console.log('File preview data:', parseResult);

            // TODO: Implement file preview modal or navigation
            alert(`File preview not yet implemented. File contains ${parseResult.data?.length || 0} rows.`);

        } catch (viewError: any) {
            console.error('Error viewing file:', viewError);
            setError(viewError.message || 'Failed to view file');
        }
    }, []);

    const downloadFile = useCallback(async (fileId: string) => {
        try {
            setError(null);

            // Get download URL
            const downloadData = await getDownloadUrl(fileId);

            // Create temporary link and trigger download
            const link = document.createElement('a');
            link.href = downloadData.downloadUrl;
            link.download = downloadData.fileName;
            link.style.display = 'none';

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

        } catch (downloadError: any) {
            console.error('Error downloading file:', downloadError);
            setError(downloadError.message || 'Failed to download file');
        }
    }, []);

    const deleteFileHandler = useCallback(async (fileId: string): Promise<string | null> => {
        try {
            setError(null);

            // Confirm deletion
            const confirmed = window.confirm('Are you sure you want to delete this file? This action cannot be undone.');
            if (!confirmed) {
                return null;
            }

            const result = await deleteFile(fileId);

            // Return operation ID for tracking
            return result.operationId;

        } catch (deleteError: any) {
            console.error('Error deleting file:', deleteError);
            setError(deleteError.message || 'Failed to delete file');
            return null;
        }
    }, []);

    const retryProcessing = useCallback(async (fileId: string) => {
        try {
            setError(null);
            setIsUploading(true);
            setUploadProgress(0);

            // Wait for processing again
            setUploadProgress(20);
            const metadata = await waitForFileProcessing(
                fileId,
                30000, // 30 second timeout
                1000   // 1 second polling interval
            );

            setUploadProgress(90);

            if (metadata.processingStatus === 'ERROR') {
                throw new Error(metadata.errorMessage || 'File processing failed again');
            }

            setUploadProgress(100);

            // Brief delay to show completion
            setTimeout(() => {
                setIsUploading(false);
                setUploadProgress(0);
            }, 1000);

        } catch (retryError: any) {
            console.error('Error retrying file processing:', retryError);
            setError(retryError.message || 'Failed to retry file processing');
            setIsUploading(false);
            setUploadProgress(0);
        }
    }, []);

    return {
        // Upload state
        isUploading,
        uploadProgress,
        error,

        // Upload actions
        handleFileUpload,
        clearError,

        // File operations
        viewFile,
        downloadFile,
        deleteFile: deleteFileHandler,
        retryProcessing
    };
};

export default useFileUploadLogic;
