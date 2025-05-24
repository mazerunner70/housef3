"""
Account models for the financial account management system.
"""
import decimal
import enum
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from models.money import Currency, Money


class AccountType(str, enum.Enum):
    """Enum for account types"""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"




@dataclass
class Account:
    """
    Represents a financial account in the system.
    """
    account_id: str
    user_id: str
    account_name: str
    account_type: AccountType
    institution: str
    balance: Money
    currency: Optional[Currency] = None
    notes: Optional[str] = None
    is_active: bool = True
    default_file_map_id: Optional[str] = None
    created_at: str = datetime.utcnow().isoformat()
    updated_at: str = datetime.utcnow().isoformat()

    @classmethod
    def create(
        cls,
        user_id: str,
        account_name: str,
        account_type: AccountType,
        institution: str,
        balance: float = 0.0,
        currency: Optional[Currency] = None,
        notes: Optional[str] = None,
        is_active: bool = True,
        default_file_map_id: Optional[str] = None
    ) -> 'Account':
        """
        Factory method to create a new account with generated ID and timestamps.
        """
        return cls(
            account_id=str(uuid.uuid4()),
            user_id=user_id,
            account_name=account_name,
            account_type=account_type,
            institution=institution,
            balance=Money(Decimal(str(balance)), currency),
            currency=currency,
            notes=notes,
            is_active=is_active,
            default_file_map_id=default_file_map_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the account object to a dictionary.
        """
        result = {
            "accountId": self.account_id,
            "userId": self.user_id,
            "accountName": self.account_name,
            "accountType": self.account_type.value,
            "institution": self.institution,
            "balance": self.balance.to_dict(),  # Use Money's to_dict method
            "currency": self.currency.value if self.currency else None,
            "isActive": self.is_active,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }
        if self.notes:
            result['notes'] = self.notes
        if self.default_file_map_id:
            result['defaultFileMapId'] = self.default_file_map_id
        return result

    def to_flat_dict(self) -> Dict[str, str]:
        """
        Convert the account object to a flat dictionary, suitable for storage in DynamoDB.
        All output values are strings.
        """
        result = {
            "accountId": self.account_id,
            "userId": self.user_id,
            "accountName": self.account_name,
            "accountType": self.account_type.value,
            "institution": self.institution,
            "balance": self.balance.amount,
            "currency": self.currency.value if self.currency else "",
            "isActive": str(self.is_active), 
            "defaultFileMapId": self.default_file_map_id,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }
        if self.notes:
            result['notes'] = self.notes
        return result
    @classmethod
    def from_flat_dict(cls, data: Dict[str, str]) -> 'Account':
        """
        Create an account object from a flat dictionary, as if from storage in DynamoDB.
        All values are strings, so we need to convert them to the correct types.
        """
        result = cls(
            account_id=data["accountId"],
            user_id=data["userId"],
            account_name=data["accountName"],
            account_type=AccountType(data["accountType"]),
            institution=data["institution"],
            balance=Money(Decimal(str(data["balance"])), Currency(data["currency"]) if data["currency"] else None),
            currency=Currency(data["currency"]) if data["currency"] else None,
            is_active=data.get("isActive") == "True",
            default_file_map_id=data.get("defaultFileMapId"),
            created_at=data.get("createdAt", datetime.utcnow().isoformat()),
            updated_at=data.get("updatedAt", datetime.utcnow().isoformat())
        )
        if data.get("notes"):
            result.notes = data["notes"]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """
        Create an account object from a dictionary (e.g. from DynamoDB).
        """
        return cls(
            account_id=data["accountId"],
            user_id=data["userId"],
            account_name=data["accountName"],
            account_type=AccountType(data["accountType"]),
            institution=data["institution"],
            balance=Money.from_dict(data["balance"]),  # Use Money's from_dict method
            currency=Currency(data["currency"]) if data.get("currency") else None,
            notes=data.get("notes"),
            is_active=data.get("isActive", True),
            default_file_map_id=data.get("defaultFileMapId"),
            created_at=data.get("createdAt", datetime.utcnow().isoformat()),
            updated_at=data.get("updatedAt", datetime.utcnow().isoformat())
        )

    def update(self, **kwargs) -> None:
        """
        Update account properties with new values.
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and key not in ("account_id", "user_id", "created_at", "updated_at"):
                setattr(self, key, value)
        
        # Always update the updated_at timestamp
        self.updated_at = datetime.utcnow().isoformat()

    def validate(self) -> None:
        """
        Validate the account object.
        """
        validate_account_data(self.to_dict())

def validate_account_data(data: Dict[str, Any]) -> bool:
    """
    Validate account data according to business rules.
    
    Returns True if valid, raises ValueError with details if invalid.
    """
    required_fields = ["accountName", "accountType", "institution", "userId"]
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate account type
    if "accountType" in data and data["accountType"] not in [t.value for t in AccountType]:
        raise ValueError(f"Invalid account type: {data['accountType']}")
    
    # Validate currency
    if "currency" in data and data["currency"] not in [c.value for c in Currency]:
        raise ValueError(f"Invalid currency: {data['currency']}")
    
    # Validate balance if present
    if "balance" in data:
        try:
            if isinstance(data["balance"], dict):
                # Validate balance dictionary structure
                if "amount" not in data["balance"] or "currency" not in data["balance"]:
                    raise ValueError("Balance must have amount and currency fields")
                Decimal(str(data["balance"]["amount"]))
                if data["balance"]["currency"] not in [c.value for c in Currency]:
                    raise ValueError(f"Invalid currency in balance: {data['balance']['currency']}")
            else:
                # For backward compatibility, try to parse as decimal
                Decimal(str(data["balance"]))
        except (ValueError, TypeError, decimal.InvalidOperation):
            raise ValueError("Balance must be a valid number or Money object")
    
    # Validate string lengths
    if "accountName" in data and len(data["accountName"]) > 100:
        raise ValueError("Account name must be 100 characters or less")
    
    if "institution" in data and len(data["institution"]) > 100:
        raise ValueError("Institution name must be 100 characters or less")
    
    if "notes" in data and len(data["notes"]) > 1000:
        raise ValueError("Notes must be 1000 characters or less")
    
    return True 