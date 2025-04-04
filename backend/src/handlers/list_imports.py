import json
import logging
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

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for returning colors list.
    Requires authentication via Cognito.
    """
    logger.info("Processing request with event: %s", json.dumps(event))

    # Handle preflight OPTIONS request
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return create_response(200, {"message": "OK"})

    try:
        # Extract user information from the authorizer context
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {}).get("jwt", {})
        
        # Log authentication details (for debugging)
        logger.info("Authorizer context: %s", json.dumps(authorizer))

        # Get user claims
        claims = authorizer.get("claims", {})
        user_sub = claims.get("sub")
        if not user_sub:
            logger.error("No user sub found in token")
            return create_response(401, {"message": "Unauthorized"})

        # Get and return colors
        colors = get_colors()
        
        # Create enriched user object
        user_info = {
            "id": user_sub,
            "email": claims.get("email", "unknown"),
            "auth_time": claims.get("auth_time"),
            "scope": "read"  # Default scope for all authenticated users
        }
        
        return create_response(200, {
            "colors": colors,
            "user": user_info,
            "metadata": {
                "totalColors": len(colors),
                "timestamp": context.aws_request_id,
                "version": "1.0.0"
            }
        })

    except Exception as e:
        logger.error("Error processing request: %s", str(e))
        return create_response(500, {"message": "Internal server error"}) 