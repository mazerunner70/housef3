from locale import currency
import uuid
from typing import Dict, Any, Optional, Union, ClassVar, List
from datetime import datetime, timezone
import logging
from decimal import Decimal
from typing_extensions import Self
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, ValidationInfo # For Pydantic v2
from pydantic import ValidationError # Import for explicit error handling if needed

from utils.transaction_utils import generate_transaction_hash
from models.money import Money # Assumed to be Pydantic compatible
from models.account import Currency # Assumed to be an Enum used by Money

logger = logging.getLogger()
# logger.setLevel(logging.INFO) # Keep existing logging setup or let it be configured elsewhere


class CategoryAssignmentStatus(str, Enum):
    """
    Enum for category assignment status in the suggestion workflow.
    """
    SUGGESTED = "suggested"  # Rule matched, awaiting user review
    CONFIRMED = "confirmed"  # User has approved the category assignment


class TransactionCategoryAssignment(BaseModel):
    """
    Represents a category assignment for a transaction.
    Supports suggestion workflow where assignments start as 'suggested' and must be confirmed by user.
    """
    category_id: uuid.UUID = Field(alias="categoryId")
    confidence: int = Field(default=100, ge=0, le=100)  # 0-100 confidence score
    status: CategoryAssignmentStatus = Field(default=CategoryAssignmentStatus.SUGGESTED)
    is_manual: bool = Field(default=False, alias="isManual")  # Manually assigned vs auto-assigned
    assigned_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), 
        alias="assignedAt"
    )
    confirmed_at: Optional[int] = Field(default=None, alias="confirmedAt")  # When user confirmed this assignment
    rule_id: Optional[str] = Field(default=None, alias="ruleId")  # Which rule triggered this assignment

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            uuid.UUID: str
        },
        use_enum_values=False  # Preserve enum objects (not strings) for type safety
    )

    @field_validator('assigned_at', 'confirmed_at')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

    def confirm_assignment(self) -> None:
        """Mark this assignment as confirmed by the user."""
        self.status = CategoryAssignmentStatus.CONFIRMED
        self.confirmed_at = int(datetime.now(timezone.utc).timestamp() * 1000)

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        data = self.model_dump(by_alias=True, exclude_none=True)
        
        # Ensure all UUID fields are converted to strings for DynamoDB
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
        
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "TransactionCategoryAssignment":
        """Create from DynamoDB item data."""
        # Copy data to avoid modifying original
        converted_data = data.copy()
        
        # Convert Decimal values to int for numeric fields
        int_fields = ['confidence', 'assignedAt', 'confirmedAt']
        for field in int_fields:
            if field in converted_data and converted_data[field] is not None:
                if isinstance(converted_data[field], Decimal):
                    converted_data[field] = int(converted_data[field])
        
        # Manually convert categoryId string to UUID object
        if 'categoryId' in converted_data and isinstance(converted_data['categoryId'], str):
            try:
                converted_data['categoryId'] = uuid.UUID(converted_data['categoryId'])
            except ValueError:
                # If invalid UUID, let Pydantic handle the error
                pass
        
        # Use model_validate for proper validation
        return cls.model_validate(converted_data)


