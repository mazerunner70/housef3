import json
import os
import boto3
import logging
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from pydantic import ValidationError

from models.category import Category, CategoryCreate, CategoryUpdate, CategoryRule, MatchCondition, CategorySuggestionStrategy
from models.transaction import Transaction
from services.category_rule_engine import CategoryRuleEngine
from utils.db_utils import create_category_in_db, delete_category_from_db, get_category_by_id_from_db, list_categories_by_user_from_db, update_category_in_db, list_user_transactions
from utils.lambda_utils import mandatory_path_parameter, optional_query_parameter, mandatory_body_parameter, optional_body_parameter, mandatory_query_parameter
from utils.auth import get_user_from_event

# Setup logging (ensure it's configured after potential path adjustments for utils if utils also configure logging)
logger = logging.getLogger(__name__) # Use __name__ for module-specific logger
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

# Database tables are initialized by db_utils when functions are called

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

# --- DRY Utility Functions ---

def parse_and_validate_json(event: Dict[str, Any], model_class):
    """Parse JSON body and validate using Pydantic model."""
    body_str = event.get('body')
    if not body_str:
        return None, create_response(400, {"message": "Request body is missing or empty"})
    
    try:
        return model_class.model_validate_json(body_str), None
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return None, create_response(400, {"message": "Invalid request data", "details": e.errors()})
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in request body")
        return None, create_response(400, {"message": "Invalid JSON format in request body"})

def serialize_model(model, success_message: Optional[str] = None) -> Dict[str, Any]:
    """Serialize a Pydantic model to JSON-safe dict."""
    result = model.model_dump(by_alias=True, mode='json')
    if success_message:
        return {"message": success_message, "data": result}
    return result

