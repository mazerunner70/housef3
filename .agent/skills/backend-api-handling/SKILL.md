---
name: Backend API Handling
description: Backend handler patterns, decorators, payload validation, parameter extraction, and HTTP response standardization.
---

# Backend API Handling Conventions

## Modern Handler Structure
Use decorator-based routing for maximum code reduction. Use `@api_handler()` which automatically handles authentication, errors, and logging.

```python
from utils.handler_decorators import api_handler

@api_handler()
def create_item_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    item_data, error = parse_and_validate_json(event, ItemCreate)
    if error:
        raise ValueError(error["message"])
    item = service.create_item(user_id, item_data)
    
    return {
        "message": "Item created",
        "item": item.model_dump(by_alias=True, mode='json')
    }
```

## Parameter Extraction Utilities
Always use the lambda utilities for consistent parameter handling instead of direct dictionary access:
- `mandatory_path_parameter(event, "id")`
- `optional_path_parameter(event, "id")`  
- `mandatory_body_parameter(event, "field")`
- `mandatory_query_parameter(event, "limit")`

## Response Standardization (CRISIS AVOIDANCE)
- **ALWAYS** use `create_response(status_code, body)` from `utils.lambda_utils` for all output.
- **NEVER** build your own `create_response` logic or `DecimalEncoder` class inside the handler. We have centralized CORS and Decimal/UUID encoding inside the global `create_response`.

## Consistent JSON Serialization in Responses
* Output models using: `model.model_dump(by_alias=True, mode='json')`
* **Stop manually stringifying Decimals or UUIDs** in the handler array! Let `DecimalEncoder` (called internally by `create_response`) do it automatically.
  ```python
  # ✅ CORRECT
  return create_response(200, { "amount": decimal_val, "id": uuid_val })
  # ❌ WRONG
  return create_response(200, { "amount": str(decimal_val) }) # DecimalEncoder handles this!
  ```
* **Dates and Timestamps**: API calls must ALWAYS have dates returned as **seconds since the Unix epoch** (integers). Do not return formatted date strings or ISO dates.

## Advanced Decorator Usage
Stack decorators logically to reduce boilerplate code inside the handler:
- `@api_handler(require_ownership=("id", "account"))`
- `@standard_error_handling` (Wraps ValidationError -> 400, NotFound -> 404)
- `@require_authenticated_user`
- `@log_request_response`
