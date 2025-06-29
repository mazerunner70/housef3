import json
import os
import boto3
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pydantic import ValidationError

from models.category import Category, CategoryCreate, CategoryUpdate, CategoryRule
from models.transaction import Transaction
from services.category_rule_engine import CategoryRuleEngine, CategorySuggestionStrategy
from utils.db_utils import create_category_in_db, delete_category_from_db, get_category_by_id_from_db, list_categories_by_user_from_db, update_category_in_db, list_user_transactions
from utils.lambda_utils import mandatory_path_parameter, optional_query_parameter
from utils.auth import get_user_from_event

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
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            category_data = CategoryCreate.model_validate_json(body_str)
        except ValidationError as e:
            logger.error(f"Validation error creating category: {str(e)}", exc_info=True)
            return create_response(400, {"error": "Invalid category data", "details": e.errors()})
        except json.JSONDecodeError:
            logger.error("JSONDecodeError creating category: Invalid JSON format")
            return create_response(400, {"error": "Invalid JSON format in request body"})

        new_category_data = category_data.model_dump()
        new_category = Category(userId=user_id, **new_category_data)
        created_category = create_category_in_db(new_category)
        return create_response(201, created_category.model_dump())
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error creating category: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e: 
        logger.error(f"Error creating category: {str(e)}", exc_info=True)
        return create_response(400, {"error": "Invalid category data or server error", "message": str(e)})

def list_categories_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        parent_category_id = optional_query_parameter(event, 'parentCategoryId') 
        top_level_only_str = optional_query_parameter(event, 'topLevelOnly') or 'false' # Handle default
        top_level_only = top_level_only_str.lower() == 'true'
        
        # Use new DB util function
        if parent_category_id is not None:
             categories = list_categories_by_user_from_db(user_id, parent_category_id=uuid.UUID(parent_category_id))
        else: 
             categories = list_categories_by_user_from_db(user_id, top_level_only=top_level_only)
        return create_response(200, [cat.model_dump() for cat in categories])
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error listing categories: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Could not list categories", "message": str(e)})

def get_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    try:
        category_id = mandatory_path_parameter(event, 'categoryId')
        # No need for: if category_id is None: as mandatory_path_parameter raises ValueError
        # Use new DB util function
        category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
        if category:
            return create_response(200, category.model_dump())
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
        category_id = mandatory_path_parameter(event, 'categoryId')
        # No need for: if category_id is None:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            update_data_model = CategoryUpdate.model_validate_json(body_str)
        except ValidationError as e:
            logger.warning(f"Validation error updating category {category_id}: {str(e)}", exc_info=True)
            return create_response(400, {"error": "Invalid update data", "details": e.errors()})
        except json.JSONDecodeError:
            logger.warning(f"JSONDecodeError updating category {category_id}: Invalid JSON format")
            return create_response(400, {"error": "Invalid JSON format in request body"})

        update_payload = update_data_model.model_dump(exclude_unset=True)
        if not update_payload: # If all fields were optional and none were provided
            return create_response(400, {"error": "Update payload is empty. No fields to update."})

        # Use new DB util function
        updated_category = update_category_in_db(uuid.UUID(category_id), user_id, update_payload)
        if updated_category:
            return create_response(200, updated_category.model_dump())
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
        category_id = mandatory_path_parameter(event, 'categoryId')
        # No need for: if category_id is None:
        # Use new DB util function
        if delete_category_from_db(uuid.UUID(category_id), user_id):
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

# --- Category Rule Testing & Suggestion Handlers ---

