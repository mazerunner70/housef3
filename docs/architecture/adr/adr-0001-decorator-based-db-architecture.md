# ADR-0001: Decorator-Based Database Architecture

**Status:** Proposed  
**Date:** 2025-11-02  
**Deciders:** Backend Team

## Context

The current `backend/src/utils/db_utils.py` has grown to 2,239 lines with significant code duplication and inconsistent patterns. We need to decide on an architectural approach for database utilities that improves maintainability without introducing excessive complexity.

### Key Problems

1. **Code Duplication**: 60+ identical try-catch blocks, 8 identical table getters, 12 similar resource checkers
2. **DynamoDB Anti-Patterns**: Using get-modify-put (2 round trips) instead of UpdateExpression (1 round trip)
3. **Lack of Reliability Features**: No retry logic for throttling, inconsistent error handling
4. **Poor Observability**: No performance monitoring, mixed diagnostic logging

### Business Impact

- **Performance**: 2x latency and 2x cost for update operations
- **Reliability**: ~2% transient failure rate due to lack of retry logic
- **Development Velocity**: Difficult to navigate and modify 2,200+ line file
- **Cost**: ~40% higher DynamoDB costs than necessary

## Decision

We will adopt a **decorator-based architecture** for database utilities with the following key patterns:

### 1. Decorator Pattern for Cross-Cutting Concerns

Use Python decorators for:
- Error handling and logging (`@dynamodb_operation`)
- Retry logic with exponential backoff (`@retry_on_throttle`)
- Performance monitoring (`@monitor_performance`)
- Authorization checks (`@require_resource_ownership`)
- Caching (`@cache_result`)

**Example:**
```python
@cache_result(ttl_seconds=60)
@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_account")
def get_account(account_id: uuid.UUID) -> Optional[Account]:
    response = tables.accounts.get_item(Key={'accountId': str(account_id)})
    return Account.from_dynamodb_item(response['Item']) if 'Item' in response else None
```

### 2. Singleton Table Manager

Replace multiple table getter functions with a single class:
```python
class DynamoDBTables:
    @property
    def transactions(self) -> Any:
        return self._get_table('transactions')

tables = DynamoDBTables()  # Global singleton
```

### 3. DynamoDB UpdateExpression Pattern

Use UpdateExpression instead of get-modify-put for atomic updates:
```python
# Build update expression dynamically
expr, names, values = build_update_expression(update_dict)
response = tables.accounts.update_item(
    Key={'accountId': str(account_id)},
    UpdateExpression=expr,
    ExpressionAttributeNames=names,
    ExpressionAttributeValues=values,
    ReturnValues='ALL_NEW'
)
```

### 4. Generic Helper Functions with Type Parameters

Use generics to eliminate resource-specific duplication:
```python
T = TypeVar('T')

def checked_mandatory_resource(
    resource_id: Optional[uuid.UUID],
    user_id: str,
    getter_func: Callable[[uuid.UUID], Optional[T]],
    resource_name: str
) -> T:
    # Single implementation for all resources
```

### 5. Modular File Organization

Split into focused modules:
- `db/base.py` - Decorators, table management, base operations
- `db/helpers.py` - Batch operations, pagination, utilities
- `db/accounts.py`, `db/transactions.py`, etc. - Resource-specific operations
- `db/__init__.py` - Public API for backward compatibility

## Consequences

### Positive Consequences

1. **Code Quality**
   - Eliminate 60+ repetitive try-catch blocks
   - 30-40% reduction in total lines of code
   - Consistent patterns across all database operations
   - Better separation of concerns

2. **Performance**
   - 50% faster updates (1 round trip vs 2)
   - 50% reduction in WCU cost for updates
   - 500x faster cache hits for frequently accessed data
   - Atomic updates prevent race conditions

3. **Reliability**
   - Automatic retry with exponential backoff for all operations
   - Transient failure rate: 2% → <0.1%
   - Consistent error handling and classification
   - Better error messages for debugging

4. **Observability**
   - Performance monitoring on all operations
   - Structured logging with operation context
   - Easy identification of slow queries
   - Metrics for optimization decisions

5. **Maintainability**
   - Focused modules (largest file ~400 lines vs 2,239)
   - Clear, composable patterns
   - Easier to test in isolation
   - Better IDE support and autocomplete

### Negative Consequences

1. **Learning Curve**
   - Team must understand decorator composition
   - New patterns to learn
   - Different from current direct approach

2. **Migration Complexity**
   - Requires phased migration approach
   - Need to update imports across codebase
   - Risk during transition period

3. **Initial Development Time**
   - Time investment to implement decorators and helpers
   - Testing overhead
   - Documentation updates needed

### Mitigation Strategies

1. **Education**: Team training on decorator patterns and new architecture
2. **Documentation**: Comprehensive examples and usage patterns
3. **Phased Migration**: Gradual rollout with validation at each step
4. **Backward Compatibility**: Maintain old interface during transition
5. **Code Reviews**: Ensure correct usage of new patterns

## Alternatives Considered

### Alternative 1: Keep Current Implementation
**Rejected because:**
- Technical debt continues to accumulate
- Performance and reliability issues persist
- Development velocity decreases over time

### Alternative 2: Use an ORM (e.g., PynamoDB)
**Rejected because:**
- Adds external dependency and complexity
- DynamoDB doesn't map well to traditional ORMs
- Boto3 is adequate for our needs
- Migration would be more complex

### Alternative 3: Service Layer Without Decorators
**Rejected because:**
- Doesn't eliminate code duplication as effectively
- Still requires manual error handling in each function
- Doesn't provide composability benefits
- Harder to add cross-cutting concerns

### Alternative 4: Complete Rewrite
**Rejected because:**
- Too risky (potential data loss)
- Longer timeline (2-3 months vs 5 weeks)
- Harder to validate correctness

## Implementation Notes

- See `docs/impl-log/db-utils-refactoring.md` for detailed migration plan
- Migration should be done in phases with validation
- Shadow mode deployment recommended for risk mitigation
- Success metrics defined in implementation plan

## References

- Full implementation plan: `docs/impl-log/db-utils-refactoring.md`
- DynamoDB Best Practices: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- Python Decorators (PEP 318): https://peps.python.org/pep-0318/

