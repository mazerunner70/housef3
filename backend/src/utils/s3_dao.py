"""
S3 Data Access Object for handling S3 operations.
"""
import logging
import os
import boto3
from typing import Optional, Dict, Any, Union
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_s3_client():
    return boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'eu-west-2'))

# Get bucket name from environment
FILE_STORAGE_BUCKET = os.environ.get('FILE_STORAGE_BUCKET', 'housef3-dev-file-storage')

def get_presigned_url(bucket: str, key: str, operation: str, expires_in: int = 3600, conditions: Optional[list] = None, fields: Optional[Dict[str, str]] = None) -> Union[str, Dict[str, Any]]:
    """
    Generate a presigned URL for S3 operations.
    
    Args:
        bucket: The S3 bucket name
        key: The S3 key
        operation: The operation ('put', 'post', or 'get')
        expires_in: URL expiration time in seconds
        conditions: Optional list of conditions for the presigned URL policy
        fields: Optional fields to include in the presigned POST URL
        
    Returns:
        For PUT/GET: The presigned URL as string
        For POST with conditions: Dict containing 'url' and 'fields' for the form
    """
    try:
        if not isinstance(bucket, str) or not bucket:
            raise ValueError("Bucket name must be a non-empty string")
            
        if not isinstance(key, str) or not key:
            raise ValueError("Key must be a non-empty string")
            
        client = get_s3_client()
        
        if operation.lower() == 'post':
            # Generate a presigned POST URL with fields for browser-based uploads
            post_fields = {}
            if fields:
                post_fields.update(fields)
                
            # Always include the key in the fields
            if 'key' not in post_fields:
                post_fields['key'] = key
                
            post_conditions = [
                {'bucket': bucket}
            ]
            
            # If the key is not in fields, add a condition for it
            if 'key' not in post_fields:
                post_conditions.append({'key': key})
            
            # Add additional conditions if provided
            if conditions:
                post_conditions.extend(conditions)
                
            logger.info(f"Generating presigned POST URL with conditions: {post_conditions}")
            logger.info(f"Fields: {post_fields}")
                
            response = client.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                Fields=post_fields,
                Conditions=post_conditions,
                ExpiresIn=expires_in
            )
            logger.info(f"Generated presigned POST URL for {bucket}/{key}")
            return response  # Return both URL and fields
        elif operation.lower() == 'put':
            params = {
                'Bucket': bucket,
                'Key': key
            }
            
            # If conditions are provided, use post_presigned_url
            if conditions:
                post_fields = {}
                if fields:
                    post_fields.update(fields)
                
                post_conditions = [
                    {'bucket': bucket},
                    {'key': key}
                ]
                post_conditions.extend(conditions)
                
                response = client.generate_presigned_post(
                    Bucket=bucket,
                    Key=key,
                    Fields=post_fields,
                    Conditions=post_conditions,
                    ExpiresIn=expires_in
                )
                return response  # Return both URL and fields
            
            # Otherwise use standard presigned URL
            return client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expires_in
            )
        elif operation.lower() == 'get':
            return client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expires_in
            )
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

def delete_object(key: str, bucket: Optional[str] = None) -> bool:
    """
    Delete an object from S3.
    
    Args:
        key: The S3 key of the object to delete
        bucket: Optional bucket name (defaults to FILE_STORAGE_BUCKET)
        
    Returns:
        True if successful or file not found, False otherwise
    """
    try:
        bucket = bucket or FILE_STORAGE_BUCKET
        get_s3_client().delete_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return True
        logger.error(f"Error deleting object from S3: {str(e)}")
        return False

def get_object(key: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get an object from S3.
    
    Args:
        key: The S3 key of the object to retrieve
        bucket: Optional bucket name (defaults to FILE_STORAGE_BUCKET)
        
    Returns:
        The S3 object response if successful, None otherwise
    """
    try:
        bucket = bucket or FILE_STORAGE_BUCKET
        response = get_s3_client().get_object(Bucket=bucket, Key=key)
        return response
    except ClientError as e:
        logger.error(f"Error getting object from S3: {str(e)}")
        return None

def put_object(key: str, body: bytes, content_type: str, bucket: Optional[str] = None) -> bool:
    """
    Upload an object to S3.
    
    Args:
        key: The S3 key for the object
        body: The object content as bytes
        content_type: The content type of the object
        bucket: Optional bucket name (defaults to FILE_STORAGE_BUCKET)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        bucket = bucket or FILE_STORAGE_BUCKET
        get_s3_client().put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType=content_type
        )
        return True
    except ClientError as e:
        logger.error(f"Error uploading object to S3: {str(e)}")
        return False

def get_object_content(key: str, bucket: Optional[str] = None) -> Optional[bytes]:
    """
    Get the content of an S3 object.
    
    Args:
        key: The S3 key of the object
        bucket: Optional bucket name (defaults to FILE_STORAGE_BUCKET)
        
    Returns:
        The object content as bytes if successful, None otherwise
    """
    try:
        response = get_object(key, bucket)
        if response:
            return response['Body'].read()
        return None
    except Exception as e:
        logger.error(f"Error reading object content from S3: {str(e)}")
        return None

def get_object_metadata(key: str, bucket: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get the metadata of an S3 object without downloading its content.
    
    Args:
        key: The S3 key of the object
        bucket: Optional bucket name (defaults to FILE_STORAGE_BUCKET)
        
    Returns:
        Dictionary containing object metadata if successful, None otherwise
        Includes: ContentType, ContentLength, LastModified, etc.
    """
    try:
        bucket = bucket or FILE_STORAGE_BUCKET
        response = get_s3_client().head_object(Bucket=bucket, Key=key)
        return {
            'content_type': response.get('ContentType'),
            'content_length': response.get('ContentLength'),
            'last_modified': response.get('LastModified'),
            'e_tag': response.get('ETag'),
            'metadata': response.get('Metadata', {})
        }
    except ClientError as e:
        logger.error(f"Error getting object metadata from S3: {str(e)}")
        return None 