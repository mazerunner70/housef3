---
name: Backend Data Modelling
description: Pydantic model rules, enum preservation, model_construct vs model_validate, and DTO structures.
---

# Backend Data Models Conventions

## Pydantic Architecture (DTO Patterns)
Always split models into three structures to separate database models from API contracts:
1. `ModelName(BaseModel)`: Main domain model with full business logic, serialization methods, and DynamoDB DB mapping.
2. `ModelNameCreate(BaseModel)`: DTO for creating new instances containing only required fields. Never use for updates.
3. `ModelNameUpdate(BaseModel)`: DTO for updates where all fields are optional.

**CRITICAL RULE**: Never directly instantiate or modify base model objects outside of their corresponding DTOs. This ensures proper constraints and data integrity.

### Create DTOs
- Include **only fields needed** for creation.
- **Exclude** auto-generated fields (like IDs, `created_at` timestamps).
- Include required validation for business rules directly on the DTO.

### Update DTOs
- All fields must be **optional** for partial updates.
- **Exclude** immutable fields (like `user_id`, `created_at`).
- Cross-field validation for updates goes here, but complex validation accessing existing entities belongs in the service layer.

## Field Validation & Defaults
- **All fields must use `snake_case` in Python but MUST declare a `camelCase` alias** for external JSON/API.
  ```python
  account_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="accountId")
  ```
- **Dates and Timestamps**: Always store these as **integers representing milliseconds since the Unix epoch**, rather than string/ISO formats.
  ```python
  created_at: int = Field(default_factory=timestamp_ms, alias="createdAt")
  ```
  Validate them to ensure they are positive:
  ```python
  @field_validator('created_at')
  @classmethod
  def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
      if v is not None and v < 0:
          raise ValueError("Timestamp must be positive milliseconds since epoch")
      return v
  ```
- Use explicit `Optional[Type]` for nullable fields.
- Use `default_factory=func` (e.g., `timestamp_ms`) for dynamic defaults.
- Use `@field_validator` for single-field logic and `@model_validator(mode='after')` for cross-field consistency.

## Enum Handling in Pydantic
Enum representation in JSON vs Database context is heavily nuanced:

- All string enums should inherit from `str` for proper JSON: `class Status(str, enum.Enum):`
- **When checking enums**: don't rely fully on `isinstance(v, Currency)`. Provide fallback validation functions capable of catching raw DB strings or API strings and auto-instantiating the Enum class `Currency("usd")`.
- When updating fields dynamically, use `type(obj).__name__` for enum type checking when validating.

## The Model Update Pattern
Provide an internal update method in the Main domain model to consume the update DTO safely:
```python
def update_account_details(self, update_data: 'AccountUpdate') -> bool:
    """Update account with DTO data. Returns True if changed."""
    updated_fields = False
    update_dict = update_data.model_dump(exclude_unset=True, by_alias=False)
    
    for key, value in update_dict.items():
        if key not in ["account_id", "user_id", "created_at"] and hasattr(self, key):
            if getattr(self, key) != value:
                setattr(self, key, value)
                updated_fields = True
                
    if updated_fields:
        self.updated_at = timestamp_ms()
    return updated_fields
```

## Logging in Models
- Use module-level logger: `logger = logging.getLogger(__name__)`
- Log warnings for data inconsistencies from database
- **Don't** log validation errors (let the caller handle it!)

## Model Organization & File Structure
- One main model per file (e.g. `Account`, `Transaction`, `Category`)
- Include related DTOs in the **same file** (e.g. `AccountCreate`, `AccountUpdate`)
- Include related enums and utilities in the **same file**
- Separate complex shared types (e.g. `Money`, `Currency`) into their own files.

### Documentation Requirements
- Include docstrings for all models and complex methods
- Document enum values and their meanings
- Explain validation rules and business constraints
- Document DynamoDB serialization behavior

## Events (Dataclasses override Pydantic)
For pure Event streams (e.g. `EventBridge`), drop Pydantic entirely and use `@dataclass` for speed, passing custom JSON dumps to AWS.
