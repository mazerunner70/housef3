---
name: Backend Database Client
description: DynamoDB interaction patterns, db_utils conventions, and serialization/deserialization rules for the Python database layer.
---

# Backend Database Conventions

## DynamoDB Integration Overview
- Always organize DynamoDB interaction code within `utils/db_utils/`.
- Handle conversion logic cleanly before items exit the DB layer context.

## Deserialization Pattern (`from_dynamodb_item`)
When loading data from DynamoDB into Pydantic models:

1. **Always copy data** before modification in `from_dynamodb_item()` to avoid mutating the original dictionary.
2. **Use `model_construct()`** instead of `model_validate()` to preserve actual `Enum` objects rather than just their string values.
3. **Convert enums manually** from string representations to proper Enum class objects *before* construction.
4. **Handle Decimal conversion** explicitly for numeric fields:
   ```python
   try:
       converted_data['balance'] = Decimal(str(converted_data['balance']))
   except decimal.InvalidOperation:
       raise ValueError(f"Invalid decimal: {converted_data['balance']}")
   ```
5. **Handle Dates/Timestamps**: Dates are **not** stored as ISO strings or `datetime` objects. They are entirely handled and stored as **integers representing milliseconds since the Unix epoch** (e.g., `created_at: int`).
6. **Contextual Validation:** Set context when you do need to use validate: `context={'from_database': True}`

## Serialization Pattern (`to_dynamodb_item`)
Every database-stored model must cleanly implement serialization to DynamoDB:

1. Start by dumping with `mode='python'`, `by_alias=True`, and `exclude_none=True`.
2. Convert all `UUID` objects to strings (DynamoDB cannot store native UUIDs).
3. Convert all `Decimal` objects to strings to preserve high precision during transmission/storage.
4. Convert all `Enum` objects to their raw `.value` strings.

## Pydantic Configuration
Models used alongside the DB should use this standard `ConfigDict`:
```python
model_config = ConfigDict(
    populate_by_name=True,           
    json_encoders={                  
        Decimal: str,
        uuid.UUID: str
    },
    use_enum_values=True,            # Warning: impacts model_validate() behavior
    arbitrary_types_allowed=True    
)
```
