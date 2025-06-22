"""
Transaction file models for the financial account management system.
"""
from decimal import Decimal
import decimal
import enum
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo

from models.account import Currency
from models.money import Money
import warnings

# Configure logging
logger = logging.getLogger(__name__)

# Convert only Pydantic serialization warnings to exceptions
warnings.filterwarnings('error', category=UserWarning, message='.*Pydantic serializer warnings.*')

def convert_currency_input(currency_input: Any) -> Optional[Currency]:
    """
    Helper function to convert currency input (typically from API) to Currency enum.
    Use this for API input handling before creating model instances.
    
    Args:
        currency_input: String currency code or Currency enum
        
    Returns:
        Currency enum or None
        
    Raises:
        ValueError: If currency_input is invalid
    """
    if currency_input is None:
        return None
    if isinstance(currency_input, Currency):
        return currency_input
    if isinstance(currency_input, str):
        try:
            return Currency(currency_input)
        except ValueError:
            raise ValueError(f"Invalid currency value: '{currency_input}'. Valid options are: {', '.join([c.value for c in Currency])}")
    raise ValueError(f"Currency must be a string or Currency enum, got {type(currency_input).__name__}: {currency_input}")


class FileFormat(str, enum.Enum):
    """Enum for transaction file formats"""
    CSV = "csv"
    OFX = "ofx"
    QFX = "qfx"
    QIF = "qif"
    PDF = "pdf"
    XLSX = "xlsx"
    OTHER = "other"
    JSON = "json"
    EXCEL = "excel"


