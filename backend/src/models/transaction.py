import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Transaction:
    """
    Represents a single financial transaction parsed from a transaction file.
    """
    def __init__(
        self,
        transaction_id: str,
        file_id: str,
        user_id: str,
        date: str,
        description: str,
        amount: float,
        balance: float,
        transaction_type: Optional[str] = None,
        category: Optional[str] = None,
        payee: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        reference: Optional[str] = None,
        account_id: Optional[str] = None,
        status: Optional[str] = None,
        import_order: Optional[int] = None
    ):
        self.transaction_id = transaction_id
        self.file_id = file_id
        self.user_id = user_id
        self.date = date
        self.description = description
        self.amount = amount
        self.balance = balance
        self.transaction_type = transaction_type
        self.category = category
        self.payee = payee
        self.memo = memo
        self.check_number = check_number
        self.reference = reference
        self.account_id = account_id
        self.status = status
        self.import_order = import_order
        
    @classmethod
    def create(
        cls,
        file_id: str,
        user_id: str,
        date: str,
        description: str,
        amount: float,
        balance: float,
        **kwargs
    ) -> 'Transaction':
        """
        Factory method to create a new transaction with a generated ID.
        """
        return cls(
            transaction_id=str(uuid.uuid4()),
            file_id=file_id,
            user_id=user_id,
            date=date,
            description=description,
            amount=amount,
            balance=balance,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction object to a dictionary suitable for storage.
        """
        result = {
            "transactionId": self.transaction_id,
            "fileId": self.file_id,
            "userId": self.user_id,
            "date": self.date,
            "description": self.description,
            "amount": str(self.amount),  # Convert to string for DynamoDB
            "balance": str(self.balance)  # Convert to string for DynamoDB
        }
        
        # Add optional fields if they exist
        if self.transaction_type:
            result["transactionType"] = self.transaction_type
            
        if self.category:
            result["category"] = self.category
            
        if self.payee:
            result["payee"] = self.payee
            
        if self.memo:
            result["memo"] = self.memo
            
        if self.check_number:
            result["checkNumber"] = self.check_number
            
        if self.reference:
            result["reference"] = self.reference
            
        if self.account_id:
            result["accountId"] = self.account_id
            
        if self.status:
            result["status"] = self.status
            
        if self.import_order is not None:
            result["importOrder"] = self.import_order
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """
        Create a transaction object from a dictionary (e.g. from DynamoDB).
        """
        return cls(
            transaction_id=data["transactionId"],
            file_id=data["fileId"],
            user_id=data["userId"],
            date=data["date"],
            description=data["description"],
            amount=float(data["amount"]),
            balance=float(data["balance"]),
            transaction_type=data.get("transactionType"),
            category=data.get("category"),
            payee=data.get("payee"),
            memo=data.get("memo"),
            check_number=data.get("checkNumber"),
            reference=data.get("reference"),
            account_id=data.get("accountId"),
            status=data.get("status"),
            import_order=data.get("importOrder")
        )

def validate_transaction_data(data: Dict[str, Any]) -> bool:
    """
    Validate transaction data according to business rules.
    
    Args:
        data: Dictionary containing transaction data
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If validation fails
    """
    required_fields = ["fileId", "userId", "date", "description", "amount", "balance"]
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate numeric fields
    try:
        float(data["amount"])
    except (ValueError, TypeError):
        raise ValueError("Amount must be a valid number")
        
    try:
        float(data["balance"])
    except (ValueError, TypeError):
        raise ValueError("Balance must be a valid number")
    
    # Validate string lengths
    if len(data["description"]) > 1000:
        raise ValueError("Description must be 1000 characters or less")
        
    if "memo" in data and data["memo"] and len(data["memo"]) > 1000:
        raise ValueError("Memo must be 1000 characters or less")
        
    if "category" in data and data["category"] and len(data["category"]) > 100:
        raise ValueError("Category must be 100 characters or less")
        
    if "payee" in data and data["payee"] and len(data["payee"]) > 100:
        raise ValueError("Payee must be 100 characters or less")
        
    if "checkNumber" in data and data["checkNumber"] and len(data["checkNumber"]) > 50:
        raise ValueError("Check number must be 50 characters or less")
        
    if "reference" in data and data["reference"] and len(data["reference"]) > 100:
        raise ValueError("Reference must be 100 characters or less")
    
    return True 