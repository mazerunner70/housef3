"""
Export models for the import/export system.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ExportStatus(str, Enum):
    """Status of an export job"""
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ExportType(str, Enum):
    """Type of export"""
    COMPLETE = "complete"
    SELECTIVE = "selective"
    ACCOUNTS_ONLY = "accounts_only"
    TRANSACTIONS_ONLY = "transactions_only"


class ExportFormat(str, Enum):
    """Export package format"""
    ZIP = "zip"
    JSON = "json"


class ExportJob(BaseModel):
    """Represents an export job with status tracking"""
    export_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="exportId")
    user_id: str = Field(alias="userId")
    status: ExportStatus = Field(default=ExportStatus.INITIATED)
    export_type: ExportType = Field(alias="exportType")
    export_format: ExportFormat = Field(default=ExportFormat.ZIP, alias="exportFormat")
    
    # Request metadata
    requested_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000),
        alias="requestedAt"
    )
    completed_at: Optional[int] = Field(default=None, alias="completedAt")
    expires_at: Optional[int] = Field(default=None, alias="expiresAt")
    
    # Export configuration
    include_analytics: bool = Field(default=False, alias="includeAnalytics")
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    # Results
    download_url: Optional[str] = Field(default=None, alias="downloadUrl")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    s3_key: Optional[str] = Field(default=None, alias="s3Key")
    
    # Error handling
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = Field(default=None, alias="errorDetails")
    
    # Progress tracking
    progress: int = Field(default=0, ge=0, le=100)
    current_phase: Optional[str] = Field(default=None, alias="currentPhase")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str,
            Decimal: str
        },
        use_enum_values=True
    )

    @field_validator('requested_at', 'completed_at', 'expires_at')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format"""
        item = self.model_dump(mode='python', by_alias=True, exclude_none=True)
        
        # Convert UUID to string
        if 'exportId' in item:
            item['exportId'] = str(item['exportId'])
            
        # Convert enum values to strings
        if 'status' in item:
            item['status'] = item['status'].value if hasattr(item['status'], 'value') else str(item['status'])
        if 'exportType' in item:
            item['exportType'] = item['exportType'].value if hasattr(item['exportType'], 'value') else str(item['exportType'])
        if 'exportFormat' in item:
            item['exportFormat'] = item['exportFormat'].value if hasattr(item['exportFormat'], 'value') else str(item['exportFormat'])
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'ExportJob':
        """Create ExportJob from DynamoDB item"""
        # Convert string UUIDs back to UUID objects
        if 'exportId' in item:
            item['exportId'] = uuid.UUID(item['exportId'])
            
        # Convert string enums back to enum objects
        if 'status' in item:
            item['status'] = ExportStatus(item['status'])
        if 'exportType' in item:
            item['exportType'] = ExportType(item['exportType'])
        if 'exportFormat' in item:
            item['exportFormat'] = ExportFormat(item['exportFormat'])
            
        return cls.model_validate(item)


class DataSummary(BaseModel):
    """Summary of data included in export"""
    accounts_count: int = Field(alias="accountsCount")
    transactions_count: int = Field(alias="transactionsCount")
    categories_count: int = Field(alias="categoriesCount")
    file_maps_count: int = Field(alias="fileMapsCount")
    transaction_files_count: int = Field(alias="transactionFilesCount")
    analytics_included: bool = Field(alias="analyticsIncluded")
    
    model_config = ConfigDict(
        populate_by_name=True
    )


class CompatibilityInfo(BaseModel):
    """Compatibility information for import"""
    minimum_version: str = Field(alias="minimumVersion")
    supported_versions: List[str] = Field(alias="supportedVersions")
    
    model_config = ConfigDict(
        populate_by_name=True
    )


class ExportManifest(BaseModel):
    """Manifest for export package validation and metadata"""
    export_format_version: str = Field(alias="exportFormatVersion")
    export_timestamp: str = Field(alias="exportTimestamp")
    user_id: str = Field(alias="userId")
    housef3_version: str = Field(alias="housef3Version")
    
    data_summary: DataSummary = Field(alias="dataSummary")
    checksums: Dict[str, str] = Field(default_factory=dict)
    compatibility: CompatibilityInfo
    
    # Export metadata
    export_id: uuid.UUID = Field(alias="exportId")
    export_type: ExportType = Field(alias="exportType")
    include_analytics: bool = Field(alias="includeAnalytics")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    )


class ExportRequest(BaseModel):
    """Request model for creating a new export"""
    include_analytics: bool = Field(default=False, alias="includeAnalytics")
    export_format: ExportFormat = Field(default=ExportFormat.ZIP, alias="exportFormat")
    export_type: ExportType = Field(default=ExportType.COMPLETE, alias="exportType")
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


class ExportResponse(BaseModel):
    """Response model for export operations"""
    export_id: uuid.UUID = Field(alias="exportId")
    status: ExportStatus
    estimated_size: Optional[str] = Field(default=None, alias="estimatedSize")
    estimated_completion: Optional[str] = Field(default=None, alias="estimatedCompletion")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    )


class ExportStatusResponse(BaseModel):
    """Response model for export status checks"""
    export_id: uuid.UUID = Field(alias="exportId")
    status: ExportStatus
    progress: int = Field(ge=0, le=100)
    current_phase: Optional[str] = Field(default=None, alias="currentPhase")
    download_url: Optional[str] = Field(default=None, alias="downloadUrl")
    expires_at: Optional[str] = Field(default=None, alias="expiresAt")
    error: Optional[str] = None
    
    # Summary information
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=True
    ) 