class Transaction(BaseModel):
    """
    Represents a single financial transaction, using Pydantic for validation and serialization.
    Enhanced to support multiple category assignments with suggestion workflow.
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
    status_date: Optional[str] = Field(default=None, alias="statusDate")  # Composite key of status#date
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdAt")
    updated_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="updatedAt")
    transaction_hash: Optional[int] = Field(default=None, alias="transactionHash")

    # Multiple category support
    categories: List[TransactionCategoryAssignment] = Field(default_factory=list)
    primary_category_id: Optional[uuid.UUID] = Field(default=None, alias="primaryCategoryId")  # Main category for display

    # Class variable to store names of fields that trigger hash regeneration
    _hash_trigger_fields: ClassVar[set[str]] = {"account_id", "date", "description", "amount", "currency"}

    model_config = ConfigDict(
        populate_by_name=True,  # Allows using field names or aliases for population
        json_encoders={
            Decimal: str,       # Serialize Decimal as string in JSON
            uuid.UUID: str      # Serialize UUID as string in JSON (default but explicit)
        },
        use_enum_values=False,  # Preserve enum objects (not strings) for type safety
        arbitrary_types_allowed=True # If Money or Currency are not Pydantic models but used directly
    )

    @field_validator('date', 'created_at', 'updated_at')
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
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
    
    # Other field-specific validators (e.g., for string patterns, specific value constraints) can be added here.
    
    # Computed properties for backward compatibility and category management
    @property
    def category_id(self) -> Optional[uuid.UUID]:
        """Returns the primary category ID for backward compatibility"""
        return self.primary_category_id

    @property
    def manual_category(self) -> bool:
        """Returns True if primary category was manually assigned"""
        if self.primary_category_id:
            primary_assignment = next(
                (cat for cat in self.categories if cat.category_id == self.primary_category_id), 
                None
            )
            return primary_assignment.is_manual if primary_assignment else False
        return False

    @property
    def confirmed_categories(self) -> List[TransactionCategoryAssignment]:
        """Returns only confirmed category assignments"""
        return [cat for cat in self.categories if type(cat.status).__name__ == "CategoryAssignmentStatus" and cat.status.name == "CONFIRMED"]

    @property
    def suggested_categories(self) -> List[TransactionCategoryAssignment]:
        """Returns only suggested category assignments awaiting review"""
        return [cat for cat in self.categories if type(cat.status).__name__ == "CategoryAssignmentStatus" and cat.status.name == "SUGGESTED"]

    @property
    def needs_category_review(self) -> bool:
        """Returns True if transaction has unconfirmed category suggestions"""
        return len(self.suggested_categories) > 0

    def add_category_suggestion(
        self, 
        category_id: uuid.UUID, 
        confidence: int = 100, 
        rule_id: Optional[str] = None
    ) -> None:
        """Add a new category suggestion that requires user review"""
        # Check if category is already assigned
        existing = next((cat for cat in self.categories if cat.category_id == category_id), None)
        if existing:
            return  # Category already assigned
        
        suggestion = TransactionCategoryAssignment(
            categoryId=category_id,
            confidence=confidence,
            status=CategoryAssignmentStatus.SUGGESTED,
            isManual=False,
            ruleId=rule_id
        )
        self.categories.append(suggestion)

    def confirm_category_assignment(self, category_id: uuid.UUID, set_as_primary: bool = False) -> bool:
        """Confirm a suggested category assignment"""
        assignment = next((cat for cat in self.categories if cat.category_id == category_id), None)
        if assignment and type(assignment.status).__name__ == "CategoryAssignmentStatus" and assignment.status.name == "SUGGESTED":
            assignment.confirm_assignment()
            if set_as_primary or self.primary_category_id is None:
                self.primary_category_id = category_id
            return True
        return False

    def add_manual_category(self, category_id: uuid.UUID, set_as_primary: bool = False) -> None:
        """Add a manually assigned category (immediately confirmed)"""
        logger.info(f"Adding manual category {category_id} to transaction {self.transaction_id}")
        logger.info(f"Categories: {self.categories}")
        logger.info(f"Primary category ID: {self.primary_category_id}")
        if self.categories is None:
            self.categories = []
        # Check if category is already assigned
        existing = next((cat for cat in self.categories if cat.category_id == category_id), None)
        if existing:
            if type(existing.status).__name__ == "CategoryAssignmentStatus" and existing.status.name == "SUGGESTED":
                existing.confirm_assignment()
                existing.is_manual = True
            return
        
        assignment = TransactionCategoryAssignment(
            categoryId=category_id,
            confidence=100,
            status=CategoryAssignmentStatus.CONFIRMED,
            isManual=True
        )
        assignment.confirm_assignment()
        self.categories.append(assignment) 
        
        if set_as_primary or self.primary_category_id is None:
            self.primary_category_id = category_id

    def remove_category_assignment(self, category_id: uuid.UUID) -> bool:
        """Remove a category assignment"""
        original_count = len(self.categories)
        self.categories = [cat for cat in self.categories if cat.category_id != category_id]
        
        # If we removed the primary category, set a new one from confirmed categories
        if self.primary_category_id == category_id:
            confirmed = self.confirmed_categories
            self.primary_category_id = confirmed[0].category_id if confirmed else None
        
        return len(self.categories) < original_count

    def set_primary_category(self, category_id: uuid.UUID) -> bool:
        """Set a confirmed category as primary"""
        # Ensure the category is confirmed
        assignment = next((cat for cat in self.categories if cat.category_id == category_id), None)
        if assignment and type(assignment.status).__name__ == "CategoryAssignmentStatus" and assignment.status.name == "CONFIRMED":
            self.primary_category_id = category_id
            return True
        return False

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

    @property
    def computed_status_date(self) -> Optional[str]:
        """Computed property for the statusDate composite key."""
        if self.status is not None and self.date is not None:
            return f"{self.status}#{self.date}"
        return None

    @classmethod
    def create(cls, create_data: "TransactionCreate") -> "Transaction":
        """
        Creates a new Transaction instance from a TransactionCreate DTO.
        `transaction_id` is generated automatically by default_factory.
        `created_at` and `updated_at` are also set by default_factories.
        Hash is calculated via model_validator.
        """
        init_data = create_data.model_dump(by_alias=True, exclude_none=True)
        return cls.model_validate(init_data)

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """
        Convert the transaction object to a flattened dictionary suitable for DynamoDB.
        Uses Pydantic's model_dump and ensures nested Money objects are also flattened via to_flat_map.
        Ensures UUID fields are converted to strings.
        """
        # Convert category assignments to DynamoDB format before calling model_dump
        processed_categories = []
        if self.categories:
            for assignment in self.categories:
                processed_categories.append(assignment.to_dynamodb_item())
        
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Add computed statusDate field
        status_date = self.computed_status_date
        if status_date is not None:
            data['statusDate'] = status_date

        # Ensure UUID fields are strings for DynamoDB
        for key, value in data.items():
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
            # If a field could be a list of UUIDs, you'd handle that here too:
            # elif isinstance(value, list) and all(isinstance(item, uuid.UUID) for item in value):
            #     data[key] = [str(item) for item in value]

        # Replace the categories with the processed ones
        if processed_categories:
            data['categories'] = processed_categories
        
        # Explicitly ensure primaryCategoryId is converted to string if it's a UUID
        if 'primaryCategoryId' in data and isinstance(data['primaryCategoryId'], uuid.UUID):
            data['primaryCategoryId'] = str(data['primaryCategoryId'])

        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> Self:
        """
        Deserializes a dictionary (from DynamoDB) into a Transaction instance.
        Handles reconstruction of Money objects and ensures correct types for other fields.
        """
        # Copy data to avoid modifying original
        converted_data = data.copy()
        
        # Convert Decimal values to int for timestamp fields
        int_fields = ['date', 'createdAt', 'updatedAt', 'transactionHash', 'importOrder']
        for field in int_fields:
            if field in converted_data and converted_data[field] is not None:
                if isinstance(converted_data[field], Decimal):
                    converted_data[field] = int(converted_data[field])

        # Handle category assignments reconstruction
        if 'categories' in converted_data and converted_data['categories']:
            processed_categories = []
            for assignment in converted_data['categories']:
                if isinstance(assignment, dict):
                    # New format: dictionary
                    processed_categories.append(
                        TransactionCategoryAssignment.from_dynamodb_item(assignment)
                    )
                elif isinstance(assignment, str):
                    # Legacy format: string representation of dictionary
                    try:
                        import json
                        import ast
                        # Try to parse as JSON first
                        try:
                            assignment_dict = json.loads(assignment)
                        except json.JSONDecodeError:
                            # If JSON parsing fails, try ast.literal_eval for Python dict format
                            assignment_dict = ast.literal_eval(assignment)
                        
                        processed_categories.append(
                            TransactionCategoryAssignment.from_dynamodb_item(assignment_dict)
                        )
                    except (json.JSONDecodeError, ValueError, SyntaxError) as e:
                        # If we can't parse the string, skip this assignment and log it
                        logger.warning(f"Unable to parse category assignment string: {assignment}, error: {e}")
                        continue
                else:
                    # Already a TransactionCategoryAssignment object
                    processed_categories.append(assignment)
            
            converted_data['categories'] = processed_categories

        # Use model_validate for proper validation
        return cls.model_validate(converted_data)


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

class _TransactionFieldsMixin(BaseModel):
    """
    Shared field definitions and validators for Transaction DTOs.
    Not meant to be used directly - use TransactionCreate or TransactionUpdate instead.
    """
    # Optional transaction detail fields (shared across Create/Update)
    balance: Optional[Decimal] = None
    import_order: Optional[int] = Field(default=None, alias="importOrder")
    transaction_type: Optional[str] = Field(default=None, alias="transactionType", max_length=50)
    memo: Optional[str] = Field(default=None, max_length=1000)
    check_number: Optional[str] = Field(default=None, alias="checkNumber", max_length=50)
    fit_id: Optional[str] = Field(default=None, alias="fitId", max_length=100)
    status: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(
        populate_by_name=True,
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


class TransactionCreate(_TransactionFieldsMixin):
    """Data Transfer Object for creating a new transaction."""
    # Required fields at creation
    user_id: str = Field(alias="userId")
    file_id: uuid.UUID = Field(alias="fileId")
    account_id: uuid.UUID = Field(alias="accountId")
    date: int  # milliseconds since epoch
    description: str = Field(max_length=1000)
    amount: Decimal
    currency: Currency

    @field_validator('date')
    @classmethod
    def check_positive_timestamp(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v


class TransactionUpdate(_TransactionFieldsMixin):
    """Data Transfer Object for updating an existing transaction.
    All fields are optional.
    """
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    date: Optional[int] = None  # milliseconds since epoch
    description: Optional[str] = Field(default=None, max_length=1000)
    amount: Optional[Decimal] = None
    currency: Optional[Currency] = None

    @field_validator('date', check_fields=False)
    @classmethod
    def check_positive_timestamp_optional(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v
