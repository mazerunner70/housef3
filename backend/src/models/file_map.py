"""
Field mapping model for transaction file processing.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field, field_validator, ConfigDict

class FieldMapping(BaseModel):
    """Represents a mapping between a source field and a transaction field using Pydantic."""
    source_field: str = Field(alias="sourceField", min_length=1)
    target_field: str = Field(alias="targetField", min_length=1)
    transformation: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        extra='forbid'
    )

class FileMap(BaseModel):
    """Represents a field mapping configuration for transaction files using Pydantic."""
    file_map_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="fileMapId")
    user_id: uuid.UUID = Field(alias="userId")
    name: str = Field(min_length=1, max_length=255)
    mappings: List[FieldMapping]
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    description: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="createdAt")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str,
            datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")
        },
        extra='forbid'
    )

    @field_validator('mappings')
    @classmethod
    def check_mappings_not_empty(cls, v: List[FieldMapping]) -> List[FieldMapping]:
        if not v:
            raise ValueError("Mappings list cannot be empty")
        return v

class FileMapCreate(BaseModel):
    """DTO for creating a new FileMap."""
    name: str = Field(min_length=1, max_length=255)
    mappings: List[FieldMapping]
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    description: Optional[str] = Field(default=None, max_length=1000)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str},
        extra='forbid'
    )

    @field_validator('mappings')
    @classmethod
    def check_create_mappings_not_empty(cls, v: List[FieldMapping]) -> List[FieldMapping]:
        if not v:
            raise ValueError("Mappings list cannot be empty for creation")
        return v

class FileMapUpdate(BaseModel):
    """DTO for updating an existing FileMap. All fields are optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    mappings: Optional[List[FieldMapping]] = None
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    description: Optional[str] = Field(default=None, max_length=1000)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str},
        extra='forbid'
    )

    @field_validator('mappings')
    @classmethod
    def check_update_mappings_not_empty_if_provided(cls, v: Optional[List[FieldMapping]]) -> Optional[List[FieldMapping]]:
        if v is not None and not v:
            raise ValueError("Mappings list, if provided for update, cannot be empty")
        return v
