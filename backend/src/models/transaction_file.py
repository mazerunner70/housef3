"""
Transaction file models for the financial account management system.
"""
from decimal import Decimal
import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import json

from backend.src.models.account import Currency
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


class DateRange:
    """Represents a date range for transactions in a file"""
    def __init__(self, start_date: str, end_date: str):
        self.start_date = start_date
        self.end_date = end_date
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for storage"""
        return {
            "startDate": self.start_date,
            "endDate": self.end_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'DateRange':
        """Create from dictionary"""
        return cls(
            start_date=data["startDate"],
            end_date=data["endDate"]
        )


@dataclass
class TransactionFile:
    """
    Represents a transaction file uploaded by a user and optionally associated with an account.
    """
    file_id: str
    user_id: str
    file_name: str
    upload_date: int # milliseconds since epoch
    file_size: int
    s3_key: str
    processing_status: ProcessingStatus
    processed_date: Optional[int] = None
    file_format: Optional[FileFormat] = None
    account_id: Optional[str] = None
    file_map_id: Optional[str] = None
    record_count: Optional[int] = None
    date_range_start: Optional[int] = None
    date_range_end: Optional[int] = None
    error_message: Optional[str] = None
    opening_balance: Optional[Money] = None
    currency: Optional[Currency] = None
    duplicate_count: Optional[int] = None
    transaction_count: Optional[int] = None
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction file object to a dictionary suitable for storage.
        """
        result = {
            "fileId": self.file_id,
            "userId": self.user_id,
            "fileName": self.file_name,
            "uploadDate": self.upload_date,
            "fileSize": str(self.file_size),  # Convert to string for DynamoDB
            "s3Key": self.s3_key,
            "processingStatus": self.processing_status.value,
            "processedDate": self.processed_date
        }
        
        if self.file_format:
            result["fileFormat"] = self.file_format.value
        
        # Add account_id only if it exists
        if self.account_id:
            result["accountId"] = self.account_id
        
        if self.file_map_id:
            result["fileMapId"] = self.file_map_id
        
        # Add optional fields if they exist
        if self.record_count is not None:
            result["recordCount"] = str(self.record_count)
        
        if self.date_range_start and self.date_range_end:
            result["dateRangeStart"] = self.date_range_start
            result["dateRangeEnd"] = self.date_range_end
        
        if self.error_message:
            result["errorMessage"] = self.error_message
            
        if self.opening_balance is not None:
            result["openingBalance"] = self.opening_balance.to_dict()  # Convert to string for DynamoDB

        if self.currency:
            result["currency"] = self.currency.value    

        if self.duplicate_count:
            result["duplicateCount"] = self.duplicate_count

        if self.transaction_count:
            result["transactionCount"] = self.transaction_count
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionFile':
        """
        Create a transaction file object from a dictionary (e.g. from DynamoDB).
        """
        account_id = data.get("accountId")  # Use get() to handle optional field
        opening_balance_amount = Decimal(str(data.get("openingBalance"))) if data.get("openingBalance") else None
        currency = Currency(data.get("currency")) if data.get("currency") else None
        opening_balance = Money(opening_balance_amount, currency) if opening_balance_amount and currency else None
        record_count_str = data.get("recordCount")
        record_count = int(record_count_str) if record_count_str else None
        
        file = cls(
            file_id=data["fileId"],
            user_id=data["userId"],
            file_name=data["fileName"],
            upload_date=data["uploadDate"],
            file_size=int(data["fileSize"]),
            s3_key=data["s3Key"],
            processing_status=ProcessingStatus(data["processingStatus"]),
            file_format=FileFormat(data.get("fileFormat")) if data.get("fileFormat") else None,
            account_id=account_id,
            file_map_id=data.get("fileMapId"),
            record_count=record_count,
            date_range_start=data.get("dateRangeStart"),
            date_range_end=data.get("dateRangeEnd"),
            error_message=data.get("errorMessage"),
            opening_balance=opening_balance,
            currency=currency,
            duplicate_count=data.get("duplicateCount") if data.get("duplicateCount") else None,
            transaction_count=data.get("transactionCount") if data.get("transactionCount") else None
        )
        
        return file

    def update_processing_status(
        self,
        status: ProcessingStatus,
        record_count: Optional[int] = None,
        date_range: Optional[Tuple[str, str]] = None,
        error_message: Optional[str] = None,
        opening_balance: Optional[Money] = None
    ) -> None:
        """
        Update processing status and related fields.
        """
        self.processing_status = status
        
        if record_count is not None:
            self.record_count = record_count
            
        if date_range is not None:
            start_date_str, end_date_str = date_range
            self.date_range_start = int(start_date_str)
            self.date_range_end = int(end_date_str)
            
        if error_message is not None:
            self.error_message = error_message
            
        if opening_balance is not None:
            self.opening_balance = opening_balance


