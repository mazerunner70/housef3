from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime, timezone

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
    categoryId: str = Field(default_factory=lambda: f"cat_{uuid4()}")
    parentCategoryId: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = Field(default_factory=list)
    createdAt: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))
    updatedAt: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000))

    # __post_init__, to_dict, and from_dict are no longer needed with Pydantic
    # Pydantic automatically handles nested model parsing (CategoryRule)
    # and enum conversion (CategoryType)

class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    parentCategoryId: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = Field(default_factory=list)
    
    # __post_init__, to_dict, and from_dict are no longer needed

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[CategoryType] = None
    parentCategoryId: Optional[str] = None # Pydantic handles if client sends "" vs null for optional fields. 
                                         # If "" should map to None explicitly, a pre-validator can be used.
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: Optional[List[CategoryRule]] = None
