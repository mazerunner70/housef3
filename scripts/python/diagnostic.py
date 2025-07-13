#!/usr/bin/env python3
import boto3
import json
from datetime import datetime, timezone
from decimal import Decimal
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'housef3')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
TABLE_NAME = f"{PROJECT_NAME}-{ENVIRONMENT}-analytics-status"

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

def describe_table(table_name):
    """Get and print table structure including GSIs"""
    dynamodb = boto3.client('dynamodb')
    try:
        response = dynamodb.describe_table(TableName=table_name)
        logger.info(f"\nTable Structure for {table_name}:")
        logger.info(json.dumps(response['Table'], indent=2, cls=DecimalEncoder))
        
        # Check specifically for ComputationNeededIndex
        gsis = response['Table'].get('GlobalSecondaryIndexes', [])
        has_computation_index = any(gsi['IndexName'] == 'ComputationNeededIndex' for gsi in gsis)
        logger.info(f"\nHas ComputationNeededIndex: {has_computation_index}")
        
        # List all available indexes
        logger.info("\nAvailable Indexes:")
        for gsi in gsis:
            logger.info(f"- {gsi['IndexName']}")
            logger.info(f"  Hash Key: {gsi.get('KeySchema', [{}])[0].get('AttributeName', 'N/A')}")
            logger.info(f"  Range Key: {gsi.get('KeySchema', [{}])[1].get('AttributeName', 'N/A') if len(gsi.get('KeySchema', [])) > 1 else 'N/A'}")
        
        return response['Table']
    except Exception as e:
        logger.error(f"Error describing table {table_name}: {str(e)}")
        return None

def check_analytics_records():
    """Query analytics records and check computation status"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        # Try to query using ProcessingQueueIndex
        logger.info("\nQuerying analytics records using ProcessingQueueIndex...")
        try:
            response = table.query(
                IndexName='ProcessingQueueIndex',
                KeyConditionExpression='processingPriority = :priority',
                ExpressionAttributeValues={':priority': 1}  # High priority items
            )
            logger.info(f"Found {len(response['Items'])} high priority items")
            
            # Print the items
            for item in response['Items']:
                logger.info(json.dumps(item, indent=2, cls=DecimalEncoder))
                
        except Exception as e:
            logger.warning(f"Failed to query using ProcessingQueueIndex: {str(e)}")
            logger.info("\nFalling back to table scan...")
            
            # Fallback to scan
            response = table.scan()
            logger.info(f"Table scan completed. Found {len(response['Items'])} items")
            
            # Print sample of items
            logger.info("\nSample of Analytics Records:")
            for item in response['Items'][:5]:  # Show first 5 items
                logger.info(json.dumps(item, indent=2, cls=DecimalEncoder))
        
        return response['Items']
    except Exception as e:
        logger.error(f"Error checking analytics records: {str(e)}")
        return []

def check_recent_analytics_updates():
    """Check recently updated analytics records"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TABLE_NAME)
    
    try:
        # Try to use UserStatusIndex to get recent updates
        logger.info("\nQuerying recent updates using UserStatusIndex...")
        try:
            # Get current timestamp
            now = datetime.now(timezone.utc).isoformat()
            
            # Query for recent items
            response = table.query(
                IndexName='UserStatusIndex',
                KeyConditionExpression='userId = :userId',
                ExpressionAttributeValues={
                    ':userId': 'SYSTEM'  # System-wide analytics
                },
                ScanIndexForward=False,  # Sort in descending order
                Limit=5
            )
            
            items = response['Items']
            logger.info(f"\nMost Recent Analytics Updates (top {len(items)}):")
            for item in items:
                logger.info(json.dumps(item, indent=2, cls=DecimalEncoder))
                
            return items
        except Exception as e:
            logger.warning(f"Failed to query using UserStatusIndex: {str(e)}")
            logger.info("\nFalling back to table scan...")
            
            # Fallback to scan
            response = table.scan()
            items = response['Items']
            
            # Sort by lastUpdated if available
            items.sort(key=lambda x: x.get('lastUpdated', ''), reverse=True)
            
            logger.info(f"\nMost Recent Analytics Updates (top {min(5, len(items))}):")
            for item in items[:5]:
                logger.info(json.dumps(item, indent=2, cls=DecimalEncoder))
            
            return items
    except Exception as e:
        logger.error(f"Error checking recent analytics updates: {str(e)}")
        return []

def main():
    logger.info("Starting Analytics Diagnostics...")
    logger.info(f"Using table: {TABLE_NAME}")
    
    # Check table structure
    describe_table(TABLE_NAME)
    
    # Check records needing computation
    computation_needed = check_analytics_records()
    logger.info(f"\nTotal records found: {len(computation_needed)}")
    
    # Check recent updates
    recent_updates = check_recent_analytics_updates()
    logger.info(f"\nTotal recent updates found: {len(recent_updates)}")

if __name__ == "__main__":
    main() 
=======
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
