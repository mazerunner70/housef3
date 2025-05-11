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
            file_format=FileFormat.CSV,
            account_id="test_account",
            field_map_id="test_field_map"
        )
        
        # Add copy method to TransactionFile for testing
        def copy(self):
            return TransactionFile(
                file_id=self.file_id,
                user_id=self.user_id,
                file_name=self.file_name,
                upload_date=self.upload_date,
                file_size=self.file_size,
                s3_key=self.s3_key,
                processing_status=self.processing_status,
                file_format=self.file_format,
                account_id=self.account_id,
                field_map_id=self.field_map_id,
                processed_date=self.processed_date,
                record_count=self.record_count,
                date_range_start=self.date_range_start,
                date_range_end=self.date_range_end,
                error_message=self.error_message,
                opening_balance=self.opening_balance
            )
        TransactionFile.copy = copy
        
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
        
        # Mock DynamoDB tables
        self.mock_files_table = MagicMock()
        self.mock_files_table.get_item.return_value = {'Item': self.transaction_file.to_dict()}
        self.mock_files_table.put_item.return_value = {}
        self.mock_files_table.update_item.return_value = {}
        
        self.mock_field_maps_table = MagicMock()
        self.mock_field_maps_table.get_item.return_value = {'Item': self.field_map.to_dict()}
        self.mock_field_maps_table.put_item.return_value = {}
        self.mock_field_maps_table.update_item.return_value = {}

    @patch('services.file_processor_service.parse_transactions')
    @patch('services.file_processor_service.get_file_content')
    @patch('services.file_processor_service.determine_field_mapping')
    @patch('services.file_processor_service.get_field_mapping')
    @patch('services.file_processor_service.update_transaction_file')
    @patch('services.file_processor_service.save_transactions')
    def test_process_new_file_success(self, mock_save_transactions, mock_update_file, mock_get_field_mapping, mock_determine_field_mapping, mock_get_content, mock_parse_transactions):
        """Test successful processing of a new file."""
        # Setup mocks
        mock_get_content.return_value = b"test content"
        mock_get_field_mapping.return_value = self.field_map
        mock_determine_field_mapping.return_value = None  # No return value needed
        mock_parse_transactions.return_value = []
        mock_save_transactions.return_value = (0, 0)  # (transaction_count, duplicate_count)
        mock_update_file.return_value = self.transaction_file
        
        # Make a copy of the transaction file and add the field_map attribute
        file_with_map = self.transaction_file.copy()
        file_with_map.field_map = self.field_map
        
        # Call function
        result = process_new_file(file_with_map, b"test content")
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('transactionCount', result['body'])
        self.assertIn('duplicateCount', result['body'])
        self.assertIn('fileId', result['body'])
        self.assertIn('file', result['body'])
        
        # Verify mock calls
        mock_get_field_mapping.assert_not_called()  # Not called directly
        mock_determine_field_mapping.assert_called_once_with(file_with_map)

    @patch('services.file_processor_service.get_field_mapping')
    @patch('services.file_processor_service.update_transaction_file')
    @patch('utils.db_utils.get_files_table')
    @patch('services.file_processor_service.checked_mandatory_field_mapping')
    @patch('services.file_processor_service.get_file_content')
    @patch('services.file_processor_service.delete_transactions_for_file')
    @patch('services.file_processor_service.parse_file_transactions')
    def test_update_file_mapping_success(self, mock_parse_transactions, mock_delete_transactions, mock_get_content, mock_checked_field_map, mock_files_table, mock_update_file, mock_get_field_map):
        """Test successful update of file mapping."""
        # Setup mocks
        mock_checked_field_map.return_value = self.field_map
        mock_get_field_map.return_value = self.field_map
        mock_files_table.return_value = self.mock_files_table
        mock_get_content.return_value = b"test content"
        mock_delete_transactions.return_value = None
        
        # Add transactions to be returned by parse_file_transactions
        mock_transactions = []
        mock_parse_transactions.return_value = mock_transactions
        
        # Call function
        result = update_file_mapping(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        
        # Verify mock calls
        mock_checked_field_map.assert_called_once_with(self.field_map.field_map_id, self.transaction_file.user_id)

    @patch('services.file_processor_service.update_opening_balance')
    def test_update_opening_balance_success(self, mock_update_opening_balance):
        """Test successful update of opening balance."""
        # Setup mock response
        mock_update_opening_balance.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'Opening balance updated successfully',
                'transactionCount': 0,
                'fileId': self.transaction_file.file_id,
                'file': self.transaction_file.to_dict()
            }
        }
        
        # Call function
        result = update_balance(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('fileId', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_update_opening_balance.assert_called_once_with(self.transaction_file)

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
    @patch('services.file_processor_service.create_transaction_file')
    @patch('services.file_processor_service.get_file_content')
    def test_process_file_success(self, mock_get_content, mock_create_transaction_file, mock_process_new_file):
        """Test successful processing of a file."""
        # Setup mocks
        mock_get_content.return_value = b"test content"
        mock_create_transaction_file.return_value = None
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
        
        # Call function
        result = process_file(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('transactionCount', result['body'])
        self.assertIn('duplicateCount', result['body'])
        self.assertIn('fileId', result['body'])
        self.assertIn('file', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_create_transaction_file.assert_called_once_with(self.transaction_file)
        mock_get_content.assert_called_once_with(self.transaction_file.file_id)
        mock_process_new_file.assert_called_once_with(self.transaction_file, b"test content")

    @patch('services.file_processor_service.update_file_mapping')
    def test_remap_file_success(self, mock_update_file_mapping):
        """Test successful remapping of a file."""
        # Setup mock response
        mock_update_file_mapping.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'File remapped successfully',
                'transactionCount': 0,
                'duplicateCount': 0,
                'fileId': self.transaction_file.file_id,
                'file': self.transaction_file.to_dict()
            }
        }
        
        # Call function
        result = remap_file(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('fileId', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_update_file_mapping.assert_called_once_with(self.transaction_file)

    @patch('services.file_processor_service.checked_optional_file')
    @patch('services.file_processor_service.process_file')
    def test_process_file_with_account_new_file(self, mock_process_file, mock_checked_file):
        """Test processing a new file through the account processor."""
        # Setup mocks
        mock_checked_file.return_value = None  # No existing file
        self.transaction_file.processing_status = ProcessingStatus.PENDING
        
        mock_process_file.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'File processed successfully',
                'transactionCount': 0,
                'duplicateCount': 0,
                'fileId': self.transaction_file.file_id,
                'file': self.transaction_file.to_dict()
            }
        }
        
        # Call function
        result = process_file_with_account(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('transactionCount', result['body'])
        self.assertIn('duplicateCount', result['body'])
        self.assertIn('fileId', result['body'])
        self.assertIn('file', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_checked_file.assert_called_once_with(self.transaction_file.file_id, self.transaction_file.user_id)
        mock_process_file.assert_called_once_with(self.transaction_file)

    @patch('services.file_processor_service.checked_optional_file')
    @patch('services.file_processor_service.reassign_file')
    def test_process_file_with_account_account_change(self, mock_reassign_file, mock_checked_file):
        """Test changing account through the account processor."""
        # Setup mocks
        old_file = self.transaction_file.copy()
        old_file.account_id = "old_account"
        mock_checked_file.return_value = old_file
        
        mock_reassign_file.return_value = {
            'statusCode': 200,
            'body': {
                'message': 'File account updated successfully',
                'transactionCount': 0,
                'file': self.transaction_file.to_dict()
            }
        }
        
        # Call function
        result = process_file_with_account(self.transaction_file)
        
        # Verify result
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result['body'])
        self.assertIn('transactionCount', result['body'])
        self.assertIn('file', result['body'])
        self.assertEqual(result['body']['file'], self.transaction_file.to_dict())
        
        # Verify mock calls
        mock_checked_file.assert_called_once_with(self.transaction_file.file_id, self.transaction_file.user_id)
        mock_reassign_file.assert_called_once_with(self.transaction_file)

if __name__ == '__main__':
    unittest.main() 