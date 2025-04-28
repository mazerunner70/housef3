import unittest
from unittest.mock import patch, MagicMock
from services.file_service import get_files_for_user, format_file_metadata
from handlers.file_operations import list_files_handler
from datetime import datetime
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus

@patch('boto3.resource', MagicMock())
@patch('utils.db_utils.dynamodb', MagicMock())
class TestFileService(unittest.TestCase):
    @patch('services.file_service.list_account_files')
    @patch('services.file_service.list_user_files')
    def test_get_files_for_user_account(self, mock_list_user_files, mock_list_account_files):
        mock_list_account_files.return_value = [{'fileId': 'f1'}]
        files = get_files_for_user('user1', 'acc1')
        self.assertEqual(files, [{'fileId': 'f1'}])
        mock_list_account_files.assert_called_once_with('acc1')
        mock_list_user_files.assert_not_called()

    @patch('services.file_service.list_account_files')
    @patch('services.file_service.list_user_files')
    def test_get_files_for_user_no_account(self, mock_list_user_files, mock_list_account_files):
        mock_list_user_files.return_value = [{'fileId': 'f2'}]
        files = get_files_for_user('user1')
        self.assertEqual(files, [{'fileId': 'f2'}])
        mock_list_user_files.assert_called_once_with('user1')
        mock_list_account_files.assert_not_called()

    @patch('services.file_service.get_field_map')
    def test_format_file_metadata_with_field_map(self, mock_get_field_map):
        mock_get_field_map.return_value = MagicMock(field_map_id='fm1', name='Map1', description='desc')
        file = TransactionFile(
            file_id='f1',
            user_id='u1',
            file_name='file.csv',
            upload_date='2024-01-01',
            file_size=123,
            file_format=FileFormat.CSV,
            s3_key='s3key',
            processing_status=ProcessingStatus.PENDING,
            field_map_id='fm1',
            opening_balance=100.0
        )
        formatted = format_file_metadata(file)
        self.assertEqual(formatted['fileId'], 'f1')
        self.assertEqual(formatted['fieldMap']['fieldMapId'], 'fm1')
        self.assertEqual(formatted['openingBalance'], 100.0)

    def test_format_file_metadata_minimal(self):
        file = TransactionFile(
            file_id='f2',
            user_id='u1',
            file_name='file2.csv',
            upload_date='2024-01-02',
            file_size=456,
            file_format=FileFormat.CSV,
            s3_key='s3key',
            processing_status=ProcessingStatus.PENDING
        )
        formatted = format_file_metadata(file)
        self.assertEqual(formatted['fileId'], 'f2')
        self.assertNotIn('fieldMap', formatted)

@patch('boto3.resource', MagicMock())
@patch('utils.db_utils.dynamodb', MagicMock())
class TestFormatFileMetadata(unittest.TestCase):
    @patch('services.file_service.get_field_map')
    def test_format_file_metadata_full(self, mock_get_field_map):
        mock_get_field_map.return_value = MagicMock(field_map_id='fm1', name='Map1', description='desc')
        file = TransactionFile(
            file_id='f1',
            user_id='u1',
            file_name='file.csv',
            upload_date='2024-01-01',
            file_size=123,
            file_format=FileFormat.CSV,
            s3_key='s3key',
            processing_status=ProcessingStatus.PROCESSED,
            field_map_id='fm1',
            opening_balance=100.0,
            account_id='acc1',
            record_count=10,
            date_range_start='2024-01-01',
            date_range_end='2024-01-31',
            error_message=None
        )
        formatted = format_file_metadata(file)
        self.assertEqual(formatted['fileId'], 'f1')
        self.assertEqual(formatted['fieldMap']['fieldMapId'], 'fm1')
        self.assertEqual(formatted['openingBalance'], 100.0)
        self.assertEqual(formatted['fileFormat'], FileFormat.CSV)
        self.assertEqual(formatted['processingStatus'], ProcessingStatus.PROCESSED)
        self.assertEqual(formatted['recordCount'], 10)

    def test_format_file_metadata_minimal(self):
        file = TransactionFile(
            file_id='f2',
            user_id='u1',
            file_name='file2.csv',
            upload_date='2024-01-02',
            file_size=456,
            file_format=FileFormat.CSV,
            s3_key='s3key',
            processing_status=ProcessingStatus.PENDING
        )
        formatted = format_file_metadata(file)
        self.assertEqual(formatted['fileId'], 'f2')
        self.assertNotIn('fieldMap', formatted)

    @patch('services.file_service.get_field_map')
    def test_format_file_metadata_no_field_map(self, mock_get_field_map):
        mock_get_field_map.return_value = None
        file = TransactionFile(
            file_id='f3',
            user_id='u1',
            file_name='file3.csv',
            upload_date='2024-01-03',
            file_size=789,
            file_format=FileFormat.CSV,
            s3_key='s3key',
            processing_status=ProcessingStatus.PENDING,
            field_map_id='fm2',
            opening_balance=200.0
        )
        formatted = format_file_metadata(file)
        self.assertEqual(formatted['fileId'], 'f3')
        self.assertNotIn('fieldMap', formatted)
        self.assertEqual(formatted['openingBalance'], 200.0)

@patch('boto3.resource', MagicMock())
@patch('utils.db_utils.dynamodb', MagicMock())
class TestListFilesHandler(unittest.TestCase):
    @patch('src.handlers.file_operations.checked_optional_account', return_value=None)
    @patch('utils.db_utils.get_files_table', return_value=MagicMock())
    @patch('services.file_service.get_files_for_user')
    @patch('services.file_service.format_file_metadata')
    def test_list_files_handler_success(self, mock_format, mock_get_files, mock_get_files_table, mock_checked_account):
        mock_get_files.return_value = [
            TransactionFile(
                file_id='f1',
                user_id='user1',
                file_name='file.csv',
                upload_date='2024-01-01',
                file_size=123,
                file_format=FileFormat.CSV,
                s3_key='s3key',
                processing_status=ProcessingStatus.PENDING
            )
        ]
        mock_format.side_effect = lambda f: f
        event = {'queryStringParameters': {}}
        user = {'id': 'user1'}
        response = list_files_handler(event, user)
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('files', response['body'] if isinstance(response['body'], dict) else response['body'])

if __name__ == '__main__':
    unittest.main() 