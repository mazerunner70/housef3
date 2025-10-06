import { useState, useCallback } from 'react';

/**
 * Enhanced import state management for Stage 2
 * 
 * Features:
 * - Import workflow state tracking
 * - Progress and status management
 * - Error handling with recovery
 * - Success notifications
 * - Step-by-step workflow support
 */

export interface ImportStatus {
    isImporting: boolean;
    currentStep: number;
    totalSteps: number;
    currentFile?: {
        fileName: string;
        accountId: string;
        progress: number; // 0-100
        status: 'uploading' | 'parsing' | 'processing' | 'complete' | 'error';
    };
    recentImports: Array<{
        fileName: string;
        accountName: string;
        importedAt: number;
        transactionCount: number;
        status: 'success' | 'error' | 'partial';
    }>;
}

export interface ImportResult {
    success: boolean;
    message?: string;
    transactionCount?: number;
    fileName?: string;
    accountName?: string;
    errorDetails?: string;
}

interface UseImportStateReturn {
    // State
    currentStep: number;
    importStatus: ImportStatus;
    errorMessage: string | null;
    successAlert: ImportResult | null;

    // Actions
    setCurrentStep: (step: number) => void;
    setImportStatus: (status: Partial<ImportStatus>) => void;
    setError: (error: string | null) => void;
    setSuccess: (result: ImportResult | null) => void;
    clearError: () => void;
    clearSuccess: () => void;
    resetImportState: () => void;

    // Workflow helpers
    startImport: (fileName: string, accountId: string) => void;
    updateProgress: (progress: number, status?: 'uploading' | 'parsing' | 'processing' | 'complete' | 'error') => void;
    completeImport: (result: ImportResult) => void;
    failImport: (error: string) => void;
}

const useImportState = (): UseImportStateReturn => {
    const [currentStep, setCurrentStep] = useState<number>(1);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [successAlert, setSuccessAlert] = useState<ImportResult | null>(null);
    const [importStatus, setImportStatusState] = useState<ImportStatus>({
        isImporting: false,
        currentStep: 1,
        totalSteps: 3,
        recentImports: []
    });

    const setImportStatus = useCallback((status: Partial<ImportStatus>) => {
        setImportStatusState(prev => ({
            ...prev,
            ...status
        }));
    }, []);

    const setError = useCallback((error: string | null) => {
        setErrorMessage(error);
        if (error) {
            setSuccessAlert(null); // Clear success when error occurs
        }
    }, []);

    const setSuccess = useCallback((result: ImportResult | null) => {
        setSuccessAlert(result);
        if (result) {
            setErrorMessage(null); // Clear error when success occurs
        }
    }, []);

    const clearError = useCallback(() => {
        setErrorMessage(null);
    }, []);

    const clearSuccess = useCallback(() => {
        setSuccessAlert(null);
    }, []);

    const resetImportState = useCallback(() => {
        setCurrentStep(1);
        setErrorMessage(null);
        setSuccessAlert(null);
        setImportStatus({
            isImporting: false,
            currentStep: 1,
            totalSteps: 3,
            recentImports: importStatus.recentImports // Preserve recent imports
        });
    }, [importStatus.recentImports, setImportStatus]);

    const startImport = useCallback((fileName: string, accountId: string) => {
        setImportStatus({
            isImporting: true,
            currentStep: 1,
            currentFile: {
                fileName,
                accountId,
                progress: 0,
                status: 'uploading'
            }
        });
        setErrorMessage(null);
        setSuccessAlert(null);
    }, [setImportStatus]);

    const updateProgress = useCallback((
        progress: number,
        status: 'uploading' | 'parsing' | 'processing' | 'complete' | 'error' = 'processing'
    ) => {
        setImportStatus({
            currentFile: importStatus.currentFile ? {
                ...importStatus.currentFile,
                progress: Math.min(100, Math.max(0, progress)),
                status
            } : undefined
        });
    }, [importStatus.currentFile, setImportStatus]);

    const completeImport = useCallback((result: ImportResult) => {
        // Add to recent imports if successful
        if (result.success && importStatus.currentFile && result.accountName) {
            const newImport = {
                fileName: result.fileName || importStatus.currentFile.fileName,
                accountName: result.accountName,
                importedAt: Date.now(),
                transactionCount: result.transactionCount || 0,
                status: 'success' as const
            };

            setImportStatus({
                isImporting: false,
                currentFile: undefined,
                recentImports: [newImport, ...importStatus.recentImports.slice(0, 4)] // Keep last 5
            });
        } else {
            setImportStatus({
                isImporting: false,
                currentFile: undefined
            });
        }

        setSuccessAlert(result);
        setCurrentStep(1); // Reset to step 1
    }, [importStatus.currentFile, importStatus.recentImports, setImportStatus]);

    const failImport = useCallback((error: string) => {
        setImportStatus({
            isImporting: false,
            currentFile: undefined
        });
        setErrorMessage(error);
        setCurrentStep(1); // Reset to step 1
    }, [setImportStatus]);

    return {
        // State
        currentStep,
        importStatus,
        errorMessage,
        successAlert,

        // Actions
        setCurrentStep,
        setImportStatus,
        setError,
        setSuccess,
        clearError,
        clearSuccess,
        resetImportState,

        // Workflow helpers
        startImport,
        updateProgress,
        completeImport,
        failImport
    };
};

export default useImportState;
