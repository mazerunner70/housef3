import unittest
from decimal import Decimal
from datetime import datetime
import uuid
import json

from models.transaction_file import (
    TransactionFile,
    FileFormat,
    ProcessingStatus,
    DateRange,
    validate_transaction_file_data,
    transaction_file_to_json,
    type_default
)
from models.money import Money, Currency


class TestTransactionFile(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.file_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.file_name = "test_transactions.csv"
        self.upload_date = int(datetime.now().timestamp() * 1000)
        self.file_size = 1024
        self.s3_key = f"transactions/{self.user_id}/{self.file_id}.csv"
        self.processing_status = ProcessingStatus.PENDING
        
        # Create a sample transaction file
        self.transaction_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name=self.file_name,
            upload_date=self.upload_date,
            file_size=self.file_size,
            s3_key=self.s3_key,
            processing_status=self.processing_status
        )

    def test_file_format_enum(self):
        """Test FileFormat enum values."""
        self.assertEqual(FileFormat.CSV.value, "csv")
        self.assertEqual(FileFormat.OFX.value, "ofx")
        self.assertEqual(FileFormat.QFX.value, "qfx")
        self.assertEqual(FileFormat.PDF.value, "pdf")
        self.assertEqual(FileFormat.XLSX.value, "xlsx")
        self.assertEqual(FileFormat.OTHER.value, "other")
        self.assertEqual(FileFormat.JSON.value, "json")
        self.assertEqual(FileFormat.EXCEL.value, "excel")

    def test_processing_status_enum(self):
        """Test ProcessingStatus enum values."""
        self.assertEqual(ProcessingStatus.PENDING.value, "pending")
        self.assertEqual(ProcessingStatus.PROCESSING.value, "processing")
        self.assertEqual(ProcessingStatus.PROCESSED.value, "processed")
        self.assertEqual(ProcessingStatus.ERROR.value, "error")
        self.assertEqual(ProcessingStatus.NEEDS_MAPPING.value, "needs_mapping")

    def test_date_range(self):
        """Test DateRange class."""
        start_date = "2024-01-01"
        end_date = "2024-02-01"
        date_range = DateRange(start_date, end_date)
        
        # Test to_dict
        date_dict = date_range.to_dict()
        self.assertEqual(date_dict["startDate"], start_date)
        self.assertEqual(date_dict["endDate"], end_date)
        
        # Test from_dict
        new_date_range = DateRange.from_dict(date_dict)
        self.assertEqual(new_date_range.start_date, start_date)
        self.assertEqual(new_date_range.end_date, end_date)

    def test_transaction_file_creation(self):
        """Test basic transaction file creation."""
        self.assertEqual(self.transaction_file.file_id, self.file_id)
        self.assertEqual(self.transaction_file.user_id, self.user_id)
        self.assertEqual(self.transaction_file.file_name, self.file_name)
        self.assertEqual(self.transaction_file.upload_date, self.upload_date)
        self.assertEqual(self.transaction_file.file_size, self.file_size)
        self.assertEqual(self.transaction_file.s3_key, self.s3_key)
        self.assertEqual(self.transaction_file.processing_status, self.processing_status)

    def test_transaction_file_optional_fields(self):
        """Test transaction file with optional fields."""
        account_id = str(uuid.uuid4())
        file_map_id = str(uuid.uuid4())
        opening_balance = Money(Decimal("1000.00"), Currency.USD)
        
        tx_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name=self.file_name,
            upload_date=self.upload_date,
            file_size=self.file_size,
            s3_key=self.s3_key,
            processing_status=self.processing_status,
            account_id=account_id,
            file_map_id=file_map_id,
            file_format=FileFormat.CSV,
            record_count=100,
            date_range_start=self.upload_date - 86400000,  # 1 day before
            date_range_end=self.upload_date,
            opening_balance=opening_balance,
            currency=Currency.USD,
            duplicate_count=5,
            transaction_count=95
        )
        
        self.assertEqual(tx_file.account_id, account_id)
        self.assertEqual(tx_file.file_map_id, file_map_id)
        self.assertEqual(tx_file.file_format, FileFormat.CSV)
        self.assertEqual(tx_file.record_count, 100)
        self.assertEqual(tx_file.opening_balance, opening_balance)
        self.assertEqual(tx_file.currency, Currency.USD)
        self.assertEqual(tx_file.duplicate_count, 5)
        self.assertEqual(tx_file.transaction_count, 95)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        tx_file_dict = self.transaction_file.to_dict()
        
        self.assertEqual(tx_file_dict["fileId"], self.file_id)
        self.assertEqual(tx_file_dict["userId"], self.user_id)
        self.assertEqual(tx_file_dict["fileName"], self.file_name)
        self.assertEqual(tx_file_dict["uploadDate"], self.upload_date)
        self.assertEqual(tx_file_dict["fileSize"], str(self.file_size))
        self.assertEqual(tx_file_dict["s3Key"], self.s3_key)
        self.assertEqual(tx_file_dict["processingStatus"], self.processing_status.value)

    def test_from_dict(self):
        """Test creation from dictionary."""
        tx_file_dict = self.transaction_file.to_dict()
        new_tx_file = TransactionFile.from_dict(tx_file_dict)
        
        self.assertEqual(new_tx_file.file_id, self.file_id)
        self.assertEqual(new_tx_file.user_id, self.user_id)
        self.assertEqual(new_tx_file.file_name, self.file_name)
        self.assertEqual(new_tx_file.upload_date, self.upload_date)
        self.assertEqual(new_tx_file.file_size, self.file_size)
        self.assertEqual(new_tx_file.s3_key, self.s3_key)
        self.assertEqual(new_tx_file.processing_status, self.processing_status)

    def test_update_processing_status(self):
        """Test updating processing status and related fields."""
        new_status = ProcessingStatus.PROCESSING
        record_count = 50
        date_range = (str(self.upload_date - 86400000), str(self.upload_date))
        error_message = "Test error"
        opening_balance = Money(Decimal("1000.00"), Currency.USD)
        
        self.transaction_file.update_processing_status(
            status=new_status,
            record_count=record_count,
            date_range=date_range,
            error_message=error_message,
            opening_balance=opening_balance
        )
        
        self.assertEqual(self.transaction_file.processing_status, new_status)
        self.assertEqual(self.transaction_file.record_count, record_count)
        self.assertEqual(self.transaction_file.date_range_start, int(date_range[0]))
        self.assertEqual(self.transaction_file.date_range_end, int(date_range[1]))
        self.assertEqual(self.transaction_file.error_message, error_message)
        self.assertEqual(self.transaction_file.opening_balance, opening_balance)

    def test_update_method(self):
        """Test the update method."""
        new_file_name = "updated_file.csv"
        new_file_size = 2048
        
        self.transaction_file.update(
            file_name=new_file_name,
            file_size=new_file_size
        )
        
        self.assertEqual(self.transaction_file.file_name, new_file_name)
        self.assertEqual(self.transaction_file.file_size, new_file_size)

    def test_validate_transaction_file_data(self):
        """Test transaction file data validation."""
        # Test valid data
        self.assertTrue(validate_transaction_file_data(self.transaction_file))
        
        # Test missing required fields
        invalid_file = TransactionFile(
            file_id=self.file_id,
            user_id="",  # Invalid empty user_id
            file_name=self.file_name,
            upload_date=self.upload_date,
            file_size=self.file_size,
            s3_key=self.s3_key,
            processing_status=self.processing_status
        )
        with self.assertRaises(ValueError):
            validate_transaction_file_data(invalid_file)
        
        # Test invalid file size
        invalid_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name=self.file_name,
            upload_date=self.upload_date,
            file_size=-1,  # Invalid negative size
            s3_key=self.s3_key,
            processing_status=self.processing_status
        )
        with self.assertRaises(ValueError):
            validate_transaction_file_data(invalid_file)
        
        # Test invalid date range
        invalid_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name=self.file_name,
            upload_date=self.upload_date,
            file_size=self.file_size,
            s3_key=self.s3_key,
            processing_status=self.processing_status,
            date_range_start=1000,
            date_range_end=500  # End before start
        )
        with self.assertRaises(ValueError):
            validate_transaction_file_data(invalid_file)

    def test_type_default(self):
        """Test type_default function."""
        # Test Decimal conversion
        decimal_val = Decimal("123.45")
        self.assertEqual(type_default(decimal_val), float(decimal_val))
        
        # Test datetime conversion
        dt = datetime.now()
        self.assertEqual(type_default(dt), dt.isoformat())
        
        # Test unsupported type
        class UnsupportedType:
            pass
        with self.assertRaises(TypeError):
            type_default(UnsupportedType())

    def test_transaction_file_to_json(self):
        """Test JSON serialization."""
        # Test with TransactionFile object
        json_str = transaction_file_to_json(self.transaction_file)
        data = json.loads(json_str)
        
        self.assertEqual(data["fileId"], self.file_id)
        self.assertEqual(data["userId"], self.user_id)
        self.assertEqual(data["fileName"], self.file_name)
        
        # Test with dictionary
        tx_file_dict = self.transaction_file.to_dict()
        json_str = transaction_file_to_json(tx_file_dict)
        data = json.loads(json_str)
        
        self.assertEqual(data["fileId"], self.file_id)
        self.assertEqual(data["userId"], self.user_id)
        self.assertEqual(data["fileName"], self.file_name)

    def test_string_field_length_validation(self):
        """Test validation of string field lengths."""
        # Test file name too long
        invalid_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name="a" * 256,  # Exceeds 255 character limit
            upload_date=self.upload_date,
            file_size=self.file_size,
            s3_key=self.s3_key,
            processing_status=self.processing_status
        )
        with self.assertRaises(ValueError):
            validate_transaction_file_data(invalid_file)
        
        # Test error message too long
        invalid_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name=self.file_name,
            upload_date=self.upload_date,
            file_size=self.file_size,
            s3_key=self.s3_key,
            processing_status=self.processing_status,
            error_message="a" * 1001  # Exceeds 1000 character limit
        )
        with self.assertRaises(ValueError):
            validate_transaction_file_data(invalid_file)

if __name__ == '__main__':
    unittest.main() 