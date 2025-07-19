from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

class ImportStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MergeStrategy(str, Enum):
    FAIL_ON_CONFLICT = "fail_on_conflict"
    OVERWRITE = "overwrite"
    SKIP_EXISTING = "skip_existing"

class ImportJob(BaseModel):
    import_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="importId")
    user_id: str = Field(alias="userId")
    status: ImportStatus
    merge_strategy: MergeStrategy = Field(alias="mergeStrategy")
    uploaded_at: int = Field(alias="uploadedAt")
    completed_at: Optional[int] = Field(default=None, alias="completedAt")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    validation_results: Dict[str, Any] = Field(default_factory=dict, alias="validationResults")
    import_results: Dict[str, Any] = Field(default_factory=dict, alias="importResults")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: int = Field(default=0)
    current_phase: str = Field(default="", alias="currentPhase")
    package_s3_key: Optional[str] = Field(default=None, alias="packageS3Key")
    expires_at: Optional[int] = Field(default=None, alias="expiresAt")

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert the model to a DynamoDB item."""
        item = {
            'importId': str(self.import_id),
            'userId': self.user_id,
            'status': self.status.value,
            'mergeStrategy': self.merge_strategy.value,
            'uploadedAt': self.uploaded_at,
            'progress': self.progress,
            'currentPhase': self.current_phase,
            'validationResults': self.validation_results,
            'importResults': self.import_results
        }
        
        if self.completed_at is not None:
            item['completedAt'] = self.completed_at
        if self.package_size is not None:
            item['packageSize'] = self.package_size
        if self.error_message is not None:
            item['errorMessage'] = self.error_message
        if self.package_s3_key is not None:
            item['packageS3Key'] = self.package_s3_key
        if self.expires_at is not None:
            item['expiresAt'] = self.expires_at
            
        return item

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'ImportJob':
        """Create an ImportJob from a DynamoDB item."""
        return cls(
            importId=uuid.UUID(item['importId']),
            userId=item['userId'],
            status=ImportStatus(item['status']),
            mergeStrategy=MergeStrategy(item['mergeStrategy']),
            uploadedAt=item['uploadedAt'],
            completedAt=item.get('completedAt'),
            packageSize=item.get('packageSize'),
            validationResults=item.get('validationResults', {}),
            importResults=item.get('importResults', {}),
            errorMessage=item.get('errorMessage'),
            progress=item.get('progress', 0),
            currentPhase=item.get('currentPhase', ''),
            packageS3Key=item.get('packageS3Key'),
            expiresAt=item.get('expiresAt')
        )

class ImportRequest(BaseModel):
    merge_strategy: MergeStrategy = Field(alias="mergeStrategy")
    validate_only: bool = Field(default=False, alias="validateOnly")

class ImportResponse(BaseModel):
    import_id: uuid.UUID = Field(alias="importId")
    status: ImportStatus
    message: str

class ImportStatusResponse(BaseModel):
    import_id: uuid.UUID = Field(alias="importId")
    status: ImportStatus
    progress: int
    current_phase: str = Field(alias="currentPhase")
    validation_results: Dict[str, Any] = Field(default_factory=dict, alias="validationResults")
    import_results: Dict[str, Any] = Field(default_factory=dict, alias="importResults")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    uploaded_at: int = Field(alias="uploadedAt")
    completed_at: Optional[int] = Field(default=None, alias="completedAt")

class ValidationSummary(BaseModel):
    valid: int
    warnings: int
    errors: int
    details: List[str] = Field(default_factory=list)

class ImportSummary(BaseModel):
    accounts_created: int = Field(alias="accountsCreated")
    accounts_updated: int = Field(alias="accountsUpdated")
    transactions_created: int = Field(alias="transactionsCreated")
    transactions_updated: int = Field(alias="transactionsUpdated")
    categories_created: int = Field(alias="categoriesCreated")
    categories_updated: int = Field(alias="categoriesUpdated")
    files_restored: int = Field(alias="filesRestored")
    file_maps_created: int = Field(alias="fileMapsCreated")
    file_maps_updated: int = Field(alias="fileMapsUpdated") 