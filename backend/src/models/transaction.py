import uuid
from typing import Dict, Any, Optional
from datetime import datetime

class Transaction:
    """
    Represents a single financial transaction parsed from a transaction file.
    """
    def __init__(
        self,
        transaction_id: str,
        file_id: str,
        date: str,
        description: str,
        amount: float,
        running_total: float,
        transaction_type: Optional[str] = None,
        category: Optional[str] = None,
        payee: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        reference: Optional[str] = None
    ):
        self.transaction_id = transaction_id
        self.file_id = file_id
        self.date = date
        self.description = description
        self.amount = amount
        self.running_total = running_total
        self.transaction_type = transaction_type
        self.category = category
        self.payee = payee
        self.memo = memo
        self.check_number = check_number
        self.reference = reference
        
    @classmethod
    def create(
        cls,
        file_id: str,
        date: str,
        description: str,
        amount: float,
        running_total: float,
        **kwargs
    ) -> 'Transaction':
        """
        Factory method to create a new transaction with a generated ID.
        """
        return cls(
            transaction_id=str(uuid.uuid4()),
            file_id=file_id,
            date=date,
            description=description,
            amount=amount,
            running_total=running_total,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction object to a dictionary suitable for storage.
        """
        result = {
            "transactionId": self.transaction_id,
            "fileId": self.file_id,
            "date": self.date,
            "description": self.description,
            "amount": str(self.amount),  # Convert to string for DynamoDB
            "runningTotal": str(self.running_total)  # Convert to string for DynamoDB
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
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """
        Create a transaction object from a dictionary (e.g. from DynamoDB).
        """
        return cls(
            transaction_id=data["transactionId"],
            file_id=data["fileId"],
            date=data["date"],
            description=data["description"],
            amount=float(data["amount"]),
            running_total=float(data["runningTotal"]),
            transaction_type=data.get("transactionType"),
            category=data.get("category"),
            payee=data.get("payee"),
            memo=data.get("memo"),
            check_number=data.get("checkNumber"),
            reference=data.get("reference")
        ) 