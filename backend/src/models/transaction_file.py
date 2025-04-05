"""
Transaction file models for the financial account management system.
"""
import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Tuple


class FileFormat(str, enum.Enum):
    """Enum for transaction file formats"""
    CSV = "csv"
    OFX = "ofx"
    QFX = "qfx"
    PDF = "pdf"
    XLSX = "xlsx"
    OTHER = "other"


class ProcessingStatus(str, enum.Enum):
    """Enum for file processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ERROR = "error"


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


class TransactionFile:
    """
    Represents a transaction file uploaded by a user and associated with an account.
    """
    def __init__(
        self,
        file_id: str,
        account_id: str,
        user_id: str,
        file_name: str,
        upload_date: str,
        file_size: int,
        file_format: FileFormat,
        s3_key: str,
        processing_status: ProcessingStatus,
        record_count: Optional[int] = None,
        date_range: Optional[DateRange] = None,
        error_message: Optional[str] = None
    ):
        self.file_id = file_id
        self.account_id = account_id
        self.user_id = user_id
        self.file_name = file_name
        self.upload_date = upload_date
        self.file_size = file_size
        self.file_format = file_format
        self.s3_key = s3_key
        self.processing_status = processing_status
        self.record_count = record_count
        self.date_range = date_range
        self.error_message = error_message

    @classmethod
    def create(
        cls,
        account_id: str,
        user_id: str,
        file_name: str,
        file_size: int,
        file_format: FileFormat,
        s3_key: str,
        processing_status: ProcessingStatus = ProcessingStatus.PENDING
    ) -> 'TransactionFile':
        """
        Factory method to create a new transaction file with generated ID and timestamp.
        """
        return cls(
            file_id=str(uuid.uuid4()),
            account_id=account_id,
            user_id=user_id,
            file_name=file_name,
            upload_date=datetime.utcnow().isoformat(),
            file_size=file_size,
            file_format=file_format,
            s3_key=s3_key,
            processing_status=processing_status
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction file object to a dictionary suitable for storage.
        """
        result = {
            "fileId": self.file_id,
            "accountId": self.account_id,
            "userId": self.user_id,
            "fileName": self.file_name,
            "uploadDate": self.upload_date,
            "fileSize": str(self.file_size),  # Convert to string for DynamoDB
            "fileFormat": self.file_format.value,
            "s3Key": self.s3_key,
            "processingStatus": self.processing_status.value
        }
        
        # Add optional fields if they exist
        if self.record_count is not None:
            result["recordCount"] = str(self.record_count)
        
        if self.date_range:
            result["dateRange"] = self.date_range.to_dict()
        
        if self.error_message:
            result["errorMessage"] = self.error_message
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionFile':
        """
        Create a transaction file object from a dictionary (e.g. from DynamoDB).
        """
        file = cls(
            file_id=data["fileId"],
            account_id=data["accountId"],
            user_id=data["userId"],
            file_name=data["fileName"],
            upload_date=data["uploadDate"],
            file_size=int(data["fileSize"]),
            file_format=FileFormat(data["fileFormat"]),
            s3_key=data["s3Key"],
            processing_status=ProcessingStatus(data["processingStatus"])
        )
        
        # Add optional fields if present in the data
        if "recordCount" in data:
            file.record_count = int(data["recordCount"])
            
        if "dateRange" in data:
            file.date_range = DateRange.from_dict(data["dateRange"])
            
        if "errorMessage" in data:
            file.error_message = data["errorMessage"]
            
        return file

    def update_processing_status(
        self,
        status: ProcessingStatus,
        record_count: Optional[int] = None,
        date_range: Optional[Tuple[str, str]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update processing status and related fields.
        """
        self.processing_status = status
        
        if record_count is not None:
            self.record_count = record_count
            
        if date_range:
            self.date_range = DateRange(date_range[0], date_range[1])
            
        if error_message:
            self.error_message = error_message


def validate_transaction_file_data(data: Dict[str, Any]) -> bool:
    """
    Validate transaction file data according to business rules.
    
    Returns True if valid, raises ValueError with details if invalid.
    """
    required_fields = ["accountId", "userId", "fileName", "fileSize", "fileFormat", "s3Key"]
    
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