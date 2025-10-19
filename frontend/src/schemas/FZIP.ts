// Zod schemas for FZIP types
// These schemas provide runtime validation for FZIP-related data

import { z } from 'zod';

// FZIP Backup Enums
export const FZIPBackupStatusSchema = z.enum([
    "backup_initiated",
    "backup_processing",
    "backup_completed",
    "backup_failed"
]);

export const FZIPBackupTypeSchema = z.enum([
    "complete",
    "accounts_only",
    "transactions_only",
    "categories_only"
]);

// FZIP Restore Enums
export const FZIPRestoreStatusSchema = z.enum([
    "restore_uploaded",
    "restore_validating",
    "restore_validation_passed",
    "restore_validation_failed",
    "restore_awaiting_confirmation",
    "restore_processing",
    "restore_completed",
    "restore_failed",
    "restore_canceled"
]);

// Validation Schema
export const FZIPValidationSchema = z.object({
    overall_quality: z.string(),
    data_integrity_score: z.number(),
    completeness_score: z.number(),
    files_processed: z.number(),
    files_failed: z.number(),
    compression_ratio: z.number(),
    processing_time_seconds: z.number(),
    issues: z.array(z.string()),
    recommendations: z.array(z.string()),
});

// FZIP Backup Job Schema
export const FZIPBackupJobSchema = z.object({
    backupId: z.string(),
    status: FZIPBackupStatusSchema,
    backupType: FZIPBackupTypeSchema,
    requestedAt: z.number(),
    completedAt: z.number().nullish(),
    progress: z.number(),
    downloadUrl: z.string().nullish(),
    expiresAt: z.number().nullish(),
    packageSize: z.number().nullish(),
    description: z.string().nullish(),
    validation: FZIPValidationSchema.nullish(),
    manifest_checksums: z.record(z.string(), z.string()).nullish(),
    error: z.string().nullish(),
});

// FZIP Restore Summary Schemas
export const FZIPRestoreAccountItemSchema = z.object({
    name: z.string(),
    type: z.string(),
});

export const FZIPRestoreCategoryItemSchema = z.object({
    name: z.string(),
    level: z.number(),
    children: z.number(),
});

export const FZIPRestoreDateRangeSchema = z.object({
    earliest: z.string(),
    latest: z.string(),
});

export const FZIPRestoreSummarySchema = z.object({
    accounts: z.object({
        count: z.number(),
        items: z.array(FZIPRestoreAccountItemSchema),
    }),
    categories: z.object({
        count: z.number(),
        hierarchyDepth: z.number(),
        items: z.array(FZIPRestoreCategoryItemSchema),
    }),
    file_maps: z.object({
        count: z.number(),
        totalSize: z.string(),
    }),
    transaction_files: z.object({
        count: z.number(),
        totalSize: z.string(),
        fileTypes: z.array(z.string()),
    }),
    transactions: z.object({
        count: z.number(),
        dateRange: FZIPRestoreDateRangeSchema.optional(),
    }),
});

// FZIP Restore Results Schema
export const FZIPRestoreResultsSchema = z.object({
    accounts: z.object({
        created: z.number(),
        errors: z.array(z.string()),
    }),
    categories: z.object({
        created: z.number(),
        errors: z.array(z.string()),
    }),
    file_maps: z.object({
        created: z.number(),
        errors: z.array(z.string()),
    }),
    transaction_files: z.object({
        created: z.number(),
        errors: z.array(z.string()),
    }),
    transactions: z.object({
        created: z.number(),
        errors: z.array(z.string()),
    }),
    total_processing_time: z.string().optional(),
    warnings: z.array(z.string()).optional(),
});

// FZIP Restore Validation Results Schema
export const FZIPRestoreValidationResultsSchema = z.object({
    profileEmpty: z.boolean(),
    schemaValid: z.boolean(),
    businessValid: z.boolean().optional(),
    ready: z.boolean(),
});

// FZIP Restore Job Schema
export const FZIPRestoreJobSchema = z.object({
    jobId: z.string(),
    status: FZIPRestoreStatusSchema,
    createdAt: z.number(),
    completedAt: z.number().nullish(),
    progress: z.number(),
    currentPhase: z.string(),
    packageSize: z.number().nullish(),
    updatedAt: z.number().nullish(),
    summary: FZIPRestoreSummarySchema.nullish(),
    validationResults: FZIPRestoreValidationResultsSchema.nullish(),
    restoreResults: FZIPRestoreResultsSchema.nullish(),
    error: z.string().nullish(),
});

// API Request Schemas
export const InitiateFZIPBackupRequestSchema = z.object({
    includeAnalytics: z.boolean().optional(),
    backupType: FZIPBackupTypeSchema.optional(),
    description: z.string().optional(),
});

export const CreateFZIPRestoreRequestSchema = z.object({
    validateOnly: z.boolean().optional(),
});

