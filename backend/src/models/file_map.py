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
    user_id: str = Field(alias="userId")
    name: str = Field(min_length=1, max_length=255)
    mappings: List[FieldMapping]
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    description: Optional[str] = Field(default=None, max_length=1000)
    reverse_amounts: bool = Field(default=False, alias="reverseAmounts")  # Flag to reverse transaction amounts (multiply by -1)
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdAt")
    updated_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        extra='forbid'
    )

    @field_validator('mappings')
    @classmethod
    def check_mappings_not_empty(cls, v: List[FieldMapping]) -> List[FieldMapping]:
        if not v:
            raise ValueError("Mappings list cannot be empty")
        return v

    @field_validator('created_at', 'updated_at')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serializes FileMap to a flat dictionary for DynamoDB."""
        data = self.model_dump(mode='json', by_alias=True, exclude_none=True)
        # mappings should already be a list of dicts due to FieldMapping being a BaseModel
        # UUIDs are handled by json_encoders in model_config (when mode='json')
        # Timestamps are already ints (milliseconds)
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "FileMap":
        """Deserializes a dictionary from DynamoDB to a FileMap instance."""
        # Pydantic should handle reconstruction of FieldMapping objects within the list
        # and UUID string conversion if type hints and config are correct.
        return cls(**data)

    def update_with_data(self, update_data: 'FileMapUpdate') -> bool:
        """
        Updates the file map with data from a FileMapUpdate DTO.
        Returns True if any fields were changed, False otherwise.
        """
        updated_fields = False
        # Use mode='python' to get the actual objects, not their string values
        update_dict = update_data.model_dump(exclude_unset=True, by_alias=False, mode='python') # Use field names

        for key, value in update_dict.items():
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                updated_fields = True
        
        if updated_fields:
            self.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        return updated_fields

class FileMapCreate(BaseModel):
    """DTO for creating a new FileMap."""
    name: str = Field(min_length=1, max_length=255)
    mappings: List[FieldMapping]
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    description: Optional[str] = Field(default=None, max_length=1000)
    reverse_amounts: bool = Field(default=False, alias="reverseAmounts")  # Flag to reverse transaction amounts (multiply by -1)

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str},
        extra='forbid'
    )

    @field_validator('mappings')
    @classmethod
    def check_create_mappings_not_empty(cls, v: List[FieldMapping]) -> List[FieldMapping]:
        if not v:
            raise ValueError("Mappings list cannot be empty")
        return v

    @field_validator('mappings', mode='before')
    @classmethod
    def convert_mapping_dicts_to_objects_create(cls, v: List[Any]) -> List[FieldMapping]:
        """Convert dictionary mappings to FieldMapping objects if needed."""
        converted_mappings = []
        for mapping in v:
            if isinstance(mapping, dict):
                # Convert dictionary to FieldMapping object
                converted_mappings.append(FieldMapping(**mapping))
            elif isinstance(mapping, FieldMapping):
                # Already a FieldMapping object
                converted_mappings.append(mapping)
            else:
                # Invalid type
                raise ValueError(f"Invalid mapping type: {type(mapping)}. Expected dict or FieldMapping.")
        
        return converted_mappings

class FileMapUpdate(BaseModel):
    """DTO for updating an existing FileMap. All fields are optional."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    mappings: Optional[List[FieldMapping]] = None
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    description: Optional[str] = Field(default=None, max_length=1000)
    reverse_amounts: Optional[bool] = Field(default=None, alias="reverseAmounts")  # Flag to reverse transaction amounts (multiply by -1)

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

    @field_validator('mappings', mode='before')
    @classmethod
    def convert_mapping_dicts_to_objects(cls, v: Optional[List[Any]]) -> Optional[List[FieldMapping]]:
        """Convert dictionary mappings to FieldMapping objects if needed."""
        if v is None:
            return v
        
        converted_mappings = []
        for mapping in v:
            if isinstance(mapping, dict):
                # Convert dictionary to FieldMapping object
                converted_mappings.append(FieldMapping(**mapping))
            elif isinstance(mapping, FieldMapping):
                # Already a FieldMapping object
                converted_mappings.append(mapping)
            else:
                # Invalid type
                raise ValueError(f"Invalid mapping type: {type(mapping)}. Expected dict or FieldMapping.")
        
        return converted_mappings
