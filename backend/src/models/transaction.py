from locale import currency
import uuid
from typing import Dict, Any, Optional, Union, ClassVar
from datetime import datetime, timezone
import logging
from decimal import Decimal
from typing_extensions import Self

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict # For Pydantic v2
from pydantic import ValidationError # Import for explicit error handling if needed

from utils.transaction_utils import generate_transaction_hash
from models.money import Money # Assumed to be Pydantic compatible
from models.account import Currency # Assumed to be an Enum used by Money

logger = logging.getLogger()
# logger.setLevel(logging.INFO) # Keep existing logging setup or let it be configured elsewhere

class Transaction(BaseModel):
    """
    Represents a single financial transaction, using Pydantic for validation and serialization.
    """
    user_id: str = Field(alias="userId")
    file_id: uuid.UUID = Field(alias="fileId")
    transaction_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="transactionId")
    account_id: uuid.UUID = Field(alias="accountId")
    date: int  # milliseconds since epoch
    description: str = Field(max_length=1000)
    amount: Decimal
    currency: Optional[Currency] = None
    balance: Optional[Decimal] = None
    import_order: Optional[int] = Field(default=None, alias="importOrder")
    transaction_type: Optional[str] = Field(default=None, alias="transactionType", max_length=50)
    memo: Optional[str] = Field(default=None, max_length=1000)
    check_number: Optional[str] = Field(default=None, alias="checkNumber", max_length=50)
    fit_id: Optional[str] = Field(default=None, alias="fitId", max_length=100)
    status: Optional[str] = Field(default=None, max_length=50)
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdAt")
    updated_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="updatedAt")
    transaction_hash: Optional[int] = Field(default=None, alias="transactionHash")

    # Class variable to store names of fields that trigger hash regeneration
    _hash_trigger_fields: ClassVar[set[str]] = {"account_id", "date", "description", "amount", "currency"}

    model_config = ConfigDict(
        populate_by_name=True,  # Allows using field names or aliases for population
        json_encoders={
            Decimal: str,       # Serialize Decimal as string in JSON
            uuid.UUID: str      # Serialize UUID as string in JSON (default but explicit)
        },
        arbitrary_types_allowed=True # If Money or Currency are not Pydantic models but used directly
    )

    @field_validator('date', 'created_at', 'updated_at')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v
    
    # Other field-specific validators (e.g., for string patterns, specific value constraints) can be added here.

    def _recalculate_and_set_hash_value(self) -> None:
        """
        Helper method to calculate the transaction hash based on key fields.
        Sets self.transaction_hash to the new value if it differs.
        """
        calculated_hash: Optional[int] = None
        required_fields_present = (
            self.account_id is not None and
            self.date is not None and
            self.amount is not None and
            self.description is not None and
            self.currency is not None
        )

        if required_fields_present:
            if isinstance(self.amount, Decimal):
                try:
                    calculated_hash = generate_transaction_hash(
                        account_id=str(self.account_id),
                        date=self.date,
                        amount=self.amount,
                        description=self.description
                    )
                except Exception as e:
                    logger.error(
                        f"Error calculating transaction hash for transactionId {self.transaction_id if hasattr(self, 'transaction_id') else 'UNKNOWN'}: {e}"
                    )
            else:
                logger.warning(
                    f"Could not calculate transaction hash for {self.transaction_id if hasattr(self, 'transaction_id') else 'UNKNOWN'} "
                    f"due to invalid amount structure (amount not Decimal)."
                )
        
        if self.transaction_hash != calculated_hash:
            self.transaction_hash = calculated_hash # This assignment uses Pydantic's __setattr__
                                                    # but won't recurse as 'transaction_hash' is not a trigger field.
            # logger.info(f"Transaction hash for {self.transaction_id if hasattr(self, 'transaction_id') else 'UNKNOWN'} set to: {calculated_hash}")


    @model_validator(mode='after')
    def initial_hash_calculation_on_validation(self) -> Self:
        """
        Calculates the transaction hash after the model is validated (e.g., on creation).
        """
        self._recalculate_and_set_hash_value()
        return self

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Override __setattr__ to recalculate the transaction_hash
        if a relevant field (account_id, date, description, amount) is modified
        after the model has been initialized.
        """
        super().__setattr__(name, value) # Call parent's __setattr__ to actually set the attribute

        # Check if the model is fully initialized and the changed attribute is a trigger field.
        # hasattr check for 'model_fields_set' is for safety during early init stages before Pydantic sets it.
        model_initialized = hasattr(self, 'model_fields_set') and self.model_fields_set
        
        if model_initialized and name in self._hash_trigger_fields:
            self._recalculate_and_set_hash_value()

    @classmethod
    def create(
        cls,
        user_id: str,
        file_id: Union[str, uuid.UUID],
        account_id: Union[str, uuid.UUID],
        date: int,
        description: str,
        amount: Decimal,
        currency: Optional[Currency] = None,
        balance: Optional[Decimal] = None,
        import_order: Optional[int] = None,
        transaction_type: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        fit_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> "Transaction":
        """
        Creates a new Transaction instance.
        `transaction_id` is generated automatically by default_factory.
        `created_at` and `updated_at` are also set by default_factories.
        Hash is calculated via model_validator.
        """
        init_data = {
            "userId": user_id, # Pass as alias, Pydantic will map due to populate_by_name
            "fileId": file_id,
            "accountId": account_id,
            "date": date,
            "description": description,
            "amount": amount,
            "currency": currency,
            "balance": balance,
            "importOrder": import_order,
            "transactionType": transaction_type,
            "memo": memo,
            "checkNumber": check_number,
            "fitId": fit_id,
            "status": status
        }
        # Filter out None kwargs to avoid overriding Pydantic defaults if not intended
        # However, Pydantic handles Optional[X]=None correctly.
        # clean_init_data = {k: v for k, v in init_data.items() if v is not None}
        # It's generally fine to pass None for optional fields.
        
        return cls.model_validate(init_data)

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """
        Convert the transaction object to a flattened dictionary suitable for DynamoDB.
        Uses Pydantic's model_dump and ensures nested Money objects are also flattened via to_flat_map.
        Ensures UUID fields are converted to strings.
        """
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Ensure UUID fields are strings for DynamoDB
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
            # If a field could be a list of UUIDs, you'd handle that here too:
            # elif isinstance(value, list) and all(isinstance(item, uuid.UUID) for item in value):
            #     data[key] = [str(item) for item in value]

        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """
        Deserializes a dictionary (from DynamoDB) into a Transaction instance.
        Handles reconstruction of Money objects and ensures correct types for other fields.
        """
        # Prepare data for Pydantic model instantiation
        # Pydantic will use aliases if populate_by_name=True in model_config

        # Pydantic handles conversion for Decimal (amount, balance) and Currency (currency)
        # from their string/numeric representations in data based on type hints.
        # Ensure data['amount'] and data['balance'] are in a format Pydantic can parse to Decimal (e.g., string or number).
        # Ensure data['currency'] is a valid string value for the Currency enum.

        # UUIDs: Pydantic should convert string UUIDs to uuid.UUID objects based on type hints.
        # Timestamps: Pydantic should convert numbers to int based on type hints.
        # Other fields should map directly or be handled by Pydantic's parsing.

        return cls.model_validate(data)


def transaction_to_json(transaction_input: Union[Transaction, Dict[str, Any]]) -> str:
    """
    Serializes a Transaction object or a compatible dictionary to a JSON string.
    Uses Pydantic's built-in JSON serialization which respects field aliases and custom encoders.
    """
    if isinstance(transaction_input, Transaction):
        return transaction_input.model_dump_json(by_alias=True, exclude_none=True)
    elif isinstance(transaction_input, dict):
        # Assume the dict can be validated into a Transaction object
        # Keys in dict can be field names (snake_case) or aliases (camelCase)
        try:
            transaction_obj = Transaction.model_validate(transaction_input)
            return transaction_obj.model_dump_json(by_alias=True, exclude_none=True)
        except ValidationError as e:
            logger.error(f"Validation error serializing dict to JSON: {e}")
            # Re-raise with a more context-specific message or handle as needed
            raise ValueError(f"Invalid data provided for transaction_to_json: {e}") from e
    else:
        raise TypeError(
            f"Input must be a Transaction object or a compatible dictionary, got {type(transaction_input)}"
        )

# Removed:
# - HashRegeneratingField class
# - Original __post_init__ and _regenerate_hash (replaced by Pydantic model_validator and __setattr__)
# - Original to_dict, from_dict (Pydantic provides model_dump, model_validate)
# - validate_transaction_data function (validations moved into Pydantic model)
# - type_default function (Pydantic json_encoders in model_config handle this)

class TransactionCreate(BaseModel):
    """Data Transfer Object for creating a new transaction."""
    user_id: str = Field(alias="userId")
    file_id: uuid.UUID = Field(alias="fileId")
    account_id: uuid.UUID = Field(alias="accountId")
    date: int  # milliseconds since epoch
    description: str = Field(max_length=1000)
    amount: Decimal
    currency: Currency

    # Optional fields at creation
    balance: Optional[Decimal] = None
    import_order: Optional[int] = Field(default=None, alias="importOrder")
    transaction_type: Optional[str] = Field(default=None, alias="transactionType", max_length=50)
    memo: Optional[str] = Field(default=None, max_length=1000)
    check_number: Optional[str] = Field(default=None, alias="checkNumber", max_length=50)
    fit_id: Optional[str] = Field(default=None, alias="fitId", max_length=100)
    status: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True # If Money is not a Pydantic model but used directly
    )

    @field_validator('date')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

class TransactionUpdate(BaseModel):
    """Data Transfer Object for updating an existing transaction.
    All fields are optional.
    """
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    date: Optional[int] = None  # milliseconds since epoch
    description: Optional[str] = Field(default=None, max_length=1000)
    amount: Optional[Decimal] = None
    currency: Optional[Currency] = None
    balance: Optional[Decimal] = None
    import_order: Optional[int] = Field(default=None, alias="importOrder")
    transaction_type: Optional[str] = Field(default=None, alias="transactionType", max_length=50)
    memo: Optional[str] = Field(default=None, max_length=1000)
    check_number: Optional[str] = Field(default=None, alias="checkNumber", max_length=50)
    fit_id: Optional[str] = Field(default=None, alias="fitId", max_length=100)
    status: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True # If Money is not a Pydantic model but used directly
    )

    @field_validator('date', check_fields=False) # check_fields=False for optional fields
    @classmethod
    def check_positive_timestamp_optional(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v
