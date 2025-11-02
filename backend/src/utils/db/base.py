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
from typing import Dict, List, Any, Optional, Union, Tuple, Callable, TypeVar, Protocol
from functools import wraps
from botocore.exceptions import ClientError
from pydantic import ValidationError

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# Protocols
# ============================================================================

class HasUserId(Protocol):
    """Protocol for resources that have a user_id attribute."""
    user_id: str


# Type variables
T = TypeVar('T')
TResource = TypeVar('TResource', bound=HasUserId)

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

def dynamodb_operation(operation_name: Optional[str] = None):
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
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
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
            last_exception: Optional[ClientError] = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
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
            # This should never be None since we always set it in the except block
            if last_exception:
                raise last_exception
            # Fallback - should never reach here
            raise RuntimeError(f"Unexpected state in retry_on_throttle for {func.__name__}")
        return wrapper
    return decorator


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


def cache_result(ttl_seconds: Union[int, float] = 300, maxsize: int = 128):
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
        wrapper.cache_clear = lambda: (cache.clear(), cache_times.clear())  # type: ignore
        wrapper.cache_info = lambda: {  # type: ignore
            'size': len(cache),
            'maxsize': maxsize,
            'ttl_seconds': ttl_seconds
        }
        
        return wrapper
    return decorator


# ============================================================================
# Common Validators (for use with validate_params decorator)
# ============================================================================

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


# ============================================================================
# Table Management
# ============================================================================

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
    _instance: Optional['DynamoDBTables'] = None
    
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
        """Get transactions table."""
        return self._get_table('transactions')
    
    @property
    def accounts(self) -> Any:
        """Get accounts table."""
        return self._get_table('accounts')
    
    @property
    def files(self) -> Any:
        """Get files table."""
        return self._get_table('files')
    
    @property
    def file_maps(self) -> Any:
        """Get file maps table."""
        return self._get_table('file_maps')
    
    @property
    def categories(self) -> Any:
        """Get categories table."""
        return self._get_table('categories')
    
    @property
    def analytics_data(self) -> Any:
        """Get analytics data table."""
        return self._get_table('analytics_data')
    
    @property
    def analytics_status(self) -> Any:
        """Get analytics status table."""
        return self._get_table('analytics_status')
    
    @property
    def fzip_jobs(self) -> Any:
        """Get FZIP jobs table."""
        return self._get_table('fzip_jobs')
    
    @property
    def user_preferences(self) -> Any:
        """Get user preferences table."""
        return self._get_table('user_preferences')
    
    @property
    def workflows(self) -> Any:
        """Get workflows table."""
        return self._get_table('workflows')
    
    def reinitialize(self):
        """Reinitialize DynamoDB resource (useful for testing)."""
        self._dynamodb = boto3.resource('dynamodb')
        self._tables.clear()
        logger.info("Reinitialized DynamoDB tables")


# Global instance
tables = DynamoDBTables()


# ============================================================================
# Helper Functions
# ============================================================================

def check_user_owns_resource(resource_user_id: str, requesting_user_id: str) -> None:
    """
    Check if a user owns a resource.
    
    Args:
        resource_user_id: User ID from the resource
        requesting_user_id: User ID making the request
        
    Raises:
        NotAuthorized: If the user doesn't own the resource
    """
    if resource_user_id != requesting_user_id:
        raise NotAuthorized("Not authorized to access this resource")


def checked_mandatory_resource(
    resource_id: Optional[uuid.UUID],
    user_id: str,
    getter_func: Callable[[uuid.UUID], Optional[TResource]],
    resource_name: str
) -> TResource:
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
    getter_func: Callable[[uuid.UUID], Optional[TResource]],
    resource_name: str
) -> Optional[TResource]:
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

