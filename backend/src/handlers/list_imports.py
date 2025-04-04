import json
import logging
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_colors() -> List[str]:
    """Return a list of color names."""
    return [
        "Cerulean",
        "Crimson",
        "Sage",
        "Amber"
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
        user_sub = authorizer.get("claims", {}).get("sub")
        if not user_sub:
            logger.error("No user sub found in token")
            return create_response(401, {"message": "Unauthorized"})

        # Get and return colors
        colors = get_colors()
        
        return create_response(200, {
            "colors": colors,
            "user": user_sub  # Include user ID in response
        })

    except Exception as e:
        logger.error("Error processing request: %s", str(e))
        return create_response(500, {"message": "Internal server error"}) 