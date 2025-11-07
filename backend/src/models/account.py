"""
Account models for the financial account management system.
"""
import decimal
import enum
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal
from typing_extensions import Self

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator, ValidationInfo

from models.money import Currency, Money
from utils.serde_utils import to_currency

# Configure logging
logger = logging.getLogger(__name__)


class AccountType(str, enum.Enum):
    """Enum for account types"""
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN = "loan"
    OTHER = "other"


class Account(BaseModel):
    """
    Represents a financial account in the system using Pydantic.
    """
    account_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="accountId")
    user_id: str = Field(alias="userId")
    account_name: str = Field(max_length=100, alias="accountName")
    account_type: AccountType = Field(alias="accountType")
    institution: Optional[str] = Field(default=None, max_length=100)
    balance: Optional[Decimal] = None
    currency: Optional[Currency] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = Field(default=True, alias="isActive")
    default_file_map_id: Optional[uuid.UUID] = Field(default=None, alias="defaultFileMapId")
    first_transaction_date: Optional[int] = Field(default=None, alias="firstTransactionDate")  # milliseconds since epoch
    last_transaction_date: Optional[int] = Field(default=None, alias="lastTransactionDate")  # milliseconds since epoch
    imports_start_date: Optional[int] = Field(default=None, alias="importsStartDate")  # milliseconds since epoch - first date covered by transaction files
    imports_end_date: Optional[int] = Field(default=None, alias="importsEndDate")  # milliseconds since epoch - last date covered by transaction files
    
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdAt")
    updated_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str
        },
        use_enum_values=False,  # Preserve enum objects (not strings) for type safety
        arbitrary_types_allowed=True
    )

    @field_validator('created_at', 'updated_at', 'imports_start_date', 'imports_end_date')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v
    
    @field_validator('currency', mode='after')
    @classmethod
    def validate_currency(cls, v, info: ValidationInfo) -> Optional[Currency]:
        """Ensure currency is always a Currency enum, never a string."""
        if v is None:
            return None
        if isinstance(v, Currency):
            return v
        # If we get here, something assigned a non-Currency value
        raise ValueError(f"Currency must be a Currency enum, got {type(v).__name__}: {v}")
    
    @model_validator(mode='after')
    def check_currency_if_balance_exists(self) -> Self:
        if self.balance is not None and self.currency is None:
            raise ValueError("Account currency must be set if balance is provided.")
        return self

    @model_validator(mode='after') 
    def check_imports_date_consistency(self) -> Self:
        if (self.imports_start_date is not None and 
            self.imports_end_date is not None and 
            self.imports_start_date > self.imports_end_date):
            raise ValueError("importsStartDate must be less than or equal to importsEndDate.")
        return self

    def update_account_details(self, update_data: 'AccountUpdate') -> bool:
        """
        Updates the account with data from an AccountUpdate DTO.
        Returns True if any fields were changed, False otherwise.
        """
        updated_fields = False
        update_dict = update_data.model_dump(exclude_unset=True, by_alias=False)

        for key, value in update_dict.items():
            if key not in ["account_id", "user_id", "created_at"] and hasattr(self, key):
                if getattr(self, key) != value:
                    setattr(self, key, value)
                    updated_fields = True
        
        if updated_fields:
            self.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        return updated_fields




    def to_dynamodb_item(self) -> Dict[str, Any]:
        """
        Serializes the Account object to a dictionary suitable for DynamoDB.
        """
        item = self.model_dump(mode='python', by_alias=True, exclude_none=True)

        if 'accountId' in item and isinstance(item.get('accountId'), uuid.UUID):
            item['accountId'] = str(item['accountId'])
        
        if 'defaultFileMapId' in item and item.get('defaultFileMapId') is not None and isinstance(item.get('defaultFileMapId'), uuid.UUID):
            item['defaultFileMapId'] = str(item.get('defaultFileMapId'))
            
        if 'balance' in item and isinstance(item['balance'], Decimal):
            item['balance'] = str(item['balance']) # Ensure string for DynamoDB if not handled by Boto3 Decimal
          
        # Convert currency enum to string for DynamoDB storage
        if 'currency' in item and item.get('currency') is not None:
            item['currency'] = item['currency'].value if hasattr(item['currency'], 'value') else str(item['currency'])
        
        # Ensure transaction dates are included if they exist
        if self.first_transaction_date is not None:
            item['firstTransactionDate'] = self.first_transaction_date
        if self.last_transaction_date is not None:
            item['lastTransactionDate'] = self.last_transaction_date
        if self.imports_start_date is not None:
            item['importsStartDate'] = self.imports_start_date
        if self.imports_end_date is not None:
            item['importsEndDate'] = self.imports_end_date
        
        # Timestamps (createdAt, updatedAt) are integers from Pydantic model.
        # Boto3 will handle Python int as DynamoDB Number (N).
        # No conversion to ISO string needed if DynamoDB attribute type is N.
            
        return item

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """
        Deserializes a dictionary (from DynamoDB item) into an Account instance.
        """
        # If createdAt/updatedAt are stored as Numbers (N) in DynamoDB,
        # Pydantic will handle conversion to int for the model fields.
        # No manual conversion from ISO string is needed here.

        if 'balance' in data and data['balance'] is not None:
            try:
                data['balance'] = Decimal(str(data['balance']))
            except decimal.InvalidOperation:
                raise ValueError(f"Invalid decimal value for balance from DB: {data['balance']}")

        # Convert currency string to Currency enum if necessary (for data from DynamoDB)
        if 'currency' in data and data.get('currency') is not None and isinstance(data.get('currency'), str):
            try:
                data['currency'] = Currency(data['currency'])
            except ValueError:
                logger.warning(f"Invalid currency value from database: {data['currency']}, setting to None")
                data['currency'] = None

        # Use model_validate for proper validation
        return cls.model_validate(data)


