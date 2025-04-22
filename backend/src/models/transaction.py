import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
import boto3
import logging
import hashlib
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Transaction:
    """
    Represents a single financial transaction parsed from a transaction file.
    """
    @staticmethod
    def generate_transaction_hash(account_id: str, date: str, amount: Decimal, description: str) -> int:
        """
        Generate a numeric hash for transaction deduplication.
        
        Args:
            account_id: The account ID
            date: Transaction date
            amount: Transaction amount as Decimal
            description: Transaction description
            
        Returns:
            int: A 64-bit hash of the transaction details
        """
        # Create a string with all the components
        # Use str() on Decimal for consistent string representation
        content = f"{account_id}|{date}|{str(amount)}|{description}"
        # Generate SHA-256 hash
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        # Take first 16 characters of hex digest and convert to int
        # This gives us a 64-bit number which is plenty for deduplication
        return int(hash_obj.hexdigest()[:16], 16)
    
    def __init__(
        self,
        transaction_id: str,
        account_id: str,
        file_id: str,
        user_id: str,
        date: int,  # milliseconds since epoch
        description: str,
        amount: Decimal,
        balance: Optional[Decimal] = None,
        import_order: Optional[int] = None,
        transaction_type: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        fit_id: Optional[str] = None,
        status: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        transaction_hash: Optional[int] = None
    ):
        self.transaction_id = transaction_id
        self.account_id = account_id
        self.file_id = file_id
        self.user_id = user_id
        self.date = date
        self.description = description
        self.amount = amount
        self.balance = balance
        self.import_order = import_order
        self.transaction_type = transaction_type
        self.memo = memo
        self.check_number = check_number
        self.fit_id = fit_id
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.transaction_hash = transaction_hash
        
    @classmethod
    def create(
        cls,
        account_id: str,
        file_id: str,
        user_id: str,
        date: str,
        description: str,
        amount: Decimal,
        balance: Optional[Decimal] = None,
        import_order: Optional[int] = None,
        transaction_type: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        fit_id: Optional[str] = None,
        status: Optional[str] = None,
        transaction_hash: Optional[int] = None
    ) -> "Transaction":
        """Create a new Transaction with a generated ID."""
        transaction_id = str(uuid.uuid4())
        return cls(
            transaction_id=transaction_id,
            account_id=account_id,
            file_id=file_id,
            user_id=user_id,
            date=date,
            description=description,
            amount=amount,
            balance=balance,
            import_order=import_order,
            transaction_type=transaction_type,
            memo=memo,
            check_number=check_number,
            fit_id=fit_id,
            status=status,
            transaction_hash=transaction_hash
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "transactionId": self.transaction_id,
            "accountId": self.account_id,
            "fileId": self.file_id,
            "userId": self.user_id,
            "date": self.date,  # Already a number
            "description": self.description,
            "amount": self.amount,  # Keep as Decimal
            "balance": self.balance,  # Keep as Decimal
            "importOrder": self.import_order,
            "transactionType": self.transaction_type,
            "memo": self.memo,
            "checkNumber": self.check_number,
            "fitId": self.fit_id,
            "status": self.status,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "transactionHash": self.transaction_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create from dictionary"""
        return cls(
            transaction_id=data["transactionId"],
            account_id=data["accountId"],
            file_id=data["fileId"],
            user_id=data["userId"],
            date=data["date"],  # Already a number
            description=data["description"],
            amount=Decimal(str(data["amount"])),  # Convert to Decimal
            balance=Decimal(str(data["balance"])) if "balance" in data else None,  # Convert to Decimal
            import_order=data.get("importOrder"),
            transaction_type=data.get("transactionType"),
            memo=data.get("memo"),
            check_number=data.get("checkNumber"),
            fit_id=data.get("fitId"),
            status=data.get("status"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
            transaction_hash=data.get("transactionHash")
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