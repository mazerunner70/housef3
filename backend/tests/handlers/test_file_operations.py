import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from decimal import Decimal
import json
from handlers.file_operations import (
    get_user_from_event,
    list_files_handler,
    get_files_by_account_handler,
    get_upload_url_handler,
    get_download_url_handler,
    delete_file_handler,
    get_file_content_handler,
    update_file_field_map_handler
)
from models.transaction_file import FileFormat, ProcessingStatus

class TestFileOperations(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.user = {
            'id': 'test-user-id',
            'email': 'test@example.com',
            'auth_time': '2024-01-01T00:00:00Z'
        }
        
        self.sample_file = MagicMock(
            file_id='test-file-id',
            user_id=self.user['id'],
            file_name='test.csv',
            file_size=1000,
            s3_key='test-user-id/test-file-id/test.csv',
            content_type='text/csv',
            file_format=FileFormat.CSV,
            processing_status=ProcessingStatus.PROCESSED.value,
            upload_date='2024-01-01T00:00:00Z',
            last_modified='2024-01-01T00:00:00Z',
            opening_balance='1.0'
        )
        
        self.sample_account = MagicMock(
            account_id='test-account-id',
            user_id=self.user['id'],
            name='Test Account'
        )

    @patch('handlers.file_operations.get_files_for_user')
    @patch('handlers.file_operations.format_file_metadata')
    def test_list_files_handler(self, mock_format_metadata, mock_get_files):
        """Test listing files for a user."""
        # Setup
        event = {}
        
        # Create a mock file object
        mock_file = {
            'file_id': 'test-file-id',
            'file_name': 'test.csv',
            'file_size': 1000,
            'upload_date': '2024-01-01',
            'account_id': 'test-account-id',
            'file_format': 'CSV',
            'processing_status': 'PROCESSED',
            'record_count': 100,
            'date_range': '2024-01-01 to 2024-01-31',
            'opening_balance': '1000.00',
            'field_map_id': 'test-map-id'
        }

        # Setup mock returns
        mock_get_files.return_value = [mock_file]
        mock_format_metadata.return_value = {
            'fileId': 'test-file-id',
            'fileName': 'test.csv',
            'fileSize': 1000,
            'uploadDate': '2024-01-01',
            'accountId': 'test-account-id',
            'fileFormat': 'CSV',
            'processingStatus': 'PROCESSED',
            'recordCount': 100,
            'dateRange': '2024-01-01 to 2024-01-31',
            'openingBalance': '1000.00'
        }

        # Execute
        response = list_files_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('files', body)
        self.assertEqual(len(body['files']), 1)
        self.assertEqual(body['files'][0]['fileId'], 'test-file-id')
        mock_get_files.assert_called_once_with(self.user['id'], None)
        mock_format_metadata.assert_called_once_with(mock_file)

    @patch('handlers.file_operations.delete_transactions_for_file')
    @patch('handlers.file_operations.delete_object')
    @patch('handlers.file_operations.delete_file_metadata')
    @patch('handlers.file_operations.get_transaction_file')
    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.list_account_files')
    def test_delete_file_handler(self, mock_list_files, mock_check_file, mock_get_file, 
                               mock_delete_metadata, mock_delete_s3, mock_delete_tx):
        """Test deleting a file."""
        # Setup
        event = {'pathParameters': {'id': 'test-file-id'}}
        
        # Create a mock file with proper attributes
        mock_file = MagicMock()
        mock_file.file_id = 'test-file-id'
        mock_file.user_id = self.user['id']
        mock_file.account_id = 'test-account-id'
        mock_file.s3_key = 'test/key'
        
        # Setup mock returns
        mock_check_file.return_value = mock_file
        mock_get_file.return_value = None
        mock_delete_tx.return_value = 5
        mock_delete_s3.return_value = True
        mock_list_files.return_value = []
        
        # Execute
        response = delete_file_handler(event, self.user)
        
        # Assert
        self.assertEqual(response['statusCode'], 200)
        mock_delete_tx.assert_called_once_with('test-file-id')
        mock_delete_s3.assert_called_once_with('test/key')
        mock_delete_metadata.assert_called_once_with('test-file-id')
        mock_get_file.assert_called_once_with('test-file-id')
        mock_list_files.assert_called_once_with('test-account-id')

    @patch('handlers.file_operations.get_files_for_account')
    @patch('handlers.file_operations.format_file_metadata')
    @patch('handlers.file_operations.checked_mandatory_account')
    def test_get_files_by_account_handler(self, mock_check_account, mock_format_metadata, mock_get_files):
        """Test listing files for an account."""
        # Setup
        event = {'pathParameters': {'accountId': 'test-account-id'}}
        
        # Create mock account
        mock_account = {
            'account_id': 'test-account-id',
            'user_id': self.user['id']
        }
        mock_check_account.return_value = mock_account
        
        # Create mock file
        mock_file = {
            'file_id': 'test-file-id',
            'file_name': 'test.csv',
            'file_size': 1000,
            'upload_date': '2024-01-01',
            'account_id': 'test-account-id',
            'file_format': 'CSV',
            'processing_status': 'PROCESSED',
            'record_count': 100,
            'date_range': '2024-01-01 to 2024-01-31',
            'opening_balance': '1000.00'
        }
        mock_get_files.return_value = [mock_file]
        
        # Setup format metadata mock
        mock_format_metadata.return_value = {
            'fileId': 'test-file-id',
            'fileName': 'test.csv',
            'fileSize': 1000,
            'uploadDate': '2024-01-01',
            'accountId': 'test-account-id',
            'fileFormat': 'CSV',
            'processingStatus': 'PROCESSED',
            'recordCount': 100,
            'dateRange': '2024-01-01 to 2024-01-31',
            'openingBalance': '1000.00'
        }

        # Execute
        response = get_files_by_account_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('files', body)
        self.assertEqual(len(body['files']), 1)
        self.assertEqual(body['files'][0]['fileId'], 'test-file-id')
        mock_check_account.assert_called_once_with('test-account-id', self.user['id'])
        mock_get_files.assert_called_once_with('test-account-id')
        mock_format_metadata.assert_called_once_with(mock_file)

    @patch('handlers.file_operations.get_presigned_url')
    @patch('handlers.file_operations.create_transaction_file')
    def test_get_upload_url_handler(self, mock_create_file, mock_get_url):
        """Test generating upload URL."""
        # Setup
        mock_get_url.return_value = 'https://test-url'
        event = {
            'body': json.dumps({
                'fileName': 'test.csv',
                'fileSize': 1000
            })
        }

        # Execute
        response = get_upload_url_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('uploadUrl', response['body'])
        mock_get_url.assert_called_once()
        mock_create_file.assert_called_once()

    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.get_presigned_url')
    def test_get_download_url_handler(self, mock_get_url, mock_get_file):
        """Test generating download URL."""
        # Setup
        mock_get_file.return_value = self.sample_file
        mock_get_url.return_value = 'https://test-url'
        event = {'pathParameters': {'id': 'test-file-id'}}

        # Execute
        response = get_download_url_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('downloadUrl', response['body'])
        mock_get_url.assert_called_once()

    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.get_object_content')
    def test_get_file_content_handler(self, mock_get_content, mock_get_file):
        """Test getting file content."""
        # Setup
        mock_get_file.return_value = self.sample_file
        mock_get_content.return_value = b'test content'
        event = {'pathParameters': {'id': 'test-file-id'}}

        # Execute
        response = get_file_content_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('content', response['body'])
        mock_get_content.assert_called_once()

    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.get_field_map')
    @patch('handlers.file_operations.update_file_field_map')
    @patch('handlers.file_operations.get_object_content')
    @patch('handlers.file_operations.process_file_with_account')
    def test_update_file_field_map_handler(self, mock_process, mock_get_content, 
                                         mock_update_map, mock_get_map, mock_get_file):
        """Test updating file field map."""
        # Setup
        mock_get_file.return_value = self.sample_file
        mock_get_map.return_value = {
            'userId': self.user['id'],
            'name': 'Test Map',
            'id': 'test-map-id',
            'mappings': {'date': 'Date', 'amount': 'Amount'}
        }
        mock_get_content.return_value = b'test content'
        mock_process.return_value = {
            'statusCode': 200,
            'body': json.dumps({'transactionCount': 5})
        }
        
        event = {
            'pathParameters': {'id': 'test-file-id'},
            'body': json.dumps({'fieldMapId': 'test-map-id'})
        }

        # Execute
        response = update_file_field_map_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('message', body)
        self.assertIn('transactionCount', body)
        self.assertEqual(body['transactionCount'], 5)
        
        mock_update_map.assert_called_once_with('test-file-id', 'test-map-id')
        mock_get_content.assert_called_once_with(self.sample_file.s3_key)
        mock_process.assert_called_once_with(
            'test-file-id',
            b'test content',
            self.sample_file.file_format,
            1.0,
            self.user['id']
        )

    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.get_field_map')
    @patch('handlers.file_operations.update_file_field_map')
    def test_update_file_field_map_handler_no_s3_key(self, mock_update_map, mock_get_map, mock_get_file):
        """Test updating file field map when file has no S3 key."""
        # Setup
        file_without_s3 = MagicMock(
            fileId='test-file-id',
            userId=self.user['id'],
            s3_key=None
        )
        mock_get_file.return_value = file_without_s3
        mock_get_map.return_value = {'userId': self.user['id'], 'name': 'Test Map'}
        
        event = {
            'pathParameters': {'id': 'test-file-id'},
            'body': json.dumps({'fieldMapId': 'test-map-id'})
        }

        # Execute
        response = update_file_field_map_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertIn('message', body)
        self.assertEqual(body['message'], 'File successfully associated with field map')
        mock_update_map.assert_called_once_with('test-file-id', 'test-map-id')

    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.get_field_map')
    def test_update_file_field_map_handler_invalid_field_map(self, mock_get_map, mock_get_file):
        """Test updating file field map with invalid field map ID."""
        # Setup
        mock_get_file.return_value = self.sample_file
        mock_get_map.return_value = None
        
        event = {
            'pathParameters': {'id': 'test-file-id'},
            'body': json.dumps({'fieldMapId': 'invalid-map-id'})
        }

        # Execute
        response = update_file_field_map_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertIn('message', body)
        self.assertEqual(body['message'], 'Field map not found')

    @patch('handlers.file_operations.checked_mandatory_file')
    @patch('handlers.file_operations.delete_transactions_for_file')
    @patch('handlers.file_operations.delete_object')
    @patch('handlers.file_operations.delete_file_metadata')
    @patch('handlers.file_operations.get_transaction_file')
    def test_delete_file_handler_failure(self, mock_get_tx_file, mock_delete_metadata, mock_delete_s3, mock_delete_tx, mock_get_file):
        """Test deleting a file when verification fails."""
        # Setup
        mock_get_file.return_value = self.sample_file
        mock_delete_tx.return_value = 5
        mock_delete_s3.return_value = True
        # Simulate verification failure - file still exists
        mock_get_tx_file.return_value = self.sample_file
        event = {'pathParameters': {'id': 'test-file-id'}}

        # Execute
        response = delete_file_handler(event, self.user)

        # Assert
        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Error verifying file deletion', response['body'])
        mock_delete_tx.assert_called_once()
        mock_delete_s3.assert_called_once()
        mock_delete_metadata.assert_called_once()
        mock_get_tx_file.assert_called_once_with('test-file-id')

    def test_get_user_from_event(self):
        """Test extracting user from event."""
        # Setup
        event = {
            'requestContext': {
                'authorizer': {
                    'jwt': {
                        'claims': {
                            'sub': 'test-user-id',
                            'email': 'test@example.com',
                            'auth_time': '2024-01-01T00:00:00Z'
                        }
                    }
                }
            }
        }

        # Execute
        user = get_user_from_event(event)

        # Assert
        self.assertIsNotNone(user)
        self.assertEqual(user['id'], 'test-user-id')
        self.assertEqual(user['email'], 'test@example.com')

if __name__ == '__main__':
    unittest.main() 