"""
Lambda function for field map operations.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from models import FileMap, validate_field_map_data
from utils.lambda_utils import create_response, handle_error
from utils.auth import get_user_from_event
from utils.db_utils import get_field_maps_table

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def create_field_map_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new field map.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_info = get_user_from_event(event)
        if not user_info:
            return handle_error(401, "Unauthorized")
            
        user_id = user_info['id']
        body = json.loads(event['body'])
        
        # Add user_id to the data for validation
        body['userId'] = user_id
        
        # Validate the input data
        validate_field_map_data(body)
        
        # Create field map
        field_map = FileMap.create(
            user_id=user_id,
            name=body['name'],
            mappings=body['mappings'],
            account_id=body.get('accountId'),
            description=body.get('description')
        )
        
        # Save to DynamoDB
        get_field_maps_table().put_item(Item=field_map.to_dict())
        
        return create_response(201, field_map.to_dict())
        
    except (ValueError, json.JSONDecodeError) as e:
        return handle_error(400, str(e))
    except ClientError as e:
        logger.error(f"DynamoDB error creating field map: {str(e)}")
        return handle_error(500, "Error creating field map")

def get_field_map_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a field map by ID.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_info = get_user_from_event(event)
        if not user_info:
            return handle_error(401, "Unauthorized")
            
        user_id = user_info['id']
        field_map_id = event['pathParameters']['id']
        
        # Get the field map
        response = get_field_maps_table().get_item(Key={'fieldMapId': field_map_id})
        
        if 'Item' not in response:
            return handle_error(404, f"Field map {field_map_id} not found")
            
        field_map = FileMap.from_dict(response['Item'])
        
        # Check ownership
        if field_map.user_id != user_id:
            return handle_error(403, "Not authorized to access this field map")
            
        return create_response(200, field_map.to_dict())
        
    except ClientError as e:
        logger.error(f"DynamoDB error getting field map: {str(e)}")
        return handle_error(500, "Error retrieving field map")

def list_field_maps_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    List field maps for a user, optionally filtered by account.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_info = get_user_from_event(event)
        if not user_info:
            return handle_error(401, "Unauthorized")
            
        user_id = user_info['id']
        account_id = event.get('queryStringParameters', {}).get('accountId')
        
        if account_id:
            # Query by account using GSI
            response = get_field_maps_table().query(
                IndexName='AccountIdIndex',
                KeyConditionExpression='accountId = :accountId',
                ExpressionAttributeValues={':accountId': account_id}
            )
        else:
            # Query by user using GSI
            response = get_field_maps_table().query(
                IndexName='UserIdIndex',
                KeyConditionExpression='userId = :userId',
                ExpressionAttributeValues={':userId': user_id}
            )
            
        field_maps = [FileMap.from_dict(item).to_dict() for item in response.get('Items', [])]
        
        # Filter out field maps not owned by the user (when querying by account)
        if account_id:
            field_maps = [fm for fm in field_maps if fm['userId'] == user_id]
            
        return create_response(200, {'fieldMaps': field_maps})
        
    except ClientError as e:
        logger.error(f"DynamoDB error listing field maps: {str(e)}")
        return handle_error(500, "Error listing field maps")

def update_field_map_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a field map.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_info = get_user_from_event(event)
        if not user_info:
            return handle_error(401, "Unauthorized")
            
        user_id = user_info['id']
        field_map_id = event['pathParameters']['id']
        body = json.loads(event['body'])
        
        # Get existing field map
        response = get_field_maps_table().get_item(Key={'fieldMapId': field_map_id})
        
        if 'Item' not in response:
            return handle_error(404, f"Field map {field_map_id} not found")
            
        field_map = FileMap.from_dict(response['Item'])
        
        # Check ownership
        if field_map.user_id != user_id:
            return handle_error(403, "Not authorized to update this field map")
            
        # Update fields
        field_map.update(
            name=body.get('name'),
            mappings=body.get('mappings'),
            description=body.get('description')
        )
        
        # Save updates
        get_field_maps_table().put_item(Item=field_map.to_dict())
        
        return create_response(200, field_map.to_dict())
        
    except (ValueError, json.JSONDecodeError) as e:
        return handle_error(400, str(e))
    except ClientError as e:
        logger.error(f"DynamoDB error updating field map: {str(e)}")
        return handle_error(500, "Error updating field map")

def delete_field_map_handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a field map.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_info = get_user_from_event(event)
        if not user_info:
            return handle_error(401, "Unauthorized")
            
        user_id = user_info['id']
        field_map_id = event['pathParameters']['id']
        
        # Get the field map to check ownership
        response = get_field_maps_table().get_item(Key={'fieldMapId': field_map_id})
        
        if 'Item' not in response:
            return handle_error(404, f"Field map {field_map_id} not found")
            
        field_map = FileMap.from_dict(response['Item'])
        
        # Check ownership
        if field_map.user_id != user_id:
            return handle_error(403, "Not authorized to delete this field map")
            
        # Delete the field map
        get_field_maps_table().delete_item(Key={'fieldMapId': field_map_id})
        
        return create_response(204, None)
        
    except ClientError as e:
        logger.error(f"DynamoDB error deleting field map: {str(e)}")
        return handle_error(500, "Error deleting field map")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for field map operations.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    logger.info(f"Processing event: {json.dumps(event)}")
    
    http_method = event['requestContext']['http']['method']
    route_key = event['routeKey']
    
    try:
        # Route to appropriate handler
        if route_key == 'POST /field-maps':
            return create_field_map_handler(event)
        elif route_key == 'GET /field-maps/{id}':
            return get_field_map_handler(event)
        elif route_key == 'GET /field-maps':
            return list_field_maps_handler(event)
        elif route_key == 'PUT /field-maps/{id}':
            return update_field_map_handler(event)
        elif route_key == 'DELETE /field-maps/{id}':
            return delete_field_map_handler(event)
        else:
            return handle_error(400, f"Unsupported route {route_key}")
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return handle_error(500, "Internal server error") 