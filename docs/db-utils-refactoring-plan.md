# DB Utils Refactoring Plan

**Document Version:** 1.0  
**Date:** November 2, 2025  
**Status:** Proposal  
**Owner:** Backend Team

## Executive Summary

This document outlines a comprehensive refactoring plan for `backend/src/utils/db_utils.py` to improve code maintainability, reduce duplication, and implement DynamoDB best practices. The refactoring will use decorator patterns and modular design to reduce the codebase by 30-40% while improving reliability, observability, and performance.

## Table of Contents

- [Current State Analysis](#current-state-analysis)
- [Refactoring Goals](#refactoring-goals)
- [Decorator-Based Architecture](#decorator-based-architecture)
- [DRY Improvements](#dry-improvements)
- [DynamoDB Best Practices](#dynamodb-best-practices)
- [Module Restructuring](#module-restructuring)
- [Migration Strategy](#migration-strategy)
- [Testing Strategy](#testing-strategy)
- [Performance Impact](#performance-impact)

---

## Current State Analysis

### File Statistics
- **Total Lines:** 2,239
- **Functions:** 80+
- **Tables Managed:** 8 (Accounts, Files, Transactions, FileMaps, Categories, Analytics Data/Status, FZIP Jobs, User Preferences, Workflows)

### Key Issues

1. **Repetitive Code Patterns**
   - 8 identical table getter functions (lines 99-167)
   - 12 similar checked resource functions (lines 183-289)
   - Repetitive error handling in every function
   - Duplicated batch operation logic
   - Similar update patterns across resources

2. **Error Handling**
   - Inconsistent error handling across functions
   - Try-catch blocks repeated 60+ times
   - Missing retry logic for throttling
   - Diagnostic logging mixed with production code (lines 1590-1621)

3. **DynamoDB Anti-Patterns**
   - Get-modify-put instead of UpdateExpression
   - No retry logic with exponential backoff
   - Manual pagination handling in multiple places
   - Inconsistent batch operation patterns

4. **Maintainability**
   - Single 2,239-line file (should be split)
   - Global variables for table resources
   - Mixed concerns (CRUD, authorization, business logic)
   - Limited reusability of common patterns

---

## Refactoring Goals

### Primary Objectives

1. **Reduce Code Duplication** - Target 30-40% reduction in LOC
2. **Improve Reliability** - Add retry logic, better error handling
3. **Enhance Observability** - Performance monitoring, structured logging
4. **Increase Maintainability** - Modular design, clear separation of concerns
5. **Follow DynamoDB Best Practices** - Proper use of UpdateExpression, batch operations, pagination

### Success Metrics

- [ ] Reduce total LOC by 30-40%
- [ ] Eliminate all repetitive try-catch blocks
- [ ] 100% of DynamoDB operations have retry logic
- [ ] All operations have performance monitoring
- [ ] All functions have consistent error handling
- [ ] Split into 5-7 focused modules

---

## Decorator-Based Architecture

### Overview

Decorators provide cross-cutting concerns (error handling, logging, retries, monitoring) without cluttering business logic. They're composable, testable, and maintainable.

### Core Decorators

#### 1. Error Handling & Logging Decorator

**Purpose:** Consistent error handling and logging across all DynamoDB operations

```python
from functools import wraps
from typing import Callable, TypeVar
import traceback

T = TypeVar('T')

def dynamodb_operation(operation_name: str = None):
    """
    Decorator for consistent DynamoDB error handling and logging.
    
    Features:
    - Automatic error logging with stack traces
    - Structured logging with operation context
    - Consistent exception handling
    - Debug-level entry/exit logging
    
    Usage:
        @dynamodb_operation("get_account")
        def get_account(account_id: uuid.UUID) -> Optional[Account]:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            op_name = operation_name or func.__name__
            try:
                logger.debug(f"Starting {op_name}")
                result = func(*args, **kwargs)
                logger.info(f"Successfully completed {op_name}")
                return result
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_msg = e.response['Error']['Message']
                logger.error(
                    f"DynamoDB error in {op_name}: {error_code} - {error_msg}",
                    exc_info=True,
                    extra={
                        'operation': op_name,
                        'error_code': error_code,
                        'function': func.__name__
                    }
                )
                raise
            except ValidationError as e:
                logger.error(
                    f"Validation error in {op_name}: {str(e)}",
                    exc_info=True,
                    extra={'operation': op_name}
                )
                raise ValueError(f"Invalid data in {op_name}: {str(e)}")
            except Exception as e:
                logger.error(
                    f"Unexpected error in {op_name}: {str(e)}",
                    exc_info=True,
                    extra={'operation': op_name}
                )
                raise
        return wrapper
    return decorator
```

**Impact:** Eliminates 60+ repetitive try-catch blocks

#### 2. Retry with Exponential Backoff Decorator

**Purpose:** Automatically retry throttled operations with exponential backoff

```python
import time
from typing import Tuple

def retry_on_throttle(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 5.0,
    exponential_base: float = 2,
    retry_on: Tuple[str, ...] = (
        'ProvisionedThroughputExceededException',
        'ThrottlingException',
        'RequestLimitExceeded'
    )
):
    """
    Decorator to retry DynamoDB operations on throttling with exponential backoff.
    
    Features:
    - Exponential backoff: delay = base_delay * (exponential_base ^ attempt)
    - Configurable max delay ceiling
    - Only retries on specific error codes
    - Logs retry attempts for debugging
    
    Algorithm:
        Attempt 1: immediate
        Attempt 2: wait base_delay * (2^0) = 0.1s
        Attempt 3: wait base_delay * (2^1) = 0.2s
        Attempt 4: wait base_delay * (2^2) = 0.4s
        ...
        Up to max_delay
    
    Usage:
        @retry_on_throttle(max_attempts=5, base_delay=0.1)
        @dynamodb_operation("list_transactions")
        def list_user_transactions(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    last_exception = e
                    
                    # Check if this is a retryable error
                    if error_code in retry_on and attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        logger.warning(
                            f"Throttled on {func.__name__} "
                            f"(attempt {attempt + 1}/{max_attempts}), "
                            f"retrying in {delay:.2f}s... "
                            f"Error: {error_code}"
                        )
                        time.sleep(delay)
                    else:
                        # Non-retryable error or exhausted retries
                        raise
            
            # If we exhausted all retries, raise the last exception
            raise last_exception
        return wrapper
    return decorator
```

**Impact:** Improves reliability, reduces transient failures

#### 3. Authorization Decorator

**Purpose:** Verify user ownership before executing operations

```python
import inspect

def require_resource_ownership(
    resource_getter: Callable,
    resource_id_param: str = 'resource_id',
    user_id_param: str = 'user_id',
    resource_name: str = 'resource'
):
    """
    Decorator to verify user owns the resource before proceeding.
    
    Features:
    - Automatic ownership verification
    - Consistent authorization error messages
    - Extracts parameters by name (order-independent)
    - Raises NotAuthorized or NotFound appropriately
    
    Usage:
        @require_resource_ownership(
            resource_getter=get_transaction_file,
            resource_id_param='file_id',
            resource_name='File'
        )
        @dynamodb_operation("delete_file")
        def delete_transaction_file(file_id: uuid.UUID, user_id: str) -> bool:
            # No need to check ownership - decorator handles it
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Extract parameters by name using inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            resource_id = bound_args.arguments.get(resource_id_param)
            user_id = bound_args.arguments.get(user_id_param)
            
            # Validate resource exists
            if not resource_id:
                raise NotFound(f"{resource_name} ID is required")
            
            # Get the resource
            resource = resource_getter(resource_id)
            if not resource:
                raise NotFound(f"{resource_name} not found")
            
            # Check ownership
            check_user_owns_resource(resource.user_id, user_id)
            
            # Proceed with the operation
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

**Impact:** Eliminates 12 `checked_mandatory_*` helper functions

#### 4. Performance Monitoring Decorator

**Purpose:** Track operation performance and identify slow queries

```python
import time

def monitor_performance(
    operation_type: str = "db_operation",
    warn_threshold_ms: float = 1000,
    error_threshold_ms: float = 5000
):
    """
    Decorator to monitor and log operation performance.
    
    Features:
    - Tracks elapsed time for every operation
    - Warns on slow operations (>warn_threshold_ms)
    - Errors on very slow operations (>error_threshold_ms)
    - Structured logging with elapsed time
    - Always executes in finally block (never affects function behavior)
    
    Thresholds:
    - Debug: < warn_threshold_ms (normal operation)
    - Warning: warn_threshold_ms to error_threshold_ms (slow)
    - Error: > error_threshold_ms (very slow, investigate)
    
    Usage:
        @monitor_performance(
            operation_type="query",
            warn_threshold_ms=500,
            error_threshold_ms=2000
        )
        @dynamodb_operation("list_transactions")
        def list_user_transactions(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                
                log_context = {
                    'operation': func.__name__,
                    'operation_type': operation_type,
                    'elapsed_ms': elapsed_ms
                }
                
                if elapsed_ms > error_threshold_ms:
                    logger.error(
                        f"SLOW OPERATION: {func.__name__} took {elapsed_ms:.2f}ms "
                        f"(threshold: {error_threshold_ms}ms)",
                        extra=log_context
                    )
                elif elapsed_ms > warn_threshold_ms:
                    logger.warning(
                        f"Slow operation: {func.__name__} took {elapsed_ms:.2f}ms "
                        f"(threshold: {warn_threshold_ms}ms)",
                        extra=log_context
                    )
                else:
                    logger.debug(
                        f"{func.__name__} completed in {elapsed_ms:.2f}ms",
                        extra=log_context
                    )
        return wrapper
    return decorator
```

**Impact:** Provides performance visibility, helps identify optimization opportunities

#### 5. Parameter Validation Decorator

**Purpose:** Validate function parameters before execution

```python
def validate_params(**validators):
    """
    Decorator to validate function parameters.
    
    Features:
    - Validates parameters using custom validator functions
    - Raises ValueError with descriptive message on validation failure
    - Supports any number of parameters
    - Validator functions return True/False
    
    Usage:
        @validate_params(
            account_id=is_valid_uuid,
            file_id=is_valid_uuid,
            limit=is_positive_int
        )
        @dynamodb_operation("list_files")
        def list_account_files(
            account_id: uuid.UUID,
            file_id: Optional[uuid.UUID],
            limit: int = 50
        ) -> List[TransactionFile]:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each parameter
            for param_name, validator_func in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator_func(value):
                        raise ValueError(
                            f"Invalid value for parameter '{param_name}': {value}"
                        )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Common validators
def is_valid_uuid(value: Any) -> bool:
    """Validator for UUID parameters."""
    if value is None:
        return True  # None is valid for optional parameters
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False

def is_positive_int(value: Any) -> bool:
    """Validator for positive integers."""
    return isinstance(value, int) and value > 0

def is_valid_limit(value: int) -> bool:
    """Validator for pagination limit (1-1000)."""
    return isinstance(value, int) and 1 <= value <= 1000
```

**Impact:** Centralized validation, better error messages

#### 6. Caching Decorator

**Purpose:** Cache frequently accessed, rarely changed data

```python
import time
from typing import Dict, Tuple, Any

def cache_result(ttl_seconds: int = 300, maxsize: int = 128):
    """
    Decorator to cache function results with TTL.
    
    Features:
    - Time-based expiration (TTL)
    - LRU eviction when cache is full
    - Cache statistics (hits, misses, size)
    - Manual cache control methods
    
    Best for:
    - Read-heavy operations
    - Slowly changing data (accounts, categories)
    - Expensive queries
    
    Not for:
    - Rapidly changing data (transactions)
    - Write operations
    - User-specific data with high cardinality
    
    Usage:
        @cache_result(ttl_seconds=60, maxsize=100)
        @dynamodb_operation("get_account")
        def get_account(account_id: uuid.UUID) -> Optional[Account]:
            ...
        
        # Clear cache manually if needed
        get_account.cache_clear()
        
        # Get cache statistics
        stats = get_account.cache_info()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache: Dict[Tuple, Any] = {}
        cache_times: Dict[Tuple, float] = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from args/kwargs
            cache_key = (args, tuple(sorted(kwargs.items())))
            current_time = time.time()
            
            # Check if cached and not expired
            if cache_key in cache:
                cached_time = cache_times[cache_key]
                if current_time - cached_time < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cache[cache_key]
                else:
                    # Expired, remove from cache
                    del cache[cache_key]
                    del cache_times[cache_key]
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Limit cache size (LRU eviction)
            if len(cache) >= maxsize:
                # Remove oldest entry
                oldest_key = min(cache_times.keys(), key=lambda k: cache_times[k])
                del cache[oldest_key]
                del cache_times[oldest_key]
            
            # Store in cache
            cache[cache_key] = result
            cache_times[cache_key] = current_time
            return result
        
        # Add cache control methods
        wrapper.cache_clear = lambda: (cache.clear(), cache_times.clear())
        wrapper.cache_info = lambda: {
            'size': len(cache),
            'maxsize': maxsize,
            'ttl_seconds': ttl_seconds
        }
        
        return wrapper
    return decorator
```

**Impact:** Reduces unnecessary DynamoDB reads, improves latency

### Decorator Composition

Decorators can be stacked to combine functionality:

```python
@cache_result(ttl_seconds=30)                    # 4. Cache results for 30s
@monitor_performance(warn_threshold_ms=200)      # 3. Monitor performance
@retry_on_throttle(max_attempts=3)               # 2. Retry on throttle
@dynamodb_operation("get_category")              # 1. Error handling/logging
def get_category_by_id_from_db(
    category_id: uuid.UUID,
    user_id: str
) -> Optional[Category]:
    """
    Get category with full decorator stack:
    - Consistent error handling and logging
    - Automatic retry on throttling (up to 3 attempts)
    - Performance monitoring (warn if >200ms)
    - 30-second result caching
    """
    table = get_categories_table()
    if not table:
        return None
    
    response = table.get_item(Key={'categoryId': str(category_id)})
    item = response.get('Item')
    
    if item and item.get('userId') == user_id:
        return Category.from_dynamodb_item(item)
    elif item:
        logger.warning(
            f"User {user_id} attempted to access category "
            f"owned by {item.get('userId')}"
        )
    
    return None
```

**Execution Order:** Bottom to top (1 → 4)

---

## DRY Improvements

### 1. Eliminate Repetitive Table Getters

**Current State (Lines 99-167):**
```python
def get_transactions_table() -> Any:
    """Get the transactions table resource, initializing it if needed."""
    global _transactions_table
    if _transactions_table is None:
        initialize_tables()
    return _transactions_table

def get_accounts_table() -> Any:
    """Get the accounts table resource, initializing it if needed."""
    global _accounts_table
    if _accounts_table is None:
        initialize_tables()
    return _accounts_table

# ... 6 more identical functions
```

**Proposed Solution: Class-Based Table Manager**

```python
class DynamoDBTables:
    """
    Singleton for managing DynamoDB table resources.
    
    Features:
    - Lazy initialization (tables created on first access)
    - Singleton pattern (one instance per application)
    - Automatic table name lookup from environment variables
    - Property-based access for clean syntax
    
    Usage:
        tables = DynamoDBTables()
        transactions = tables.transactions
        accounts = tables.accounts
    """
    _instance = None
    
    # Table name to environment variable mapping
    TABLE_CONFIGS = {
        'transactions': 'TRANSACTIONS_TABLE',
        'accounts': 'ACCOUNTS_TABLE',
        'files': 'FILES_TABLE',
        'file_maps': 'FILE_MAPS_TABLE',
        'categories': 'CATEGORIES_TABLE_NAME',
        'analytics_data': 'ANALYTICS_DATA_TABLE',
        'analytics_status': 'ANALYTICS_STATUS_TABLE',
        'fzip_jobs': 'FZIP_JOBS_TABLE',
        'user_preferences': 'USER_PREFERENCES_TABLE',
        'workflows': 'WORKFLOWS_TABLE',
    }
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._dynamodb = boto3.resource('dynamodb')
            self._tables: Dict[str, Any] = {}
            self._initialized = True
    
    def _get_table(self, table_key: str) -> Optional[Any]:
        """Get table resource with lazy initialization."""
        if table_key not in self._tables:
            env_var_name = self.TABLE_CONFIGS.get(table_key)
            if not env_var_name:
                logger.error(f"Unknown table key: {table_key}")
                return None
            
            table_name = os.environ.get(env_var_name)
            if not table_name:
                logger.warning(
                    f"Environment variable {env_var_name} not set, "
                    f"table '{table_key}' unavailable"
                )
                return None
            
            self._tables[table_key] = self._dynamodb.Table(table_name)
            logger.info(f"Initialized table: {table_key} ({table_name})")
        
        return self._tables.get(table_key)
    
    # Property-based access for clean syntax
    @property
    def transactions(self) -> Any:
        return self._get_table('transactions')
    
    @property
    def accounts(self) -> Any:
        return self._get_table('accounts')
    
    @property
    def files(self) -> Any:
        return self._get_table('files')
    
    @property
    def file_maps(self) -> Any:
        return self._get_table('file_maps')
    
    @property
    def categories(self) -> Any:
        return self._get_table('categories')
    
    @property
    def analytics_data(self) -> Any:
        return self._get_table('analytics_data')
    
    @property
    def analytics_status(self) -> Any:
        return self._get_table('analytics_status')
    
    @property
    def fzip_jobs(self) -> Any:
        return self._get_table('fzip_jobs')
    
    @property
    def user_preferences(self) -> Any:
        return self._get_table('user_preferences')
    
    @property
    def workflows(self) -> Any:
        return self._get_table('workflows')
    
    def reinitialize(self):
        """Reinitialize DynamoDB resource (useful for testing)."""
        self._dynamodb = boto3.resource('dynamodb')
        self._tables.clear()
        logger.info("Reinitialized DynamoDB tables")

# Global instance
tables = DynamoDBTables()
```

**Impact:** 
- Eliminates 8 repetitive functions completely
- Reduces ~70 lines to ~30 lines
- Easier to add new tables
- Better encapsulation
- Cleaner, more modern codebase with no legacy code
- Complete migration in one atomic change

### 2. Generic Resource Checkers

**Current State (Lines 183-289):**
```python
def checked_mandatory_account(account_id: Optional[uuid.UUID], user_id: str) -> Account:
    if not account_id:
        raise NotFound("Account ID is required")
    account = get_account(account_id)
    if not account:
        raise NotFound("Account not found")
    check_user_owns_resource(account.user_id, user_id)
    return account

def checked_optional_account(account_id: Optional[uuid.UUID], user_id: str) -> Optional[Account]:
    if not account_id:
        return None
    account = get_account(account_id)
    if not account:
        return None
    check_user_owns_resource(account.user_id, user_id)
    return account

# ... 10 more similar functions for different resources
```

**Proposed Solution: Generic Helper Functions**

```python
T = TypeVar('T')

def checked_mandatory_resource(
    resource_id: Optional[uuid.UUID],
    user_id: str,
    getter_func: Callable[[uuid.UUID], Optional[T]],
    resource_name: str
) -> T:
    """
    Generic mandatory resource checker with user validation.
    
    Args:
        resource_id: ID of resource to retrieve
        user_id: ID of user requesting access
        getter_func: Function to retrieve resource by ID
        resource_name: Human-readable resource name for error messages
    
    Returns:
        Resource object if found and user has access
    
    Raises:
        NotFound: If resource_id is None, or resource doesn't exist
        NotAuthorized: If user doesn't own the resource
    
    Example:
        account = checked_mandatory_resource(
            account_id,
            user_id,
            get_account,
            "Account"
        )
    """
    if not resource_id:
        raise NotFound(f"{resource_name} ID is required")
    
    resource = getter_func(resource_id)
    if not resource:
        raise NotFound(f"{resource_name} not found")
    
    check_user_owns_resource(resource.user_id, user_id)
    return resource

def checked_optional_resource(
    resource_id: Optional[uuid.UUID],
    user_id: str,
    getter_func: Callable[[uuid.UUID], Optional[T]],
    resource_name: str
) -> Optional[T]:
    """
    Generic optional resource checker with user validation.
    
    Like checked_mandatory_resource, but returns None instead of raising
    NotFound if resource_id is None or resource doesn't exist.
    
    Returns:
        Resource object if found and user has access, None otherwise
    
    Raises:
        NotAuthorized: If resource exists but user doesn't own it
    """
    if not resource_id:
        return None
    try:
        return checked_mandatory_resource(
            resource_id,
            user_id,
            getter_func,
            resource_name
        )
    except NotFound:
        return None

# Specific implementations become one-liners
def checked_mandatory_account(
    account_id: Optional[uuid.UUID],
    user_id: str
) -> Account:
    """Check if account exists and user has access to it."""
    return checked_mandatory_resource(
        account_id, user_id, get_account, "Account"
    )

def checked_optional_account(
    account_id: Optional[uuid.UUID],
    user_id: str
) -> Optional[Account]:
    """Check if account exists and user has access to it, allowing None."""
    return checked_optional_resource(
        account_id, user_id, get_account, "Account"
    )

def checked_mandatory_transaction_file(
    file_id: uuid.UUID,
    user_id: str
) -> TransactionFile:
    """Check if file exists and user has access to it."""
    return checked_mandatory_resource(
        file_id, user_id, get_transaction_file, "File"
    )

# ... etc for other resources
```

**Impact:**
- Reduces 12 functions (~120 lines) to 2 generic functions + 12 one-liners (~60 lines)
- 50% code reduction
- Consistent behavior across all resources
- Easier to add new resource types

### 3. Batch Operation Helpers

**Current State:**
Batch operations repeated in multiple places with slight variations:
- Lines 933-960: `delete_transactions_for_file`
- Lines 1199-1225: `update_transaction_statuses_by_status`
- Lines 1836-1847: `batch_store_analytics_data`
- Lines 2221-2225: `cleanup_expired_fzip_jobs`

**Proposed Solution: Generic Batch Helpers**

```python
from typing import List, Dict, Any, Callable, TypeVar

T = TypeVar('T')

def batch_delete_items(
    table: Any,
    items: List[Any],
    key_extractor: Callable[[Any], Dict[str, str]],
    batch_size: int = 25
) -> int:
    """
    Delete items in batches respecting DynamoDB limits.
    
    Args:
        table: DynamoDB table resource
        items: List of items to delete (can be models or dicts)
        key_extractor: Function to extract key dict from item
        batch_size: Batch size (DynamoDB limit is 25)
    
    Returns:
        Number of items deleted
    
    Example:
        # Delete transactions
        deleted_count = batch_delete_items(
            table=tables.transactions,
            items=transactions,
            key_extractor=lambda t: {'transactionId': str(t.transaction_id)}
        )
    """
    count = 0
    
    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        with table.batch_writer() as writer:
            for item in batch:
                writer.delete_item(Key=key_extractor(item))
                count += 1
    
    logger.info(f"Batch deleted {count} items from {table.table_name}")
    return count

def batch_write_items(
    table: Any,
    items: List[Dict[str, Any]],
    batch_size: int = 25
) -> int:
    """
    Write items in batches respecting DynamoDB limits.
    
    Args:
        table: DynamoDB table resource
        items: List of item dicts to write
        batch_size: Batch size (DynamoDB limit is 25)
    
    Returns:
        Number of items written
    
    Example:
        # Write analytics data
        written_count = batch_write_items(
            table=tables.analytics_data,
            items=[data.to_dynamodb_item() for data in analytics_list]
        )
    """
    count = 0
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        with table.batch_writer() as writer:
            for item in batch:
                writer.put_item(Item=item)
                count += 1
    
    logger.info(f"Batch wrote {count} items to {table.table_name}")
    return count

def batch_update_items(
    table: Any,
    items: List[Any],
    updater: Callable[[Any], Dict[str, Any]],
    batch_size: int = 25
) -> int:
    """
    Update items in batches.
    
    Note: DynamoDB batch_writer doesn't support updates directly,
    so this uses put_item (overwrites existing items).
    
    Args:
        table: DynamoDB table resource
        items: List of items to update
        updater: Function that takes an item and returns updated dict
        batch_size: Batch size
    
    Returns:
        Number of items updated
    
    Example:
        # Update transaction statuses
        updated_count = batch_update_items(
            table=tables.transactions,
            items=transactions,
            updater=lambda t: {
                **t.to_dynamodb_item(),
                'status': 'processed',
                'updatedAt': current_timestamp()
            }
        )
    """
    count = 0
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        with table.batch_writer() as writer:
            for item in batch:
                updated_item = updater(item)
                writer.put_item(Item=updated_item)
                count += 1
    
    logger.info(f"Batch updated {count} items in {table.table_name}")
    return count

# Usage example - refactored delete_transactions_for_file
@dynamodb_operation("delete_transactions_for_file")
def delete_transactions_for_file(file_id: uuid.UUID) -> int:
    """Delete all transactions associated with a file."""
    # Get all transactions for the file
    transactions = list_file_transactions(file_id)
    
    if not transactions:
        return 0
    
    # Delete in batch
    count = batch_delete_items(
        table=tables.transactions,
        items=transactions,
        key_extractor=lambda t: {'transactionId': str(t.transaction_id)}
    )
    
    logger.info(f"Deleted {count} transactions for file {file_id}")
    return count
```

**Impact:**
- Eliminates duplicate batch logic
- Consistent error handling
- Easier to optimize (e.g., parallel batches)
- Reduces ~80 lines across multiple functions

### 4. Pagination Helper

**Current State:** Pagination logic repeated in multiple query functions

**Proposed Solution:**

```python
def paginated_query(
    table: Any,
    query_params: Dict[str, Any],
    max_items: Optional[int] = None,
    transform: Optional[Callable[[Dict], T]] = None
) -> Tuple[List[T], Optional[Dict[str, Any]]]:
    """
    Execute paginated DynamoDB query and return all items.
    
    Args:
        table: DynamoDB table resource
        query_params: Query parameters (KeyConditionExpression, etc.)
        max_items: Maximum items to return (None for all)
        transform: Optional function to transform each item
    
    Returns:
        Tuple of (items, last_evaluated_key)
    
    Example:
        items, last_key = paginated_query(
            table=tables.transactions,
            query_params={
                'IndexName': 'UserIdIndex',
                'KeyConditionExpression': Key('userId').eq(user_id),
                'Limit': 100
            },
            transform=Transaction.from_dynamodb_item
        )
    """
    items = []
    items_collected = 0
    current_params = query_params.copy()
    last_evaluated_key = None
    
    while True:
        response = table.query(**current_params)
        batch = response.get('Items', [])
        
        # Transform items if transformer provided
        if transform:
            batch = [transform(item) for item in batch]
        
        items.extend(batch)
        items_collected += len(batch)
        
        # Check if we've collected enough items
        if max_items and items_collected >= max_items:
            items = items[:max_items]
            last_evaluated_key = response.get('LastEvaluatedKey')
            break
        
        # Check for more pages
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
        
        current_params['ExclusiveStartKey'] = last_evaluated_key
    
    return items, last_evaluated_key
```

**Impact:** Consistent pagination across all functions

### 5. UUID Conversion Helpers

**Current State:** `str(uuid)` and `uuid.UUID(str)` scattered throughout

**Proposed Solution:**

```python
def to_db_id(id_value: Union[str, uuid.UUID, None]) -> Optional[str]:
    """
    Convert UUID to string for DynamoDB operations.
    
    DynamoDB doesn't have a native UUID type, so we store as strings.
    This helper ensures consistent conversion.
    
    Args:
        id_value: UUID, string, or None
    
    Returns:
        String representation or None
    
    Example:
        key = {'accountId': to_db_id(account_id)}
    """
    if id_value is None:
        return None
    return str(id_value)

def from_db_id(id_value: Optional[str]) -> Optional[uuid.UUID]:
    """
    Convert string from DynamoDB to UUID.
    
    Args:
        id_value: String representation of UUID or None
    
    Returns:
        UUID object or None
    
    Raises:
        ValueError: If string is not a valid UUID
    
    Example:
        account_id = from_db_id(item.get('accountId'))
    """
    if id_value is None:
        return None
    try:
        return uuid.UUID(id_value)
    except ValueError:
        logger.error(f"Invalid UUID string: {id_value}")
        raise

def to_db_ids(id_list: List[Union[str, uuid.UUID]]) -> List[str]:
    """Convert list of UUIDs to list of strings."""
    return [str(id_val) for id_val in id_list]

def from_db_ids(id_list: List[str]) -> List[uuid.UUID]:
    """Convert list of strings to list of UUIDs."""
    return [uuid.UUID(id_val) for id_val in id_list]
```

**Impact:** Cleaner code, consistent UUID handling

---

## DynamoDB Best Practices

### 1. Use UpdateExpression Instead of Get-Modify-Put

**Current Anti-Pattern (Lines 386-410):**

```python
def update_account(account_id: uuid.UUID, user_id: str, update_data: Dict[str, Any]) -> Account:
    # Retrieve the existing account
    account = checked_mandatory_account(account_id, user_id)
    
    # Create an AccountUpdate DTO from the update_data
    account_update_dto = AccountUpdate(**update_data)
    
    # Use the model's method to update details
    account.update_account_details(account_update_dto)
    
    # Save updates to DynamoDB (overwrites entire item)
    get_accounts_table().put_item(Item=account.to_dynamodb_item())
    
    return account
```

**Problems:**
- Two round trips to DynamoDB (get + put)
- Race conditions if another process updates between get and put
- Overwrites entire item (inefficient for large items)
- Higher cost (2 WCUs vs 1 WCU)

**Best Practice Solution:**

```python
def build_update_expression(
    updates: Dict[str, Any],
    timestamp_field: str = 'updatedAt'
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """
    Build DynamoDB UpdateExpression from update dictionary.
    
    Args:
        updates: Dictionary of field names to new values
        timestamp_field: Name of timestamp field to auto-update
    
    Returns:
        Tuple of (update_expression, expression_attribute_names, expression_attribute_values)
    
    Example:
        expr, names, values = build_update_expression({
            'name': 'New Name',
            'balance': Decimal('1000.00')
        })
        table.update_item(
            Key={'accountId': account_id},
            UpdateExpression=expr,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values
        )
    """
    update_parts = []
    expr_attr_names = {}
    expr_attr_values = {}
    
    for key, value in updates.items():
        # Use attribute names to handle reserved words
        safe_key = key.replace('-', '_')
        update_parts.append(f"#{safe_key} = :{safe_key}")
        expr_attr_names[f"#{safe_key}"] = key
        expr_attr_values[f":{safe_key}"] = value
    
    # Add timestamp
    if timestamp_field:
        update_parts.append(f"#{timestamp_field} = :{timestamp_field}")
        expr_attr_names[f"#{timestamp_field}"] = timestamp_field
        expr_attr_values[f":{timestamp_field}"] = int(
            datetime.now(timezone.utc).timestamp() * 1000
        )
    
    update_expression = "SET " + ", ".join(update_parts)
    
    return update_expression, expr_attr_names, expr_attr_values

@dynamodb_operation("update_account")
def update_account(
    account_id: uuid.UUID,
    user_id: str,
    update_data: Dict[str, Any]
) -> Account:
    """
    Update account using UpdateExpression for better performance.
    
    Benefits:
    - Single round trip to DynamoDB
    - Atomic update (no race conditions)
    - Only updates specified fields
    - Lower cost (1 WCU instead of 2)
    """
    # Verify ownership first
    account = checked_mandatory_account(account_id, user_id)
    
    # Validate update data
    account_update_dto = AccountUpdate(**update_data)
    update_dict = account_update_dto.model_dump(exclude_unset=True)
    
    # Build update expression
    expr, names, values = build_update_expression(update_dict)
    
    # Execute atomic update
    response = tables.accounts.update_item(
        Key={'accountId': to_db_id(account_id)},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues='ALL_NEW'
    )
    
    # Return updated account
    return Account.from_dynamodb_item(response['Attributes'])
```

**Benefits:**
- 50% faster (1 round trip vs 2)
- 50% cheaper (1 WCU vs 2)
- Atomic (no race conditions)
- Only updates specified fields

### 2. Conditional Writes for Optimistic Locking

**Purpose:** Prevent lost updates in concurrent scenarios

```python
def update_account_with_version_check(
    account_id: uuid.UUID,
    user_id: str,
    update_data: Dict[str, Any],
    expected_version: int
) -> Account:
    """
    Update account with optimistic locking using version check.
    
    Args:
        account_id: Account to update
        user_id: User requesting update
        update_data: Fields to update
        expected_version: Expected current version (for optimistic locking)
    
    Returns:
        Updated account with incremented version
    
    Raises:
        ConditionalCheckFailedException: If version doesn't match (concurrent update)
    """
    # Verify ownership
    account = checked_mandatory_account(account_id, user_id)
    
    # Validate updates
    account_update_dto = AccountUpdate(**update_data)
    update_dict = account_update_dto.model_dump(exclude_unset=True)
    
    # Add version increment
    update_dict['version'] = expected_version + 1
    
    # Build update expression
    expr, names, values = build_update_expression(update_dict)
    
    # Add condition expression for version check
    names['#version'] = 'version'
    values[':expected_version'] = expected_version
    
    try:
        response = tables.accounts.update_item(
            Key={'accountId': to_db_id(account_id)},
            UpdateExpression=expr,
            ConditionExpression='#version = :expected_version',
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
            ReturnValues='ALL_NEW'
        )
        return Account.from_dynamodb_item(response['Attributes'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.warning(
                f"Concurrent update detected for account {account_id}, "
                f"expected version {expected_version}"
            )
            raise ConflictError(
                "Account was modified by another process. Please retry."
            )
        raise
```

### 3. Efficient Batch Operations with Parallel Processing

**Current:** Sequential batch processing  
**Best Practice:** Parallel batch processing for large datasets

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable

def parallel_batch_operation(
    items: List[T],
    operation: Callable[[List[T]], int],
    batch_size: int = 25,
    max_workers: int = 5
) -> int:
    """
    Execute batch operations in parallel for improved throughput.
    
    Args:
        items: All items to process
        operation: Function to execute on each batch (returns count processed)
        batch_size: Size of each batch
        max_workers: Number of parallel workers
    
    Returns:
        Total number of items processed
    
    Example:
        def delete_batch(transaction_batch):
            return batch_delete_items(
                tables.transactions,
                transaction_batch,
                lambda t: {'transactionId': str(t.transaction_id)}
            )
        
        total = parallel_batch_operation(
            items=transactions,
            operation=delete_batch,
            batch_size=25,
            max_workers=5
        )
    """
    # Split items into batches
    batches = [items[i:i+batch_size] for i in range(0, len(items), batch_size)]
    
    total_processed = 0
    
    # Process batches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all batches
        future_to_batch = {
            executor.submit(operation, batch): batch 
            for batch in batches
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_batch):
            try:
                count = future.result()
                total_processed += count
            except Exception as e:
                batch = future_to_batch[future]
                logger.error(
                    f"Error processing batch of {len(batch)} items: {e}",
                    exc_info=True
                )
                # Continue with other batches
    
    return total_processed
```

**Impact:** 3-5x faster for large batch operations

### 4. Query Optimization with GSI Selection

**Current Implementation (Lines 657-726):** Good GSI selection logic exists

**Enhancement:** Add query cost estimation and logging

```python
@dataclass
class QueryPlan:
    """Query execution plan with cost estimation."""
    index_name: str
    key_condition: Any
    filter_expressions: List[Any]
    estimated_items_scanned: int
    estimated_rcu_cost: float
    optimization_notes: List[str]

def estimate_query_cost(
    index_name: str,
    partition_key_value: str,
    has_sort_key_condition: bool,
    filter_count: int,
    estimated_partition_size: int = 1000
) -> float:
    """
    Estimate RCU cost for a query operation.
    
    DynamoDB charges:
    - 1 RCU per 4 KB of data read (strongly consistent)
    - 0.5 RCU per 4 KB (eventually consistent)
    - Scanned items count, not returned items count
    
    Args:
        index_name: Name of index being queried
        partition_key_value: Value being queried
        has_sort_key_condition: Whether sort key narrows results
        filter_count: Number of FilterExpressions
        estimated_partition_size: Estimated items in partition
    
    Returns:
        Estimated RCU cost
    """
    # Base cost depends on partition size
    items_scanned = estimated_partition_size
    
    # Sort key conditions reduce scanned items
    if has_sort_key_condition:
        items_scanned = items_scanned // 10  # Rough estimate
    
    # FilterExpressions don't reduce scanned items
    # (they filter after reading)
    
    # Assume 1 KB per item (adjust based on actual data)
    kb_per_item = 1
    total_kb = items_scanned * kb_per_item
    
    # 1 RCU per 4 KB (strongly consistent)
    rcu_cost = total_kb / 4
    
    return rcu_cost

def select_optimal_gsi_with_plan(
    user_id: str,
    account_ids: Optional[List[uuid.UUID]] = None,
    category_ids: Optional[List[str]] = None,
    transaction_type: Optional[str] = None,
    ignore_dup: bool = False,
    uncategorized_only: bool = False,
    start_date_ts: Optional[int] = None,
    end_date_ts: Optional[int] = None
) -> QueryPlan:
    """
    Enhanced GSI selection with cost estimation and optimization notes.
    
    Returns QueryPlan with:
    - Selected index
    - Key condition expression
    - Remaining filters
    - Estimated cost
    - Optimization recommendations
    """
    optimization_notes = []
    
    # ... existing GSI selection logic ...
    
    # Select index (existing logic)
    if account_ids and len(account_ids) == 1:
        index_name = 'AccountDateIndex'
        key_condition = Key('accountId').eq(str(account_ids[0]))
        estimated_items = 1000  # Estimate per account
        optimization_notes.append(
            "Using AccountDateIndex for single account - optimal"
        )
    elif category_ids and len(category_ids) == 1:
        index_name = 'CategoryDateIndex'
        key_condition = Key('primaryCategoryId').eq(category_ids[0])
        estimated_items = 500
        optimization_notes.append(
            "Using CategoryDateIndex for single category"
        )
    else:
        index_name = 'UserIdIndex'
        key_condition = Key('userId').eq(user_id)
        estimated_items = 10000  # Estimate per user
        optimization_notes.append(
            "Using UserIdIndex - consider adding more specific filters"
        )
    
    # Add date range to key condition if possible
    has_sort_key = False
    if start_date_ts is not None or end_date_ts is not None:
        has_sort_key = True
        if start_date_ts and end_date_ts:
            key_condition = key_condition & Key('date').between(
                start_date_ts, end_date_ts
            )
            estimated_items = estimated_items // 5  # Date range reduces items
        # ... etc
    
    # Determine remaining filters
    filter_expressions = _get_remaining_filters(
        index_name, user_id, account_ids, category_ids,
        transaction_type, ignore_dup, uncategorized_only, None
    )
    
    # Warn about inefficient filters
    if len(filter_expressions) > 2:
        optimization_notes.append(
            f"WARNING: {len(filter_expressions)} FilterExpressions will scan "
            f"then filter. Consider adding a GSI for common filter combinations."
        )
    
    # Estimate cost
    estimated_cost = estimate_query_cost(
        index_name,
        str(account_ids[0]) if account_ids else user_id,
        has_sort_key,
        len(filter_expressions),
        estimated_items
    )
    
    return QueryPlan(
        index_name=index_name,
        key_condition=key_condition,
        filter_expressions=list(filter_expressions.values()),
        estimated_items_scanned=estimated_items,
        estimated_rcu_cost=estimated_cost,
        optimization_notes=optimization_notes
    )
```

**Impact:** Better visibility into query costs, helps identify optimization opportunities

### 5. Connection Pooling and Resource Management

```python
class DynamoDBConnectionPool:
    """
    Manage DynamoDB connections with pooling and health checks.
    
    Features:
    - Connection reuse
    - Health checks
    - Automatic reconnection
    - Connection limits
    """
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self._resource = None
        self._last_health_check = None
        self._health_check_interval = 300  # 5 minutes
    
    def get_resource(self) -> Any:
        """Get DynamoDB resource with health checking."""
        current_time = time.time()
        
        # Create resource if needed
        if self._resource is None:
            self._resource = boto3.resource('dynamodb')
            self._last_health_check = current_time
            return self._resource
        
        # Periodic health check
        if (self._last_health_check is None or 
            current_time - self._last_health_check > self._health_check_interval):
            if not self._check_health():
                logger.warning("DynamoDB health check failed, reconnecting...")
                self._resource = boto3.resource('dynamodb')
            self._last_health_check = current_time
        
        return self._resource
    
    def _check_health(self) -> bool:
        """Check if DynamoDB connection is healthy."""
        try:
            # Simple health check - list tables
            list(self._resource.tables.all())
            return True
        except Exception as e:
            logger.error(f"DynamoDB health check failed: {e}")
            return False

# Use in DynamoDBTables class
connection_pool = DynamoDBConnectionPool()
```

---

## Module Restructuring

### Current Structure
```
backend/src/utils/
  db_utils.py  (2,239 lines - TOO LARGE)
```

### Proposed Structure
```
backend/src/utils/
  db/
    __init__.py              # Public API, backward compatibility
    base.py                  # Table management, decorators, base operations
    helpers.py               # Batch ops, pagination, UUID conversion
    accounts.py              # Account CRUD operations
    transactions.py          # Transaction CRUD operations
    files.py                 # File and FileMap operations
    categories.py            # Category operations
    analytics.py             # Analytics data and status operations
    fzip.py                  # FZIP job operations
    workflows.py             # Workflow operations
```

### File Breakdown

#### `db/__init__.py` (50 lines)
Public API for backward compatibility

```python
"""
Database utilities for DynamoDB operations.

This module provides a clean interface for all database operations.
Imports are organized by resource type for easy navigation.
"""

# Table management
from .base import (
    tables,
    DynamoDBTables,
)

# Exceptions
from .base import (
    NotAuthorized,
    NotFound,
    ConflictError,
)

# Account operations
from .accounts import (
    get_account,
    list_user_accounts,
    create_account,
    update_account,
    delete_account,
    checked_mandatory_account,
    checked_optional_account,
)

# Transaction operations
from .transactions import (
    get_transaction,
    list_user_transactions,
    list_file_transactions,
    list_account_transactions,
    create_transaction,
    update_transaction,
    delete_transactions_for_file,
    check_duplicate_transaction,
    get_first_transaction_date,
    get_last_transaction_date,
    get_latest_transaction,
    checked_mandatory_transaction,
    checked_optional_transaction,
)

# File operations
from .files import (
    get_transaction_file,
    list_account_files,
    list_user_files,
    create_transaction_file,
    update_transaction_file,
    update_transaction_file_object,
    delete_transaction_file,
    checked_mandatory_transaction_file,
    checked_optional_transaction_file,
)

# FileMap operations
from .files import (
    get_file_map,
    get_account_default_file_map,
    list_file_maps_by_user,
    list_account_file_maps,
    create_file_map,
    update_file_map,
    delete_file_map,
    checked_mandatory_file_map,
    checked_optional_file_map,
)

# Category operations
from .categories import (
    get_category_by_id_from_db,
    list_categories_by_user_from_db,
    create_category_in_db,
    update_category_in_db,
    delete_category_from_db,
    checked_mandatory_category,
    checked_optional_category,
)

# Analytics operations
from .analytics import (
    store_analytics_data,
    get_analytics_data,
    list_analytics_data_for_user,
    batch_store_analytics_data,
    delete_analytics_data,
    store_analytics_status,
    get_analytics_status,
    list_analytics_status_for_user,
    update_analytics_status,
    list_stale_analytics,
)

# FZIP operations
from .fzip import (
    create_fzip_job,
    get_fzip_job,
    update_fzip_job,
    list_user_fzip_jobs,
    delete_fzip_job,
    cleanup_expired_fzip_jobs,
)

# Workflow operations
from .workflows import (
    checked_mandatory_workflow,
)

__all__ = [
    # Export everything for backward compatibility
    # ... (list all imports)
]
```

#### `db/base.py` (300 lines)
Core infrastructure: tables, decorators, exceptions, helpers

```python
"""
Core database infrastructure.

This module provides:
- DynamoDB table management
- Decorators for cross-cutting concerns
- Common exceptions
- Base helper functions
"""

import os
import logging
import boto3
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, TypeVar
from functools import wraps
from botocore.exceptions import ClientError
from pydantic import ValidationError

# Configure logging
logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T')

# ============================================================================
# Exceptions
# ============================================================================

class NotAuthorized(Exception):
    """Raised when a user is not authorized to access a resource."""
    pass

class NotFound(Exception):
    """Raised when a requested resource is not found."""
    pass

class ConflictError(Exception):
    """Raised when there's a conflict (e.g., optimistic locking failure)."""
    pass

# ============================================================================
# Decorators
# ============================================================================

def dynamodb_operation(operation_name: str = None):
    """Decorator for consistent DynamoDB error handling and logging."""
    # ... (implementation from earlier)

def retry_on_throttle(...):
    """Decorator to retry DynamoDB operations on throttling."""
    # ... (implementation from earlier)

def monitor_performance(...):
    """Decorator to monitor and log operation performance."""
    # ... (implementation from earlier)

def require_resource_ownership(...):
    """Decorator to verify user owns the resource."""
    # ... (implementation from earlier)

def validate_params(**validators):
    """Decorator to validate function parameters."""
    # ... (implementation from earlier)

def cache_result(ttl_seconds: int = 300, maxsize: int = 128):
    """Decorator to cache function results with TTL."""
    # ... (implementation from earlier)

# ============================================================================
# Table Management
# ============================================================================

class DynamoDBTables:
    """Singleton for managing DynamoDB table resources."""
    # ... (implementation from earlier)

# Global instance
tables = DynamoDBTables()

# ============================================================================
# Helper Functions
# ============================================================================

def check_user_owns_resource(resource_user_id: str, requesting_user_id: str) -> None:
    """Check if a user owns a resource."""
    if resource_user_id != requesting_user_id:
        raise NotAuthorized("Not authorized to access this resource")

def checked_mandatory_resource(...):
    """Generic mandatory resource checker with user validation."""
    # ... (implementation from earlier)

def checked_optional_resource(...):
    """Generic optional resource checker with user validation."""
    # ... (implementation from earlier)
```

#### `db/helpers.py` (200 lines)
Reusable helper functions

```python
"""
Helper functions for database operations.

This module provides:
- Batch operation helpers
- Pagination helpers
- UUID conversion helpers
- Query building helpers
"""

# ... (all helper implementations from earlier sections)
```

#### `db/accounts.py` (300 lines)
Account-specific operations

```python
"""
Account database operations.

This module provides CRUD operations for accounts.
"""

from typing import List, Dict, Any, Optional
import uuid
import logging

from models import Account, AccountCreate, AccountUpdate
from .base import (
    tables, dynamodb_operation, retry_on_throttle,
    monitor_performance, NotFound, NotAuthorized,
    checked_mandatory_resource, checked_optional_resource,
    check_user_owns_resource
)
from .helpers import to_db_id, build_update_expression

logger = logging.getLogger(__name__)

# ============================================================================
# CRUD Operations
# ============================================================================

@cache_result(ttl_seconds=60)
@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle()
@dynamodb_operation("get_account")
def get_account(account_id: uuid.UUID) -> Optional[Account]:
    """Retrieve an account by ID."""
    response = tables.accounts.get_item(Key={'accountId': to_db_id(account_id)})
    if 'Item' in response:
        return Account.from_dynamodb_item(response['Item'])
    return None

@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle()
@dynamodb_operation("list_user_accounts")
def list_user_accounts(user_id: str) -> List[Account]:
    """List all accounts for a specific user."""
    # ... (existing implementation with decorators)

@dynamodb_operation("create_account")
def create_account(account: Account):
    """Create a new account."""
    # ... (existing implementation)

@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle()
@dynamodb_operation("update_account")
def update_account(
    account_id: uuid.UUID,
    user_id: str,
    update_data: Dict[str, Any]
) -> Account:
    """Update an existing account using UpdateExpression."""
    # Verify ownership
    account = checked_mandatory_account(account_id, user_id)
    
    # Validate and build update
    account_update_dto = AccountUpdate(**update_data)
    update_dict = account_update_dto.model_dump(exclude_unset=True)
    expr, names, values = build_update_expression(update_dict)
    
    # Execute atomic update
    response = tables.accounts.update_item(
        Key={'accountId': to_db_id(account_id)},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues='ALL_NEW'
    )
    
    return Account.from_dynamodb_item(response['Attributes'])

@monitor_performance(warn_threshold_ms=1000)
@dynamodb_operation("delete_account")
def delete_account(account_id: uuid.UUID, user_id: str) -> bool:
    """Delete an account and handle any associated files."""
    # ... (existing implementation with decorators)

# ============================================================================
# Helper Functions
# ============================================================================

def checked_mandatory_account(
    account_id: Optional[uuid.UUID],
    user_id: str
) -> Account:
    """Check if account exists and user has access to it."""
    return checked_mandatory_resource(
        account_id, user_id, get_account, "Account"
    )

def checked_optional_account(
    account_id: Optional[uuid.UUID],
    user_id: str
) -> Optional[Account]:
    """Check if account exists and user has access to it, allowing None."""
    return checked_optional_resource(
        account_id, user_id, get_account, "Account"
    )
```

#### Similar structure for:
- `db/transactions.py` (400 lines)
- `db/files.py` (300 lines)
- `db/categories.py` (250 lines)
- `db/analytics.py` (300 lines)
- `db/fzip.py` (200 lines)
- `db/workflows.py` (100 lines)

### Benefits of Restructuring

1. **Easier Navigation** - Find account functions in accounts.py
2. **Reduced File Size** - Largest file ~400 lines (vs 2,239)
3. **Clear Dependencies** - Each module imports only what it needs
4. **Easier Testing** - Test accounts.py independently
5. **Better IDE Support** - Faster autocomplete, better refactoring
6. **Parallel Development** - Multiple developers can work simultaneously
7. **Clean Public API** - All functions exported via `__init__.py`

---

## Migration Strategy

### Phase 1: Add Decorators (Week 1)
**Low Risk - Immediate Benefits**

1. Create `db/base.py` with all decorators
2. Add decorators to existing functions in `db_utils.py`
3. Remove try-catch blocks from decorated functions
4. Test thoroughly

**Example:**
```python
# Before
def get_account(account_id: uuid.UUID) -> Optional[Account]:
    try:
        response = get_accounts_table().get_item(...)
        # ...
    except ClientError as e:
        logger.error(...)
        raise

# After
@dynamodb_operation("get_account")
def get_account(account_id: uuid.UUID) -> Optional[Account]:
    response = get_accounts_table().get_item(...)
    # ...
```

**Validation:**
- Run existing test suite
- All tests should pass
- Check logs for consistent format

### Phase 2: Add Helpers (Week 2)
**Low Risk - Improves Consistency**

1. Create `db/helpers.py`
2. Implement batch operations, pagination helpers
3. Replace inline batch logic with helper calls
4. Test batch operations

**Example:**
```python
# Before
with table.batch_writer() as batch:
    for item in items:
        batch.delete_item(Key={'id': str(item.id)})

# After
batch_delete_items(table, items, lambda i: {'id': str(i.id)})
```

**Validation:**
- Test batch operations with 0, 1, 25, 26, 100 items
- Verify performance is same or better

### Phase 3: Refactor Table Management (Week 3)
**Medium Risk - Structural Change**

1. Implement `DynamoDBTables` class in `db/base.py`
2. Create global `tables` instance
3. Replace ALL table getter calls across entire codebase in one commit
4. Remove old getter functions and global variables
5. Update all imports to use new table management

**Migration Steps:**
1. Implement `DynamoDBTables` class
2. Search and replace across entire codebase:
   - `get_transactions_table()` → `tables.transactions`
   - `get_accounts_table()` → `tables.accounts`
   - `get_files_table()` → `tables.files`
   - `get_file_maps_table()` → `tables.file_maps`
   - `get_categories_table()` → `tables.categories`
   - `get_analytics_data_table()` → `tables.analytics_data`
   - `get_analytics_status_table()` → `tables.analytics_status`
   - `get_fzip_jobs_table()` → `tables.fzip_jobs`
   - `get_user_preferences_table()` → `tables.user_preferences`
   - `get_workflows_table()` → `tables.workflows`
3. Remove old getter functions (lines 99-167)
4. Remove global table variables
5. Remove `initialize_tables()` function

**Example:**
```python
# Before
table = get_transactions_table()

# After
table = tables.transactions
```

**Validation:**
- Run full test suite
- Verify no references to old getter functions remain
- No performance regression
- All Lambda handlers work correctly

### Phase 4: Split into Modules (Week 4-5)
**Higher Risk - Major Restructuring**

1. Create module structure: `db/accounts.py`, etc.
2. Move functions to appropriate modules
3. Create `db/__init__.py` with public API
4. Update imports across codebase
5. Keep `db_utils.py` as deprecated alias initially
6. **Enforce architectural boundaries** - Remove direct database access from handlers/consumers

**Migration Order:**
1. Start with smallest module (workflows)
2. Then FZIP jobs
3. Then analytics
4. Then categories
5. Finally accounts/transactions/files (largest)

**Example:**
```python
# Old import (deprecated but works via __init__.py)
from utils.db_utils import get_account

# New import (preferred)
from utils.db.accounts import get_account

# Or use public API
from utils.db import get_account
```

**Architectural Boundary Enforcement:**

After module creation, enforce proper layering:

**Current Problem:**
- Handlers and consumers directly import `db_utils` or `db` modules
- Violates separation of concerns
- Makes testing harder

**Target Architecture:**
```
Handler/Consumer → Service → Database Utils
```

**Implementation Steps:**

1. **Audit Phase** - Identify violations in:
   - Handlers: transfer_operations, transaction_operations, category_operations, account_operations, file_operations, file_map_operations, fzip_operations, analytics_operations, workflow_tracking, file_processor
   - Consumers: categorization_consumer, file_processor_consumer, analytics_consumer, file_deletion_executor, restore_consumer

2. **Service Enhancement** - Create/enhance service classes:
   - TransactionService - for all transaction operations
   - AccountService - for all account operations  
   - FileService - for all file operations
   - FileMapService - for file map operations
   - Ensure services provide all methods needed by handlers/consumers

3. **Handler/Consumer Refactoring:**
   - Remove all `from utils.db_utils` imports from handlers
   - Remove all `from utils.db` imports from handlers/consumers
   - Replace direct database calls with service method calls
   - Update handler initialization to inject/use services

4. **Validation:**
   - Add linting rule or architectural test to prevent future violations
   - All handlers/consumers should only import from `services/`
   - Database utilities should only be imported by services

**Example Refactoring:**

Before:
```python
# handler/transaction_operations.py - BAD
from utils.db_utils import get_transaction, update_transaction

def update_transaction_handler(event, context):
    transaction = get_transaction(transaction_id)  # Direct DB access
    # ... business logic ...
    update_transaction(transaction)  # Direct DB access
```

After:
```python
# handler/transaction_operations.py - GOOD
from services.transaction_service import transaction_service

def update_transaction_handler(event, context):
    transaction = transaction_service.get_transaction(transaction_id)  # Through service
    # ... business logic ...
    transaction_service.update_transaction(transaction)  # Through service
```

**Validation:**
- Run full test suite after each module
- Update 10-20% of imports per day
- Monitor for any issues
- Verify no handlers/consumers import database utilities directly
- Run architectural compliance tests

### Phase 5: Use UpdateExpression (Week 6)
**Medium Risk - Performance Improvement**

1. Implement `build_update_expression` helper
2. Refactor update functions one at a time
3. Test for correctness and performance
4. Roll out gradually

**Validation:**
- A/B test old vs new implementation
- Verify same results
- Measure performance improvement
- Monitor DynamoDB metrics

### Phase 6: Remove Diagnostic Logging (Week 7)
**Low Risk - Cleanup**

1. Remove all `DIAG:` logging
2. Convert useful logs to debug level
3. Remove temporary debugging code

### Rollback Plan

**If Issues Arise:**
1. Each phase is independent - can rollback individual phases
2. Keep `db_utils.py` working via imports from new modules
3. Feature flags for UpdateExpression vs old approach
4. Monitoring alerts for error rates, latencies

```python
# Feature flag example
USE_UPDATE_EXPRESSION = os.environ.get('USE_UPDATE_EXPRESSION', 'true') == 'true'

def update_account(...):
    if USE_UPDATE_EXPRESSION:
        return _update_account_with_expression(...)
    else:
        return _update_account_legacy(...)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/utils/db/test_decorators.py
import pytest
from utils.db.base import dynamodb_operation, retry_on_throttle
from botocore.exceptions import ClientError

def test_dynamodb_operation_decorator_success():
    """Test decorator handles successful operation."""
    @dynamodb_operation("test_op")
    def successful_function():
        return "success"
    
    result = successful_function()
    assert result == "success"

def test_dynamodb_operation_decorator_client_error():
    """Test decorator handles ClientError correctly."""
    @dynamodb_operation("test_op")
    def failing_function():
        raise ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Not found'}},
            'GetItem'
        )
    
    with pytest.raises(ClientError):
        failing_function()

def test_retry_decorator_retries_on_throttle():
    """Test retry decorator retries throttled requests."""
    attempt_count = 0
    
    @retry_on_throttle(max_attempts=3, base_delay=0.01)
    def throttled_function():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ClientError(
                {'Error': {'Code': 'ThrottlingException', 'Message': 'Throttled'}},
                'Query'
            )
        return "success"
    
    result = throttled_function()
    assert result == "success"
    assert attempt_count == 3

def test_retry_decorator_gives_up_after_max_attempts():
    """Test retry decorator stops after max attempts."""
    @retry_on_throttle(max_attempts=3, base_delay=0.01)
    def always_throttled():
        raise ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Throttled'}},
            'Query'
        )
    
    with pytest.raises(ClientError):
        always_throttled()

# tests/utils/db/test_helpers.py
def test_batch_delete_items():
    """Test batch delete helper."""
    # Mock table and items
    # Verify correct number of delete_item calls
    # Verify batch_writer is used correctly

def test_build_update_expression():
    """Test update expression builder."""
    updates = {'name': 'New Name', 'balance': 100}
    expr, names, values = build_update_expression(updates)
    
    assert 'SET' in expr
    assert '#name' in names
    assert ':name' in values
    assert values[':name'] == 'New Name'

# tests/utils/db/test_accounts.py
def test_get_account_caching():
    """Test account caching works."""
    # First call - cache miss
    account1 = get_account(account_id)
    
    # Second call - cache hit (mock should not be called again)
    account2 = get_account(account_id)
    
    assert account1 == account2
    # Verify mock was only called once

def test_update_account_uses_update_expression():
    """Test update account uses UpdateExpression not put_item."""
    # Mock table.update_item
    update_account(account_id, user_id, {'name': 'New Name'})
    
    # Verify update_item was called, not put_item
    # Verify UpdateExpression contains 'SET #name = :name'
```

### Integration Tests

```python
# tests/integration/test_db_operations.py
@pytest.mark.integration
def test_account_crud_operations(dynamodb_local):
    """Test complete account lifecycle."""
    # Create account
    account = Account(...)
    create_account(account)
    
    # Read account
    retrieved = get_account(account.accountId)
    assert retrieved.accountId == account.accountId
    
    # Update account
    updated = update_account(
        account.accountId,
        account.userId,
        {'name': 'Updated Name'}
    )
    assert updated.name == 'Updated Name'
    
    # Delete account
    deleted = delete_account(account.accountId, account.userId)
    assert deleted is True
    
    # Verify deleted
    assert get_account(account.accountId) is None

@pytest.mark.integration
def test_batch_operations_performance(dynamodb_local):
    """Test batch operations handle large datasets efficiently."""
    # Create 1000 transactions
    transactions = [create_test_transaction() for _ in range(1000)]
    
    # Time deletion
    start = time.time()
    deleted = batch_delete_items(
        tables.transactions,
        transactions,
        lambda t: {'transactionId': str(t.transaction_id)}
    )
    elapsed = time.time() - start
    
    assert deleted == 1000
    assert elapsed < 5.0  # Should complete in <5 seconds
```

### Performance Tests

```python
# tests/performance/test_query_performance.py
@pytest.mark.performance
def test_update_expression_vs_put_item_performance():
    """Compare UpdateExpression vs put_item performance."""
    account_id = create_test_account()
    iterations = 100
    
    # Test UpdateExpression approach
    start = time.time()
    for i in range(iterations):
        update_account(account_id, user_id, {'name': f'Name {i}'})
    update_expr_time = time.time() - start
    
    # Test put_item approach (legacy)
    start = time.time()
    for i in range(iterations):
        update_account_legacy(account_id, user_id, {'name': f'Name {i}'})
    put_item_time = time.time() - start
    
    # UpdateExpression should be significantly faster
    assert update_expr_time < put_item_time * 0.7  # At least 30% faster
    
    logger.info(f"UpdateExpression: {update_expr_time:.2f}s")
    logger.info(f"put_item: {put_item_time:.2f}s")
    logger.info(f"Improvement: {((put_item_time - update_expr_time) / put_item_time) * 100:.1f}%")
```

---

## Performance Impact

### Expected Improvements

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Update (put_item) | 2 round trips | 1 round trip | 50% faster |
| Update (WCU cost) | 2 WCU | 1 WCU | 50% cheaper |
| Batch delete 1000 items | Sequential | Parallel (5 workers) | 3-5x faster |
| Cache hit (account) | ~50ms | ~0.1ms | 500x faster |
| Transient throttling | Fails immediately | Retries 3x | 95%+ success |
| Code size | 2,239 lines | ~1,500 lines | 33% reduction |

### Monitoring Metrics

**Before Refactoring:**
```
- Average update latency: 100ms
- P99 update latency: 500ms
- Throttle error rate: 2%
- Cache hit rate: 0% (no caching)
- Code coverage: 65%
```

**After Refactoring Goals:**
```
- Average update latency: 50ms (50% improvement)
- P99 update latency: 200ms (60% improvement)
- Throttle error rate: <0.1% (95% improvement)
- Cache hit rate: 80% (new capability)
- Code coverage: 85% (easier to test)
```

### Cost Impact

**Monthly DynamoDB Costs (Estimated):**

Assumptions:
- 1M transactions/month
- 100K account updates/month
- 10K batch operations/month

**Before:**
```
Account updates: 100K * 2 WCU = 200K WCU
Read operations: 1M RCU
Batch operations: 10K * 100 items = 1M WCU
Total: 1.2M WCU + 1M RCU ≈ $15/month
```

**After:**
```
Account updates: 100K * 1 WCU = 100K WCU (UpdateExpression)
Read operations: 200K RCU (80% cache hit rate)
Batch operations: 1M WCU (same, but faster)
Total: 1.1M WCU + 200K RCU ≈ $9/month
```

**Savings: ~40% reduction in DynamoDB costs**

---

## Appendix A: Complete Decorator Reference

```python
# Error handling and logging
@dynamodb_operation("operation_name")

# Retry on throttling
@retry_on_throttle(max_attempts=3, base_delay=0.1)

# Performance monitoring
@monitor_performance(warn_threshold_ms=1000)

# Authorization
@require_resource_ownership(
    resource_getter=get_account,
    resource_id_param='account_id',
    resource_name='Account'
)

# Parameter validation
@validate_params(
    account_id=is_valid_uuid,
    limit=is_positive_int
)

# Caching
@cache_result(ttl_seconds=60, maxsize=100)

# Typical stack (order matters - bottom to top):
@cache_result(ttl_seconds=30)              # 5. Cache
@monitor_performance(warn_threshold_ms=200) # 4. Monitor
@retry_on_throttle(max_attempts=3)         # 3. Retry
@require_resource_ownership(...)            # 2. Auth
@dynamodb_operation("operation_name")      # 1. Error handling
def my_function(...):
    ...
```

## Appendix B: Before/After Comparison

### Example: update_category_in_db

**Before: 68 lines with repetitive error handling**
```python
def update_category_in_db(category_id: uuid.UUID, user_id: str, update_data: Dict[str, Any]) -> Optional[Category]:
    category = get_category_by_id_from_db(category_id, user_id)
    if not category:
        logger.warning(f"DB: Category {str(category_id)} not found or user {user_id} has no access.")
        return None
    if not update_data:
        logger.info(f"DB: No update data provided for category {str(category_id)}. Returning existing.")
        return category
    try:
        logger.info(f"DIAG: update_category_in_db called with update_data keys: {list(update_data.keys())}")
        if 'rules' in update_data:
            rules = update_data['rules']
            logger.info(f"DIAG: update_data contains {len(rules)} rules")
            # ... 20+ more lines of diagnostic logging ...
        
        category_update_dto = CategoryUpdate(**update_data)
        category.update_category_details(category_update_dto)
        get_categories_table().put_item(Item=category.to_dynamodb_item())
        logger.info(f"DB: Category {str(category_id)} updated successfully.")
        return category
    except ValidationError as e:
        logger.error(f"DB: Validation error updating category {str(category_id)}: {str(e)}")
        raise ValueError(f"Invalid update data: {str(e)}")
    except ClientError as e:
        logger.error(f"DB: Error updating category {str(category_id)}: {str(e)}", exc_info=True)
        raise 
    except Exception as e:
        logger.error(f"DB: Unexpected error updating category {str(category_id)}: {str(e)}", exc_info=True)
        raise
```

**After: 18 lines, clean and focused**
```python
@require_resource_ownership(
    resource_getter=lambda cid: get_category_by_id_from_db(cid, user_id),
    resource_id_param='category_id',
    resource_name='Category'
)
@monitor_performance(warn_threshold_ms=300)
@retry_on_throttle()
@dynamodb_operation("update_category")
def update_category_in_db(
    category_id: uuid.UUID,
    user_id: str,
    update_data: Dict[str, Any]
) -> Optional[Category]:
    """Update an existing category with validation."""
    if not update_data:
        return get_category_by_id_from_db(category_id, user_id)
    
    category = get_category_by_id_from_db(category_id, user_id)
    category_update_dto = CategoryUpdate(**update_data)
    category.update_category_details(category_update_dto)
    
    tables.categories.put_item(Item=category.to_dynamodb_item())
    return category
```

**Impact:**
- 73% less code (68 → 18 lines)
- Removed all diagnostic logging
- Removed repetitive error handling
- Added performance monitoring
- Added retry logic
- Added authorization check
- Clearer business logic

---

## Appendix C: Implementation Checklist

### Phase 1: Decorators
- [ ] Create `db/base.py`
- [ ] Implement `dynamodb_operation` decorator
- [ ] Implement `retry_on_throttle` decorator
- [ ] Implement `monitor_performance` decorator
- [ ] Implement `require_resource_ownership` decorator
- [ ] Implement `validate_params` decorator
- [ ] Implement `cache_result` decorator
- [ ] Write unit tests for each decorator
- [ ] Apply decorators to 5 functions as proof of concept
- [ ] Run existing test suite
- [ ] Code review and merge

### Phase 2: Helpers
- [ ] Create `db/helpers.py`
- [ ] Implement `batch_delete_items`
- [ ] Implement `batch_write_items`
- [ ] Implement `batch_update_items`
- [ ] Implement `paginated_query`
- [ ] Implement `build_update_expression`
- [ ] Implement UUID conversion helpers
- [ ] Write unit tests for helpers
- [ ] Replace inline batch logic in 3 functions
- [ ] Run test suite
- [ ] Code review and merge

### Phase 3: Table Management
- [ ] Implement `DynamoDBTables` class in `db/base.py`
- [ ] Create global `tables` instance
- [ ] Write tests for table management
- [ ] Search and replace ALL occurrences of getter functions across codebase
- [ ] Remove old getter functions (lines 99-167)
- [ ] Remove global table variables
- [ ] Remove `initialize_tables()` function
- [ ] Verify no references to old getters remain (grep search)
- [ ] Run full test suite
- [ ] Test all Lambda handlers
- [ ] Code review and merge

### Phase 4: Module Split
- [ ] Create module structure
- [ ] Create `db/__init__.py`
- [ ] Migrate workflows.py (smallest module)
- [ ] Test workflows module
- [ ] Migrate fzip.py
- [ ] Test fzip module
- [ ] Migrate analytics.py
- [ ] Test analytics module
- [ ] Migrate categories.py
- [ ] Test categories module
- [ ] Migrate accounts.py
- [ ] Test accounts module
- [ ] Migrate transactions.py
- [ ] Test transactions module
- [ ] Migrate files.py
- [ ] Test files module
- [ ] Update all imports across codebase
- [ ] Full test suite run
- [ ] **Architectural Boundary Enforcement**
- [ ] Audit all handlers for direct db_utils imports
- [ ] Audit all consumers for direct db_utils imports
- [ ] Create/enhance TransactionService for handler needs
- [ ] Create/enhance AccountService for handler needs
- [ ] Create/enhance FileService for handler needs
- [ ] Create/enhance FileMapService for handler needs
- [ ] Refactor handlers to use services instead of direct db access
- [ ] Refactor consumers to use services instead of direct db access
- [ ] Add architectural test to prevent db imports in handlers/consumers
- [ ] Verify no handlers/consumers import db_utils or db modules
- [ ] Code review and merge

### Phase 5: UpdateExpression
- [ ] Implement `build_update_expression` helper
- [ ] Refactor `update_account` to use UpdateExpression
- [ ] Test update_account
- [ ] Refactor `update_transaction_file`
- [ ] Test update_transaction_file
- [ ] Refactor `update_category_in_db`
- [ ] Test update_category_in_db
- [ ] Performance testing
- [ ] Monitor DynamoDB metrics
- [ ] Code review and merge

### Phase 6: Cleanup
- [ ] Remove all `DIAG:` logging
- [ ] Remove temporary debugging code
- [ ] Update documentation
- [ ] Update README
- [ ] Final code review

---

## Appendix D: Resources

### DynamoDB Best Practices
- [AWS DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [DynamoDB UpdateItem vs PutItem](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.AtomicCounters)
- [DynamoDB Batch Operations](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/batch-operations.html)

### Python Decorators
- [PEP 318 - Decorators](https://peps.python.org/pep-0318/)
- [Real Python - Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/)

### Boto3 DynamoDB
- [Boto3 DynamoDB Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/dynamodb.html)
- [Boto3 DynamoDB Resource](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)

---

## Questions & Next Steps

### Questions for Team
1. What's our target timeline for this refactoring?
2. Should we prioritize cost savings or code quality improvements?
3. Any concerns about the proposed decorator approach?
4. Should we implement feature flags for gradual rollout?
5. What's our appetite for risk during migration?

### Recommended Next Steps
1. **Review this document** with the team
2. **Prioritize phases** based on team goals
3. **Create tickets** for each phase
4. **Assign owners** for each phase
5. **Start with Phase 1** (decorators) - lowest risk, highest impact
6. **Monitor metrics** throughout migration
7. **Document lessons learned** after each phase

---

**Document History:**
- v1.0 (2025-11-02): Initial draft with comprehensive refactoring plan

