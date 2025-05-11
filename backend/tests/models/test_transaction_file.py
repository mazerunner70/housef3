import traceback
import unittest
from decimal import Decimal, InvalidOperation
from datetime import datetime

from models.account import Currency
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus, validate_transaction_file_data
from models.money import Money

class TestTransactionFileValidation(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.valid_file = TransactionFile(
            file_id="test_file",
            user_id="test_user",
            account_id="test_account",
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING,
            file_format=FileFormat.CSV,
            opening_balance=Money(Decimal("1000.00"), Currency.USD)
        )

    def test_valid_file(self):
        """Test validation of a valid file."""
        self.assertTrue(validate_transaction_file_data(self.valid_file))

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        # Test missing user_id
        file = TransactionFile(
            file_id="test_file",
            user_id="",  # Empty string instead of missing
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(file)
        self.assertIn("Missing required field: user_id", str(context.exception))

        # Test missing file_name
        file = TransactionFile(
            file_id="test_file",
            user_id="test_user",
            file_name="",  # Empty string instead of missing
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(file)
        self.assertIn("Missing required field: file_name", str(context.exception))

        # Test missing file_size
        file = TransactionFile(
            file_id="test_file",
            user_id="test_user",
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=0,  # Zero instead of missing
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING
        )
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(file)
        self.assertIn("Missing required field: file_size", str(context.exception))

        # Test missing s3_key
        file = TransactionFile(
            file_id="test_file",
            user_id="test_user",
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="",  # Empty string instead of missing
            processing_status=ProcessingStatus.PENDING
        )
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(file)
        self.assertIn("Missing required field: s3_key", str(context.exception))

    def test_invalid_file_format(self):
        """Test validation fails with invalid file format."""
        self.valid_file.file_format = "INVALID"
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Invalid file format", str(context.exception))

    def test_invalid_processing_status(self):
        """Test validation fails with invalid processing status."""
        self.valid_file.processing_status = "INVALID"
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Invalid processing status", str(context.exception))

    def test_invalid_file_size(self):
        """Test validation fails with invalid file size."""
        # Test with negative file size
        with self.assertRaises(ValueError) as context:
            self.valid_file.file_size = -1000
            validate_transaction_file_data(self.valid_file)
        self.assertIn("File size must be positive", str(context.exception))
        
        # Test with non-integer file size
        with self.assertRaises(ValueError) as context:
            self.valid_file.file_size = "1000.34"
            validate_transaction_file_data(self.valid_file)
        self.assertIn("File size must be a valid integer", str(context.exception))

    def test_invalid_transaction_count(self):
        """Test validation fails with invalid transaction count."""
        # Test negative transaction count
        self.valid_file.record_count = -1
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Record count must be non-negative", str(context.exception))

        # Reset to valid count
        self.valid_file.record_count = 0
        
        # Test non-integer transaction count
        self.valid_file.record_count = "100"
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Record count must be a valid integer", str(context.exception))

    def test_invalid_opening_balance(self):
        """Test validation fails with invalid opening balance."""
        # Test non-Money opening balance
        self.valid_file.opening_balance = "1000.00"
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Opening balance must be a Money object", str(context.exception))

        # Test invalid Money amount
        with self.assertRaises(InvalidOperation):
            self.valid_file.opening_balance = Money("invalid", Currency.USD)
            validate_transaction_file_data(self.valid_file)

    def test_invalid_date_range(self):
        """Test validation fails with invalid date range."""
        # Test invalid date range types
        self.valid_file.date_range_start = "invalid"
        self.valid_file.date_range_end = "invalid"
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Date range must be timestamps", str(context.exception))

        # Test end date before start date
        self.valid_file.date_range_start = 2000000000000  # Later timestamp
        self.valid_file.date_range_end = 1000000000000    # Earlier timestamp
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Start date must be before end date", str(context.exception))

    def test_invalid_string_lengths(self):
        """Test validation fails with invalid string lengths."""
        # Test long file name
        self.valid_file.file_name = "x" * 256
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("File name must be 255 characters or less", str(context.exception))

        # Reset file name to valid length
        self.valid_file.file_name = "test.csv"
        
        # Test long error message
        self.valid_file.error_message = "x" * 1001
        with self.assertRaises(ValueError) as context:
            validate_transaction_file_data(self.valid_file)
        self.assertIn("Error message must be 1000 characters or less", str(context.exception))

if __name__ == '__main__':
    unittest.main() 