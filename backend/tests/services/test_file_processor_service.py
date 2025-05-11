import unittest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime

from models.account import Account, AccountType, Currency
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
from models.file_map import FileMap, FieldMapping
from models.money import Money
from services.file_processor_service import (
    process_new_file,
    update_file_mapping,
    update_opening_balance,
    change_file_account,
    process_file,
    remap_file,
    update_balance,
    reassign_file,
    process_file_with_account
)

class TestFileProcessorService(unittest.TestCase):
    def setUp(self):
        """Set up test data."""
        self.account = Account(
            account_id="test_account",
            user_id="test_user",
            account_name="Test Account",
            account_type=AccountType.CHECKING,
            institution="Test Bank",
            balance=Decimal("1000.00"),
            currency=Currency.USD
        )
        
        self.transaction_file = TransactionFile(
            file_id="test_file",
            user_id="test_user",
            file_name="test.csv",
            upload_date=int(datetime.now().timestamp() * 1000),
            file_size=1000,
            s3_key="test/test.csv",
            processing_status=ProcessingStatus.PENDING,
            file_format=FileFormat.CSV
        )
        
        self.field_map = FileMap(
            field_map_id="test_field_map",
            user_id="test_user",
            name="Test Field Map",
            mappings=[
                FieldMapping(source_field="Date", target_field="date"),
                FieldMapping(source_field="Amount", target_field="amount"),
                FieldMapping(source_field="Description", target_field="description")
            ],
            account_id="test_account"
        )

    @patch('utils.db_utils.get_account')
    @patch('services.file_processor_service.get_field_mapping')
    @patch('services.file_processor_service.parse_file_transactions')
    @patch('services.file_processor_service.update_transaction_file')
    @patch('utils.db_utils.get_files_table')
    def test_process_new_file_success(self, mock_files_table, mock_update_file, mock_parse_transactions, 
                                    mock_get_field_map, mock_get_account):
        """Test successful processing of a new file."""
        # Setup mocks
        mock_get_account.return_value = self.account
        mock_get_field_map.return_value = self.field_map
        mock_parse_transactions.return_value = [
            MagicMock(amount=Money(Decimal("100.00"), Currency.USD))
        ]
        mock_files_table.return_value = MagicMock()
        
        # Call function
        content_bytes = b"test content"
        result = process_new_file(self.transaction_file, content_bytes)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        self.assertEqual(result.processing_status, ProcessingStatus.PROCESSED)
        
        # Verify mock calls
        mock_get_account.assert_called_once_with(self.account.account_id)
        mock_get_field_map.assert_called_once_with(self.field_map.field_map_id)
        mock_parse_transactions.assert_called_once()
        mock_update_file.assert_called_once()

    @patch('services.file_processor_service.get_field_mapping')
    @patch('services.file_processor_service.update_transaction_file')
    @patch('utils.db_utils.get_files_table')
    def test_update_file_mapping_success(self, mock_files_table, mock_update_file, mock_get_field_map):
        """Test successful update of file mapping."""
        # Setup mocks
        mock_get_field_map.return_value = self.field_map
        mock_files_table.return_value = MagicMock()
        
        # Call function
        result = update_file_mapping(self.transaction_file)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        self.assertEqual(result.field_map_id, self.field_map.field_map_id)
        
        # Verify mock calls
        mock_get_field_map.assert_called_once_with(self.field_map.field_map_id)
        mock_update_file.assert_called_once()

    @patch('services.file_processor_service.update_transaction_file')
    @patch('utils.db_utils.get_files_table')
    def test_update_opening_balance_success(self, mock_files_table, mock_update_file):
        """Test successful update of opening balance."""
        # Setup test data
        opening_balance = Money(Decimal("500.00"), Currency.USD)
        mock_files_table.return_value = MagicMock()
        
        # Call function
        result = update_opening_balance(self.transaction_file)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        self.assertEqual(result.opening_balance, opening_balance)
        
        # Verify mock calls
        mock_update_file.assert_called_once()

    @patch('services.file_processor_service.update_transaction_file')
    @patch('utils.db_utils.get_files_table')
    @patch('services.file_processor_service.checked_mandatory_file')
    @patch('services.file_processor_service.checked_mandatory_account')
    @patch('services.file_processor_service.list_file_transactions')
    @patch('services.file_processor_service.update_transaction_duplicates')
    @patch('services.file_processor_service.determine_opening_balances_from_transaction_overlap')
    @patch('services.file_processor_service.calculate_running_balances')
    @patch('services.file_processor_service.create_response')
    def test_change_file_account_success(self, mock_create_response, mock_calculate_balances, 
                                       mock_determine_balances, mock_update_duplicates, mock_list_transactions, 
                                       mock_checked_account, mock_checked_file, mock_files_table, mock_update_file):
        """Test successful change of file account."""
        # Setup mocks
        mock_files_table.return_value = MagicMock()
        mock_update_file.return_value = self.transaction_file
        mock_checked_file.return_value = self.transaction_file
        mock_checked_account.return_value = self.account
        mock_list_transactions.return_value = []  # Return empty list for simplicity
        mock_update_duplicates.return_value = None
        mock_determine_balances.return_value = Money(Decimal("1000.00"), Currency.USD)
        mock_calculate_balances.return_value = None
        
        # Mock create_response to return a simple dict
        mock_create_response.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'File account updated successfully',
                'transactionCount': 0,
                'file': self.transaction_file.to_dict()
            }
        }
        
        # Call function
        result = change_file_account(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('transactionCount', result['body'])
        self.assertIn('file', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_update_file.assert_called_once()
        mock_checked_file.assert_called_once_with(self.transaction_file.file_id, self.transaction_file.user_id)
        mock_checked_account.assert_called_once_with(self.transaction_file.account_id, self.transaction_file.user_id)
        mock_list_transactions.assert_called_once_with(self.transaction_file.file_id)
        mock_update_duplicates.assert_not_called()  # Not called with empty transaction list
        mock_determine_balances.assert_not_called()  # Not called with empty transaction list
        mock_calculate_balances.assert_not_called()  # Not called with empty transaction list
        mock_create_response.assert_called_once_with(200, {
            'message': 'File account updated successfully',
            'transactionCount': 0,
            'file': self.transaction_file.to_dict()
        })

    @patch('services.file_processor_service.process_new_file')
    @patch('utils.db_utils.get_files_table')
    @patch('services.file_processor_service.create_response')
    @patch('utils.db_utils.get_transaction_file')
    @patch('services.file_processor_service.get_file_content')
    def test_process_file_success(self, mock_get_content, mock_get_file, mock_create_response, mock_files_table, mock_process_new_file):
        """Test successful processing of a file."""
        # Setup mocks
        mock_process_new_file.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'File processed successfully',
                'transactionCount': 0,
                'duplicateCount': 0,
                'fileId': self.transaction_file.file_id,
                'file': self.transaction_file.to_dict()
            }
        } 
        mock_files_table.return_value = MagicMock()
        mock_get_file.return_value = self.transaction_file
        mock_get_content.return_value = b"test content"  # Mock file content
        
        # Mock create_response to return a simple dict
        mock_create_response.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'File processed successfully',
                'fileId': self.transaction_file.file_id,
                'file': self.transaction_file.to_dict()
            }
        }
        
        # Call function
        result = process_file(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('fileId', result['body'])
        self.assertIn('file', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_process_new_file.assert_called_once_with(self.transaction_file)
        mock_get_file.assert_called_once_with(self.transaction_file.file_id)
        mock_get_content.assert_called_once_with(self.transaction_file.file_id)
        mock_create_response.assert_called_once_with(200, {
            'message': 'File processed successfully',
            'fileId': self.transaction_file.file_id,
            'file': self.transaction_file.to_dict()
        })

    @patch('services.file_processor_service.update_file_mapping')
    @patch('services.file_processor_service.process_file')
    @patch('utils.db_utils.get_files_table')
    def test_remap_file_success(self, mock_files_table, mock_process_file, mock_update_mapping):
        """Test successful remapping of a file."""
        # Setup mocks
        mock_update_mapping.return_value = self.transaction_file
        mock_process_file.return_value = self.transaction_file
        mock_files_table.return_value = MagicMock()
        
        # Call function
        result = remap_file(self.transaction_file)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        
        # Verify mock calls
        mock_update_mapping.assert_called_once_with(self.transaction_file)
        mock_process_file.assert_called_once_with(self.transaction_file)

    @patch('services.file_processor_service.update_transaction_file')
    @patch('utils.db_utils.get_files_table')
    def test_update_balance_success(self, mock_files_table, mock_update_file):
        """Test successful update of balance."""
        # Setup test data
        new_balance = Money(Decimal("2000.00"), Currency.USD)
        mock_files_table.return_value = MagicMock()
        
        # Call function
        result = update_balance(self.transaction_file)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        self.assertEqual(result.opening_balance, new_balance)
        
        # Verify mock calls
        mock_update_file.assert_called_once()

    @patch('services.file_processor_service.process_new_file')
    @patch('utils.db_utils.get_files_table')
    def test_process_file_with_account_new_file(self, mock_files_table, mock_process_new_file):
        """Test processing a new file through the account processor."""
        # Setup mocks
        mock_process_new_file.return_value = self.transaction_file
        mock_files_table.return_value = MagicMock()
        
        # Call function
        result = process_file_with_account(self.transaction_file)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        self.assertEqual(result.account_id, self.account.account_id)
        
        # Verify mock calls
        mock_process_new_file.assert_called_once_with(self.transaction_file)

    @patch('services.file_processor_service.reassign_file')
    @patch('utils.db_utils.get_files_table')
    def test_process_file_with_account_account_change(self, mock_files_table, mock_reassign_file):
        """Test changing account through the account processor."""
        # Setup test data
        self.transaction_file.account_id = "old_account"
        mock_files_table.return_value = MagicMock()
        
        # Setup mocks
        mock_reassign_file.return_value = self.transaction_file
        
        # Call function
        result = process_file_with_account(self.transaction_file)
        
        # Verify result
        self.assertEqual(result, self.transaction_file)
        self.assertEqual(result.account_id, self.account.account_id)
        
        # Verify mock calls
        mock_reassign_file.assert_called_once_with(self.transaction_file)

if __name__ == '__main__':
    unittest.main() 