class ProcessingStatus(str, enum.Enum):
    """Enum for file processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"
    NEEDS_MAPPING = "needs_mapping"


class DateRange(BaseModel):
    """Represents a date range for transactions in a file"""
    start_date: int = Field(alias="startDate") # milliseconds since epoch
    end_date: int = Field(alias="endDate") # milliseconds since epoch

    model_config = ConfigDict(
        populate_by_name=True
    )


class TransactionFile(BaseModel):
    """
    Represents a transaction file uploaded by a user and optionally associated with an account.
    Uses Pydantic for validation and serialization.
    """
    file_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="fileId")
    user_id: str = Field(alias="userId") # Changed to str
    file_name: str = Field(alias="fileName")
    upload_date: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="uploadDate") # milliseconds since epoch
    file_size: int = Field(alias="fileSize")
    s3_key: str = Field(alias="s3Key")
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, alias="processingStatus")
    
    processed_date: Optional[int] = Field(default=None, alias="processedDate") # milliseconds since epoch
    file_format: Optional[FileFormat] = Field(default=None, alias="fileFormat")
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    file_map_id: Optional[uuid.UUID] = Field(default=None, alias="fileMapId") # Changed to UUID
    record_count: Optional[int] = Field(default=None, alias="recordCount")
    
    # Replaced date_range_start and date_range_end with a DateRange object
    date_range: Optional[DateRange] = Field(default=None, alias="dateRange")
    
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    opening_balance: Optional[Decimal] = Field(default=None, alias="openingBalance")
    currency: Optional[Currency] = None # This might be part of Money or derived, review usage
    duplicate_count: Optional[int] = Field(default=None, alias="duplicateCount")
    transaction_count: Optional[int] = Field(default=None, alias="transactionCount")
    
    created_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="createdAt")
    updated_at: int = Field(default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000), alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            Decimal: str,
            uuid.UUID: str,
            # enum.Enum: lambda e: e.value # Handles FileFormat and ProcessingStatus automatically with Pydantic v2 if they are StrEnum
        },
        arbitrary_types_allowed=True # For Money if it's not a Pydantic model
    )

    @field_validator('upload_date', 'processed_date', 'created_at', 'updated_at', check_fields=False)
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
        # Check if this is from database deserialization
        if info.context and info.context.get('from_database'):
            # During database deserialization, we've already converted strings to enums
            return v
        # If we get here, something assigned a non-Currency value
        raise ValueError(f"Currency must be a Currency enum, got {type(v).__name__}: {v}")

    # to_flat_dict, from_flat_dict, to_dict, from_dict are replaced by Pydantic's model_dump and model_validate

    def update_processing_status(
        self,
        status: ProcessingStatus,
        record_count: Optional[int] = None,
        date_range_input: Optional[Tuple[int, int]] = None, # Expect tuple of int timestamps
        error_message: Optional[str] = None,
        opening_balance_input: Optional[Decimal] = None # Expect Decimal object
    ) -> None:
        """
        Update processing status and related fields.
        """
        self.processing_status = status
        self.processed_date = int(datetime.now(timezone.utc).timestamp() * 1000) # Set processed_date on status update
        
        if record_count is not None:
            self.record_count = record_count
            
        if date_range_input is not None:
            start_ts, end_ts = date_range_input
            self.date_range = DateRange(startDate=start_ts, endDate=end_ts)
            
        if error_message is not None:
            self.error_message = error_message
        else: # Clear error message if status is not ERROR
            if status != ProcessingStatus.ERROR:
                 self.error_message = None
            
        if opening_balance_input is not None:
            self.opening_balance = opening_balance_input
        
        self.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)


    def update_with_data(self, update_data: 'TransactionFileUpdate') -> bool:
        """
        Updates the transaction file with data from a TransactionFileUpdate DTO.
        Returns True if any fields were changed, False otherwise.
        """
        updated_fields = False
        # Use mode='python' to get the actual enum objects, not their string values
        update_dict = update_data.model_dump(exclude_unset=True, by_alias=False, mode='python') # Use field names

        for key, value in update_dict.items():
            if hasattr(self, key) and getattr(self, key) != value:
                setattr(self, key, value)
                updated_fields = True
        
        if updated_fields:
            self.updated_at = int(datetime.now(timezone.utc).timestamp() * 1000)
        return updated_fields

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Serializes TransactionFile to a flat dictionary for DynamoDB."""
        # Use mode='python' to get native Python types, then manually convert UUIDs
        data = self.model_dump(mode='python', by_alias=True, exclude_none=True)

        # Manually convert UUID fields to strings for DynamoDB
        if 'fileId' in data and isinstance(data.get('fileId'), uuid.UUID):
            data['fileId'] = str(data['fileId'])
        
        if 'accountId' in data and data.get('accountId') is not None and isinstance(data.get('accountId'), uuid.UUID):
            data['accountId'] = str(data['accountId'])

        if 'fileMapId' in data and data.get('fileMapId') is not None and isinstance(data.get('fileMapId'), uuid.UUID):
            data['fileMapId'] = str(data['fileMapId'])

        # Decimal 'openingBalance' is handled by Pydantic's model_dump and json_encoders if mode='json'.
        # For mode='python', it will be a Decimal object. Boto3 can handle Decimal, or convert to str if preferred.
        if 'openingBalance' in data and data.get('openingBalance') is not None and isinstance(data.get('openingBalance'), Decimal):
             data['openingBalance'] = str(data['openingBalance']) # Explicitly convert Decimal to string for DynamoDB
        
        # Manually convert enums to strings for DynamoDB storage
        if 'fileFormat' in data and data.get('fileFormat') is not None:
            data['fileFormat'] = data['fileFormat'].value if hasattr(data['fileFormat'], 'value') else str(data['fileFormat'])
            
        if 'processingStatus' in data and data.get('processingStatus') is not None:
            data['processingStatus'] = data['processingStatus'].value if hasattr(data['processingStatus'], 'value') else str(data['processingStatus'])
        
        # Convert currency enum to string for DynamoDB storage
        if 'currency' in data and data.get('currency') is not None:
            data['currency'] = data['currency'].value if hasattr(data['currency'], 'value') else str(data['currency'])
        
        # date_range is a DateRange model; model_dump already converts it to a dict.
        # Timestamps are already ints (milliseconds)
        
        # Debug: Log the dateRange structure
        if 'dateRange' in data:
            logger.info(f"Serialized dateRange: {data['dateRange']} (type: {type(data['dateRange'])})")
        
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "TransactionFile":
        """Deserializes a dictionary from DynamoDB to a TransactionFile instance."""
        
        # Handle DynamoDB type descriptors if they appear (defensive programming)
        data = TransactionFile._convert_dynamodb_types(data)
        
        # Manually convert openingBalance from string to Decimal if necessary
        if 'openingBalance' in data and data.get('openingBalance') is not None and isinstance(data.get('openingBalance'), str):
            try:
                data['openingBalance'] = Decimal(data['openingBalance'])
            except decimal.InvalidOperation as e:
                # Handle potential error if the string is not a valid Decimal
                raise ValueError(f"Invalid string format for Decimal 'openingBalance': {data['openingBalance']} - {e}")

        # Convert currency string to Currency enum if necessary (for data from DynamoDB)
        if 'currency' in data and data.get('currency') is not None and isinstance(data.get('currency'), str):
            try:
                data['currency'] = Currency(data['currency'])
            except ValueError:
                logger.warning(f"Invalid currency value from database: {data['currency']}, setting to None")
                data['currency'] = None

        # Pydantic will handle Decimal conversion for 'openingBalance' if it's a string/number in data.
        # Pydantic will automatically convert string enum values to enum objects based on type hints.
        # Pydantic will reconstruct DateRange if 'dateRange' in data is a dict and matches DateRange fields.
        # Pydantic handles UUIDs based on type hints and model_config.
        return cls.model_validate(data, context={'from_database': True})
    
    @staticmethod
    def _convert_dynamodb_types(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert DynamoDB type descriptors to Python types recursively.
        This handles cases where DynamoDB returns raw type descriptors.
        """
        if not isinstance(data, dict):
            return data
            
        converted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Check if this is a DynamoDB type descriptor
                if len(value) == 1:
                    type_key = next(iter(value.keys()))
                    type_value = next(iter(value.values()))
                    
                    if type_key == 'N':  # Number
                        converted[key] = int(type_value) if type_value.isdigit() else float(type_value)
                    elif type_key == 'S':  # String
                        converted[key] = type_value
                    elif type_key == 'BOOL':  # Boolean
                        converted[key] = type_value
                    elif type_key == 'NULL':  # Null
                        converted[key] = None
                    elif type_key == 'L':  # List
                        converted[key] = [TransactionFile._convert_dynamodb_types(item) for item in type_value]
                    elif type_key == 'M':  # Map
                        converted[key] = TransactionFile._convert_dynamodb_types(type_value)
                    else:
                        # Not a type descriptor, recurse into nested dict
                        converted[key] = TransactionFile._convert_dynamodb_types(value)
                else:
                    # Not a type descriptor, recurse into nested dict
                    converted[key] = TransactionFile._convert_dynamodb_types(value)
            elif isinstance(value, list):
                converted[key] = [TransactionFile._convert_dynamodb_types(item) for item in value]
            else:
                converted[key] = value
                
        return converted

    # Removed validate method as Pydantic handles validation

# DTO for creating a TransactionFile
class TransactionFileCreate(BaseModel):
    user_id: str = Field(alias="userId")
    file_name: str = Field(alias="fileName")
    file_size: int = Field(alias="fileSize")
    s3_key: str = Field(alias="s3Key")
    
    file_format: Optional[FileFormat] = Field(default=None, alias="fileFormat")
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    file_map_id: Optional[uuid.UUID] = Field(default=None, alias="fileMapId") # Changed to UUID
    currency: Optional[Currency] = None 

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str}
    )

    @field_validator('currency', mode='after')
    @classmethod
    def validate_currency(cls, v, info: ValidationInfo) -> Optional[Currency]:
        """Ensure currency is always a Currency enum, never a string."""
        if v is None:
            return None
        if isinstance(v, Currency):
            return v
        # Check if this is from database deserialization
        if info.context and info.context.get('from_database'):
            # During database deserialization, we've already converted strings to enums
            return v
        # If we get here, something assigned a non-Currency value
        raise ValueError(f"Currency must be a Currency enum, got {type(v).__name__}: {v}")

    def to_transaction_file(self, file_id: Optional[uuid.UUID] = None) -> 'TransactionFile':
        """
        Convert this TransactionFileCreate DTO to a full TransactionFile entity.
        
        Args:
            file_id: Optional file_id to use instead of auto-generating one
            
        Returns:
            TransactionFile: The full entity with auto-generated fields
        """
        # Get the data from this DTO
        transaction_file_data = self.model_dump(by_alias=False)
        
        # Set the file_id if provided, otherwise let TransactionFile generate it
        if file_id is not None:
            transaction_file_data['file_id'] = file_id
            
        # Create and return the full TransactionFile entity
        return TransactionFile(**transaction_file_data)

# DTO for updating a TransactionFile
class TransactionFileUpdate(BaseModel):
    file_name: Optional[str] = Field(default=None, alias="fileName")
    processing_status: Optional[ProcessingStatus] = Field(default=None, alias="processingStatus")
    processed_date: Optional[int] = Field(default=None, alias="processedDate")
    file_format: Optional[FileFormat] = Field(default=None, alias="fileFormat")
    account_id: Optional[uuid.UUID] = Field(default=None, alias="accountId")
    file_map_id: Optional[uuid.UUID] = Field(default=None, alias="fileMapId") # Changed to UUID
    record_count: Optional[int] = Field(default=None, alias="recordCount")
    date_range: Optional[DateRange] = Field(default=None, alias="dateRange")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    opening_balance: Optional[Decimal] = Field(default=None, alias="openingBalance")
    currency: Optional[Currency] = None
    duplicate_count: Optional[int] = Field(default=None, alias="duplicateCount")
    transaction_count: Optional[int] = Field(default=None, alias="transactionCount")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str},
        arbitrary_types_allowed=True 
    )

    @field_validator('processed_date', check_fields=False)
    @classmethod
    def check_positive_timestamp_optional(cls, v: Optional[int]) -> Optional[int]:
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
        # Check if this is from database deserialization
        if info.context and info.context.get('from_database'):
            # During database deserialization, we've already converted strings to enums
            return v
        # If we get here, something assigned a non-Currency value
        raise ValueError(f"Currency must be a Currency enum, got {type(v).__name__}: {v}")
