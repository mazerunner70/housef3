import json
import logging
import os
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    # Try direct imports for Lambda environment
    import sys
    # Add the /var/task (Lambda root) to the path if not already there
    if '/var/task' not in sys.path:
        sys.path.insert(0, '/var/task')
    
    # Add the parent directory to allow direct imports
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Now try the imports
    from models.account import Account, AccountType, Currency, validate_account_data
    from utils.db_utils import get_account, list_user_accounts, create_account, update_account, delete_account
    
    logger.info("Successfully imported modules using adjusted path")
except ImportError as e:
    logger.error(f"Import error: {str(e)}")
    # Log the current sys.path to debug import issues
    logger.error(f"Current sys.path: {sys.path}")
    # Last resort, try relative import
    try:
        from ..models.account import Account, AccountType, Currency, validate_account_data
        from ..utils.db_utils import get_account, list_user_accounts, create_account, update_account, delete_account
        logger.info("Successfully imported modules using relative imports")
    except ImportError as e2:
        logger.error(f"Final import attempt failed: {str(e2)}")
        raise

# Custom JSON encoder to handle Decimal values
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)

def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create an API Gateway response object."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }

def get_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract user information from the event."""
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {}).get("jwt", {})
        claims = authorizer.get("claims", {})
        
        user_sub = claims.get("sub")
        if not user_sub:
            return None
        
        return {
            "id": user_sub,
            "email": claims.get("email", "unknown"),
            "auth_time": claims.get("auth_time")
        }
    except Exception as e:
        logger.error(f"Error extracting user from event: {str(e)}")
        return None

def create_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new financial account."""
    try:
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Add user ID to the account data
        body['userId'] = user['id']
        
        # Convert string values to enum types
        if 'accountType' in body and isinstance(body['accountType'], str):
            body['accountType'] = AccountType(body['accountType'])
            
        if 'currency' in body and isinstance(body['currency'], str):
            body['currency'] = Currency(body['currency'])
        
        # Validate and create the account
        account = create_account(body)
        
        # Return the created account
        account_dict = account.to_dict()
        
        return create_response(201, {
            'message': 'Account created successfully',
            'account': account_dict
        })
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error creating account: {str(e)}")
        return create_response(500, {"message": "Error creating account"})

def get_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Get a specific account by ID."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Get the account
        account = get_account(account_id)
        
        if not account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        # Verify user ownership
        if account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Convert account to dictionary
        account_dict = account.to_dict()
        
        return create_response(200, {
            'account': account_dict
        })
    except Exception as e:
        logger.error(f"Error getting account: {str(e)}")
        return create_response(500, {"message": "Error retrieving account"})

def list_accounts_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List all accounts for the current user."""
    try:
        # Get query parameters for filtering/sorting (if implemented)
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Get accounts for the user
        accounts = list_user_accounts(user['id'])
        
        # Convert accounts to dictionary format
        account_dicts = [account.to_dict() for account in accounts]
        
        return create_response(200, {
            'accounts': account_dicts,
            'user': user,
            'metadata': {
                'totalAccounts': len(account_dicts)
            }
        })
    except Exception as e:
        logger.error(f"Error listing accounts: {str(e)}")
        return create_response(500, {"message": "Error listing accounts"})

def update_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Convert string values to enum types
        if 'accountType' in body and isinstance(body['accountType'], str):
            body['accountType'] = AccountType(body['accountType'])
            
        if 'currency' in body and isinstance(body['currency'], str):
            body['currency'] = Currency(body['currency'])
        
        # Verify the account exists and belongs to the user
        existing_account = get_account(account_id)
        
        if not existing_account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if existing_account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Update the account
        updated_account = update_account(account_id, body)
        
        # Return the updated account
        account_dict = updated_account.to_dict()
        
        return create_response(200, {
            'message': 'Account updated successfully',
            'account': account_dict
        })
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return create_response(400, {"message": str(e)})
    except Exception as e:
        logger.error(f"Error updating account: {str(e)}")
        return create_response(500, {"message": "Error updating account"})

def delete_account_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an account."""
    try:
        # Get account ID from path parameters
        account_id = event.get('pathParameters', {}).get('id')
        
        if not account_id:
            return create_response(400, {"message": "Account ID is required"})
        
        # Verify the account exists and belongs to the user
        existing_account = get_account(account_id)
        
        if not existing_account:
            return create_response(404, {"message": f"Account not found: {account_id}"})
        
        if existing_account.user_id != user['id']:
            return create_response(403, {"message": "Access denied"})
        
        # Delete the account
        delete_account(account_id)
        
        return create_response(200, {
            'message': 'Account deleted successfully',
            'accountId': account_id
        })
    except Exception as e:
        logger.error(f"Error deleting account: {str(e)}")
        return create_response(500, {"message": "Error deleting account"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for account operations."""
    logger.info(f"Processing request with event: {json.dumps(event)}")
    
    # Handle preflight OPTIONS request
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return create_response(200, {"message": "OK"})
    
    # Extract user information
    user = get_user_from_event(event)
    if not user:
        logger.error("No user found in token")
        return create_response(401, {"message": "Unauthorized"})
    
    # Get the HTTP method and route
    method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
    route = event.get("routeKey", "")
    
    # Log request details
    logger.info(f"Request: {method} {route}")
    
    # Handle based on route
    if route == "POST /accounts":
        return create_account_handler(event, user)
    elif route == "GET /accounts":
        return list_accounts_handler(event, user)
    elif route == "GET /accounts/{id}":
        return get_account_handler(event, user)
    elif route == "PUT /accounts/{id}":
        return update_account_handler(event, user)
    elif route == "DELETE /accounts/{id}":
        return delete_account_handler(event, user)
    else:
        return create_response(400, {"message": f"Unsupported route: {route}"}) 