# Enhanced Resource Ownership System

The resource ownership system has been enhanced to support all major resource types with explicit type declarations. This provides better type safety, clearer code, and easier maintenance.

## Overview

**Option 2 Implementation**: Explicit resource type parameters for maximum clarity and flexibility.

## Available Resource Types

- `"account"` - User bank accounts
- `"transaction"` - Individual transactions
- `"category"` - User-defined categories
- `"transaction_file"` - Uploaded transaction files
- `"file_map"` - File mapping configurations

## Basic Usage

### 1. Simple Resource Ownership Decorator

```python
from utils.handler_decorators import require_resource_ownership

@require_resource_ownership("account_id", "account")
def update_account_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """Update account details. The account is pre-verified to belong to user_id."""
    # account parameter is guaranteed to exist and belong to the user
    # No manual ownership checking needed
    return {"message": f"Updated account {account.account_id}"}

@require_resource_ownership("transaction_id", "transaction") 
def get_transaction_handler(event: Dict[str, Any], user_id: str, transaction: Transaction) -> Dict[str, Any]:
    """Get transaction details. The transaction is pre-verified to belong to user_id."""
    return transaction.model_dump(by_alias=True, mode="json")

@require_resource_ownership("category_id", "category")
def delete_category_handler(event: Dict[str, Any], user_id: str, category: Category) -> Dict[str, Any]:
    """Delete a category. The category is pre-verified to belong to user_id."""
    # Safe to delete - ownership already verified
    return {"message": f"Deleted category {category.name}"}
```

### 2. Combined API Handler (Recommended)

```python
from utils.handler_decorators import api_handler

@api_handler(require_ownership=("account_id", "account"))
def update_account_handler(event: Dict[str, Any], user_id: str, account: Account) -> Dict[str, Any]:
    """
    Complete handler with:
    - Authentication required
    - Account ownership verified
    - Error handling automatic
    - Request/response logging
    """
    # Just focus on business logic
    update_data = mandatory_body_parameter(event, "updates")
    # Update account logic here
    return {"message": "Account updated successfully"}

@api_handler(require_ownership=("transaction_id", "transaction"))
def mark_transaction_handler(event: Dict[str, Any], user_id: str, transaction: Transaction) -> Dict[str, Any]:
    """Mark transaction with special status."""
    new_status = mandatory_body_parameter(event, "status")
    # Business logic here - transaction ownership already verified
    return {"message": f"Transaction {transaction.transaction_id} marked as {new_status}"}
```

## Before vs. After Comparison

### Before (Manual Ownership Checking)

```python
def mark_transfer_pair_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        # Manual parameter extraction
        body = json.loads(event.get("body", "{}"))
        outgoing_tx_id = body.get("outgoingTransactionId")
        incoming_tx_id = body.get("incomingTransactionId")
        
        if not outgoing_tx_id or not incoming_tx_id:
            return create_response(400, {"message": "Both transaction IDs are required"})
        
        # Manual transaction lookup
        outgoing_tx = get_transaction_by_id(uuid.UUID(outgoing_tx_id))
        incoming_tx = get_transaction_by_id(uuid.UUID(incoming_tx_id))
        
        if not outgoing_tx or not incoming_tx:
            return create_response(404, {"message": "One or both transactions not found"})
        
        # Manual ownership verification
        if outgoing_tx.user_id != user_id or incoming_tx.user_id != user_id:
            return create_response(403, {"message": "Unauthorized access to transactions"})
        
        # Business logic
        success = transfer_service.mark_as_transfer_pair(outgoing_tx, incoming_tx, user_id)
        
        if success:
            return create_response(200, {"message": "Transfer pair marked successfully"})
        else:
            return create_response(500, {"message": "Error marking transfer pair"})
            
    except json.JSONDecodeError:
        return create_response(400, {"message": "Invalid JSON in request body"})
    except Exception as e:
        logger.error(f"Error marking transfer pair: {str(e)}")
        return create_response(500, {"message": "Error marking transfer pair"})
```

### After (Enhanced Decorators)

```python
@api_handler()  # Handles auth, errors, logging automatically
def mark_transfer_pair_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Mark two transactions as a transfer pair."""
    # Clean parameter extraction
    outgoing_tx_id = mandatory_body_parameter(event, "outgoingTransactionId") 
    incoming_tx_id = mandatory_body_parameter(event, "incomingTransactionId")
    
    # Get transactions with automatic ownership verification
    outgoing_tx = checked_mandatory_transaction(uuid.UUID(outgoing_tx_id), user_id)
    incoming_tx = checked_mandatory_transaction(uuid.UUID(incoming_tx_id), user_id)
    
    # Pure business logic
    success = transfer_service.mark_as_transfer_pair(outgoing_tx, incoming_tx, user_id)
    
    if not success:
        raise RuntimeError("Failed to mark transfer pair")
    
    return {"message": "Transfer pair marked successfully"}
```

### Even Better (Single Transaction with Ownership)

For handlers that work with a single transaction from the URL path:

```python
@api_handler(require_ownership=("transaction_id", "transaction"))
def update_transaction_handler(event: Dict[str, Any], user_id: str, transaction: Transaction) -> Dict[str, Any]:
    """Update a transaction. Path: PUT /transactions/{transaction_id}"""
    # transaction is already verified to belong to user_id
    update_data = parse_and_validate_json(event, TransactionUpdate)
    
    # Pure business logic
    updated_transaction = transaction_service.update(transaction, update_data)
    return updated_transaction.model_dump(by_alias=True, mode="json")
```

## Error Handling

The decorators automatically handle common error cases:

- **Invalid UUID**: Returns 400 Bad Request
- **Resource not found**: Returns 404 Not Found  
- **Unauthorized access**: Returns 403 Forbidden
- **Unexpected errors**: Returns 500 Internal Server Error with logging

## Benefits of Option 2

1. **Explicit and Clear**: Resource type is obvious from the decorator
2. **Type Safe**: Each resource type has its own checker function
3. **Extensible**: Easy to add new resource types
4. **Maintainable**: No complex parameter-to-type mapping logic
5. **Self-Documenting**: Code clearly shows what resources are being verified

## Adding New Resource Types

To add a new resource type:

1. **Create checker function** in `db_utils.py`:
```python
def checked_mandatory_new_resource(resource_id: uuid.UUID, user_id: str) -> NewResource:
    resource = get_new_resource(resource_id)
    if not resource:
        raise NotFound("Resource not found")
    check_user_owns_resource(resource.user_id, user_id)
    return resource
```

2. **Add to decorator mapping** in `handler_decorators.py`:
```python
checker_map = {
    # ... existing types ...
    "new_resource": checked_mandatory_new_resource,
}
```

3. **Use in handlers**:
```python
@api_handler(require_ownership=("new_resource_id", "new_resource"))
def handle_new_resource(event, user_id, new_resource):
    # Handler implementation
```

## Migration Notes

- The old `require_resource_ownership(resource_param)` pattern still works for accounts
- New code should use the explicit `require_resource_ownership(resource_param, resource_type)` pattern
- The `api_handler` convenience decorator now takes tuples: `require_ownership=("param", "type")`
