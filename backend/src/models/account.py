"""
Account models for the financial account management system.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


class AccountType(str, enum.Enum):
    """Enum for account types"""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class Currency(str, enum.Enum):
    """Enum for currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    JPY = "JPY"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
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
    balance: Decimal
    currency: Currency
    notes: Optional[str] = None
    is_active: bool = True
    default_field_map_id: Optional[str] = None
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
        currency: Currency = Currency.USD,
        notes: Optional[str] = None,
        is_active: bool = True,
        default_field_map_id: Optional[str] = None
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
            balance=Decimal(str(balance)),
            currency=currency,
            notes=notes,
            is_active=is_active,
            default_field_map_id=default_field_map_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the account object to a dictionary suitable for storage.
        """
        result = {
            "accountId": self.account_id,
            "userId": self.user_id,
            "accountName": self.account_name,
            "accountType": self.account_type.value,
            "institution": self.institution,
            "balance": str(self.balance),  # Convert to string for DynamoDB
            "currency": self.currency.value,
            "isActive": self.is_active,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at
        }
        if self.notes:
            result['notes'] = self.notes
        if self.default_field_map_id:
            result['defaultFieldMapId'] = self.default_field_map_id
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
            balance=Decimal(data["balance"]),
            currency=Currency(data["currency"]),
            notes=data.get("notes"),
            is_active=data.get("isActive", True),
            default_field_map_id=data.get("defaultFieldMapId"),
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
    
    # Validate numeric fields
    if "balance" in data:
        try:
            Decimal(str(data["balance"]))
        except (ValueError, TypeError, decimal.InvalidOperation):
            raise ValueError("Balance must be a valid number")
    
    # Validate string lengths
    if "accountName" in data and len(data["accountName"]) > 100:
        raise ValueError("Account name must be 100 characters or less")
    
    if "institution" in data and len(data["institution"]) > 100:
        raise ValueError("Institution name must be 100 characters or less")
    
    if "notes" in data and len(data["notes"]) > 1000:
        raise ValueError("Notes must be 1000 characters or less")
    
    return True 