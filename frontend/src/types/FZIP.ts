// FZIP (File ZIP) Type Definitions
// These interfaces define the data models for FZIP backup and restore operations

// FZIP Backup Types
export enum FZIPBackupStatus {
    INITIATED = "backup_initiated",
    COLLECTING_DATA = "backup_processing",
    BUILDING_FZIP_PACKAGE = "backup_processing",
    UPLOADING = "backup_processing",
    COMPLETED = "backup_completed",
    FAILED = "backup_failed"
}

export enum FZIPBackupType {
    COMPLETE = "complete",
    ACCOUNTS_ONLY = "accounts_only",
    TRANSACTIONS_ONLY = "transactions_only",
    CATEGORIES_ONLY = "categories_only"
}

export interface FZIPBackupJob {
    backupId: string;
    status: FZIPBackupStatus;
    backupType: FZIPBackupType;
    requestedAt: number;
    completedAt?: number;
    progress: number;
    downloadUrl?: string;
    expiresAt?: number;
    packageSize?: number;
    description?: string;
    validation?: {
        overall_quality: string;
        data_integrity_score: number;
        completeness_score: number;
        files_processed: number;
        files_failed: number;
        compression_ratio: number;
        processing_time_seconds: number;
        issues: string[];
        recommendations: string[];
    };
    manifest_checksums?: Record<string, string>;
    error?: string;
}

// FZIP Restore Types
export enum FZIPRestoreStatus {
    // Mirror backend FZIPStatus values exactly
    UPLOADED = "restore_uploaded",
    VALIDATING = "restore_validating",
    VALIDATION_PASSED = "restore_validation_passed",
    VALIDATION_FAILED = "restore_validation_failed",
    AWAITING_CONFIRMATION = "restore_awaiting_confirmation",
    PROCESSING = "restore_processing",
    COMPLETED = "restore_completed",
    FAILED = "restore_failed",
    CANCELED = "restore_canceled"
}

export interface FZIPRestoreSummary {
    accounts: {
        count: number;
        items: Array<{
            name: string;
            type: string;
        }>;
    };
    categories: {
        count: number;
        hierarchyDepth: number;
        items: Array<{
            name: string;
            level: number;
            children: number;
        }>;
    };
    file_maps: {
        count: number;
        totalSize: string;
    };
    transaction_files: {
        count: number;
        totalSize: string;
        fileTypes: string[];
    };
    transactions: {
        count: number;
        dateRange?: {
            earliest: string;
            latest: string;
        };
    };
}

export interface FZIPRestoreResults {
    accounts: { created: number; errors: string[] };
    categories: { created: number; errors: string[] };
    file_maps: { created: number; errors: string[] };
    transaction_files: { created: number; errors: string[] };
    transactions: { created: number; errors: string[] };
}

export interface FZIPRestoreJob {
    restoreId: string;
    status: FZIPRestoreStatus;
    uploadedAt: number;
    validatedAt?: number;
    processedAt?: number;
    completedAt?: number;
    progress: number;
    fileName: string;
    fileSize: number;
    validation?: {
        isValid: boolean;
        errors: string[];
        warnings: string[];
        summary?: FZIPRestoreSummary;
    };
    results?: FZIPRestoreResults;
    error?: string;
}

// FZIP Operation Request/Response Types (Service-specific)
export interface InitiateFZIPBackupRequest {
    includeAnalytics?: boolean;
    backupType?: FZIPBackupType;
    description?: string;
}

export interface InitiateFZIPBackupResponse {
    backupId: string;
    status: FZIPBackupStatus;
    estimatedSize?: string;
    estimatedCompletion?: string;
}

export interface CreateFZIPRestoreRequest {
    validateOnly?: boolean;
}

export interface CreateFZIPRestoreResponse {
    restoreId: string;
    status: FZIPRestoreStatus;
    message: string;
    uploadUrl?: {
        url: string;
        fields: Record<string, string>;
    };
    profileSummary?: {
        accounts_count: number;
        transactions_count: number;
        categories_count: number;
        file_maps_count: number;
        transaction_files_count: number;
    };
    suggestion?: string;
}

export interface FZIPRestoreUploadUrlResponse {
    restoreId: string;
    url: string;
    fields: Record<string, string>;
    expiresIn: number;
}

export interface FZIPRestoreConfirmRequest {
    restoreId: string;
    confirmed: boolean;
}

export interface FZIPRestoreConfirmResponse {
    success: boolean;
    message: string;
    error?: string;
}

// FZIP List/Status Response Types
export interface FZIPBackupListResponse {
    backups: FZIPBackupJob[];  // API uses "backups" not "exports"
    total: number;
    limit: number;
    offset: number;
    hasMore: boolean;
    packageFormat?: string;
}

export interface FZIPRestoreListResponse {
    restoreJobs: FZIPRestoreJob[];  // API returns "restoreJobs"
    nextEvaluatedKey?: string;
    packageFormat?: string;
}

export interface FZIPJobStatusResponse {
    success: boolean;
    job: FZIPBackupJob | FZIPRestoreJob;
    message?: string;
    error?: string;
}

// FZIP Validation Types
export interface FZIPValidationError {
    type: 'error' | 'warning';
    message: string;
    details?: any;
}

export interface FZIPValidationResult {
    isValid: boolean;
    errors: FZIPValidationError[];
    warnings: FZIPValidationError[];
    summary?: FZIPRestoreSummary;
}

// FZIP Progress Types
export interface FZIPProgressUpdate {
    jobId: string;
    jobType: 'backup' | 'restore';
    status: FZIPBackupStatus | FZIPRestoreStatus;
    progress: number;
    message?: string;
    error?: string;
}

// FZIP File Upload Types
export interface FZIPFileUpload {
    file: File;
    onProgress?: (progress: number) => void;
    onComplete?: (restoreId: string) => void;
    onError?: (error: string) => void;
}

// Utility Types
export type FZIPJobType = 'backup' | 'restore';
export type FZIPJobStatus = FZIPBackupStatus | FZIPRestoreStatus;

// Form State Types
export interface FZIPBackupFormState {
    backupType: FZIPBackupType;
    description: string;
    includeFiles: boolean;
    isSubmitting: boolean;
    errors: Record<string, string>;
}

export interface FZIPRestoreFormState {
    selectedFile: File | null;
    isUploading: boolean;
    uploadProgress: number;
    errors: Record<string, string>;
}

// Error Types
export interface FZIPError {
    code: string;
    message: string;
    details?: any;
}

export interface FZIPApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: FZIPError;
    message?: string;
}