// API Response Schemas
export const InitiateFZIPBackupResponseSchema = z.object({
    backupId: z.string(),
    status: FZIPBackupStatusSchema,
    estimatedCompletion: z.string().nullish(),
});

export const FZIPBackupListResponseSchema = z.object({
    backups: z.array(FZIPBackupJobSchema),
    total: z.number(),
    limit: z.number(),
    offset: z.number(),
    hasMore: z.boolean(),
    packageFormat: z.string().optional(),
});

export const CreateFZIPRestoreResponseSchema = z.object({
    restoreId: z.string(),
    status: FZIPRestoreStatusSchema,
    message: z.string(),
    uploadUrl: z.object({
        url: z.string(),
        fields: z.record(z.string(), z.string()),
    }).nullish(),
    profileSummary: z.object({
        accounts_count: z.number(),
        transactions_count: z.number(),
        categories_count: z.number(),
        file_maps_count: z.number(),
        transaction_files_count: z.number(),
    }).nullish(),
    suggestion: z.string().nullish(),
});

export const FZIPRestoreListResponseSchema = z.object({
    restoreJobs: z.array(FZIPRestoreJobSchema),
    nextEvaluatedKey: z.string().optional(),
    packageFormat: z.string().optional(),
});

export const FZIPRestoreUploadUrlResponseSchema = z.object({
    restoreId: z.string(),
    url: z.string(),
    fields: z.record(z.string(), z.string()),
    expiresIn: z.number(),
});

// Backend Response Mapping Schemas (for convertBackupResponseToFrontend)
export const BackendFZIPBackupResponseSchema = z.object({
    jobId: z.string(),
    status: z.string(),
    backupType: z.string().optional(),
    jobType: z.string().optional(),
    createdAt: z.union([z.string(), z.number()]),
    completedAt: z.union([z.string(), z.number()]).optional(),
    progress: z.number().optional(),
    downloadUrl: z.string().optional(),
    expiresAt: z.union([z.string(), z.number()]).optional(),
    packageSize: z.number().optional(),
    description: z.string().optional(),
    error: z.string().optional(),
});

// Type inference from schemas
export type FZIPBackupStatus = z.infer<typeof FZIPBackupStatusSchema>;
export type FZIPBackupType = z.infer<typeof FZIPBackupTypeSchema>;
export type FZIPRestoreStatus = z.infer<typeof FZIPRestoreStatusSchema>;
export type FZIPBackupJob = z.infer<typeof FZIPBackupJobSchema>;
export type FZIPRestoreSummary = z.infer<typeof FZIPRestoreSummarySchema>;
export type FZIPRestoreResults = z.infer<typeof FZIPRestoreResultsSchema>;
export type FZIPRestoreJob = z.infer<typeof FZIPRestoreJobSchema>;
export type InitiateFZIPBackupRequest = z.infer<typeof InitiateFZIPBackupRequestSchema>;
export type InitiateFZIPBackupResponse = z.infer<typeof InitiateFZIPBackupResponseSchema>;
export type FZIPBackupListResponse = z.infer<typeof FZIPBackupListResponseSchema>;
export type CreateFZIPRestoreRequest = z.infer<typeof CreateFZIPRestoreRequestSchema>;
export type CreateFZIPRestoreResponse = z.infer<typeof CreateFZIPRestoreResponseSchema>;
export type FZIPRestoreListResponse = z.infer<typeof FZIPRestoreListResponseSchema>;
export type FZIPRestoreUploadUrlResponse = z.infer<typeof FZIPRestoreUploadUrlResponseSchema>;

// Export enum values for backward compatibility
export const FZIPBackupStatus = {
    INITIATED: "backup_initiated" as const,
    COLLECTING_DATA: "backup_processing" as const,
    BUILDING_FZIP_PACKAGE: "backup_processing" as const,
    UPLOADING: "backup_processing" as const,
    COMPLETED: "backup_completed" as const,
    FAILED: "backup_failed" as const,
} as const;

export const FZIPBackupType = {
    COMPLETE: "complete" as const,
    ACCOUNTS_ONLY: "accounts_only" as const,
    TRANSACTIONS_ONLY: "transactions_only" as const,
    CATEGORIES_ONLY: "categories_only" as const,
} as const;

export const FZIPRestoreStatus = {
    UPLOADED: "restore_uploaded" as const,
    VALIDATING: "restore_validating" as const,
    VALIDATION_PASSED: "restore_validation_passed" as const,
    VALIDATION_FAILED: "restore_validation_failed" as const,
    AWAITING_CONFIRMATION: "restore_awaiting_confirmation" as const,
    PROCESSING: "restore_processing" as const,
    COMPLETED: "restore_completed" as const,
    FAILED: "restore_failed" as const,
    CANCELED: "restore_canceled" as const,
} as const;
