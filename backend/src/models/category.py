from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ConfigDict
import logging

logger = logging.getLogger(__name__)

class CategoryType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"

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
    priority: int = Field(default=0)  # Higher priority rules checked first (0-100)
    enabled: bool = Field(default=True)
    confidence: int = Field(default=100)  # How confident we are in this rule (0-100)
    
    # For amount-based rules
    amount_min: Optional[Decimal] = Field(default=None, alias="amountMin")
    amount_max: Optional[Decimal] = Field(default=None, alias="amountMax")
    
    # Suggestion behavior
    allow_multiple_matches: bool = Field(default=True, alias="allowMultipleMatches")
    auto_suggest: bool = Field(default=True, alias="autoSuggest")  # If false, rule won't create automatic suggestions
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ 
            Decimal: str,
            UUID: str
        },
        use_enum_values=True,
        arbitrary_types_allowed=True
    )
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Confidence must be between 0 and 100')
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Priority must be between 0 and 100')
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

    def update_category_details(self, update_data: 'CategoryUpdate') -> bool:
        """
        Updates the category with data from a CategoryUpdate DTO.
        Returns True if any fields were changed, False otherwise.
        """
        updated_fields = False
        
        # Get only the fields that were actually set (not None)
        update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True, by_alias=False)
        
        # Handle each field individually to preserve object types
        for key, value in update_dict.items():
            if key not in ["categoryId", "userId", "createdAt"] and hasattr(self, key):
                if key == "rules":
                    # Special handling for rules to preserve CategoryRule objects
                    if value is not None and getattr(self, key) != value:
                        logger.info(f"DIAG: Updating rules field - using actual CategoryRule objects from DTO")
                        if update_data.rules is not None:
                            logger.info(f"DIAG: update_data.rules has {len(update_data.rules)} rules of types: {[type(r) for r in update_data.rules]}")
                            setattr(self, key, update_data.rules)  # Use the actual objects, not serialized dict
                        else:
                            logger.info(f"DIAG: update_data.rules is None, setting empty list")
                            setattr(self, key, [])
                        updated_fields = True
                else:
                    # Normal field handling
                    if getattr(self, key) != value:
                        setattr(self, key, value)
                        updated_fields = True
        
        if updated_fields:
            self.updatedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
        return updated_fields

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serializes Category to a flat dictionary for DynamoDB."""
        # Diagnostic logging
        logger.debug(f"DIAG: to_dynamodb_item called for category {self.categoryId}")
        logger.debug(f"DIAG: Rules count: {len(self.rules)}")
        for i, rule in enumerate(self.rules):
            logger.debug(f"DIAG: Rule {i}: type={type(rule)}, is_dict={isinstance(rule, dict)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
            if isinstance(rule, dict):
                logger.debug(f"DIAG: Rule {i} dict keys: {list(rule.keys())}")
                logger.debug(f"DIAG: Rule {i} dict sample: {str(rule)[:200]}...")
        
        item = self.model_dump(mode='python', by_alias=True, exclude_none=True)
        
        # Explicitly convert UUID fields to strings for DynamoDB
        if 'categoryId' in item and isinstance(item.get('categoryId'), UUID):
            item['categoryId'] = str(item['categoryId'])
            
        if 'parentCategoryId' in item and item.get('parentCategoryId') is not None and isinstance(item.get('parentCategoryId'), UUID):
            item['parentCategoryId'] = str(item.get('parentCategoryId'))
        
        # Convert any rules that contain UUIDs or Decimals
        if 'rules' in item and item['rules']:
            for rule in item['rules']:
                if isinstance(rule, dict):
                    # Handle UUID fields in rules if they exist
                    for key, value in rule.items():
                        if isinstance(value, UUID):
                            rule[key] = str(value)
                        # Convert Decimal fields (amountMin, amountMax) to strings for DynamoDB
                        elif isinstance(value, Decimal):
                            rule[key] = str(value)
        
        return item

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "Category":
        """Deserializes a dictionary from DynamoDB to a Category instance."""
        # Diagnostic logging
        category_id = data.get('categoryId', 'UNKNOWN')
        logger.debug(f"DIAG: from_dynamodb_item called for category {category_id}")
        
        # Convert rules dictionaries to CategoryRule objects if needed
        if 'rules' in data and data['rules']:
            logger.debug(f"DIAG: Found {len(data['rules'])} rules in DynamoDB data")
            converted_rules = []
            for i, rule_data in enumerate(data['rules']):
                logger.debug(f"DIAG: Processing rule {i}: type={type(rule_data)}")
                if isinstance(rule_data, dict):
                    logger.debug(f"DIAG: Rule {i} is dict with keys: {list(rule_data.keys())}")
                    # Convert string amount fields back to Decimal objects if needed
                    if 'amountMin' in rule_data and rule_data['amountMin'] is not None:
                        rule_data['amountMin'] = Decimal(str(rule_data['amountMin']))
                    if 'amountMax' in rule_data and rule_data['amountMax'] is not None:
                        rule_data['amountMax'] = Decimal(str(rule_data['amountMax']))
                    
                    # Convert dictionary to CategoryRule object
                    converted_rule = CategoryRule(**rule_data)
                    converted_rules.append(converted_rule)
                    logger.debug(f"DIAG: Successfully converted rule {i} to CategoryRule")
                elif isinstance(rule_data, CategoryRule):
                    # Already a CategoryRule object
                    converted_rules.append(rule_data)
                    logger.debug(f"DIAG: Rule {i} was already CategoryRule")
                else:
                    # Skip invalid rule data
                    logger.warning(f"DIAG: Skipping invalid rule {i} of type {type(rule_data)}")
                    continue
            data['rules'] = converted_rules
            logger.debug(f"DIAG: Converted all rules, final count: {len(converted_rules)}")
        else:
            logger.debug(f"DIAG: No rules found in DynamoDB data")
        
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
