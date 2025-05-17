"""
Lambda function for file map operations.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from models.file_map import FileMap, validate_file_map_data
from utils.lambda_utils import create_response, handle_error
from utils.auth import get_user_from_event
from utils.db_utils import get_file_maps_table

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def create_file_map_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new file map.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_id = user['id']
        body = json.loads(event['body'])
        
        # Add user_id to the data for validation
        body['userId'] = user_id
        
        # Validate the input data
        validate_file_map_data(body)
        
        # Create file map
        file_map = FileMap.create(
            user_id=user_id,
            name=body['name'],
            mappings=body['mappings'],
            account_id=body.get('accountId'),
            description=body.get('description')
        )
        
        # Save to DynamoDB
        get_file_maps_table().put_item(Item=file_map.to_dict())
        
        return create_response(201, file_map.to_dict())
        
    except (ValueError, json.JSONDecodeError) as e:
        return handle_error(400, str(e))
    except ClientError as e:
        logger.error(f"DynamoDB error creating file map: {str(e)}")
        return handle_error(500, "Error creating file map")

def get_file_map_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a file map by ID.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_id = user['id']
        file_map_id = event['pathParameters']['id']
        
        # Get the file map
        response = get_file_maps_table().get_item(Key={'fileMapId': file_map_id})
        
        if 'Item' not in response:
            return handle_error(404, f"File map {file_map_id} not found")
            
        file_map = FileMap.from_dict(response['Item'])
        
        # Check ownership
        if file_map.user_id != user_id:
            return handle_error(403, "Not authorized to access this file map")
            
        return create_response(200, file_map.to_dict())
        
    except ClientError as e:
        logger.error(f"DynamoDB error getting file map: {str(e)}")
        return handle_error(500, "Error retrieving file map")

def list_file_maps_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """
    List file maps for a user, optionally filtered by account.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_id = user['id']
        account_id = event.get('queryStringParameters', {}).get('accountId')
        
        if account_id:
            # Query by account using GSI
            response = get_file_maps_table().query(
                IndexName='AccountIdIndex',
                KeyConditionExpression='accountId = :accountId',
                ExpressionAttributeValues={':accountId': account_id}
            )
        else:
            # Query by user using GSI
            response = get_file_maps_table().query(
                IndexName='UserIdIndex',
                KeyConditionExpression='userId = :userId',
                ExpressionAttributeValues={':userId': user_id}
            )
            
        file_maps = [FileMap.from_dict(item).to_dict() for item in response.get('Items', [])]
        
        # Filter out file maps not owned by the user (when querying by account)
        if account_id:
            file_maps = [fm for fm in file_maps if fm['userId'] == user_id]
            
        return create_response(200, {'fileMaps': file_maps})
        
    except ClientError as e:
        logger.error(f"DynamoDB error listing file maps: {str(e)}")
        return handle_error(500, "Error listing file maps")

def update_file_map_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a file map.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_id = user['id']
        file_map_id = event['pathParameters']['id']
        body = json.loads(event['body'])
        
        # Get existing file map
        response = get_file_maps_table().get_item(Key={'fileMapId': file_map_id})
        
        if 'Item' not in response:
            return handle_error(404, f"File map {file_map_id} not found")
            
        file_map = FileMap.from_dict(response['Item'])
        
        # Check ownership
        if file_map.user_id != user_id:
            return handle_error(403, "Not authorized to update this file map")
            
        # Update fields
        file_map.update(
            name=body.get('name'),
            mappings=body.get('mappings'),
            description=body.get('description')
        )
        
        # Save updates
        get_file_maps_table().put_item(Item=file_map.to_dict())
        
        return create_response(200, file_map.to_dict())
        
    except (ValueError, json.JSONDecodeError) as e:
        return handle_error(400, str(e))
    except ClientError as e:
        logger.error(f"DynamoDB error updating file map: {str(e)}")
        return handle_error(500, "Error updating file map")

def delete_file_map_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a file map.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        user_id = user['id']
        file_map_id = event['pathParameters']['id']
        
        # Get the file map to check ownership
        response = get_file_maps_table().get_item(Key={'fileMapId': file_map_id})
        
        if 'Item' not in response:
            return handle_error(404, f"File map {file_map_id} not found")
            
        file_map = FileMap.from_dict(response['Item'])
        
        # Check ownership
        if file_map.user_id != user_id:
            return handle_error(403, "Not authorized to delete this file map")
            
        # Delete the file map
        get_file_maps_table().delete_item(Key={'fileMapId': file_map_id})
        
        return create_response(204, {})
        
    except ClientError as e:
        logger.error(f"DynamoDB error deleting file map: {str(e)}")
        return handle_error(500, "Error deleting file map")

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for file map operations.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway Lambda proxy response
    """
    try:
        # Get user from Cognito
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        
        # Get route from event
        route = event.get('routeKey')
        if not route:
            return create_response(400, {"message": "Route not specified"})
        
            # Log request details
                # Get the HTTP method and route
        method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
        logger.info(f"Request: {method} {route}")

        # Route to appropriate handler
        if route == 'POST /file-maps':
            return create_file_map_handler(event, user)
        elif route == 'GET /file-maps/{id}':
            return get_file_map_handler(event, user)
        elif route == 'GET /file-maps':
            return list_file_maps_handler(event, user)
        elif route == 'PUT /file-maps/{id}':
            return update_file_map_handler(event, user)
        elif route == 'DELETE /file-maps/{id}':
            return delete_file_map_handler(event, user)
        else:
            return handle_error(404, f"Route {route} not found")
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return handle_error(500, "Internal server error") 