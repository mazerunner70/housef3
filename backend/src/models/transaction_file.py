"""
Transaction file models for the financial account management system.
"""
from decimal import Decimal
import decimal
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

from models.account import Currency
from models.money import Money


class FileFormat(str, enum.Enum):
    """Enum for transaction file formats"""
    CSV = "csv"
    OFX = "ofx"
    QFX = "qfx"
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
        use_enum_values=True, # Ensures enum values are used in serialization
        arbitrary_types_allowed=True # For Money if it's not a Pydantic model
    )

    @field_validator('upload_date', 'processed_date', 'created_at', 'updated_at', check_fields=False)
    @classmethod
    def check_positive_timestamp(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

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
        update_dict = update_data.model_dump(exclude_unset=True, by_alias=False) # Use field names

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
        
        # date_range is a DateRange model; model_dump already converts it to a dict.
        # Enums (processingStatus, fileFormat) are handled by Pydantic (use_enum_values=True)
        # Timestamps are already ints (milliseconds)
        return data

    @classmethod
    def from_dynamodb_item(cls, data: Dict[str, Any]) -> "TransactionFile":
        """Deserializes a dictionary from DynamoDB to a TransactionFile instance."""
        
        # Manually convert openingBalance from string to Decimal if necessary
        if 'openingBalance' in data and data.get('openingBalance') is not None and isinstance(data.get('openingBalance'), str):
            try:
                data['openingBalance'] = Decimal(data['openingBalance'])
            except decimal.InvalidOperation as e:
                # Handle potential error if the string is not a valid Decimal
                raise ValueError(f"Invalid string format for Decimal 'openingBalance': {data['openingBalance']} - {e}")

        # Pydantic will handle Decimal conversion for 'openingBalance' if it's a string/number in data.
        # No special Money conversion needed.
        
        # Pydantic will reconstruct DateRange if 'dateRange' in data is a dict and matches DateRange fields.
        # Pydantic handles enums and UUIDs based on type hints and model_config.
        return cls.model_validate(data)

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
        use_enum_values=True,
        json_encoders={uuid.UUID: str}
    )

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
        use_enum_values=True,
        json_encoders={uuid.UUID: str},
        arbitrary_types_allowed=True 
    )

    @field_validator('processed_date', check_fields=False)
    @classmethod
    def check_positive_timestamp_optional(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Timestamp must be a positive integer representing milliseconds since epoch")
        return v

# Removed validate_transaction_file_data function (validations moved into Pydantic model or handled by type hints)
# Removed type_default function (Pydantic handles JSON serialization defaults)
# Removed transaction_file_to_json function (use model_instance.model_dump_json())


# Example of how to use (optional, can be removed):
# if __name__ == '__main__':
#     # Create
#     file_create_data = TransactionFileCreate(
#         userId="user123",
#         fileName="transactions.csv",
#         fileSize=1024,
#         s3Key="s3://bucket/transactions.csv",
#         fileFormat=FileFormat.CSV,
#         accountId=uuid.uuid4()
#     )
#     print("Create DTO:", file_create_data.model_dump_json(by_alias=True, indent=2))

#     # Instantiate main model from create DTO + other defaults
#     # In a real scenario, you'd pass file_create_data and then fill in system-set fields
#     new_file = TransactionFile(**file_create_data.model_dump(by_alias=False), file_id=uuid.uuid4())
#     print("\nNew File:", new_file.model_dump_json(by_alias=True, indent=2))

#     # Update status
#     new_file.update_processing_status(
#         status=ProcessingStatus.PROCESSED,
#         record_count=100,
#         date_range_input=(int(datetime(2023,1,1, tzinfo=timezone.utc).timestamp()*1000), int(datetime(2023,1,31, tzinfo=timezone.utc).timestamp()*1000)),
#         opening_balance_input=Decimal("100.00")
#     )
#     print("\nFile after status update:", new_file.model_dump_json(by_alias=True, indent=2))

#     # Update with DTO
#     update_dto = TransactionFileUpdate(fileName="transactions_final.csv", transaction_count=98)
#     changed = new_file.update_with_data(update_dto)
#     print(f"\nFile changed by update DTO: {changed}")
#     print("File after DTO update:", new_file.model_dump_json(by_alias=True, indent=2))

#     # Simulate loading from DB (dict with aliases)
#     db_data = new_file.model_dump(by_alias=True)
#     loaded_file = TransactionFile.model_validate(db_data)
#     print("\nLoaded File from DB data:", loaded_file.model_dump_json(by_alias=True, indent=2))

#     assert loaded_file.file_id == new_file.file_id
#     assert loaded_file.date_range.start_date == new_file.date_range.start_date 