def serialize_model_list(models: List, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Serialize a list of Pydantic models to JSON-safe dict."""
    result = [model.model_dump(by_alias=True, mode='json') for model in models]
    response: Dict[str, Any] = {"data": result}
    if metadata:
        response["metadata"] = metadata
    return response

def serialize_transactions(transactions: List[Transaction], additional_data: Optional[Dict] = None) -> List[Dict]:
    """Serialize transactions with proper Decimal handling."""
    serialized = []
    for transaction in transactions:
        tx_data = transaction.model_dump(by_alias=True, mode='json')
        # Convert Decimals to strings for JSON serialization
        if tx_data.get("amount") is not None:
            tx_data["amount"] = str(tx_data["amount"])
        if tx_data.get("balance") is not None:
            tx_data["balance"] = str(tx_data["balance"])
        
        # Add any additional data
        if additional_data and str(transaction.transaction_id) in additional_data:
            tx_data.update(additional_data[str(transaction.transaction_id)])
        
        serialized.append(tx_data)
    return serialized

def get_rule_engine() -> CategoryRuleEngine:
    """Get a CategoryRuleEngine instance."""
    return CategoryRuleEngine()

def handle_category_not_found(category_id: str) -> Dict[str, Any]:
    """Standard response for category not found."""
    return create_response(404, {"message": "Category not found or access denied"})

def handle_validation_error(operation: str, error: Exception) -> Dict[str, Any]:
    """Standard response for validation errors."""
    logger.error(f"Validation error {operation}: {str(error)}")
    return create_response(400, {"message": str(error)})

def handle_server_error(operation: str, error: Exception) -> Dict[str, Any]:
    """Standard response for server errors."""
    logger.error(f"Error {operation}: {str(error)}")
    return create_response(500, {"message": f"Error {operation}"})


# --- Specific Operation Handlers (Refactored to use db_utils_categories) ---

def create_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create a new category."""
    try:
        # Parse and validate JSON using utility function
        category_data, error_response = parse_and_validate_json(event, CategoryCreate)
        if error_response:
            return error_response
        
        # category_data is guaranteed to be valid CategoryCreate here
        assert category_data is not None
        
        # Convert CategoryCreate to Category
        new_category_data = category_data.model_dump()
        category = Category(userId=user_id, **new_category_data)
        created_category = create_category_in_db(category)
        
        return create_response(201, {
            'message': 'Category created successfully',
            'category': serialize_model(created_category)
        })
        
    except Exception as e:
        return handle_server_error("creating category", e)

def list_categories_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """List all categories for the current user."""
    try:
        # Get optional query parameters
        parent_category_id = optional_query_parameter(event, 'parentCategoryId')
        top_level_only_str = optional_query_parameter(event, 'topLevelOnly') or 'false'
        top_level_only = top_level_only_str.lower() == 'true'
        
        # Get categories from database
        if parent_category_id:
            categories = list_categories_by_user_from_db(user_id, parent_category_id=uuid.UUID(parent_category_id))
        else:
            categories = list_categories_by_user_from_db(user_id, top_level_only=top_level_only)
        
        # Use utility function for serialization
        metadata = {
            'totalCategories': len(categories),
            'parentCategoryId': parent_category_id,
            'topLevelOnly': top_level_only
        }
        
        response_data = serialize_model_list(categories, metadata)
        return create_response(200, {
            'categories': response_data['data'],
            'metadata': response_data['metadata']
        })
        
    except Exception as e:
        return handle_server_error("listing categories", e)

def get_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get a specific category by ID."""
    try:
        # Get category ID from path parameters
        category_id = mandatory_path_parameter(event, 'categoryId')
        
        # Get the category
        category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
        if not category:
            return handle_category_not_found(category_id)
        
        return create_response(200, {
            'category': serialize_model(category)
        })
        
    except ValueError as e:
        return handle_validation_error("retrieving category", e)
    except Exception as e:
        return handle_server_error("retrieving category", e)

def update_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Update an existing category."""
    try:
        # Get category ID from path parameters
        category_id = mandatory_path_parameter(event, 'categoryId')
        
        # Parse and validate JSON using utility function
        update_data, error_response = parse_and_validate_json(event, CategoryUpdate)
        if error_response:
            return error_response
        
        # update_data is guaranteed to be valid CategoryUpdate here
        assert update_data is not None
        
        # Convert CategoryUpdate to dict, excluding unset fields
        update_payload = update_data.model_dump(exclude_unset=True)
        if not update_payload:
            return create_response(400, {"message": "No fields provided for update"})
        
        # Update the category
        updated_category = update_category_in_db(uuid.UUID(category_id), user_id, update_payload)
        if not updated_category:
            return handle_category_not_found(category_id)
        
        return create_response(200, {
            'message': 'Category updated successfully',
            'category': serialize_model(updated_category)
        })
        
    except ValueError as e:
        return handle_validation_error("updating category", e)
    except Exception as e:
        return handle_server_error("updating category", e)

def delete_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Delete a category."""
    try:
        # Get category ID from path parameters
        category_id = mandatory_path_parameter(event, 'categoryId')
        
        # Delete the category
        if delete_category_from_db(uuid.UUID(category_id), user_id):
            return create_response(200, {
                'message': 'Category deleted successfully',
                'categoryId': category_id
            })
        else:
            return handle_category_not_found(category_id)
        
    except ValueError as e:
        # Special handling for child categories error
        if "it has child categories" in str(e):
            return handle_validation_error("deleting category", e)
        return handle_validation_error("deleting category", e)
    except Exception as e:
        return handle_server_error("deleting category", e)

def get_category_hierarchy_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Get category hierarchy for the user
    GET /categories/hierarchy
    Returns hierarchical structure of all user categories with parent-child relationships
    """
    try:
        # Get all user categories
        categories = list_categories_by_user_from_db(user_id)
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Build category hierarchy using existing method
        hierarchy_dict = rule_engine.build_category_hierarchy(categories)
        
        # Convert to list of root-level hierarchies (categories without parents)
        root_hierarchies = []
        for cat_id, hierarchy in hierarchy_dict.items():
            if hierarchy.category.parentCategoryId is None:
                root_hierarchies.append(hierarchy)
        
        # Sort by category name for consistent ordering
        root_hierarchies.sort(key=lambda h: h.category.name)
        
        # Serialize hierarchies
        serialized_hierarchies = []
        for hierarchy in root_hierarchies:
            serialized_hierarchy = serialize_hierarchy(hierarchy)
            serialized_hierarchies.append(serialized_hierarchy)
        
        return create_response(200, serialized_hierarchies)
        
    except ConnectionError as ce:
        logger.critical(f"DB Connection Error getting category hierarchy: {str(ce)}", exc_info=True)
        return create_response(500, {"error": "Server configuration error", "message": "Database not initialized"})
    except Exception as e:
        logger.error(f"Error getting category hierarchy: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Could not get category hierarchy", "message": str(e)})

