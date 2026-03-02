"""
Utility functions for database operations.

DEPRECATED: This module is maintained for backward compatibility.
New code should import directly from utils.db instead.

Example:
    OLD: from utils.db_utils import get_account
    NEW: from utils.db import get_account
    OR:  from utils.db.accounts import get_account
"""

# Re-export everything from the new db package for backward compatibility
from utils.db import *  # noqa: F401, F403

# Import specific items that might be referenced
from utils.db import (  # noqa: F401
    # Core infrastructure
    tables,
    DynamoDBTables,
    NotAuthorized,
    NotFound,
    ConflictError,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    validate_params,
    cache_result,
    check_user_owns_resource,
    
    # Helpers
    to_db_id,
    batch_delete_items,
    batch_write_items,
    
    # Account operations
    list_user_accounts,
    create_account,
    update_account,
    delete_account,
    checked_mandatory_account,
    checked_optional_account,
    get_account_transaction_date_range,
    update_account_derived_values,
    
    # Transaction operations
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
    
    # File operations
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
    _get_transaction_file,  # Internal use only
    
    # FileMap operations
    get_account_default_file_map,
    create_file_map,
    update_file_map,
    delete_file_map,
    list_file_maps_by_user,
    list_account_file_maps,
    checked_mandatory_file_map,
    checked_optional_file_map,
    
    # Category operations
    create_category_in_db,
    list_categories_by_user_from_db,
    update_category_in_db,
    delete_category_from_db,
    checked_mandatory_category,
    checked_optional_category,
    
    # Analytics operations
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
    
    # FZIP operations
    create_fzip_job,
    get_fzip_job,
    update_fzip_job,
    list_user_fzip_jobs,
    delete_fzip_job,
    cleanup_expired_fzip_jobs,
    
    # Workflow operations
    checked_mandatory_workflow,
)