class AccountCreate(BaseModel):
    """DTO for creating a new Account."""
    user_id: str = Field(alias="userId")
    account_name: str = Field(max_length=100, alias="accountName")
    account_type: AccountType = Field(alias="accountType")
    institution: Optional[str] = Field(default=None, max_length=100)
    balance: Optional[Decimal] = None
    currency: Optional[Currency] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    is_active: bool = Field(default=True, alias="isActive")
    default_file_map_id: Optional[uuid.UUID] = Field(default=None, alias="defaultFileMapId")
    imports_start_date: Optional[int] = Field(default=None, alias="importsStartDate")  # milliseconds since epoch
    imports_end_date: Optional[int] = Field(default=None, alias="importsEndDate")  # milliseconds since epoch

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str, Decimal: str},
        use_enum_values=False,  # Preserve enum objects (not strings) for type safety
        arbitrary_types_allowed=True
    )
    
    @field_validator('currency', mode='after')
    @classmethod
    def validate_currency(cls, v, info: ValidationInfo) -> Optional[Currency]:
        """Ensure currency is always a Currency enum, never a string."""
        if v is None:
            return None
        if isinstance(v, Currency):
            return v
        # If we get here, something assigned a non-Currency value
        raise ValueError(f"Currency must be a Currency enum, got {type(v).__name__}: {v}")
    
    @model_validator(mode='after')
    def check_currency_if_balance_exists_create(self: Self) -> Self:
        if self.balance is not None and self.currency is None:
            raise ValueError("Currency must be provided with balance.")
        return self
    
    @model_validator(mode='after') 
    def check_imports_date_consistency_create(self) -> Self:
        if (self.imports_start_date is not None and 
            self.imports_end_date is not None and 
            self.imports_start_date > self.imports_end_date):
            raise ValueError("importsStartDate must be less than or equal to importsEndDate.")
        return self

class AccountUpdate(BaseModel):
    """DTO for updating an existing Account. All fields are optional."""
    account_name: Optional[str] = Field(default=None, max_length=100, alias="accountName")
    account_type: Optional[AccountType] = Field(default=None, alias="accountType")
    institution: Optional[str] = Field(default=None, max_length=100)
    balance: Optional[Decimal] = None
    currency: Optional[Currency] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = Field(default=None, alias="isActive")
    default_file_map_id: Optional[uuid.UUID] = Field(default=None, alias="defaultFileMapId")
    imports_start_date: Optional[int] = Field(default=None, alias="importsStartDate")  # milliseconds since epoch
    imports_end_date: Optional[int] = Field(default=None, alias="importsEndDate")  # milliseconds since epoch

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str, Decimal: str},
        use_enum_values=False,  # Preserve enum objects (not strings) for type safety
        arbitrary_types_allowed=True
    )

    @field_validator('currency', mode='after')
    @classmethod
    def validate_currency(cls, v, info: ValidationInfo) -> Optional[Currency]:
        """Ensure currency is always a Currency enum, never a string."""
        if v is None:
            return None
        if isinstance(v, Currency):
            return v
        # If we get here, something assigned a non-Currency value
        raise ValueError(f"Currency must be a Currency enum, got {type(v).__name__}: {v}")

    @model_validator(mode='after')
    def check_currency_consistency_on_update(self: Self, info: ValidationInfo) -> Self:
        # If balance is being updated (not None) AND currency is also being set (not None), they should be consistent.
        # However, balance is Decimal, so it has no inner currency.
        # The main concern is if the account has a currency and a new balance is set, or if currency is changed.
        # If 'balance' is provided in the update, and the account *already* has a currency, it's fine.
        # If 'balance' is provided, and 'currency' is also provided in the update, they apply.
        # If 'balance' is provided, but 'currency' is NOT provided in the update, AND the account has no currency, then it's an issue.

        # This validator needs context of the existing Account object, which is not available here directly.
        # This type of validation is better suited for a service layer.
        # For the DTO itself, we can check if 'balance' is set, 'currency' must also be set OR already exist on the entity.
        # A simpler check: if balance is being set, currency must not be None (either in update or existing).
        # Given the validator has no access to the existing entity state, we can only validate fields within the DTO.
        if self.balance is not None and self.currency is None:
            # This means user is trying to set a balance without specifying a currency.
            # This is only problematic if the account doesn't already have a currency.
            # We can't check that here. A common pattern is that if you update balance, you might also need to update currency
            # or the existing currency is assumed.
            # For now, let's remove this validator as its logic is complex without context.
            # The service layer should handle this: if balance is updated, ensure currency is set.
            pass # Removing the previous raise ValueError for now. Service layer should handle this.
        return self
    
    @model_validator(mode='after') 
    def check_imports_date_consistency_update(self) -> Self:
        if (self.imports_start_date is not None and 
            self.imports_end_date is not None and 
            self.imports_start_date > self.imports_end_date):
            raise ValueError("importsStartDate must be less than or equal to importsEndDate.")
        return self

# Removed validate_account_data function (validations moved into Pydantic models) 