def test_category_rule_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Test a category rule against user's transactions
    POST /categories/test-rule
    Body: { "fieldToMatch": "description", "condition": "contains", "value": "AMAZON" }
    """
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            rule_data = json.loads(body_str)
            rule = CategoryRule(
                fieldToMatch=rule_data.get('fieldToMatch', 'description'),
                condition=rule_data.get('condition', 'contains'),
                value=rule_data.get('value', '')
            )
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Error parsing rule data: {str(e)}")
            return create_response(400, {"error": "Invalid rule data", "details": str(e)})
        
        # Get optional parameters
        limit = int(event.get('queryStringParameters', {}).get('limit', 100))
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Test rule against transactions
        matching_transactions = rule_engine.test_rule_against_transactions(
            user_id=user_id,
            rule=rule,
            field_to_match=rule.fieldToMatch,
            limit=limit
        )
        
        # Serialize transactions
        serialized_transactions = []
        for transaction in matching_transactions:
            tx_data = transaction.model_dump(by_alias=True)
            # Convert Decimals to strings for JSON serialization
            if tx_data.get("amount") is not None:
                tx_data["amount"] = str(tx_data["amount"])
            if tx_data.get("balance") is not None:
                tx_data["balance"] = str(tx_data["balance"])
            serialized_transactions.append(tx_data)
        
        return create_response(200, {
            "matchingTransactions": serialized_transactions,
            "totalMatches": len(matching_transactions),
            "rule": rule.model_dump(),
            "limit": limit
        })
        
    except Exception as e:
        logger.error(f"Error testing category rule: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def generate_category_suggestions_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Generate category suggestions for a transaction
    POST /transactions/{transactionId}/category-suggestions
    """
    try:
        transaction_id = mandatory_path_parameter(event, 'transactionId')
        
        # Get transaction from database (placeholder - would need actual implementation)
        # For now, we'll use the transaction from user transactions list
        transactions, _, _ = list_user_transactions(user_id, limit=1000)
        transaction = next((tx for tx in transactions if str(tx.transaction_id) == transaction_id), None)
        
        if not transaction:
            return create_response(404, {"error": "Transaction not found"})
        
        # Get optional parameters
        query_params = event.get('queryStringParameters', {})
        strategy = query_params.get('strategy', 'all_matches')
        
        try:
            suggestion_strategy = CategorySuggestionStrategy(strategy)
        except ValueError:
            suggestion_strategy = CategorySuggestionStrategy.ALL_MATCHES
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine(suggestion_strategy)
        
        # Generate suggestions
        suggestions = rule_engine.categorize_transaction(
            transaction=transaction,
            user_id=user_id,
            create_suggestions=False  # Just return suggestions, don't modify transaction
        )
        
        # Serialize suggestions
        serialized_suggestions = []
        for suggestion in suggestions:
            suggestion_data = suggestion.model_dump(by_alias=True)
            serialized_suggestions.append(suggestion_data)
        
        return create_response(200, {
            "transactionId": transaction_id,
            "suggestions": serialized_suggestions,
            "totalSuggestions": len(suggestions),
            "strategy": strategy
        })
        
    except ValueError as ve:
        logger.warning(f"Missing transaction ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error generating category suggestions: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def apply_category_rules_bulk_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Apply category rules to transactions in bulk
    POST /categories/apply-rules-bulk
    Body: { "categoryId": "uuid", "transactionIds": ["uuid1", "uuid2"], "strategy": "all_matches" }
    """
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        category_id = body_data.get('categoryId')
        transaction_ids = body_data.get('transactionIds')
        strategy = body_data.get('strategy', 'all_matches')
        
        try:
            suggestion_strategy = CategorySuggestionStrategy(strategy)
        except ValueError:
            suggestion_strategy = CategorySuggestionStrategy.ALL_MATCHES
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine(suggestion_strategy)
        
        # Apply rules in bulk
        results = rule_engine.apply_category_rules_bulk(
            user_id=user_id,
            category_id=category_id,
            transaction_ids=transaction_ids
        )
        
        return create_response(200, {
            "results": results,
            "strategy": strategy
        })
        
    except Exception as e:
        logger.error(f"Error applying category rules in bulk: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def validate_regex_pattern_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Validate a regex pattern
    POST /categories/validate-regex
    Body: { "pattern": "AM[AZ]ON.*" }
    """
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
            pattern = body_data.get('pattern', '')
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        if not pattern:
            return create_response(400, {"error": "Pattern is required"})
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Validate pattern
        is_valid, error_message = rule_engine.validate_regex_pattern(pattern)
        
        return create_response(200, {
            "pattern": pattern,
            "isValid": is_valid,
            "errorMessage": error_message
        })
        
    except Exception as e:
        logger.error(f"Error validating regex pattern: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def generate_simple_pattern_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Generate a simple pattern from sample descriptions
    POST /categories/generate-pattern
    Body: { "descriptions": ["AMAZON.COM PURCHASE", "AMAZON PRIME", "AMAZON MARKETPLACE"] }
    """
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
            descriptions = body_data.get('descriptions', [])
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        if not descriptions or not isinstance(descriptions, list):
            return create_response(400, {"error": "Descriptions array is required"})
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Generate pattern
        generated_pattern = rule_engine.generate_simple_pattern(descriptions)
        
        return create_response(200, {
            "descriptions": descriptions,
            "generatedPattern": generated_pattern,
            "confidence": 0.8 if generated_pattern else 0.0  # Simple confidence scoring
        })
        
    except Exception as e:
        logger.error(f"Error generating simple pattern: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

# --- Main Lambda Handler (Router) ---

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Get route from event
        route = event.get('routeKey')
        if not route:
            return create_response(400, {"message": "Missing route key"})
            
        # Get user from event
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user.get('id')
        if not user_id:
            return create_response(401, {"message": "Unauthorized"})
            
        logger.info(f"Processing {route} request for user {user_id}")

        if route == "POST /categories":
            return create_category_handler(event, user_id)
        elif route == "GET /categories":
            return list_categories_handler(event, user_id)
        elif route == "GET /categories/{categoryId}":
            return get_category_handler(event, user_id)
        elif route == "PUT /categories/{categoryId}":
            return update_category_handler(event, user_id)
        elif route == "DELETE /categories/{categoryId}":
            return delete_category_handler(event, user_id)
        elif route == "POST /categories/test-rule":
            return test_category_rule_handler(event, user_id)
        elif route == "POST /transactions/{transactionId}/category-suggestions":
            return generate_category_suggestions_handler(event, user_id)
        elif route == "POST /categories/apply-rules-bulk":
            return apply_category_rules_bulk_handler(event, user_id)
        elif route == "POST /categories/validate-regex":
            return validate_regex_pattern_handler(event, user_id)
        elif route == "POST /categories/generate-pattern":
            return generate_simple_pattern_handler(event, user_id)
        else:
            return create_response(404, {"error": "Not Found: Invalid path or method"})


