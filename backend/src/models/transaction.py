import json
import uuid
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic, Type
from datetime import datetime
import logging
from decimal import Decimal
from dataclasses import dataclass, field
from utils.transaction_utils import generate_transaction_hash
from models.money import Money
from models.account import Currency

logger = logging.getLogger()
logger.setLevel(logging.INFO)

T = TypeVar('T')

class HashRegeneratingField(Generic[T]):
    """Descriptor that regenerates hash when field value changes."""
    
    def __init__(self, field_type: Type[T]):
        self._field_type = field_type
    
    def __set_name__(self, owner, name):
        self._name = f"_{name}"
    
    def __get__(self, obj: Any, objtype: Any = None) -> T:
        if obj is None:
            raise AttributeError(f"Cannot access {self._name} at class level - this field requires instance initialization")
        return getattr(obj, self._name)
    
    def __set__(self, obj: Any, value: T) -> None:
        if not isinstance(value, self._field_type):
            raise TypeError(f"Value must be of type {self._field_type.__name__}")
        setattr(obj, self._name, value)
        obj._regenerate_hash()

@dataclass
class Transaction:
    """
    Represents a single financial transaction parsed from a transaction file.
    """
    # Required fields (no defaults)
    user_id: str
    file_id: str
    transaction_id: str
    account_id: HashRegeneratingField[str] = HashRegeneratingField(str)
    date: HashRegeneratingField[int] = HashRegeneratingField(int)
    description: HashRegeneratingField[str] = HashRegeneratingField(str)
    amount: HashRegeneratingField[Money] = HashRegeneratingField(Money)
    
    # Private attributes created by HashRegeneratingField
    _account_id: str = field(init=False, repr=False)
    _date: int = field(init=False, repr=False)
    _description: str = field(init=False, repr=False)
    _amount: Money = field(init=False, repr=False)
    
    # Optional fields (with defaults)
    balance: Optional[Money] = None
    import_order: Optional[int] = None
    transaction_type: Optional[str] = None
    memo: Optional[str] = None
    check_number: Optional[str] = None
    fit_id: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    transaction_hash: Optional[int] = field(default=None, init=False)

    def __post_init__(self):
        """Initialize private fields and generate transaction hash."""
        self._regenerate_hash()

    def _regenerate_hash(self):
        """Regenerate the transaction hash if required fields are present."""
        # Only regenerate if all required fields are set
        try:
            if all(hasattr(self, f"_{field}") for field in ['account_id', 'date', 'amount', 'description']) and (self.account_id and self.date and self.amount and self.description):
                self.transaction_hash = generate_transaction_hash(
                    account_id=self.account_id,
                    date=self.date,
                    amount=self.amount.amount,
                    description=self.description
                )
                logger.info(f"Regenerated transaction hash: {self}")
        except AttributeError:
            # Skip hash generation if any required field is not set
            pass

    def __str__(self):
        """String representation of the transaction."""
        return (f"Transaction(account_id={self._account_id}, "
                f"date={self._date}, "
                f"amount={self._amount}, "
                f"description={self._description}, "
                f"hash={self.transaction_hash})")

    @classmethod
    def create(
        cls,
        account_id: str,
        user_id: str,
        file_id: str,
        date: int,  # milliseconds since epoch
        description: str,
        amount: Money,
        balance: Optional[Money] = None,
        import_order: Optional[int] = None,
        transaction_type: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        fit_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> "Transaction":
        """Create a new Transaction with a generated ID."""
        transaction_id = str(uuid.uuid4())
        return cls(
            user_id=user_id,
            file_id=file_id,
            transaction_id=transaction_id,
            account_id=account_id,
            date=date,
            description=description,
            amount=amount,
            balance=balance,
            import_order=import_order,
            transaction_type=transaction_type,
            memo=memo,
            check_number=check_number,
            fit_id=fit_id,
            status=status
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "transactionId": self.transaction_id,
            "accountId": self._account_id,
            "fileId": self.file_id,
            "userId": self.user_id,
            "date": self._date,  # milliseconds since epoch
            "description": self._description,
            "amount": self._amount.to_dict(),
            "balance": self.balance.to_dict() if self.balance else None,
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

    def to_flat_dict(self) -> Dict[str, str]:
        """
        Convert the transaction object to a flattened dictionary where all values are strings.
        This is useful for storage systems that don't support nested structures.
        """
        result = {
            "transactionId": self.transaction_id,
            "accountId": self._account_id,
            "fileId": self.file_id,
            "userId": self.user_id,
            "date": self._date,  # Keep as number, don't convert to string
            "description": self._description,
            "amount": self._amount.amount,  # Keep as Decimal for DynamoDB
            "currency": self._amount.currency.value if self._amount.currency else None
        }

        if self.balance:
            result["balance"] = self.balance.amount  # Keep as Decimal for DynamoDB

        if self.import_order is not None:
            result["importOrder"] = self.import_order

        if self.transaction_type:
            result["transactionType"] = self.transaction_type

        if self.memo:
            result["memo"] = self.memo

        if self.check_number:
            result["checkNumber"] = self.check_number

        if self.fit_id:
            result["fitId"] = self.fit_id

        if self.status:
            result["status"] = self.status

        if self.created_at:
            result["createdAt"] = self.created_at  # Keep as number, don't convert to string

        if self.updated_at:
            result["updatedAt"] = self.updated_at  # Keep as number, don't convert to string

        if self.transaction_hash:
            result["transactionHash"] = self.transaction_hash

        return result

    @classmethod
    def from_flat_dict(cls, data: Dict[str, str]) -> 'Transaction':
        """
        Create a transaction object from a flattened dictionary where all values are strings.
        This is useful for reconstructing objects from storage systems that don't support nested structures.
        """
        # Create Money objects for amount and balance
        amount = Money(
            amount=Decimal(data["amount"]),
            currency=Currency(data["currency"]) if data["currency"] else None
        )

        balance = None
        if "balance" in data:
            balance = Money(
                amount=Decimal(data["balance"]),
                currency=Currency(data["currency"]) if data["currency"] else None
            )

        # Create the Transaction object
        return cls(
            transaction_id=data["transactionId"],
            account_id=data["accountId"],
            file_id=data["fileId"],
            user_id=data["userId"],
            date=int(data["date"]),
            description=data["description"],
            amount=amount,
            balance=balance,
            import_order=int(data["importOrder"]) if "importOrder" in data else None,
            transaction_type=data.get("transactionType"),
            memo=data.get("memo"),
            check_number=data.get("checkNumber"),
            fit_id=data.get("fitId"),
            status=data.get("status"),
            created_at=int(data["createdAt"]) if "createdAt" in data else None,
            updated_at=int(data["updatedAt"]) if "updatedAt" in data else None
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create from dictionary"""
        return cls(
            user_id=data["userId"],
            file_id=data["fileId"],
            transaction_id=data["transactionId"],
            account_id=data["accountId"],
            date=data["date"],  # milliseconds since epoch
            description=data["description"],
            amount=Money.from_dict(data["amount"]),
            balance=Money.from_dict(data["balance"]) if data.get("balance") else None,
            import_order=data.get("importOrder"),
            transaction_type=data.get("transactionType"),
            memo=data.get("memo"),
            check_number=data.get("checkNumber"),
            fit_id=data.get("fitId"),
            status=data.get("status"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt")
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
    # Required fields
    required_fields = {
        "fileId": str,
        "userId": str,
        "date": int,
        "description": str,
        "amount": dict
    }
    
    # Check required fields and their types
    for field, expected_type in required_fields.items():
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
        if not isinstance(data[field], expected_type):
            raise ValueError(f"Field {field} must be of type {expected_type.__name__}")
    
    # Validate date is milliseconds since epoch
    if not isinstance(data["date"], int) or data["date"] < 0:
        raise ValueError("Date must be a positive integer representing milliseconds since epoch")
    
    # Validate timestamps
    if "createdAt" in data:
        if not isinstance(data["createdAt"], int) or data["createdAt"] < 0:
            raise ValueError("Created at must be a positive integer representing milliseconds since epoch")
    
    if "updatedAt" in data:
        if not isinstance(data["updatedAt"], int) or data["updatedAt"] < 0:
            raise ValueError("Updated at must be a positive integer representing milliseconds since epoch")
    
    # Validate amount is a valid Money object
    if not isinstance(data["amount"], dict) or "amount" not in data["amount"] or "currency" not in data["amount"]:
        raise ValueError("Amount must be a valid Money object")
    
    # Validate balance if present
    if "balance" in data and data["balance"]:
        if not isinstance(data["balance"], dict) or "amount" not in data["balance"] or "currency" not in data["balance"]:
            raise ValueError("Balance must be a valid Money object")
    
    # Validate string fields and their lengths
    string_fields = {
        "description": 1000,
        "memo": 1000,
        "category": 100,
        "payee": 100,
        "checkNumber": 50,
        "reference": 100,
        "transactionType": 50,
        "status": 50,
        "fitId": 100
    }
    
    for field, max_length in string_fields.items():
        if field in data and data[field]:
            if not isinstance(data[field], str):
                raise ValueError(f"Field {field} must be a string")
            if len(data[field]) > max_length:
                raise ValueError(f"Field {field} must be {max_length} characters or less")
    
    # Validate numeric fields
    numeric_fields = {
        "importOrder": int
    }
    
    for field, expected_type in numeric_fields.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                raise ValueError(f"Field {field} must be of type {expected_type.__name__}")
    
    # Validate IDs are valid UUIDs
    id_fields = ["transactionId", "accountId", "fileId", "userId"]
    for field in id_fields:
        if field in data and data[field]:
            try:
                uuid.UUID(data[field])
            except ValueError:
                raise ValueError(f"Field {field} must be a valid UUID")
    
    return True

def type_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError

def transaction_to_json(tx):
    # If already a Transaction object, use to_dict; else, from_dict
    if isinstance(tx, Transaction):
        d = tx.to_dict()
    else:
        d = Transaction.from_dict(tx).to_dict()
    
    return json.dumps(d, default=type_default)
