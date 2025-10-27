import React, { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAccountsData from '@/components/domain/accounts/hooks/useAccountsData';
import useFileUploadLogic from '@/hooks/useFileUploadLogic';
import useUploadedFiles from '@/hooks/useUploadedFiles';
import useFieldMapping from '@/hooks/useFieldMapping';
import AccountUploadLayout from '@/components/domain/accounts/components/AccountUploadLayout';
import AccountUploadHeader from '@/components/domain/accounts/components/AccountUploadHeader';
import FileUploadStatus from '@/components/domain/accounts/components/FileUploadStatus';
import FieldMappingSection from '@/components/domain/accounts/components/FieldMappingSection';
import DragDropUploadPanel from '@/components/domain/accounts/components/DragDropUploadPanel';
import UploadedFilesList from '@/components/domain/accounts/components/UploadedFilesList';
import './AccountFileUploadView.css';

interface AccountFileUploadViewProps {
    accountId: string;
}

/**
 * AccountFileUploadView - Main orchestrating component for account file upload
 * 
 * This view component handles:
 * - Account-specific file upload workflow
 * - Integration with existing file upload infrastructure
 * - Field mapping management
 * - File list management and operations
 * - Error handling and loading states
 * 
 * Architecture:
 * - Uses composition pattern with focused business components
 * - Leverages existing services (FileService, FileMapService)
 * - Maintains existing API compatibility
 * - Enhances UX with account-specific context
 */
const AccountFileUploadView: React.FC<AccountFileUploadViewProps> = ({ accountId }) => {
    const navigate = useNavigate();

    // State management hooks
    const { accounts, isLoading: accountsLoading, error: accountsError } = useAccountsData();
    const uploadedFiles = useUploadedFiles(accountId);

    // Find the specific account
    const account = accounts.find(acc => acc.accountId === accountId);

    const fieldMapping = useFieldMapping(accountId, account);
    const fileUpload = useFileUploadLogic(accountId);

    // Handle navigation back to main import page
    const handleBackToImport = useCallback(() => {
        navigate('/import');
    }, [navigate]);

    // Handle account not found or loading states
    useEffect(() => {
        if (!accountsLoading && !account && !accountsError) {
            console.error(`Account not found: ${accountId}`);
            // Could redirect to 404 or back to import page
        }
    }, [accountsLoading, account, accountsError, accountId]);

    // Loading state
    if (accountsLoading) {
        return (
            <AccountUploadLayout>
                <div className="account-upload-loading">
                    <div className="loading-spinner"></div>
                    <p>Loading account information...</p>
                </div>
            </AccountUploadLayout>
        );
    }

    // Error state
    if (accountsError) {
        return (
            <AccountUploadLayout>
                <div className="account-upload-error">
                    <h1>Error Loading Account</h1>
                    <p>{accountsError}</p>
                    <button onClick={handleBackToImport} className="button-secondary">
                        Back to Import
                    </button>
                </div>
            </AccountUploadLayout>
        );
    }

    // Account not found
    if (!account) {
        return (
            <AccountUploadLayout>
                <div className="account-upload-not-found">
                    <h1>Account Not Found</h1>
                    <p>The account with ID "{accountId}" could not be found.</p>
                    <button onClick={handleBackToImport} className="button-secondary">
                        Back to Import
                    </button>
                </div>
            </AccountUploadLayout>
        );
    }

    // Calculate file upload status
    const fileCount = uploadedFiles.files.length;
    const totalTransactions = uploadedFiles.files.reduce((sum, file) => sum + (file.transactionCount || 0), 0);

    // Calculate date range only from files that have valid date ranges
    const filesWithDateRanges = uploadedFiles.files.filter(f => f.dateRange?.startDate && f.dateRange?.endDate);
    const dateRange = filesWithDateRanges.length > 0 ? {
        startDate: Math.min(...filesWithDateRanges.map(f => f.dateRange!.startDate)),
        endDate: Math.max(...filesWithDateRanges.map(f => f.dateRange!.endDate))
    } : null;

    return (
        <AccountUploadLayout>
            <AccountUploadHeader
                account={account}
                onBackClick={handleBackToImport}
            />

            <FileUploadStatus
                fileCount={fileCount}
                totalTransactions={totalTransactions}
                dateRange={dateRange}
                isLoading={uploadedFiles.isLoading}
            />

            <FieldMappingSection
                mapping={fieldMapping.mapping}
                hasFiles={fileCount > 0}
                isLoading={fieldMapping.isLoading}
                error={fieldMapping.error}
                onCreateMapping={() => fieldMapping.createMapping({})}
                onEditMapping={fieldMapping.editMapping}
                onDeleteMapping={fieldMapping.deleteMapping}
                onViewMapping={fieldMapping.viewMapping}
            />

            <DragDropUploadPanel
                accountId={accountId}
                onFileSelect={fileUpload.handleFileUpload}
                isUploading={fileUpload.isUploading}
                uploadProgress={fileUpload.uploadProgress}
                error={fileUpload.error}
                onClearError={fileUpload.clearError}
            />

            <UploadedFilesList
                files={uploadedFiles.files}
                isLoading={uploadedFiles.isLoading}
                error={uploadedFiles.error}
                onViewFile={fileUpload.viewFile}
                onDownloadFile={fileUpload.downloadFile}
                onDeleteFile={fileUpload.deleteFile}
                onRetryProcessing={fileUpload.retryProcessing}
            />
        </AccountUploadLayout>
    );
};

export default AccountFileUploadView;
