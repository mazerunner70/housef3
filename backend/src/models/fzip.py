"""
Unified FZIP (Financial ZIP) models for the backup/restore system.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# ENUMS
# ============================================================================

class FZIPStatus(str, Enum):
    """Status of FZIP operations"""
    # Backup statuses
    BACKUP_INITIATED = "backup_initiated"
    BACKUP_PROCESSING = "backup_processing"
    BACKUP_COMPLETED = "backup_completed"
    BACKUP_FAILED = "backup_failed"
    BACKUP_EXPIRED = "backup_expired"
    
    # Restore statuses
    RESTORE_UPLOADED = "restore_uploaded"
    RESTORE_VALIDATING = "restore_validating"
    RESTORE_VALIDATION_PASSED = "restore_validation_passed"
    RESTORE_VALIDATION_FAILED = "restore_validation_failed"
    RESTORE_AWAITING_CONFIRMATION = "restore_awaiting_confirmation"
    RESTORE_PROCESSING = "restore_processing"
    RESTORE_COMPLETED = "restore_completed"
    RESTORE_FAILED = "restore_failed"
    RESTORE_CANCELED = "restore_canceled"


class FZIPType(str, Enum):
    """Type of FZIP operation"""
    BACKUP = "backup"
    RESTORE = "restore"


class FZIPBackupType(str, Enum):
    """Type of FZIP backup"""
    COMPLETE = "complete"
    SELECTIVE = "selective"
    ACCOUNTS_ONLY = "accounts_only"
    TRANSACTIONS_ONLY = "transactions_only"


class FZIPFormat(str, Enum):
    """FZIP package format"""
    FZIP = "fzip"
    JSON = "json"





# ============================================================================
# CORE MODELS
# ============================================================================

class FZIPJob(BaseModel):
    """Unified model for FZIP backup and restore jobs"""
    # Core identifiers
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="jobId")
    user_id: str = Field(alias="userId")
    job_type: FZIPType = Field(alias="jobType")
    status: FZIPStatus = Field(alias="status")
    
    # Timestamps
    created_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000),
        alias="createdAt"
    )
    completed_at: Optional[int] = Field(default=None, alias="completedAt")
    expires_at: Optional[int] = Field(default=None, alias="expiresAt")
    
    # Backup-specific fields
    backup_type: Optional[FZIPBackupType] = Field(default=None, alias="backupType")
    include_analytics: bool = Field(default=False, alias="includeAnalytics")
    description: Optional[str] = None
    
    # Restore-specific fields (empty profile restore only)
    backup_id: Optional[str] = Field(default=None, alias="backupId")
    
    # Package information
    package_format: FZIPFormat = Field(default=FZIPFormat.FZIP, alias="packageFormat")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    s3_key: Optional[str] = Field(default=None, alias="s3Key")
    download_url: Optional[str] = Field(default=None, alias="downloadUrl")
    
    # Progress tracking
    progress: int = Field(default=0, ge=0, le=100)
    current_phase: Optional[str] = Field(default=None, alias="currentPhase")
    
    # Error handling
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = Field(default=None, alias="errorDetails")
    
    # Results
    validation_results: Dict[str, Any] = Field(default_factory=dict, alias="validationResults")
    restore_results: Dict[str, Any] = Field(default_factory=dict, alias="restoreResults")
    
    # Configuration
    parameters: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str,
            Decimal: str
        },
        use_enum_values=True
    )

    @field_validator('created_at', 'completed_at', 'expires_at')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        item = self.model_dump(mode='python', by_alias=True, exclude_none=True)
        
        # Convert UUID to string
        if 'jobId' in item:
            item['jobId'] = str(item['jobId'])
            
        # Convert enum values to strings
        for field in ['status', 'jobType', 'backupType', 'mergeStrategy', 'packageFormat']:
            if field in item and item[field] is not None:
                item[field] = item[field].value if hasattr(item[field], 'value') else str(item[field])
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'FZIPJob':
        """Create FZIPJob from DynamoDB item"""
        # Make a copy to avoid modifying the original
        converted_item = item.copy()
        
        # Convert Decimal values to int for numeric fields
        int_fields = ['createdAt', 'completedAt', 'expiresAt', 'packageSize', 'progress']
        for field in int_fields:
            if field in converted_item and converted_item[field] is not None:
                if isinstance(converted_item[field], Decimal):
                    converted_item[field] = int(converted_item[field])
        
        # Convert string UUIDs back to UUID objects
        if 'jobId' in converted_item:
            converted_item['jobId'] = uuid.UUID(converted_item['jobId'])
            
        # Convert string enums back to enum objects
        if 'status' in converted_item:
            converted_item['status'] = FZIPStatus(converted_item['status'])
        if 'jobType' in converted_item:
            converted_item['jobType'] = FZIPType(converted_item['jobType'])
        if 'backupType' in converted_item and converted_item['backupType']:
            converted_item['backupType'] = FZIPBackupType(converted_item['backupType'])
        if 'packageFormat' in converted_item:
            converted_item['packageFormat'] = FZIPFormat(converted_item['packageFormat'])
        
        # Ensure default dicts for nested result fields (model_construct bypasses defaults)
        if 'validationResults' not in converted_item or converted_item.get('validationResults') is None:
            converted_item['validationResults'] = {}
        if 'restoreResults' not in converted_item or converted_item.get('restoreResults') is None:
            converted_item['restoreResults'] = {}
            
        # Use model_construct to bypass validation that would convert enums back to strings
        # This preserves our enum objects instead of converting them to string values
        return cls.model_construct(**converted_item)

    def is_backup(self) -> bool:
        """Check if this is a backup job"""
        return self.job_type == FZIPType.BACKUP

    def is_restore(self) -> bool:
        """Check if this is a restore job"""
        return self.job_type == FZIPType.RESTORE

    def is_completed(self) -> bool:
        """Check if the job is completed"""
        return self.status in [FZIPStatus.BACKUP_COMPLETED, FZIPStatus.RESTORE_COMPLETED]

    def is_failed(self) -> bool:
        """Check if the job failed"""
        return self.status in [FZIPStatus.BACKUP_FAILED, FZIPStatus.RESTORE_FAILED, 
                              FZIPStatus.RESTORE_VALIDATION_FAILED]


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class FZIPBackupRequest(BaseModel):
    """Request model for creating a new FZIP backup"""
    include_analytics: bool = Field(default=False, alias="includeAnalytics")
    backup_type: FZIPBackupType = Field(default=FZIPBackupType.COMPLETE, alias="backupType")
    description: Optional[str] = None
    
    # Selective backup parameters
    account_ids: Optional[List[uuid.UUID]] = Field(default=None, alias="accountIds")
    date_range_start: Optional[int] = Field(default=None, alias="dateRangeStart")
    date_range_end: Optional[int] = Field(default=None, alias="dateRangeEnd")
    category_ids: Optional[List[uuid.UUID]] = Field(default=None, alias="categoryIds")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    )


class FZIPRestoreRequest(BaseModel):
    """Request model for creating a new FZIP restore (empty profile only)"""
    validate_only: bool = Field(default=False, alias="validateOnly")
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )


class FZIPResponse(BaseModel):
    """Unified response model for FZIP operations"""
    job_id: uuid.UUID = Field(alias="jobId")
    job_type: FZIPType = Field(alias="jobType")
    status: FZIPStatus
    package_format: FZIPFormat = Field(default=FZIPFormat.FZIP, alias="packageFormat")
    message: Optional[str] = None
    
    # Backup-specific fields
    estimated_completion: Optional[str] = Field(default=None, alias="estimatedCompletion")
    
    # Restore-specific fields
    upload_url: Optional[Dict[str, Any]] = Field(default=None, alias="uploadUrl")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    )


class FZIPStatusResponse(BaseModel):
    """Unified response model for FZIP status checks"""
    job_id: uuid.UUID = Field(alias="jobId")
    job_type: FZIPType = Field(alias="jobType")
    status: FZIPStatus
    progress: int = Field(ge=0, le=100)
    current_phase: Optional[str] = Field(default=None, alias="currentPhase")
    package_format: FZIPFormat = Field(default=FZIPFormat.FZIP, alias="packageFormat")
    
    # Timestamps
    created_at: int = Field(alias="createdAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    expires_at: Optional[str] = Field(default=None, alias="expiresAt")
    
    # Backup-specific fields
    download_url: Optional[str] = Field(default=None, alias="downloadUrl")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    
    # Restore-specific fields
    validation_results: Dict[str, Any] = Field(default_factory=dict, alias="validationResults")
    restore_results: Dict[str, Any] = Field(default_factory=dict, alias="restoreResults")
    
    # Error handling
    error: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    )


# ============================================================================
# DATA MODELS
# ============================================================================

class FZIPDataSummary(BaseModel):
    """Summary of data included in FZIP backup"""
    accounts_count: int = Field(alias="accountsCount")
    transactions_count: int = Field(alias="transactionsCount")
    categories_count: int = Field(alias="categoriesCount")
    file_maps_count: int = Field(alias="fileMapsCount")
    transaction_files_count: int = Field(alias="transactionFilesCount")
    analytics_included: bool = Field(alias="analyticsIncluded")
    
    model_config = ConfigDict(
        populate_by_name=True
    )


class FZIPCompatibilityInfo(BaseModel):
    """Compatibility information for FZIP restore"""
    minimum_version: str = Field(alias="minimumVersion")
    supported_versions: List[str] = Field(alias="supportedVersions")
    
    model_config = ConfigDict(
        populate_by_name=True
    )


class FZIPManifest(BaseModel):
    """Manifest for FZIP package validation and metadata"""
    backup_format_version: str = Field(alias="backupFormatVersion")
    backup_timestamp: str = Field(alias="backupTimestamp")
    user_id: str = Field(alias="userId")
    housef3_version: str = Field(alias="housef3Version")
    package_format: FZIPFormat = Field(default=FZIPFormat.FZIP, alias="packageFormat")
    
    data_summary: FZIPDataSummary = Field(alias="dataSummary")
    checksums: Dict[str, str] = Field(default_factory=dict)
    compatibility: FZIPCompatibilityInfo
    
    # Backup metadata
    job_id: uuid.UUID = Field(alias="jobId")
    backup_type: FZIPBackupType = Field(alias="backupType")
    include_analytics: bool = Field(alias="includeAnalytics")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    )


# ============================================================================
# VALIDATION MODELS
# ============================================================================

class FZIPValidationSummary(BaseModel):
    """Summary of validation results"""
    valid: int
    warnings: int
    errors: int
    details: List[str] = Field(default_factory=list)


class FZIPRestoreSummary(BaseModel):
    """Summary of restore results"""
    accounts_created: int = Field(alias="accountsCreated")
    accounts_updated: int = Field(alias="accountsUpdated")
    transactions_created: int = Field(alias="transactionsCreated")
    transactions_updated: int = Field(alias="transactionsUpdated")
    categories_created: int = Field(alias="categoriesCreated")
    categories_updated: int = Field(alias="categoriesUpdated")
    files_restored: int = Field(alias="filesRestored")
    file_maps_created: int = Field(alias="fileMapsCreated")
    file_maps_updated: int = Field(alias="fileMapsUpdated")
    
    model_config = ConfigDict(
        populate_by_name=True
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_backup_job(user_id: str, backup_request: FZIPBackupRequest) -> FZIPJob:
    """Create a new FZIP backup job"""
    return FZIPJob(
        userId=user_id,
        jobType=FZIPType.BACKUP,
        status=FZIPStatus.BACKUP_INITIATED,
        backupType=backup_request.backup_type,
        includeAnalytics=backup_request.include_analytics,
        description=backup_request.description,
        parameters={
            'accountIds': backup_request.account_ids,
            'dateRangeStart': backup_request.date_range_start,
            'dateRangeEnd': backup_request.date_range_end,
            'categoryIds': backup_request.category_ids
        } if any([backup_request.account_ids, backup_request.date_range_start, 
                   backup_request.date_range_end, backup_request.category_ids]) else None
    )


def create_restore_job(user_id: str, restore_request: FZIPRestoreRequest) -> FZIPJob:
    """Create a new FZIP restore job (empty profile only)"""
    return FZIPJob(
        userId=user_id,
        jobType=FZIPType.RESTORE,
        status=FZIPStatus.RESTORE_UPLOADED,
        # Note: No merge strategy for empty profile restores
        parameters={
            'validateOnly': restore_request.validate_only
        }
    )

 