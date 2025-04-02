import json
from typing import Dict, Any

def list_imports(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler that returns a list of colors.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        Dictionary containing list of colors and status code
    """
    try:
        if event is None:
            raise ValueError("Event cannot be None")
            
        colors = [
            "Cerulean",
            "Crimson", 
            "Sage",
            "Amber"
        ]
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # Configure this appropriately in production
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Content-Type,Authorization"
            },
            "body": json.dumps({"colors": colors})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        } 