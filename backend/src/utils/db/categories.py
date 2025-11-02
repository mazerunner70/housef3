"""
Category database operations.

This module provides CRUD operations for categories.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from boto3.dynamodb.conditions import Key, Attr

from models.category import Category, CategoryUpdate, CategoryRule
from .base import (
    tables,
    dynamodb_operation,
    retry_on_throttle,
    monitor_performance,
    NotFound,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def checked_mandatory_category(category_id: uuid.UUID, user_id: str) -> Category:
    """
    Check if category exists and user has access to it.
    
    Args:
        category_id: ID of the category
        user_id: ID of the user requesting access
        
    Returns:
        Category object if found and authorized
        
    Raises:
        NotFound: If category doesn't exist or user doesn't have access
    """
    category = get_category_by_id_from_db(category_id, user_id)
    if not category:
        raise NotFound("Category not found")
    return category


def checked_optional_category(category_id: Optional[uuid.UUID], user_id: str) -> Optional[Category]:
    """
    Check if category exists and user has access to it, allowing None.
    
    Args:
        category_id: ID of the category (or None)
        user_id: ID of the user requesting access
        
    Returns:
        Category object if found and authorized, None if category_id is None or not found
    """
    if not category_id:
        return None
    try:
        return checked_mandatory_category(category_id, user_id)
    except NotFound:
        return None


# ============================================================================
# CRUD Operations
# ============================================================================

def create_category_in_db(category: Category) -> Category:
    """
    Persist a new category to DynamoDB.
    
    Args:
        category: The Category object to create
        
    Returns:
        The created Category object
        
    Raises:
        ConnectionError: If database table is not initialized
    """
    table = tables.categories
    if not table:
        logger.error("DB: Categories table not initialized for create_category_in_db")
        raise ConnectionError("Database table not initialized")
    
    table.put_item(Item=category.to_dynamodb_item())
    logger.info(f"DB: Category {str(category.categoryId)} created successfully for user {category.userId}.")
    return category


@monitor_performance(warn_threshold_ms=200)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("get_category_by_id_from_db")
def get_category_by_id_from_db(category_id: uuid.UUID, user_id: str) -> Optional[Category]:
    """
    Retrieve a category by ID and user ID.
    
    Args:
        category_id: The category ID
        user_id: The user ID (for access control)
        
    Returns:
        Category object if found and owned by user, None otherwise
    """
    table = tables.categories
    if not table:
        logger.error("DB: Categories table not initialized for get_category_by_id_from_db")
        return None
    
    logger.debug(f"DB: Getting category {str(category_id)} for user {user_id}")
    response = table.get_item(Key={'categoryId': str(category_id)})
    item = response.get('Item')
    
    if item and item.get('userId') == user_id:
        return Category.from_dynamodb_item(item)
    elif item:
        logger.warning(f"User {user_id} attempted to access category {str(category_id)} owned by {item.get('userId')}")
        return None
    return None


@monitor_performance(operation_type="query", warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("list_categories_by_user_from_db")
def list_categories_by_user_from_db(
    user_id: str,
    parent_category_id: Optional[uuid.UUID] = None,
    top_level_only: bool = False
) -> List[Category]:
    """
    List categories for a user with optional parent filter.
    
    Args:
        user_id: The user ID
        parent_category_id: Optional parent category filter
        top_level_only: If True, only return top-level categories (no parent)
        
    Returns:
        List of Category objects
    """
    table = tables.categories
    if not table:
        logger.error("DB: Categories table not initialized for list_categories_by_user_from_db")
        return []
    
    logger.debug(f"DB: Listing categories for user {user_id}, parent: {str(parent_category_id) if parent_category_id else None}, top_level: {top_level_only}")
    
    params: Dict[str, Any] = {}
    filter_expressions = []
    
    if parent_category_id is not None:
        params['IndexName'] = 'UserIdParentCategoryIdIndex'
        params['KeyConditionExpression'] = Key('userId').eq(user_id) & Key('parentCategoryId').eq(str(parent_category_id))
    else: 
        params['IndexName'] = 'UserIdIndex'
        params['KeyConditionExpression'] = Key('userId').eq(user_id)
        if top_level_only:
            filter_expressions.append(Attr('parentCategoryId').not_exists())
    
    if filter_expressions:
        final_filter_expression = filter_expressions[0]
        for i in range(1, len(filter_expressions)):
            final_filter_expression = final_filter_expression & filter_expressions[i]
        params['FilterExpression'] = final_filter_expression

    all_items_raw = []
    current_params = params.copy()
    while True:
        response = table.query(**current_params)
        all_items_raw.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        current_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
    
    return [Category.from_dynamodb_item(item) for item in all_items_raw]


@monitor_performance(warn_threshold_ms=400)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("update_category_in_db")
def update_category_in_db(
    category_id: uuid.UUID,
    user_id: str,
    update_data: Dict[str, Any]
) -> Optional[Category]:
    """
    Update an existing category in DynamoDB.
    
    Args:
        category_id: The unique identifier of the category to update
        user_id: The ID of the user making the request
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated Category object if successful, None if category not found
    """
    # Retrieve the existing category
    category = get_category_by_id_from_db(category_id, user_id)
    if not category:
        logger.warning(f"DB: Category {str(category_id)} not found or user {user_id} has no access.")
        return None

    if not update_data:
        logger.info(f"DB: No update data provided for category {str(category_id)}. Returning existing.")
        return category

    # Diagnostic logging
    logger.info(f"DIAG: update_category_in_db called with update_data keys: {list(update_data.keys())}")
    if 'rules' in update_data:
        rules = update_data['rules']
        logger.info(f"DIAG: update_data contains {len(rules)} rules")
        for i, rule in enumerate(rules):
            logger.info(f"DIAG: update_data rule {i}: type={type(rule)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
    
    # Create a CategoryUpdate DTO from the update_data
    logger.info("DIAG: Creating CategoryUpdate DTO...")
    category_update_dto = CategoryUpdate(**update_data)
    logger.info("DIAG: CategoryUpdate DTO created successfully")
    
    # Check the DTO's rules
    if hasattr(category_update_dto, 'rules') and category_update_dto.rules:
        logger.info(f"DIAG: CategoryUpdate DTO has {len(category_update_dto.rules)} rules")
        for i, rule in enumerate(category_update_dto.rules):
            logger.info(f"DIAG: DTO rule {i}: type={type(rule)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
    
    # Use the model's method to update details
    logger.info("DIAG: Calling update_category_details...")
    category.update_category_details(category_update_dto)
    logger.info("DIAG: update_category_details completed")
    
    # Check category rules after update
    logger.info(f"DIAG: After update, category has {len(category.rules)} rules")
    for i, rule in enumerate(category.rules):
        logger.info(f"DIAG: Post-update rule {i}: type={type(rule)}, is_CategoryRule={isinstance(rule, CategoryRule)}")
    
    # Save updates to DynamoDB
    logger.info("DIAG: Calling to_dynamodb_item...")
    tables.categories.put_item(Item=category.to_dynamodb_item())
    
    logger.info(f"DB: Category {str(category_id)} updated successfully.")
    return category


@monitor_performance(warn_threshold_ms=500)
@retry_on_throttle(max_attempts=3)
@dynamodb_operation("delete_category_from_db")
def delete_category_from_db(category_id: uuid.UUID, user_id: str) -> bool:
    """
    Delete a category from DynamoDB.
    
    Args:
        category_id: The category ID to delete
        user_id: The user ID (for access control)
        
    Returns:
        True if deleted, False if not found or access denied
        
    Raises:
        ValueError: If category has child categories
    """
    table = tables.categories
    if not table:
        logger.error("DB: Categories table not initialized for delete_category_from_db")
        return False
    
    logger.debug(f"DB: Deleting category {str(category_id)} for user {user_id}")
    category_to_delete = get_category_by_id_from_db(category_id, user_id)
    if not category_to_delete:
        return False
    
    child_categories = list_categories_by_user_from_db(user_id, parent_category_id=category_id)
    if child_categories:
        logger.warning(f"Attempt to delete category {str(category_id)} which has child categories.")
        raise ValueError("Cannot delete category: it has child categories.")
    
    # Clean up transaction references before deleting the category
    logger.info(f"DB: Cleaning up transaction references for category {str(category_id)}")
    transactions_cleaned = _cleanup_transaction_category_references(category_id, user_id)
    logger.info(f"DB: Cleaned up {transactions_cleaned} transactions that referenced category {str(category_id)}")
    
    table.delete_item(Key={'categoryId': str(category_id)})
    return True


# ============================================================================
# Helper Functions
# ============================================================================

@monitor_performance(warn_threshold_ms=2000)
@dynamodb_operation("_cleanup_transaction_category_references")
def _cleanup_transaction_category_references(category_id: uuid.UUID, user_id: str) -> int:
    """
    Clean up all transaction references to a category before deleting it.
    
    Args:
        category_id: The category ID to remove from transactions
        user_id: The user ID to limit scope of cleanup
        
    Returns:
        Number of transactions that were cleaned up
    """
    # Import here to avoid circular dependency
    from .transactions import list_user_transactions, update_transaction
    
    cleaned_count = 0
    
    # Get all transactions that reference this category either as primary or in categories list
    # We need to scan through all user transactions since DynamoDB doesn't have a direct way
    # to query by category references efficiently
    
    # Get transactions in batches to avoid memory issues
    last_evaluated_key = None
    batch_size = 1000
    
    while True:
        # Get batch of transactions
        transactions, last_evaluated_key, _ = list_user_transactions(
            user_id=user_id,
            limit=batch_size,
            last_evaluated_key=last_evaluated_key,
            uncategorized_only=False  # Get all transactions, not just uncategorized ones
        )
        
        if not transactions:
            break
        
        # Process transactions in this batch
        for transaction in transactions:
            transaction_updated = False
            
            # Check if this transaction references the category being deleted
            if transaction.primary_category_id == category_id:
                # Remove primary category reference
                transaction.primary_category_id = None
                transaction_updated = True
                logger.debug(f"DB: Removed primary category reference from transaction {transaction.transaction_id}")
            
            # Check categories list for references to this category
            if transaction.categories:
                original_categories_count = len(transaction.categories)
                # Remove any category assignments that reference the deleted category
                transaction.categories = [
                    cat for cat in transaction.categories 
                    if cat.category_id != category_id
                ]
                
                if len(transaction.categories) < original_categories_count:
                    transaction_updated = True
                    logger.debug(f"DB: Removed category assignment from transaction {transaction.transaction_id}")
                    
                    # If we removed categories and there's no primary category, 
                    # set a new primary from remaining confirmed categories
                    if not transaction.primary_category_id and transaction.confirmed_categories:
                        transaction.primary_category_id = transaction.confirmed_categories[0].category_id
                        logger.debug(f"DB: Set new primary category for transaction {transaction.transaction_id}")
            
            # Update transaction if it was modified
            if transaction_updated:
                update_transaction(transaction)
                cleaned_count += 1
        
        # If we got fewer transactions than requested, we're done
        if not last_evaluated_key:
            break
    
    return cleaned_count

