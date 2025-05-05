"""
Utility functions for transaction operations.
"""
import hashlib
from decimal import Decimal
from typing import Dict, Any, Union
import logging
import os


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def generate_transaction_hash(account_id: str, date: int, amount: Decimal, description: str) -> int:
    """
    Generate a numeric hash for transaction deduplication
    
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
    
    return hash_value

    