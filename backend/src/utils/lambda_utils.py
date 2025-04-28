from typing import Dict, Any
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized API response."""
    print(f"Creating response with status code {status_code} and body {body}")
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }

def handle_error(status_code: int, message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    return create_response(status_code, {"message": message}) 


# extract path parameters from the event
def optional_path_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a path parameter from the event."""
    return event.get('pathParameters', {}).get(parameter_name)

def mandatory_path_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a mandatory path parameter from the event."""
    if not parameter_name:
        raise ValueError("Parameter name is required")
    parameter = optional_path_parameter(event, parameter_name)
    if not parameter:
        raise ValueError(f"Path parameter {parameter_name} is required")
    return parameter

# extract query parameters from the event
def optional_query_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a query parameter from the event."""
    return event.get('queryStringParameters', {}).get(parameter_name)

def mandatory_query_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a mandatory query parameter from the event."""
    if not parameter_name:
        raise ValueError("Parameter name is required")
    parameter_value = optional_query_parameter(event, parameter_name)
    if not parameter_value:
        raise ValueError(f"Query parameter {parameter_name} is required")
    return parameter_value
    
# extract paameters from json payload body
def optional_body_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a json-encoded body parameter from the event."""
    return json.loads(event.get('body', '{}')).get(parameter_name)

def mandatory_body_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a mandatory json-encoded body parameter from the event."""
    parameter_value = optional_body_parameter(event, parameter_name)
    if not parameter_value:
        raise ValueError(f"Body parameter {parameter_name} is required")
    return parameter_value