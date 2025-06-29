from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ConfigDict

class CategoryType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class MatchCondition(str, Enum):
    CONTAINS = "contains"
    STARTS_WITH = "starts_with" 
    ENDS_WITH = "ends_with"
    EQUALS = "equals"
    REGEX = "regex"
    AMOUNT_GREATER = "amount_greater"
    AMOUNT_LESS = "amount_less"
    AMOUNT_BETWEEN = "amount_between"

class CategoryRule(BaseModel):
    rule_id: str = Field(default_factory=lambda: f"rule_{uuid4().hex[:8]}", alias="ruleId")
    field_to_match: str = Field(alias="fieldToMatch")  # description, payee, memo, amount
    condition: MatchCondition
    value: str  # The pattern/value to match
    case_sensitive: bool = Field(default=False, alias="caseSensitive")
    priority: int = Field(default=0)  # Higher priority rules checked first
    enabled: bool = Field(default=True)
    confidence: float = Field(default=1.0)  # How confident we are in this rule (0.0-1.0)
    
    # For amount-based rules
    amount_min: Optional[Decimal] = Field(default=None, alias="amountMin")
    amount_max: Optional[Decimal] = Field(default=None, alias="amountMax")
    
    # Suggestion behavior
    allow_multiple_matches: bool = Field(default=True, alias="allowMultipleMatches")
    auto_suggest: bool = Field(default=True, alias="autoSuggest")  # If false, rule won't create automatic suggestions
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    @validator('amount_min', 'amount_max')
    def validate_amounts(cls, v):
        if v is not None and v < 0:
            raise ValueError('Amount values must be non-negative')
        return v

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
    
    # Enhanced hierarchical support
    inherit_parent_rules: bool = Field(default=True, alias="inheritParentRules")
    rule_inheritance_mode: str = Field(default="additive", alias="ruleInheritanceMode")  # "additive", "override", "disabled"

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            UUID: str,
            Decimal: str
        },
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    @property
    def is_root_category(self) -> bool:
        """Returns True if this is a root category (no parent)"""
        return self.parentCategoryId is None
    
    @validator('rule_inheritance_mode')
    def validate_inheritance_mode(cls, v):
        valid_modes = ["additive", "override", "disabled"]
        if v not in valid_modes:
            raise ValueError(f'Rule inheritance mode must be one of: {valid_modes}')
        return v

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serializes Category to a flat dictionary for DynamoDB."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "Category":
        """Deserializes a dictionary from DynamoDB to a Category instance."""
        return cls(**data)

class CategoryHierarchy(BaseModel):
    """Helper model for managing category hierarchies"""
    category: Category
    children: List['CategoryHierarchy'] = Field(default_factory=list)
    depth: int = Field(default=0)
    full_path: str
    inherited_rules: List[CategoryRule] = Field(default_factory=list)
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

class CategorySuggestionStrategy(str, Enum):
    ALL_MATCHES = "all_matches"  # Show all matching categories as suggestions
    TOP_N_MATCHES = "top_n_matches"  # Show only top N highest confidence matches
    CONFIDENCE_THRESHOLD = "confidence_threshold"  # Show only matches above threshold
    PRIORITY_FILTERED = "priority_filtered"  # Show matches filtered by rule priority

class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    parentCategoryId: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: List[CategoryRule] = Field(default_factory=list)
    inherit_parent_rules: bool = Field(default=True, alias="inheritParentRules")
    rule_inheritance_mode: str = Field(default="additive", alias="ruleInheritanceMode")

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[CategoryType] = None
    parentCategoryId: Optional[UUID] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    rules: Optional[List[CategoryRule]] = None
    inherit_parent_rules: Optional[bool] = Field(default=None, alias="inheritParentRules")
    rule_inheritance_mode: Optional[str] = Field(default=None, alias="ruleInheritanceMode")
