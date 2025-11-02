"""
Database utilities for DynamoDB operations.

This module provides a clean interface for all database operations.
Imports are organized by resource type for easy navigation.
"""

# ============================================================================
# Core Infrastructure
# ============================================================================

from .base import (
    # Table management
    tables,
    DynamoDBTables,
    
    # Exceptions
    NotAuthorized,
    NotFound,
    ConflictError,
    
    # Decorators
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    validate_params,
    cache_result,
    
    # Validators
    is_valid_uuid,
    is_positive_int,
    is_valid_limit,
    
    # Helper functions
    check_user_owns_resource,
    checked_mandatory_resource,
    checked_optional_resource,
)

from .helpers import (
    # UUID conversion
    to_db_id,
    from_db_id,
    to_db_ids,
    from_db_ids,
    
    # Batch operations
    batch_delete_items,
    batch_write_items,
    batch_update_items,
    
    # Pagination
    paginated_query,
    paginated_scan,
    
    # Update expressions
    build_update_expression,
    build_condition_expression,
    
    # Timestamp helpers
    current_timestamp,
    timestamp_from_datetime,
    datetime_from_timestamp,
    
    # Decimal conversion
    decimal_to_float,
    float_to_decimal,
)

# ============================================================================
# Account Operations
# ============================================================================

from .accounts import (
    get_account,
    list_user_accounts,
    create_account,
    update_account,
    delete_account,
    checked_mandatory_account,
    checked_optional_account,
    get_account_transaction_date_range,
    update_account_derived_values,
)

# ============================================================================
# Transaction Operations
# ============================================================================

from .transactions import (
    list_file_transactions,
    list_user_transactions,
    create_transaction,
    delete_transactions_for_file,
    list_account_transactions,
    update_transaction_statuses_by_status,
    get_transaction_by_account_and_hash,
    check_duplicate_transaction,
    update_transaction,
    get_first_transaction_date,
    get_last_transaction_date,
    get_latest_transaction,
    checked_mandatory_transaction,
    checked_optional_transaction,
)

# ============================================================================
# File Operations
# ============================================================================

from .files import (
    # TransactionFile operations
    get_transaction_file,
    list_account_files,
    list_user_files,
    create_transaction_file,
    update_transaction_file,
    update_transaction_file_object,
    delete_transaction_file,
    delete_file_metadata,
    update_file_account_id,
    update_file_field_map,
    checked_mandatory_transaction_file,
    checked_optional_transaction_file,
    
    # FileMap operations
    get_file_map,
    get_account_default_file_map,
    create_file_map,
    update_file_map,
    delete_file_map,
    list_file_maps_by_user,
    list_account_file_maps,
    checked_mandatory_file_map,
    checked_optional_file_map,
)

# ============================================================================
# Category Operations
# ============================================================================

from .categories import (
    create_category_in_db,
    get_category_by_id_from_db,
    list_categories_by_user_from_db,
    update_category_in_db,
    delete_category_from_db,
    checked_mandatory_category,
    checked_optional_category,
)

# ============================================================================
# Analytics Operations
# ============================================================================

from .analytics import (
    # Analytics Data
    store_analytics_data,
    get_analytics_data,
    list_analytics_data_for_user,
    batch_store_analytics_data,
    delete_analytics_data,
    
    # Analytics Status
    store_analytics_status,
    get_analytics_status,
    list_analytics_status_for_user,
    update_analytics_status,
    list_stale_analytics,
)

# ============================================================================
# FZIP Operations
# ============================================================================

from .fzip import (
    create_fzip_job,
    get_fzip_job,
    update_fzip_job,
    list_user_fzip_jobs,
    delete_fzip_job,
    cleanup_expired_fzip_jobs,
)

# ============================================================================
# Workflow Operations
# ============================================================================

from .workflows import (
    checked_mandatory_workflow,
)

# ============================================================================
# __all__ Export List
# ============================================================================

__all__ = [
    # Table management
    'tables',
    'DynamoDBTables',
    
    # Exceptions
    'NotAuthorized',
    'NotFound',
    'ConflictError',
    
    # Decorators
    'dynamodb_operation',
    'retry_on_throttle',
    'monitor_performance',
    'validate_params',
    'cache_result',
    
    # Validators
    'is_valid_uuid',
    'is_positive_int',
    'is_valid_limit',
    
    # Helper functions
    'check_user_owns_resource',
    'checked_mandatory_resource',
    'checked_optional_resource',
    
    # UUID conversion
    'to_db_id',
    'from_db_id',
    'to_db_ids',
    'from_db_ids',
    
    # Batch operations
    'batch_delete_items',
    'batch_write_items',
    'batch_update_items',
    
    # Pagination
    'paginated_query',
    'paginated_scan',
    
    # Update expressions
    'build_update_expression',
    'build_condition_expression',
    
    # Timestamp helpers
    'current_timestamp',
    'timestamp_from_datetime',
    'datetime_from_timestamp',
    
    # Decimal conversion
    'decimal_to_float',
    'float_to_decimal',
    
    # Account operations
    'get_account',
    'list_user_accounts',
    'create_account',
    'update_account',
    'delete_account',
    'checked_mandatory_account',
    'checked_optional_account',
    'get_account_transaction_date_range',
    'update_account_derived_values',
    
    # Transaction operations
    'list_file_transactions',
    'list_user_transactions',
    'create_transaction',
    'delete_transactions_for_file',
    'list_account_transactions',
    'update_transaction_statuses_by_status',
    'get_transaction_by_account_and_hash',
    'check_duplicate_transaction',
    'update_transaction',
    'get_first_transaction_date',
    'get_last_transaction_date',
    'get_latest_transaction',
    'checked_mandatory_transaction',
    'checked_optional_transaction',
    
    # File operations
    'get_transaction_file',
    'list_account_files',
    'list_user_files',
    'create_transaction_file',
    'update_transaction_file',
    'update_transaction_file_object',
    'delete_transaction_file',
    'delete_file_metadata',
    'update_file_account_id',
    'update_file_field_map',
    'checked_mandatory_transaction_file',
    'checked_optional_transaction_file',
    
    # FileMap operations
    'get_file_map',
    'get_account_default_file_map',
    'create_file_map',
    'update_file_map',
    'delete_file_map',
    'list_file_maps_by_user',
    'list_account_file_maps',
    'checked_mandatory_file_map',
    'checked_optional_file_map',
    
    # Category operations
    'create_category_in_db',
    'get_category_by_id_from_db',
    'list_categories_by_user_from_db',
    'update_category_in_db',
    'delete_category_from_db',
    'checked_mandatory_category',
    'checked_optional_category',
    
    # Analytics operations
    'store_analytics_data',
    'get_analytics_data',
    'list_analytics_data_for_user',
    'batch_store_analytics_data',
    'delete_analytics_data',
    'store_analytics_status',
    'get_analytics_status',
    'list_analytics_status_for_user',
    'update_analytics_status',
    'list_stale_analytics',
    
    # FZIP operations
    'create_fzip_job',
    'get_fzip_job',
    'update_fzip_job',
    'list_user_fzip_jobs',
    'delete_fzip_job',
    'cleanup_expired_fzip_jobs',
    
    # Workflow operations
    'checked_mandatory_workflow',
]
