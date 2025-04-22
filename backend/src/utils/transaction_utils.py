"""
Utility functions for transaction operations.
"""
import hashlib
from decimal import Decimal
from typing import Dict, Any
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def generate_transaction_hash(account_id: str, date: int, amount: Decimal, description: str) -> int:
    """
    Generate a numeric hash for transaction deduplication.
    
    Args:
        account_id: The account ID
        date: Transaction date as milliseconds since epoch
        amount: Transaction amount as Decimal
        description: Transaction description
        
    Returns:
        int: A 64-bit hash of the transaction details
    """
    # Normalize the amount by removing trailing zeros and decimal point if not needed
    normalized_amount = amount.normalize()
    
    # Create a string with all the components using normalized amount
    content = f"{account_id}|{date}|{str(normalized_amount)}|{description}"
    
    # Generate SHA-256 hash
    hash_obj = hashlib.sha256(content.encode('utf-8'))
    hash_value = int(hash_obj.hexdigest()[:16], 16)
    
    # Only log for specific hash
    if hash_value == 251919912236021373:
        logger.info(f"Generating hash with values:")
        logger.info(f"  account_id: {account_id} (type: {type(account_id)})")
        logger.info(f"  date: {date} (type: {type(date)})")
        logger.info(f"  amount: {amount} (type: {type(amount)}, str: {str(amount)})")
        logger.info(f"  normalized_amount: {normalized_amount} (type: {type(normalized_amount)}, str: {str(normalized_amount)})")
        logger.info(f"  description: {description} (type: {type(description)})")
        logger.info(f"Hash input string: {content}")
        logger.info(f"Generated hash: {hash_value}")
    
    return hash_value

def check_duplicate_transaction(transaction: Dict[str, Any], account_id: str) -> bool:
    """
    Check if a transaction already exists for the given account using numeric hash.
    
    Args:
        transaction: Dictionary containing transaction details
        account_id: ID of the account to check for duplicates
        
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        # Log function entry
        logger.info(f"Entering check_duplicate_transaction for account_id: {account_id}")
        
        # Generate the hash for the transaction
        transaction_hash = generate_transaction_hash(
            account_id,
            transaction['date'],
            Decimal(str(transaction['amount'])),  # Ensure amount is Decimal
            transaction['description']
        )
        
        # Only log for specific hash
        if transaction_hash == 251919912236021373:
            logger.info(f"Checking for duplicate transaction:")
            logger.info(f"  account_id: {account_id}")
            logger.info(f"  transaction_hash: {transaction_hash}")
            logger.info(f"  date: {transaction['date']}")
            logger.info(f"  amount: {transaction['amount']}")
            logger.info(f"  description: {transaction['description']}")
            
            # Query DynamoDB using the account ID and hash
            table = boto3.resource('dynamodb').Table(os.environ.get('TRANSACTIONS_TABLE', 'transactions'))
            logger.info(f"Querying DynamoDB with:")
            logger.info(f"  IndexName: TransactionHashIndex")
            logger.info(f"  KeyCondition: accountId={account_id} AND transactionHash={transaction_hash}")
            
            response = table.query(
                IndexName='TransactionHashIndex',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id) & 
                                     boto3.dynamodb.conditions.Key('transactionHash').eq(transaction_hash)
            )
            
            items = response.get('Items', [])
            logger.info(f"Query returned {len(items)} items")
            if items:
                logger.info(f"Found duplicate transaction(s):")
                for item in items:
                    logger.info(f"  transactionId: {item.get('transactionId')}")
                    logger.info(f"  date: {item.get('date')}")
                    logger.info(f"  amount: {item.get('amount')}")
                    logger.info(f"  description: {item.get('description')}")
            
            return len(items) > 0
        
        # For other hashes, perform the check without logging
        response = boto3.resource('dynamodb').Table(os.environ.get('TRANSACTIONS_TABLE', 'transactions')).query(
            IndexName='TransactionHashIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('accountId').eq(account_id) & 
                                 boto3.dynamodb.conditions.Key('transactionHash').eq(transaction_hash)
        )
        
        return len(response.get('Items', [])) > 0
    except Exception as e:
        logger.error(f"Error checking for duplicate transaction: {str(e)}")
        # If there's an error checking for duplicates, return False to allow the transaction
        return False 