def validate_transaction_file_data(transaction_file: TransactionFile) -> bool:
    """
    Validate transaction file data according to business rules.
    
    Args:
        transaction_file: TransactionFile object to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If validation fails, with details about what failed
    """
    # Check required fields
    if not transaction_file.user_id:
        raise ValueError("Missing required field: user_id")
    if not transaction_file.file_name:
        raise ValueError("Missing required field: file_name")
    if not transaction_file.file_size:
        raise ValueError("Missing required field: file_size")
    if not transaction_file.s3_key:
        raise ValueError("Missing required field: s3_key")
    
    # Validate file format if provided
    if transaction_file.file_format and not isinstance(transaction_file.file_format, FileFormat):
        raise ValueError(f"Invalid file format: {transaction_file.file_format}")
    
    # Validate processing status if provided
    if transaction_file.processing_status and not isinstance(transaction_file.processing_status, ProcessingStatus):
        raise ValueError(f"Invalid processing status: {transaction_file.processing_status}")
    
    # Validate account_id if provided
    if transaction_file.account_id and not isinstance(transaction_file.account_id, str):
        raise ValueError("Account ID must be a string")
    
    # Validate numeric fields
    if transaction_file.file_size:
        if not isinstance(transaction_file.file_size, int):
            raise ValueError("File size must be a valid integer")
        if transaction_file.file_size <= 0:
            raise ValueError("File size must be positive")
    
    if transaction_file.record_count is not None:
        if not isinstance(transaction_file.record_count, int):
            raise ValueError("Record count must be a valid integer")
        if transaction_file.record_count < 0:
            raise ValueError("Record count must be non-negative")

    # Validate opening balance if provided
    if transaction_file.opening_balance:
        if not isinstance(transaction_file.opening_balance, Money):
            raise ValueError("Opening balance must be a Money object")
        try:
            Decimal(str(transaction_file.opening_balance.amount))
        except (ValueError, TypeError):
            raise ValueError("Opening balance amount must be a valid number")
    
    # Validate date range if provided
    if transaction_file.date_range_start or transaction_file.date_range_end:
        if not isinstance(transaction_file.date_range_start, int) or not isinstance(transaction_file.date_range_end, int):
            raise ValueError("Date range must be timestamps")
        
        if transaction_file.date_range_start > transaction_file.date_range_end:
            raise ValueError("Start date must be before end date")
    
    # Validate string lengths
    if transaction_file.file_name and len(transaction_file.file_name) > 255:
        raise ValueError("File name must be 255 characters or less")
    
    if transaction_file.error_message and len(transaction_file.error_message) > 1000:
        raise ValueError("Error message must be 1000 characters or less")
    
    return True

def type_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)  # Convert Decimal to float for JSON
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError

def transaction_file_to_json(file):
    """Convert a TransactionFile object to a JSON string with proper type handling."""
    # If already a TransactionFile object, use to_dict; else, from_dict
    if isinstance(file, TransactionFile):
        d = file.to_dict()
    else:
        d = TransactionFile.from_dict(file).to_dict()
    
    # Handle date range formatting if both start and end exist
    if 'dateRangeStart' in d and 'dateRangeEnd' in d:
        d['dateRange'] = f"{d.pop('dateRangeStart')} to {d.pop('dateRangeEnd')}"
    
    return json.dumps(d, default=type_default) 