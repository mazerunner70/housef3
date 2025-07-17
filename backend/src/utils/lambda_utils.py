from typing import Dict, Any
import json
from decimal import Decimal
import uuid
from models.transaction_file import DateRange

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Always return as string to preserve precision and ensure consistent type
            return str(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, DateRange):
            return obj.model_dump()
        return super(DecimalEncoder, self).default(obj)

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized API response."""
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
    """Extract a mandatory path parameter from the event.
    Raises ValueError if the parameter is not found.
    
    """
    if not parameter_name:
        raise KeyError("Parameter name is required")
    parameter = optional_path_parameter(event, parameter_name)
    if not parameter:
        raise ValueError(f"Path parameter {parameter_name} not found")
    return parameter

# extract query parameters from the event
def optional_query_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a query parameter from the event."""
    return event.get('queryStringParameters', {}).get(parameter_name)

def mandatory_query_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a mandatory query parameter from the event."""
    if not parameter_name:
        raise KeyError("Parameter name is required")
    parameter_value = optional_query_parameter(event, parameter_name)
    if not parameter_value:
        raise ValueError(f"Query parameter {parameter_name} not found")
    return parameter_value
    
# extract paameters from json payload body
def optional_body_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a json-encoded body parameter from the event."""
    return json.loads(event.get('body', '{}')).get(parameter_name)

def mandatory_body_parameter(event: Dict[str, Any], parameter_name: str) -> str:
    """Extract a mandatory json-encoded body parameter from the event."""
    parameter_value = optional_body_parameter(event, parameter_name)
    if not parameter_value:
        raise KeyError(f"Body parameter {parameter_name} is required")
    return parameter_value