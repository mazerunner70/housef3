import json
import logging
import os
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_colors() -> List[Dict[str, Any]]:
    """Return a list of color objects with metadata."""
    return [
        {
            "name": "Cerulean",
            "hex": "#007BA7",
            "category": "blue"
        },
        {
            "name": "Crimson",
            "hex": "#DC143C",
            "category": "red"
        },
        {
            "name": "Sage",
            "hex": "#BCB88A",
            "category": "green"
        },
        {
            "name": "Amber",
            "hex": "#FFBF00",
            "category": "yellow"
        }
    ]

def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create an API Gateway response object."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS"
        },
        "body": json.dumps(body)
    }

def list_imports(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for returning colors list.
    Requires authentication via Cognito.
    """
    try:
        # Handle None event
        if event is None:
            logger.error("Event is None")
            return create_response(500, {"message": "Internal server error"})
            
        logger.info("Processing request with event: %s", json.dumps(event))

        # Handle preflight OPTIONS request
        if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
            return create_response(200, {"message": "OK"})

        # Extract user information from the authorizer context
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {}).get("jwt", {})
        
        # Log authentication details (for debugging)
        logger.info("Authorizer context: %s", json.dumps(authorizer))

        # Get user claims
        claims = authorizer.get("claims", {})
        user_sub = claims.get("sub")
        
        # Skip authentication check in test mode
        is_test = os.environ.get("TESTING", "").lower() == "true"
        if not user_sub and not is_test:
            logger.error("No user sub found in token")
            return create_response(401, {"message": "Unauthorized"})

        # Get and return colors
        colors = get_colors()
        
        # Create enriched user object
        user_info = {
            "id": user_sub or "test-user-id",
            "email": claims.get("email", "test@example.com"),
            "auth_time": claims.get("auth_time", "2024-01-01T00:00:00Z"),
            "scope": "read"  # Default scope for all authenticated users
        }
        
        # Get request ID from context (handle both object and dict)
        request_id = (
            getattr(context, "aws_request_id", None)  # Try object attribute
            or (context.get("aws_request_id") if isinstance(context, dict) else None)  # Try dict key
            or "test-request-id"  # Default value
        )
        
        return create_response(200, {
            "colors": colors,
            "user": user_info,
            "metadata": {
                "totalColors": len(colors),
                "timestamp": request_id,
                "version": "1.0.0"
            }
        })

    except Exception as e:
        logger.error("Error processing request: %s", str(e))
        return create_response(500, {"message": "Internal server error"})

# Make list_imports the default export
handler = list_imports 