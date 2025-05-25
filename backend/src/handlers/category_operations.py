import json
import os
import boto3
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from models.category import Category, CategoryCreate, CategoryUpdate
from utils.db_utils import create_category_in_db, delete_category_from_db, get_category_by_id_from_db, list_categories_by_user_from_db, update_category_in_db
from utils.lambda_utils import mandatory_path_parameter, mandatory_query_parameter, optional_body_parameter

# Setup logging (ensure it's configured after potential path adjustments for utils if utils also configure logging)
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


categories_table = None # Will be initialized in the main handler

# --- Local Utility Functions (kept as per account_operations.py pattern) ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, uuid.UUID):
            return str(o)
        if isinstance(o, datetime):
             return o.isoformat()
        return super(DecimalEncoder, self).default(o)

def create_response(status_code: int, body: Any, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    final_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*", 
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
    }
    if headers:
        final_headers.update(headers)
    return {
        "statusCode": status_code,
        "headers": final_headers,
        "body": json.dumps(body, cls=DecimalEncoder)
    }


# --- Specific Operation Handlers (Refactored to use db_utils_categories) ---

def create_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        body = get_json_body(event)
        category_data = CategoryCreate(**body)
        new_category = Category(userId=user_id, **category_data.dict())
        # Use new DB util function
        created_category = create_category_in_db(new_category)
        return create_response(201, created_category.dict())
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error creating category: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e: 
        logger.error(f"Error creating category: {str(e)}", exc_info=True)
        return create_response(400, {"error": "Invalid category data or server error", "message": str(e)})

def list_categories_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        parent_category_id = get_query_param(event, 'parentCategoryId') 
        top_level_only_str = get_query_param(event, 'topLevelOnly', 'false').lower()
        top_level_only = top_level_only_str == 'true'
        
        # Use new DB util function
        if parent_category_id is not None:
             categories = list_categories_by_user_from_db(user_id, parent_category_id=parent_category_id)
        else: 
             categories = list_categories_by_user_from_db(user_id, top_level_only=top_level_only)
        return create_response(200, [cat.dict() for cat in categories])
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error listing categories: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Could not list categories", "message": str(e)})

def get_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        category_id = get_path_param(event, 'categoryId', required=True)
        if category_id is None: # Should be caught by required=True, but defensive
            return create_response(400, {"error": "categoryId path parameter is required"})
        # Use new DB util function
        category = get_category_by_id_from_db(category_id, user_id)
        if category:
            return create_response(200, category.dict())
        else:
            return create_response(404, {"error": "Category not found or access denied"})
    except ValueError as ve: 
        logger.warning(f"Missing categoryId path parameter: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error getting category: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e:
        logger.error(f"Error getting category: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Could not get category", "message": str(e)})

def update_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        category_id = get_path_param(event, 'categoryId', required=True)
        if category_id is None: # Defensive
            return create_response(400, {"error": "categoryId path parameter is required"})
        body = get_json_body(event) 
        update_data = CategoryUpdate(**body)
        # Use new DB util function
        updated_category = update_category_in_db(category_id, user_id, update_data)
        if updated_category:
            return create_response(200, updated_category.dict())
        else:
            # This could be 404 if not found, or if update_data was empty leading to no change
            # db_util returns None if not found, or the same object if no changes from update_data
            # Check if the category exists first if finer grained error is needed.
            return create_response(404, {"error": "Category not found or update failed (no changes?)"}) 
    except ValueError as ve: 
        # category_id_for_log might be None if get_path_param itself failed. Handle this gracefully.
        category_id_from_event = event.get('pathParameters', {}).get('categoryId', 'UNKNOWN')
        logger.warning(f"Validation error updating category {category_id_from_event}: {str(ve)}")
        return create_response(400, {"error": "Invalid update data or missing ID", "message": str(ve)})
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error updating category: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e: 
        logger.error(f"Error updating category: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Could not update category", "message": str(e)})

def delete_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        category_id = get_path_param(event, 'categoryId', required=True)
        if category_id is None: # Defensive
            return create_response(400, {"error": "categoryId path parameter is required"})
        # Use new DB util function
        if delete_category_from_db(category_id, user_id):
            return create_response(204, {})
        else:
            return create_response(404, {"error": "Category not found or access denied"})
    except ValueError as ve: 
        category_id_from_event = event.get('pathParameters', {}).get('categoryId', 'UNKNOWN')
        logger.warning(f"Validation error deleting category {category_id_from_event}: {str(ve)}")
        if "it has child categories" in str(ve):
             return create_response(400, {"error": str(ve)}) 
        return create_response(400, {"error": "Invalid request or missing ID", "message": str(ve)})
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error deleting category: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Could not delete category", "message": str(e)})

# --- Main Lambda Handler (Router) ---

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # Global categories_table initialization is removed. It's handled in db_utils_categories.py
    # global categories_table
    # if categories_table is None:
    #     if CATEGORIES_TABLE_NAME:
    #         categories_table = dynamodb.Table(CATEGORIES_TABLE_NAME)
    #         logger.info(f"DynamoDB Categories table {CATEGORIES_TABLE_NAME} initialized.")
    #     else:
    #         logger.critical("CRITICAL: CATEGORIES_TABLE_NAME env var not set.")
    #         return create_response(500, {"error": "Server configuration error"})

    logger.debug(f"Received event: {json.dumps(event)}")
    
    user_details = get_user_from_event(event)
    if not user_details or not user_details.get('id'):
        logger.error("Unauthorized: User details or ID missing from token.")
        return create_response(401, {"error": "Unauthorized"})
    user_id = user_details['id']

    http_method = event.get('httpMethod')
    resource = event.get('resource')

    if resource == "/categories":
        if http_method == "POST":
            return create_category_handler(event, user_id)
        elif http_method == "GET":
            return list_categories_handler(event, user_id)
    elif resource == "/categories/{categoryId}":
        if http_method == "GET":
            return get_category_handler(event, user_id)
        elif http_method == "PUT":
            return update_category_handler(event, user_id)
        elif http_method == "DELETE":
            return delete_category_handler(event, user_id)
            
    return create_response(404, {"error": "Not Found: Invalid path or method"})

if __name__ == '__main__':
    # Add placeholder for local testing if utils are not available without AWS context
    # This helps if you run the file directly for syntax checks or very basic tests.
    if 'get_user_from_event' not in globals():
        def get_user_from_event(event): return {"id": "test-user-id"}
        def get_path_param(event, name, required=False, default=None): return default
        def get_query_param(event, name, default=None): return default
        def get_json_body(event): return json.loads(event.get('body', '{}'))
    pass 