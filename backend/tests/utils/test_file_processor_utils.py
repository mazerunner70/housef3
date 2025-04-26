import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import boto3
from decimal import Decimal

from models.transaction_file import FileFormat
from utils.file_processor_utils import (
    check_duplicate_transaction,
    get_file_content,
    find_file_records_by_s3_key,
    extract_opening_balance,
    extract_opening_balance_ofx,
    extract_opening_balance_csv,
    calculate_opening_balance_from_duplicates
)

class TestFileProcessorUtils(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.sample_transaction = {
            'date': '2024-01-01',
            'description': 'Test Transaction',
            'amount': '100.00'
        }
        
        self.sample_file_record = MagicMock(
            s3_key='test-key',
            file_id='test-file-1'
        )
        
    @patch('utils.file_processor_utils.transaction_table')
    def test_check_duplicate_transaction(self, mock_table):
        """Test duplicate transaction checking."""
        # Test exact match
        mock_table.query.return_value = {'Items': [self.sample_transaction]}
        result = check_duplicate_transaction(self.sample_transaction, 'test-account')
        self.assertTrue(result)
        mock_table.query.assert_called_once()
        
        # Test no match
        mock_table.query.return_value = {'Items': []}
        result = check_duplicate_transaction(self.sample_transaction, 'test-account')
        self.assertFalse(result)
        
        # Test different amount
        different_transaction = self.sample_transaction.copy()
        different_transaction['amount'] = '200.00'
        result = check_duplicate_transaction(different_transaction, 'test-account')
        self.assertFalse(result)
        
        # Test error handling
        mock_table.query.side_effect = Exception('Test error')
        result = check_duplicate_transaction(self.sample_transaction, 'test-account')
        self.assertFalse(result)
        
    @patch('utils.file_processor_utils.get_transaction_file')
    @patch('utils.file_processor_utils.s3_client')
    def test_get_file_content(self, mock_s3, mock_get_file):
        """Test file content retrieval."""
        # Test successful retrieval
        mock_get_file.return_value = self.sample_file_record
        mock_s3.get_object.return_value = {'Body': MagicMock(read=lambda: b'test content')}
        
        result = get_file_content('test-file-1')
        self.assertEqual(result, b'test content')
        mock_s3.get_object.assert_called_once()
        
        # Test missing file record
        mock_get_file.return_value = None
        result = get_file_content('test-file-1')
        self.assertIsNone(result)
        
        # Test missing S3 key
        self.sample_file_record.s3_key = None
        mock_get_file.return_value = self.sample_file_record
        result = get_file_content('test-file-1')
        self.assertIsNone(result)
        
        # Test S3 error
        self.sample_file_record.s3_key = 'test-key'
        mock_get_file.return_value = self.sample_file_record
        mock_s3.get_object.side_effect = Exception('S3 error')
        result = get_file_content('test-file-1')
        self.assertIsNone(result)
        
    @patch('utils.file_processor_utils.file_table')
    def test_find_file_records_by_s3_key(self, mock_table):
        """Test finding file records by S3 key."""
        # Test found records
        mock_table.query.return_value = {
            'Items': [
                {'fileId': 'test-1', 's3Key': 'test-key'},
                {'fileId': 'test-2', 's3Key': 'test-key'}
            ]
        }
        result = find_file_records_by_s3_key('test-key')
        self.assertEqual(len(result), 2)
        mock_table.query.assert_called_once()
        
        # Test no records
        mock_table.query.return_value = {'Items': []}
        result = find_file_records_by_s3_key('test-key')
        self.assertEqual(len(result), 0)
        
        # Test error handling
        mock_table.query.side_effect = Exception('Test error')
        result = find_file_records_by_s3_key('test-key')
        self.assertEqual(len(result), 0)
        
    def test_extract_opening_balance_ofx(self):
        """Test OFX opening balance extraction."""
        # Test modern OFX format
        content = '<LEDGERBAL><BALAMT>1000.00</BALAMT></LEDGERBAL>'
        result = extract_opening_balance_ofx(content)
        self.assertEqual(result, 1000.00)
        
        # Test SGML format
        content = 'LEDGERBAL BALAMT:1000.00'
        result = extract_opening_balance_ofx(content)
        self.assertEqual(result, 1000.00)
        
        # Test AVAILBAL fallback
        content = '<AVAILBAL><BALAMT>2000.00</BALAMT></AVAILBAL>'
        result = extract_opening_balance_ofx(content)
        self.assertEqual(result, 2000.00)
        
        # Test no balance found
        content = 'No balance here'
        result = extract_opening_balance_ofx(content)
        self.assertIsNone(result)
        
        # Test invalid number format
        content = '<LEDGERBAL><BALAMT>invalid</BALAMT></LEDGERBAL>'
        result = extract_opening_balance_ofx(content)
        self.assertIsNone(result)
        
    def test_extract_opening_balance_csv(self):
        """Test CSV opening balance extraction."""
        # Test various CSV formats
        test_cases = [
            ('Opening Balance,1000.00', 1000.00),
            ('Beginning Balance, 2000.00', 2000.00),
            ('Balance Forward, 3000.00', 3000.00),
            ('Previous Balance, 4000.00', 4000.00),
            ('No balance here', None),
            ('Opening Balance,invalid', None)
        ]
        
        for content, expected in test_cases:
            result = extract_opening_balance_csv(content)
            self.assertEqual(result, expected)
            
        # Test heuristic matching
        content = """Opening Balance
        Date,Description,Amount
        2024-01-01,Opening Balance,1000.00"""
        result = extract_opening_balance_csv(content)
        self.assertEqual(result, 1000.00)
        
    def test_extract_opening_balance(self):
        """Test opening balance extraction with different formats."""
        # Test OFX format
        content = b'<LEDGERBAL><BALAMT>1000.00</BALAMT></LEDGERBAL>'
        result = extract_opening_balance(content, FileFormat.OFX)
        self.assertEqual(result, 1000.00)
        
        # Test CSV format
        content = b'Opening Balance,1000.00'
        result = extract_opening_balance(content, FileFormat.CSV)
        self.assertEqual(result, 1000.00)
        
        # Test unsupported format
        content = b'Some content'
        result = extract_opening_balance(content, FileFormat.OTHER)
        self.assertIsNone(result)
        
        # Test decoding error
        content = b'\xff\xfe'  # Invalid UTF-8
        result = extract_opening_balance(content, FileFormat.CSV)
        self.assertIsNone(result)

    @patch('utils.file_processor_utils.check_duplicate_transaction')
    def test_calculate_opening_balance_first_duplicate(self, mock_check_dup):
        """Test opening balance calculation when first transaction is duplicate."""
        transactions = [
            {'amount': '100.00', 'balance': '1100.00', 'date': '2024-01-01', 'description': 'A'},
            {'amount': '200.00', 'balance': '1300.00', 'date': '2024-01-02', 'description': 'B'}
        ]
        # First is duplicate
        mock_check_dup.side_effect = [True, False]
        result = calculate_opening_balance_from_duplicates(transactions, 'acc-1')
        self.assertEqual(result, Decimal('1100.00'))

    @patch('utils.file_processor_utils.check_duplicate_transaction')
    def test_calculate_opening_balance_last_duplicate(self, mock_check_dup):
        """Test opening balance calculation when last transaction is duplicate."""
        transactions = [
            {'amount': '100.00', 'balance': '1100.00', 'date': '2024-01-01', 'description': 'A'},
            {'amount': '200.00', 'balance': '1300.00', 'date': '2024-01-02', 'description': 'B'}
        ]
        # First is not, last is duplicate
        mock_check_dup.side_effect = [False, True]
        # total_amount = 100 + 200 = 300, opening = 1300 - 300 = 1000
        result = calculate_opening_balance_from_duplicates(transactions, 'acc-1')
        self.assertEqual(result, Decimal('1000.00'))

    @patch('utils.file_processor_utils.check_duplicate_transaction')
    def test_calculate_opening_balance_no_duplicates(self, mock_check_dup):
        """Test opening balance calculation when no transaction is duplicate."""
        transactions = [
            {'amount': '100.00', 'balance': '1100.00', 'date': '2024-01-01', 'description': 'A'},
            {'amount': '200.00', 'balance': '1300.00', 'date': '2024-01-02', 'description': 'B'}
        ]
        mock_check_dup.side_effect = [False, False]
        result = calculate_opening_balance_from_duplicates(transactions, 'acc-1')
        self.assertIsNone(result)

    def test_calculate_opening_balance_empty(self):
        """Test opening balance calculation with empty transactions list."""
        result = calculate_opening_balance_from_duplicates([], 'acc-1')
        self.assertIsNone(result)

    @patch('utils.file_processor_utils.check_duplicate_transaction')
    def test_calculate_opening_balance_error(self, mock_check_dup):
        """Test error handling in opening balance calculation."""
        transactions = [
            {'amount': 'bad', 'balance': 'bad', 'date': '2024-01-01', 'description': 'A'}
        ]
        mock_check_dup.side_effect = Exception('fail')
        result = calculate_opening_balance_from_duplicates(transactions, 'acc-1')
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main() 