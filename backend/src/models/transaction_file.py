"""
Transaction file models for the financial account management system.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


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
    upload_date: str
    file_size: int
    file_format: FileFormat
    s3_key: str
    processing_status: ProcessingStatus
    account_id: Optional[str] = None
    field_map_id: Optional[str] = None
    record_count: Optional[int] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    error_message: Optional[str] = None
    opening_balance: Optional[float] = None

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
            "fileFormat": self.file_format.value,
            "s3Key": self.s3_key,
            "processingStatus": self.processing_status.value
        }
        
        # Add account_id only if it exists
        if self.account_id:
            result["accountId"] = self.account_id
        
        if self.field_map_id:
            result["fieldMapId"] = self.field_map_id
        
        # Add optional fields if they exist
        if self.record_count is not None:
            result["recordCount"] = str(self.record_count)
        
        if self.date_range_start and self.date_range_end:
            result["dateRangeStart"] = self.date_range_start
            result["dateRangeEnd"] = self.date_range_end
        
        if self.error_message:
            result["errorMessage"] = self.error_message
            
        if self.opening_balance is not None:
            result["openingBalance"] = str(self.opening_balance)  # Convert to string for DynamoDB
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionFile':
        """
        Create a transaction file object from a dictionary (e.g. from DynamoDB).
        """
        account_id = data.get("accountId")  # Use get() to handle optional field
        opening_balance = float(data.get("openingBalance")) if data.get("openingBalance") else None
        
        file = cls(
            file_id=data["fileId"],
            user_id=data["userId"],
            file_name=data["fileName"],
            upload_date=data["uploadDate"],
            file_size=int(data["fileSize"]),
            file_format=FileFormat(data["fileFormat"]),
            s3_key=data["s3Key"],
            processing_status=ProcessingStatus(data["processingStatus"]),
            account_id=account_id,
            field_map_id=data.get("fieldMapId"),
            record_count=int(data.get("recordCount")) if data.get("recordCount") else None,
            date_range_start=data.get("dateRangeStart"),
            date_range_end=data.get("dateRangeEnd"),
            error_message=data.get("errorMessage"),
            opening_balance=opening_balance
        )
        
        return file

    def update_processing_status(
        self,
        status: ProcessingStatus,
        record_count: Optional[int] = None,
        date_range: Optional[Tuple[str, str]] = None,
        error_message: Optional[str] = None,
        opening_balance: Optional[float] = None
    ) -> None:
        """
        Update processing status and related fields.
        """
        self.processing_status = status
        
        if record_count is not None:
            self.record_count = record_count
            
        if date_range is not None:
            self.date_range_start, self.date_range_end = date_range
            
        if error_message is not None:
            self.error_message = error_message
            
        if opening_balance is not None:
            self.opening_balance = opening_balance


def validate_transaction_file_data(data: Dict[str, Any]) -> bool:
    """
    Validate transaction file data according to business rules.
    
    Returns True if valid, raises ValueError with details if invalid.
    """
    required_fields = ["userId", "fileName", "fileSize", "fileFormat", "s3Key"]
    
    # Check required fields
    for field in required_fields:
        if field not in data or not data[field]:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate file format
    if "fileFormat" in data and data["fileFormat"] not in [f.value for f in FileFormat]:
        raise ValueError(f"Invalid file format: {data['fileFormat']}")
    
    # Validate processing status if provided
    if "processingStatus" in data and data["processingStatus"] not in [s.value for s in ProcessingStatus]:
        raise ValueError(f"Invalid processing status: {data['processingStatus']}")
    
    # Validate account_id if provided
    if "accountId" in data and data["accountId"] and not isinstance(data["accountId"], str):
        raise ValueError("Account ID must be a string")
    
    # Validate numeric fields
    if "fileSize" in data:
        try:
            size = int(data["fileSize"])
            if size <= 0:
                raise ValueError("File size must be positive")
        except (ValueError, TypeError):
            raise ValueError("File size must be a valid integer")
    
    if "recordCount" in data:
        try:
            count = int(data["recordCount"])
            if count < 0:
                raise ValueError("Record count must be non-negative")
        except (ValueError, TypeError):
            raise ValueError("Record count must be a valid integer")

    # Validate opening balance if provided
    if "openingBalance" in data:
        try:
            float(data["openingBalance"])
        except (ValueError, TypeError):
            raise ValueError("Opening balance must be a valid number")
    
    # Validate date range if provided
    if "dateRange" in data:
        date_range = data["dateRange"]
        if not isinstance(date_range, dict):
            raise ValueError("Date range must be a dictionary")
        
        if "startDate" not in date_range or "endDate" not in date_range:
            raise ValueError("Date range must include startDate and endDate")
        
        # Try parsing the dates to validate format
        try:
            datetime.fromisoformat(date_range["startDate"].replace('Z', '+00:00'))
            datetime.fromisoformat(date_range["endDate"].replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Dates must be in ISO format")
    
    # Validate string lengths
    if "fileName" in data and len(data["fileName"]) > 255:
        raise ValueError("File name must be 255 characters or less")
    
    if "errorMessage" in data and len(data["errorMessage"]) > 1000:
        raise ValueError("Error message must be 1000 characters or less")
    
    return True 