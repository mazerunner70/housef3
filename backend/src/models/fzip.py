"""
Unified FZIP (Financial ZIP) models for the import/export system.
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
    # Export statuses
    EXPORT_INITIATED = "export_initiated"
    EXPORT_PROCESSING = "export_processing"
    EXPORT_COMPLETED = "export_completed"
    EXPORT_FAILED = "export_failed"
    EXPORT_EXPIRED = "export_expired"
    
    # Import statuses
    IMPORT_UPLOADED = "import_uploaded"
    IMPORT_VALIDATING = "import_validating"
    IMPORT_VALIDATION_PASSED = "import_validation_passed"
    IMPORT_VALIDATION_FAILED = "import_validation_failed"
    IMPORT_PROCESSING = "import_processing"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"


class FZIPType(str, Enum):
    """Type of FZIP operation"""
    EXPORT = "export"
    IMPORT = "import"


class FZIPExportType(str, Enum):
    """Type of FZIP export"""
    COMPLETE = "complete"
    SELECTIVE = "selective"
    ACCOUNTS_ONLY = "accounts_only"
    TRANSACTIONS_ONLY = "transactions_only"


class FZIPFormat(str, Enum):
    """FZIP package format"""
    FZIP = "fzip"
    JSON = "json"


class FZIPMergeStrategy(str, Enum):
    """Merge strategy for FZIP imports"""
    FAIL_ON_CONFLICT = "fail_on_conflict"
    OVERWRITE = "overwrite"
    SKIP_EXISTING = "skip_existing"


# ============================================================================
# CORE MODELS
# ============================================================================

class FZIPJob(BaseModel):
    """Unified model for FZIP export and import jobs"""
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
    
    # Export-specific fields
    export_type: Optional[FZIPExportType] = Field(default=None, alias="exportType")
    include_analytics: bool = Field(default=False, alias="includeAnalytics")
    description: Optional[str] = None
    
    # Import-specific fields
    merge_strategy: Optional[FZIPMergeStrategy] = Field(default=None, alias="mergeStrategy")
    
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
    import_results: Dict[str, Any] = Field(default_factory=dict, alias="importResults")
    
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
        for field in ['status', 'jobType', 'exportType', 'mergeStrategy', 'packageFormat']:
            if field in item and item[field] is not None:
                item[field] = item[field].value if hasattr(item[field], 'value') else str(item[field])
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'FZIPJob':
        """Create FZIPJob from DynamoDB item"""
        # Convert string UUIDs back to UUID objects
        if 'jobId' in item:
            item['jobId'] = uuid.UUID(item['jobId'])
            
        # Convert string enums back to enum objects
        if 'status' in item:
            item['status'] = FZIPStatus(item['status'])
        if 'jobType' in item:
            item['jobType'] = FZIPType(item['jobType'])
        if 'exportType' in item and item['exportType']:
            item['exportType'] = FZIPExportType(item['exportType'])
        if 'mergeStrategy' in item and item['mergeStrategy']:
            item['mergeStrategy'] = FZIPMergeStrategy(item['mergeStrategy'])
        if 'packageFormat' in item:
            item['packageFormat'] = FZIPFormat(item['packageFormat'])
            
        return cls.model_validate(item)

    def is_export(self) -> bool:
        """Check if this is an export job"""
        return self.job_type == FZIPType.EXPORT

    def is_import(self) -> bool:
        """Check if this is an import job"""
        return self.job_type == FZIPType.IMPORT

    def is_completed(self) -> bool:
        """Check if the job is completed"""
        return self.status in [FZIPStatus.EXPORT_COMPLETED, FZIPStatus.IMPORT_COMPLETED]

    def is_failed(self) -> bool:
        """Check if the job failed"""
        return self.status in [FZIPStatus.EXPORT_FAILED, FZIPStatus.IMPORT_FAILED, 
                              FZIPStatus.IMPORT_VALIDATION_FAILED]


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class FZIPExportRequest(BaseModel):
    """Request model for creating a new FZIP export"""
    include_analytics: bool = Field(default=False, alias="includeAnalytics")
    export_type: FZIPExportType = Field(default=FZIPExportType.COMPLETE, alias="exportType")
    description: Optional[str] = None
    
    # Selective export parameters
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


class FZIPImportRequest(BaseModel):
    """Request model for creating a new FZIP import"""
    merge_strategy: FZIPMergeStrategy = Field(alias="mergeStrategy")
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
    
    # Export-specific fields
    estimated_size: Optional[str] = Field(default=None, alias="estimatedSize")
    estimated_completion: Optional[str] = Field(default=None, alias="estimatedCompletion")
    
    # Import-specific fields
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
    
    # Export-specific fields
    download_url: Optional[str] = Field(default=None, alias="downloadUrl")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    
    # Import-specific fields
    validation_results: Dict[str, Any] = Field(default_factory=dict, alias="validationResults")
    import_results: Dict[str, Any] = Field(default_factory=dict, alias="importResults")
    
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
    """Summary of data included in FZIP export"""
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
    """Compatibility information for FZIP import"""
    minimum_version: str = Field(alias="minimumVersion")
    supported_versions: List[str] = Field(alias="supportedVersions")
    
    model_config = ConfigDict(
        populate_by_name=True
    )


class FZIPManifest(BaseModel):
    """Manifest for FZIP package validation and metadata"""
    export_format_version: str = Field(alias="exportFormatVersion")
    export_timestamp: str = Field(alias="exportTimestamp")
    user_id: str = Field(alias="userId")
    housef3_version: str = Field(alias="housef3Version")
    package_format: FZIPFormat = Field(default=FZIPFormat.FZIP, alias="packageFormat")
    
    data_summary: FZIPDataSummary = Field(alias="dataSummary")
    checksums: Dict[str, str] = Field(default_factory=dict)
    compatibility: FZIPCompatibilityInfo
    
    # Export metadata
    job_id: uuid.UUID = Field(alias="jobId")
    export_type: FZIPExportType = Field(alias="exportType")
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


class FZIPImportSummary(BaseModel):
    """Summary of import results"""
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

def create_export_job(user_id: str, export_request: FZIPExportRequest) -> FZIPJob:
    """Create a new FZIP export job"""
    return FZIPJob(
        userId=user_id,
        jobType=FZIPType.EXPORT,
        status=FZIPStatus.EXPORT_INITIATED,
        exportType=export_request.export_type,
        includeAnalytics=export_request.include_analytics,
        description=export_request.description,
        parameters={
            'accountIds': export_request.account_ids,
            'dateRangeStart': export_request.date_range_start,
            'dateRangeEnd': export_request.date_range_end,
            'categoryIds': export_request.category_ids
        } if any([export_request.account_ids, export_request.date_range_start, 
                   export_request.date_range_end, export_request.category_ids]) else None
    )


def create_import_job(user_id: str, import_request: FZIPImportRequest) -> FZIPJob:
    """Create a new FZIP import job"""
    return FZIPJob(
        userId=user_id,
        jobType=FZIPType.IMPORT,
        status=FZIPStatus.IMPORT_UPLOADED,
        mergeStrategy=import_request.merge_strategy,
        parameters={
            'validateOnly': import_request.validate_only
        }
    ) 