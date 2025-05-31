from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import ConfigDict

class CategoryType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class CategoryRule(BaseModel):
    fieldToMatch: str
    condition: str
    value: Any
    # ruleLogic: Optional[str] = None # Pydantic handles Optional directly

    # to_dict and from_dict are no longer needed with Pydantic

class Category(BaseModel):
    userId: str
    name: str
    type: CategoryType
    categoryId: UUID = Field(default_factory=uuid4)
    parentCategoryId: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = Field(default_factory=list)
    createdAt: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
    updatedAt: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    model_config = ConfigDict(
        populate_by_name=True, # Alias support if needed elsewhere
        json_encoders={
            UUID: str  # Ensures UUIDs are converted to strings in JSON output
        },
        use_enum_values=True, # Ensures enum values are used (good for CategoryType)
        arbitrary_types_allowed=True # If any non-Pydantic complex types were used
    )

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serializes Category to a flat dictionary for DynamoDB."""
        data = self.model_dump(by_alias=True, exclude_none=True) # Pydantic v2
        # rules will be a list of dicts as CategoryRule is a BaseModel
        # Enums (type) are handled by Pydantic (use_enum_values=True in global config or if set here)
        # Timestamps are already ints (milliseconds)
        # categoryId and parentCategoryId are already strings
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "Category":
        """Deserializes a dictionary from DynamoDB to a Category instance."""
        # Pydantic will reconstruct CategoryRule objects in the list
        # and handle enum conversion for 'type'.
        return cls(**data)

    # __post_init__, to_dict, and from_dict are no longer needed with Pydantic
    # Pydantic automatically handles nested model parsing (CategoryRule)
    # and enum conversion (CategoryType)

class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    parentCategoryId: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = Field(default_factory=list)
    
    # __post_init__, to_dict, and from_dict are no longer needed

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[CategoryType] = None
    parentCategoryId: Optional[UUID] = None # Pydantic handles if client sends "" vs null for optional fields. 
                                         # If "" should map to None explicitly, a pre-validator can be used.
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: Optional[List[CategoryRule]] = None