def serialize_hierarchy(hierarchy):
    """Helper function to serialize CategoryHierarchy for JSON response"""
    return {
        "category": hierarchy.category.model_dump(by_alias=True, mode='json'),
        "children": [serialize_hierarchy(child) for child in hierarchy.children],
        "depth": hierarchy.depth,
        "fullPath": hierarchy.full_path,
        "inheritedRules": [rule.model_dump(by_alias=True, mode='json') for rule in hierarchy.inherited_rules]
    }

# --- Category Rule Testing & Suggestion Handlers (Phase 2.1 Enhanced) ---

def test_category_rule_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Test a category rule against user's transactions."""
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"message": "Request body is missing or empty"})
        
        try:
            request_data = json.loads(body_str)
            
            # Extract rule from the request (frontend sends { rule: {...}, limit: 50 })
            if 'rule' not in request_data:
                return create_response(400, {"message": "Missing 'rule' field in request body"})
            
            rule_data = request_data['rule']
            
            # Create enhanced CategoryRule with Phase 2.1 fields using Pydantic parsing
            # This ensures proper alias mapping from camelCase to snake_case
            rule = CategoryRule(**rule_data)
            
            # Get limit from request body or query params, defaulting to 100
            limit = request_data.get('limit', 100)
            if isinstance(limit, str):
                limit = int(limit)
                
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.error(f"Error parsing rule data: {str(e)}")
            return create_response(400, {"message": "Invalid rule data"})
        
        # Also check query parameters for limit as fallback
        query_limit = optional_query_parameter(event, 'limit')
        if query_limit:
            limit = int(query_limit)
        
        # Initialize rule engine using utility function
        rule_engine = get_rule_engine()
        
        # Test rule against transactions
        matching_transactions = rule_engine.test_rule_against_transactions(
            user_id=user_id,
            rule=rule,
            limit=limit
        )
        
        # Calculate confidence scores for matched transactions
        confidence_data = {}
        for transaction in matching_transactions:
            confidence = rule_engine.calculate_rule_confidence(rule, transaction)
            confidence_data[str(transaction.transaction_id)] = {"matchConfidence": confidence}
        
        # Use utility function for transaction serialization
        serialized_transactions = serialize_transactions(matching_transactions, confidence_data)
        confidence_scores = [data["matchConfidence"] for data in confidence_data.values()]

        return create_response(200, {
            "matchingTransactions": serialized_transactions,
            "totalMatches": len(matching_transactions),
            "rule": serialize_model(rule),
            "limit": limit,
            "averageConfidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        })
        
    except Exception as e:
        return handle_server_error("testing category rule", e)

def preview_category_matches_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Preview all transactions that would match a category's rules
    GET /categories/{categoryId}/preview-matches
    """
    try:
        category_id = mandatory_path_parameter(event, 'categoryId')
        
        # Get category from database
        category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
        if not category:
            return create_response(404, {"error": "Category not found or access denied"})
        
        # Get optional parameters
        query_params = event.get('queryStringParameters', {}) or {}
        include_inherited = query_params.get('includeInherited', 'true').lower() == 'true'
        limit = int(query_params.get('limit', 200))
        
        # Get all user categories for hierarchy processing
        all_categories = list_categories_by_user_from_db(user_id)
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Get effective rules for this category (including inherited)
        effective_rules = rule_engine.get_effective_rules(category, all_categories)
        
        # Get user transactions
        transactions, _, _ = list_user_transactions(user_id, limit=limit * 2)
        
        # Find matching transactions
        matching_transactions = []
        rule_matches = {}  # Track which rules matched each transaction
        
        for transaction in transactions:
            matched_rules = []
            for rule in effective_rules:
                if rule_engine.rule_matches_transaction(rule, transaction):
                    confidence = rule_engine.calculate_rule_confidence(rule, transaction)
                    matched_rules.append({
                        "ruleId": rule.rule_id,
                        "rule": rule.model_dump(by_alias=True, mode='json'),
                        "confidence": confidence
                    })
            
            if matched_rules:
                matching_transactions.append(transaction)
                rule_matches[str(transaction.transaction_id)] = matched_rules
                
                if len(matching_transactions) >= limit:
                    break
        
                # Serialize transactions
        serialized_transactions = []
        for transaction in matching_transactions:
            tx_data = transaction.model_dump(by_alias=True, mode='json')
            # Convert Decimals to strings for JSON serialization
            if tx_data.get("amount") is not None:
                tx_data["amount"] = str(tx_data["amount"])
            if tx_data.get("balance") is not None:
                tx_data["balance"] = str(tx_data["balance"])
            # Add rule match information
            tx_data["matchedRules"] = rule_matches.get(str(transaction.transaction_id), [])
            serialized_transactions.append(tx_data)

        return create_response(200, {
            "categoryId": category_id,
            "categoryName": category.name,
            "matchingTransactions": serialized_transactions,
            "totalMatches": len(matching_transactions),
            "effectiveRules": [rule.model_dump(by_alias=True, mode='json') for rule in effective_rules],
            "totalRules": len(effective_rules),
            "includeInherited": include_inherited,
            "limit": limit
        })
        
    except ValueError as ve:
        logger.warning(f"Missing category ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error previewing category matches: {str(e)}", exc_info=True)
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
        query_params = event.get('queryStringParameters', {}) or {}
        strategy = query_params.get('strategy', 'all_matches')
        
        try:
            suggestion_strategy = CategorySuggestionStrategy(strategy)
        except ValueError:
            suggestion_strategy = CategorySuggestionStrategy.ALL_MATCHES
        
        # Get all user categories
        user_categories = list_categories_by_user_from_db(user_id)
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Generate suggestions using Phase 2.1 enhanced method
        suggestions = rule_engine.categorize_transaction(
            transaction=transaction,
            user_categories=user_categories,
            suggestion_strategy=suggestion_strategy
        )
        
        # Serialize suggestions
        serialized_suggestions = []
        for suggestion in suggestions:
            suggestion_data = suggestion.model_dump(by_alias=True, mode='json')
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
    Body: { "transactionIds": ["uuid1", "uuid2"], "strategy": "all_matches" }
    """
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        transaction_ids = body_data.get('transactionIds')
        strategy = body_data.get('strategy', 'all_matches')
        
        try:
            suggestion_strategy = CategorySuggestionStrategy(strategy)
        except ValueError:
            suggestion_strategy = CategorySuggestionStrategy.ALL_MATCHES
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Apply rules in bulk using Phase 2.1 enhanced method
        results = rule_engine.apply_category_rules_bulk(
            user_id=user_id,
            transaction_ids=transaction_ids,
            suggestion_strategy=suggestion_strategy
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
    Body: { "pattern": "AMAZON.*" }
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
        
        # Validate pattern using Phase 2.1 enhanced method
        validation_result = rule_engine.validate_regex_pattern(pattern)
        
        return create_response(200, {
            "pattern": pattern,
            "valid": validation_result['valid'],
            "message": validation_result['message'],
            "suggestions": validation_result['suggestions']
        })
        
    except Exception as e:
        logger.error(f"Error validating regex pattern: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def generate_pattern_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Generate a pattern from sample descriptions
    POST /categories/generate-pattern
    Body: { 
        "descriptions": ["AMAZON.COM PURCHASE", "AMAZON PRIME", "AMAZON MARKETPLACE"],
        "patternType": "contains"  // or "regex"
    }
    """
    try:
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            body_data = json.loads(body_str)
            descriptions = body_data.get('descriptions', [])
            pattern_type = body_data.get('patternType', 'contains')
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        if not descriptions or not isinstance(descriptions, list):
            return create_response(400, {"error": "Descriptions array is required"})
        
        # Initialize rule engine
        rule_engine = CategoryRuleEngine()
        
        # Generate pattern using Phase 2.1 enhanced method
        pattern_result = rule_engine.generate_pattern_from_descriptions(
            descriptions=descriptions,
            pattern_type=pattern_type
        )
        
        return create_response(200, {
            "descriptions": descriptions,
            "patternType": pattern_type,
            "generatedPattern": pattern_result.get('pattern', ''),
            "confidence": pattern_result.get('confidence', 0.0)
        })
        
    except Exception as e:
        logger.error(f"Error generating pattern: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

# --- Category Rule Management Handlers (Individual Rules) ---

def add_rule_to_category_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Add a rule to a category
    POST /categories/{categoryId}/rules
    Body: { "fieldToMatch": "description", "condition": "contains", "value": "AMAZON", ... }
    """
    try:
        category_id = mandatory_path_parameter(event, 'categoryId')
        
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            rule_data = json.loads(body_str)
            # Create new rule with generated ID
            rule = CategoryRule(**rule_data)
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.error(f"Error parsing rule data: {str(e)}")
            return create_response(400, {"error": "Invalid rule data", "details": str(e)})
        
        # Get existing category
        category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
        if not category:
            return create_response(404, {"error": "Category not found or access denied"})
        
        # Diagnostic logging
        logger.info(f"DIAG: Retrieved category {category_id} with {len(category.rules)} existing rules")
        for i, existing_rule in enumerate(category.rules):
            logger.info(f"DIAG: Existing rule {i}: type={type(existing_rule)}, is_dict={isinstance(existing_rule, dict)}, is_CategoryRule={isinstance(existing_rule, CategoryRule)}")
            if isinstance(existing_rule, dict):
                logger.info(f"DIAG: Dict rule {i} keys: {list(existing_rule.keys())}")
        
        # Ensure all existing rules are CategoryRule objects and add the new rule
        rules_list = []
        for i, existing_rule in enumerate(category.rules):
            if isinstance(existing_rule, CategoryRule):
                logger.info(f"DIAG: Rule {i} is already CategoryRule, appending directly")
                rules_list.append(existing_rule)
            elif isinstance(existing_rule, dict):
                logger.info(f"DIAG: Rule {i} is dict, converting to CategoryRule")
                # Convert string amount fields back to Decimal objects if needed
                if 'amountMin' in existing_rule and existing_rule['amountMin'] is not None:
                    existing_rule['amountMin'] = Decimal(str(existing_rule['amountMin']))
                if 'amountMax' in existing_rule and existing_rule['amountMax'] is not None:
                    existing_rule['amountMax'] = Decimal(str(existing_rule['amountMax']))
                
                # Convert dict to CategoryRule object
                converted_rule = CategoryRule(**existing_rule)
                rules_list.append(converted_rule)
                logger.info(f"DIAG: Successfully converted dict rule {i} to CategoryRule")
            else:
                logger.warning(f"DIAG: Rule {i} has unexpected type {type(existing_rule)}, skipping")
        
        # Add the new rule
        logger.info(f"DIAG: Adding new rule: type={type(rule)}")
        rules_list.append(rule)
        logger.info(f"DIAG: Final rules list has {len(rules_list)} rules")
        
        # Update category in database
        updated_category = update_category_in_db(uuid.UUID(category_id), user_id, {"rules": rules_list})
        if not updated_category:
            return create_response(500, {"error": "Failed to update category with new rule"})
        
        return create_response(201, updated_category.model_dump(by_alias=True, mode='json'))
        
    except ValueError as ve:
        logger.warning(f"Invalid category ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error adding rule to category: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def update_category_rule_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Update a specific rule in a category
    PUT /categories/{categoryId}/rules/{ruleId}
    Body: { "value": "NEW VALUE", "enabled": true, ... }
    """
    try:
        category_id = mandatory_path_parameter(event, 'categoryId')
        rule_id = mandatory_path_parameter(event, 'ruleId')
        
        body_str = event.get('body')
        if not body_str:
            return create_response(400, {"error": "Request body is missing or empty"})
        
        try:
            update_data = json.loads(body_str)
        except json.JSONDecodeError:
            return create_response(400, {"error": "Invalid JSON format in request body"})
        
        # Get existing category
        category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
        if not category:
            return create_response(404, {"error": "Category not found or access denied"})
        
        # Find rule to update
        rule_index = None
        for i, rule in enumerate(category.rules):
            if rule.rule_id == rule_id:
                rule_index = i
                break
        
        if rule_index is None:
            return create_response(404, {"error": "Rule not found in category"})
        
        # Update rule fields
        existing_rule = category.rules[rule_index]
        rule_dict = existing_rule.model_dump()
        rule_dict.update(update_data)
        
        try:
            updated_rule = CategoryRule(**rule_dict)
            category.rules[rule_index] = updated_rule
        except ValidationError as e:
            return create_response(400, {"error": "Invalid rule update data", "details": e.errors()})
        
        # Update category in database
        updated_category = update_category_in_db(uuid.UUID(category_id), user_id, {"rules": category.rules})
        if not updated_category:
            return create_response(500, {"error": "Failed to update category rule"})
        
        return create_response(200, updated_category.model_dump(by_alias=True, mode='json'))
        
    except ValueError as ve:
        logger.warning(f"Invalid category or rule ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error updating category rule: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

def delete_category_rule_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Delete a specific rule from a category
    DELETE /categories/{categoryId}/rules/{ruleId}
    """
    try:
        category_id = mandatory_path_parameter(event, 'categoryId')
        rule_id = mandatory_path_parameter(event, 'ruleId')
        
        # Get existing category
        category = get_category_by_id_from_db(uuid.UUID(category_id), user_id)
        if not category:
            return create_response(404, {"error": "Category not found or access denied"})
        
        # Find and remove rule
        original_count = len(category.rules)
        category.rules = [rule for rule in category.rules if rule.rule_id != rule_id]
        
        if len(category.rules) == original_count:
            return create_response(404, {"error": "Rule not found in category"})
        
        # Update category in database
        updated_category = update_category_in_db(uuid.UUID(category_id), user_id, {"rules": category.rules})
        if not updated_category:
            return create_response(500, {"error": "Failed to delete category rule"})
        
        return create_response(200, updated_category.model_dump(by_alias=True, mode='json'))
        
    except ValueError as ve:
        logger.warning(f"Invalid category or rule ID: {str(ve)}")
        return create_response(400, {"error": str(ve)})
    except Exception as e:
        logger.error(f"Error deleting category rule: {str(e)}", exc_info=True)
        return create_response(500, {"error": "Internal server error", "message": str(e)})

# --- Phase 4.1 Pattern Extraction & Smart Category Creation Handlers ---

def suggest_category_from_transaction_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Suggest category name and type from transaction details."""
    try:
        from services.pattern_extraction_service import PatternExtractionService
        from utils.db_utils import get_transactions_table
        from decimal import Decimal
        
        # Get either transaction ID or direct transaction data
        transaction_id = optional_body_parameter(event, 'transactionId')
        description = optional_body_parameter(event, 'description')
        amount = optional_body_parameter(event, 'amount')
        
        if not transaction_id and not description:
            return create_response(400, {"message": "Either 'transactionId' or 'description' is required"})
        
        # Initialize pattern extraction service
        extractor = PatternExtractionService()
        
        # Handle transaction ID or direct transaction data
        if transaction_id:
            # Get transaction from database
            response = get_transactions_table().get_item(Key={'transactionId': transaction_id})
            if 'Item' not in response:
                return create_response(404, {"message": "Transaction not found"})
            
            transaction = Transaction.from_dynamodb_item(response['Item'])
            if transaction.user_id != user_id:
                return create_response(403, {"message": "Unauthorized to access this transaction"})
        else:
            # Create temporary transaction object from provided data
            transaction = Transaction(
                userId=user_id,
                fileId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=0,  # Not used for pattern extraction
                description=description,
                amount=Decimal(str(amount or 0))
            )
        
        # Generate category suggestion
        suggestion = extractor.suggest_category_from_transaction(transaction)
        
        if not suggestion:
            return create_response(200, {
                "categoryName": "General",
                "categoryType": "EXPENSE",
                "confidence": 0.5,
                "icon": "📁",
                "suggestedPatterns": []
            })
        
        return create_response(200, {
            "categoryName": suggestion.name,
            "categoryType": suggestion.category_type,
            "confidence": suggestion.confidence,
            "icon": suggestion.icon,
            "suggestedPatterns": [
                {
                    "pattern": p.pattern,
                    "confidence": p.confidence,
                    "field": p.field,
                    "condition": p.condition.value,
                    "explanation": p.explanation
                }
                for p in suggestion.suggested_patterns
            ]
        })
        
    except Exception as e:
        logger.error(f"Error suggesting category from transaction: {str(e)}")
        return create_response(500, {"message": "Error suggesting category from transaction"})

def extract_patterns_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Extract rule patterns from transaction description(s)."""
    try:
        from services.pattern_extraction_service import PatternExtractionService
        
        # Get descriptions from request body
        descriptions = mandatory_body_parameter(event, 'descriptions')
        
        if not isinstance(descriptions, list) or not descriptions:
            return create_response(400, {"message": "Field 'descriptions' must be a non-empty array"})
        
        # Initialize pattern extraction service
        extractor = PatternExtractionService()
        
        # Extract patterns from all descriptions and find common ones
        all_patterns = []
        for description in descriptions:
            patterns = extractor.extract_patterns_from_description(description)
            all_patterns.extend(patterns)
        
        # Group by pattern and select best ones
        pattern_groups = {}
        for pattern in all_patterns:
            key = pattern.pattern.lower()
            if key in pattern_groups:
                pattern_groups[key].confidence = max(pattern_groups[key].confidence, pattern.confidence)
                pattern_groups[key].match_count += 1
            else:
                pattern_groups[key] = pattern
        
        # Sort by confidence and return top patterns
        best_patterns = sorted(pattern_groups.values(), key=lambda x: x.confidence, reverse=True)[:5]
        
        return create_response(200, {
            "patterns": [
                {
                    "pattern": p.pattern,
                    "confidence": p.confidence,
                    "matchCount": p.match_count,
                    "field": p.field,
                    "condition": p.condition.value,
                    "explanation": p.explanation
                }
                for p in best_patterns
            ],
            "totalDescriptions": len(descriptions),
            "totalPatterns": len(best_patterns)
        })
        
    except ValueError as e:
        logger.error(f"Validation error extracting patterns: {str(e)}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error extracting patterns: {str(e)}")
        return create_response(500, {"message": "Error extracting patterns"})

def create_category_with_rule_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Create category with pre-populated rule."""
    try:
        from services.pattern_extraction_service import PatternExtractionService
        from models.category import MatchCondition
        
        # Extract required parameters
        category_name = mandatory_body_parameter(event, 'categoryName')
        category_type = mandatory_body_parameter(event, 'categoryType')
        pattern = mandatory_body_parameter(event, 'pattern')
        
        # Extract optional parameters
        field_to_match = optional_body_parameter(event, 'fieldToMatch') or 'description'
        condition_str = optional_body_parameter(event, 'condition') or 'contains'
        
        # Validate condition
        try:
            condition = MatchCondition(condition_str)
        except ValueError:
            return create_response(400, {"message": f"Invalid condition: {condition_str}"})
        
        # Initialize pattern extraction service
        extractor = PatternExtractionService()
        
        # Create category with rule structure
        result = extractor.create_category_with_rule(
            category_name=category_name,
            category_type=category_type,
            pattern=pattern,
            field_to_match=field_to_match,
            condition=condition
        )
        
        if not result.get('success'):
            return create_response(500, {"message": result.get('error', 'Failed to create category structure')})
        
        # Create the category in the database
        category_data = result['category']
        category_data['userId'] = user_id  # Add user ID
        
        try:
            category = Category(**category_data)
            created_category = create_category_in_db(category)
            
            return create_response(201, {
                'message': 'Category with rule created successfully',
                "category": created_category.model_dump(by_alias=True, mode='json'),
                "rule": result['rule']
            })
            
        except ValidationError as e:
            logger.error(f"Validation error creating category: {str(e)}")
            return create_response(400, {"message": "Invalid category data"})
        
    except ValueError as e:
        logger.error(f"Validation error creating category with rule: {str(e)}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error creating category with rule: {str(e)}")
        return create_response(500, {"message": "Error creating category with rule"})

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

        # Basic CRUD operations
        if route == "POST /categories":
            return create_category_handler(event, user_id)
        elif route == "GET /categories":
            return list_categories_handler(event, user_id)
        elif route == "GET /categories/hierarchy":
            return get_category_hierarchy_handler(event, user_id)
        elif route == "GET /categories/{categoryId}":
            return get_category_handler(event, user_id)
        elif route == "PUT /categories/{categoryId}":
            return update_category_handler(event, user_id)
        elif route == "DELETE /categories/{categoryId}":
            return delete_category_handler(event, user_id)
        
        # Phase 2.1 Rule Testing & Preview APIs
        elif route == "POST /categories/test-rule":
            return test_category_rule_handler(event, user_id)
        elif route == "GET /categories/{categoryId}/preview-matches":
            return preview_category_matches_handler(event, user_id)
        elif route == "POST /categories/validate-regex":
            return validate_regex_pattern_handler(event, user_id)
        elif route == "POST /categories/generate-pattern":
            return generate_pattern_handler(event, user_id)
        
        # Category suggestion and bulk operations
        elif route == "POST /transactions/{transactionId}/category-suggestions":
            return generate_category_suggestions_handler(event, user_id)
        elif route == "POST /categories/apply-rules-bulk":
            return apply_category_rules_bulk_handler(event, user_id)
        
        # Category rule management
        elif route == "POST /categories/{categoryId}/rules":
            return add_rule_to_category_handler(event, user_id)
        elif route == "PUT /categories/{categoryId}/rules/{ruleId}":
            return update_category_rule_handler(event, user_id)
        elif route == "DELETE /categories/{categoryId}/rules/{ruleId}":
            return delete_category_rule_handler(event, user_id)
        
        # Phase 4.1 Pattern Extraction & Smart Category Creation
        elif route == "POST /categories/suggest-from-transaction":
            return suggest_category_from_transaction_handler(event, user_id)
        elif route == "POST /categories/extract-patterns":
            return extract_patterns_handler(event, user_id)
        elif route == "POST /categories/create-with-rule":
            return create_category_with_rule_handler(event, user_id)
        
        else:
            return create_response(404, {"error": "Not Found: Invalid path or method"})


