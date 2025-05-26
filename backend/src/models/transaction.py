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
    user_id: uuid.UUID = Field(alias="userId")
    file_id: uuid.UUID = Field(alias="fileId")
    transaction_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="transactionId")
    account_id: uuid.UUID = Field(alias="accountId")
    date: int  # milliseconds since epoch
    description: str = Field(max_length=1000)
    amount: Money

    balance: Optional[Money] = None
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
    _hash_trigger_fields: ClassVar[set[str]] = {"account_id", "date", "description", "amount"}

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
            self.description is not None
        )

        if required_fields_present:
            if hasattr(self.amount, 'amount') and isinstance(self.amount.amount, Decimal):
                try:
                    calculated_hash = generate_transaction_hash(
                        account_id=str(self.account_id),
                        date=self.date,
                        amount=self.amount.amount,
                        description=self.description
                    )
                except Exception as e:
                    logger.error(
                        f"Error calculating transaction hash for transactionId {self.transaction_id if hasattr(self, 'transaction_id') else 'UNKNOWN'}: {e}"
                    )
            else:
                logger.warning(
                    f"Could not calculate transaction hash for {self.transaction_id if hasattr(self, 'transaction_id') else 'UNKNOWN'} "
                    f"due to invalid amount structure (amount.amount missing or not Decimal)."
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
        user_id: Union[str, uuid.UUID],
        file_id: Union[str, uuid.UUID],
        account_id: Union[str, uuid.UUID],
        date: int,
        description: str,
        amount: Union[Money, Dict[str, Any]], # Allow Money object or dict to parse into Money
        balance: Optional[Union[Money, Dict[str, Any]]] = None,
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

    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction object to a flattened dictionary.
        Uses Pydantic's model_dump and then adjusts for specific flat structure requirements.
        Output values match types expected by original `to_flat_dict` (e.g., Decimal for amount).
        """
        # `mode='python'` tries to return rich Python types (like Decimal, UUID)
        # `by_alias=True` uses the aliases (camelCase) as keys
        data = self.model_dump(mode='python', by_alias=True, exclude_none=True)
        
        flat_dict_output = {}

        for key_alias, value in data.items():
            if key_alias == "amount" and self.amount: # value from model_dump(mode='python') on Money is a dict
                flat_dict_output["amount"] = self.amount.amount # Store as Decimal
                if self.amount.currency and hasattr(self.amount.currency, 'value'):
                    flat_dict_output["currency"] = self.amount.currency.value # Store enum value
                elif self.amount.currency: # If currency is not an enum but a simple string/value
                     flat_dict_output["currency"] = self.amount.currency

            elif key_alias == "balance" and self.balance: # value is Money.model_dump()
                flat_dict_output["balance"] = self.balance.amount # Store as Decimal
                # Original to_flat_dict did not store balance_currency, so we replicate that.
            
            elif isinstance(value, uuid.UUID): # Ensure UUIDs are strings in the flat dict
                flat_dict_output[key_alias] = str(value)
            
            else:
                flat_dict_output[key_alias] = value
        
        return flat_dict_output

    @classmethod
    def from_flat_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """
        Create a transaction object from a flattened dictionary.
        The input `data` dictionary is expected to have camelCase keys.
        """
        # Create a mutable copy for manipulation if needed
        input_data_for_pydantic = data.copy()

        # Reconstruct Money object for 'amount'
        amount_decimal_val = input_data_for_pydantic.pop("amount", None)
        # 'currency' is a top-level key in the flat dict, associated with 'amount'
        currency_enum_val = input_data_for_pydantic.pop("currency", None)

        if amount_decimal_val is None:
            # Original code did not raise error here but amount is not optional in Transaction
            # Pydantic will raise error if 'amount' is missing after this.
            # Consider if this method should pre-validate or let Pydantic handle it.
            # For safety, let's ensure amount components are present for Money construction.
             raise ValueError("Missing 'amount' value in flat_dict for Transaction amount.")

        # Construct the amount Money object to be passed to Pydantic
        # Pydantic will parse this dict into a Money field if 'amount' field is of type Money
        input_data_for_pydantic["amount"] = {
            "amount": Decimal(str(amount_decimal_val)), # Ensure Decimal from string
            "currency": currency_enum_val # Pass currency value; Money model should handle it
        }
        
        # Reconstruct Money object for 'balance' if present
        balance_decimal_val = input_data_for_pydantic.pop("balance", None)
        if balance_decimal_val is not None:
            # Balance uses the same 'currency' from the flat dict as 'amount'
            input_data_for_pydantic["balance"] = {
                "amount": Decimal(str(balance_decimal_val)),
                "currency": currency_enum_val 
            }
        
        # Pydantic's model_validate will use aliases due to populate_by_name=True
        # It will also handle type conversions (e.g., string to int, string to UUID).
        try:
            return cls.model_validate(input_data_for_pydantic)
        except ValidationError as e:
            logger.error(f"Validation error in Transaction.from_flat_dict: {e}")
            # Re-raise or handle as appropriate for the application
            raise ValueError(f"Failed to create Transaction from flat_dict: {e}") from e


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
    user_id: uuid.UUID = Field(alias="userId")
    file_id: uuid.UUID = Field(alias="fileId")
    account_id: uuid.UUID = Field(alias="accountId")
    date: int  # milliseconds since epoch
    description: str = Field(max_length=1000)
    amount: Money # Expects a Money object or a dict that can be parsed into Money

    # Optional fields at creation
    balance: Optional[Money] = None
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
    amount: Optional[Money] = None # Expects a Money object or a dict that can be parsed

    balance: Optional[Money] = None
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
