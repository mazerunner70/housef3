"""
Unit tests for file processor utilities.
"""
import unittest
from unittest.mock import patch, MagicMock, ANY
import boto3
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List
import os

from utils.file_processor_utils import (
    create_composite_key,
    get_file_content,
    find_file_records_by_s3_key,
    extract_opening_balance,
    extract_opening_balance_ofx,
    extract_opening_balance_csv,
    calculate_opening_balance_from_duplicates
)
from models.transaction import Transaction
from models.transaction_file import FileFormat
from models.money import Money, Currency

class TestFileProcessorUtils(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Sample transaction data
        self.user_id = "test_user"
        self.transaction_data = {
            "date": "2024-01-01",
            "amount": "100.00",
            "description": "Test Transaction"
        }
        
        # Sample file content
        self.ofx_content = b'''OFXHEADER:100
<OFX>
<LEDGERBAL>
<BALAMT>1000.50</BALAMT>
<DTASOF>20240101</DTASOF>
</LEDGERBAL>
</OFX>'''

        self.csv_content = b'''Opening Balance,1500.25
Date,Description,Amount
2024-01-01,Test Transaction,100.00'''

        # Sample transactions for opening balance calculation
        date_ms = int(datetime(2024, 1, 1).timestamp() * 1000)
        self.transactions = [
            Transaction(
                user_id="test_user",
                file_id="file1",
                transaction_id="tx1",
                account_id="account1",
                date=date_ms,
                description="Transaction 1",
                amount=Money(Decimal("100.00"), Currency.USD),
                balance=Money(Decimal("1000.00"), Currency.USD)
            ),
            Transaction(
                user_id="test_user",
                file_id="file1",
                transaction_id="tx2",
                account_id="account1",
                date=date_ms + 86400000,  # Next day in milliseconds
                description="Transaction 2",
                amount=Money(Decimal("200.00"), Currency.USD),
                balance=Money(Decimal("1200.00"), Currency.USD)
            )
        ]

    def test_create_composite_key(self):
        """Test creating composite key from transaction data."""
        # Execute
        result = create_composite_key(self.user_id, self.transaction_data)

        # Verify
        expected = "test_user#2024-01-01#100.00#Test Transaction"
        self.assertEqual(result, expected)

    @patch.dict(os.environ, {'FILE_STORAGE_BUCKET': 'test-bucket'})
    @patch('utils.file_processor_utils.get_transaction_file')
    @patch('utils.file_processor_utils.get_s3_client')
    def test_get_file_content_success(self, mock_get_s3_client, mock_get_transaction_file):
        """Test successful retrieval of file content from S3."""
        # Setup
        mock_s3 = MagicMock()
        mock_get_s3_client.return_value = mock_s3
        mock_get_transaction_file.return_value = MagicMock(s3_key="test/key.csv")
        mock_response = MagicMock()
        mock_response.read.return_value = b'test content'
        mock_s3.get_object.return_value = {
            'Body': mock_response
        }

        # Execute
        result = get_file_content("test_file_id")

        # Verify
        self.assertEqual(result, b'test content')
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key="test/key.csv"
        )

    @patch('utils.file_processor_utils.get_transaction_file')
    def test_get_file_content_no_record(self, mock_get_transaction_file):
        """Test get_file_content when file record not found."""
        # Setup
        mock_get_transaction_file.return_value = None

        # Execute
        result = get_file_content("test_file_id")

        # Verify
        self.assertIsNone(result)

    def test_find_file_records_by_s3_key(self):
        """Test finding file records by S3 key."""
        # Setup
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [
                {'fileId': 'file1', 's3Key': 'test/key.csv'},
                {'fileId': 'file2', 's3Key': 'test/key.csv'}
            ]
        }

        # Execute
        result = find_file_records_by_s3_key("test/key.csv", table=mock_table)

        # Verify
        self.assertEqual(len(result), 2)
        mock_table.query.assert_called_once()

    def test_extract_opening_balance_ofx(self):
        """Test extracting opening balance from OFX content."""
        # Test modern OFX format
        result = extract_opening_balance_ofx(self.ofx_content.decode('utf-8'))
        self.assertEqual(result, 1000.50)

        # Test SGML format
        sgml_content = "LEDGERBAL\nBALAMT:2000.75"
        result = extract_opening_balance_ofx(sgml_content)
        self.assertEqual(result, 2000.75)

        # Test with AVAILBAL
        avail_content = "<AVAILBAL><BALAMT>3000.25</BALAMT></AVAILBAL>"
        result = extract_opening_balance_ofx(avail_content)
        self.assertEqual(result, 3000.25)

    def test_extract_opening_balance_csv(self):
        """Test extracting opening balance from CSV content."""
        # Test explicit opening balance
        result = extract_opening_balance_csv(self.csv_content.decode('utf-8'))
        self.assertEqual(result, 1500.25)

        # Test other balance formats
        variations = [
            "Beginning Balance,2000.50",
            "Balance Forward,2500.75",
            "Previous Balance,3000.25"
        ]
        
        for content in variations:
            result = extract_opening_balance_csv(content)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, float)

    def test_extract_opening_balance(self):
        """Test extracting opening balance based on file format."""
        # Test OFX format
        result = extract_opening_balance(self.ofx_content, FileFormat.OFX)
        self.assertEqual(result, 1000.50)

        # Test CSV format
        result = extract_opening_balance(self.csv_content, FileFormat.CSV)
        self.assertEqual(result, 1500.25)

        # Test unsupported format
        result = extract_opening_balance(b"some content", FileFormat.PDF)
        self.assertIsNone(result)

    @patch('utils.file_processor_utils.check_duplicate_transaction')
    def test_calculate_opening_balance_from_duplicates(self, mock_check_duplicate):
        """Test calculating opening balance from duplicate transactions."""
        # Test when first transaction is duplicate
        mock_check_duplicate.side_effect = [True, False]
        result = calculate_opening_balance_from_duplicates(self.transactions)
        self.assertEqual(result, Decimal("1000.00"))

        # Test when last transaction is duplicate
        mock_check_duplicate.side_effect = [False, True]
        result = calculate_opening_balance_from_duplicates(self.transactions)
        self.assertEqual(result, Decimal("900.00"))  # 1200 - (100 + 200)

        # Test when no duplicates found
        mock_check_duplicate.side_effect = [False, False]
        result = calculate_opening_balance_from_duplicates(self.transactions)
        self.assertIsNone(result)

        # Test with empty transaction list
        result = calculate_opening_balance_from_duplicates([])
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main() 