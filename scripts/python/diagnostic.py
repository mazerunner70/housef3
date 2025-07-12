#!/usr/bin/env python3
import boto3
import logging
from typing import Dict, Any, Optional, Union, List, cast
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_table_exists(table_name: str, region: str = 'us-east-1') -> bool:
    """
    Check if the DynamoDB table exists and is active.
    """
    try:
        dynamodb = boto3.client('dynamodb', region_name=region)
        response = dynamodb.describe_table(TableName=table_name)
        table_status = response['Table']['TableStatus']
        logger.info(f"Table {table_name} status: {table_status}")
        return table_status == 'ACTIVE'
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Table {table_name} does not exist")
            return False
        logger.error(f"Error checking table {table_name}: {str(e)}")
        raise

def get_table_info(table_name: str, region: str = 'us-east-1') -> Optional[Dict[str, Any]]:
    """
    Get detailed information about the DynamoDB table.
    """
    try:
        dynamodb = boto3.client('dynamodb', region_name=region)
        response = dynamodb.describe_table(TableName=table_name)
        table_info = response['Table']
        logger.info(f"Table {table_name} info:")
        logger.info(f"  - Item count: {table_info.get('ItemCount', 'N/A')}")
        logger.info(f"  - Size (bytes): {table_info.get('TableSizeBytes', 'N/A')}")
        logger.info(f"  - Status: {table_info.get('TableStatus', 'N/A')}")
        return table_info
    except ClientError as e:
        logger.error(f"Error getting table info for {table_name}: {str(e)}")
        return None

def initialize_dynamodb(table_name: str, region: str = 'us-east-1') -> bool:
    """
    Initialize DynamoDB connection and verify table access.
    Returns True if initialization is successful.
    """
    try:
        logger.info("Initializing DynamoDB connection...")
        
        # Check AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            logger.error("No AWS credentials found")
            return False
            
        # Log configuration
        logger.info(f"Using AWS Region: {region}")
        logger.info(f"Using table: {table_name}")
        
        # Check if table exists and is accessible
        if not check_table_exists(table_name, region):
            return False
            
        # Get table information
        table_info = get_table_info(table_name, region)
        if not table_info:
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB: {str(e)}")
        return False

def get_dynamodb_resource(table_names: Union[str, List[str]], region: str = 'us-east-1') -> Any:
    """
    Get the DynamoDB resource with connection diagnostics.
    Args:
        table_names: Single table name or list of table names to verify access
        region: AWS region name
    Returns:
        DynamoDB resource if successful, None otherwise
    """
    try:
        resource = boto3.resource('dynamodb', region_name=region)
        
        # Convert single table name to list for consistent handling
        if isinstance(table_names, str):
            table_names = [table_names]
            
        # Verify we can access all tables
        for table_name in table_names:
            table = resource.Table(table_name)
            table.table_status  # This will raise an exception if the table doesn't exist
            logger.info(f"Successfully verified access to table {table_name}")
            
        logger.info("Successfully connected to DynamoDB and verified table access")
        return resource
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB resource: {str(e)}")
        return None 