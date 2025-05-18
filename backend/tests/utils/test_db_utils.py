"""
Unit tests for database utility functions.
"""
import unittest
from unittest.mock import patch, MagicMock, ANY
from decimal import Decimal
from datetime import datetime
import uuid
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from utils.db_utils import (
    get_account,
    list_user_accounts,
    create_account,
    update_account,
    delete_account,
    get_transaction_file,
    list_account_files,
    list_user_files,
    create_transaction_file,
    update_transaction_file,
    delete_transaction_file,
    list_file_transactions,
    list_user_transactions,
    create_transaction,
    delete_transactions_for_file,
    get_file_map,
    create_file_map,
    update_file_map,
    delete_file_map,
    list_file_maps_by_user,
    list_account_file_maps,
    check_duplicate_transaction,
    NotAuthorized,
    NotFound
)
from models.account import Account, AccountType
from models.transaction import Transaction
from models.transaction_file import TransactionFile, FileFormat, ProcessingStatus
from models.file_map import FileMap, FieldMapping
from models.money import Money, Currency

class TestDBUtils(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.account_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.file_id = str(uuid.uuid4())
        self.file_map_id = str(uuid.uuid4())
        self.transaction_id = str(uuid.uuid4())
        self.upload_date = int(datetime.now().timestamp() * 1000)

        # Create sample account
        self.account = Account.create(
            user_id=self.user_id,
            account_name="Test Account",
            account_type=AccountType.CHECKING,
            institution="Test Bank",
            balance=1000.00,
            currency=Currency.USD
        )

        # Create sample transaction file
        self.transaction_file = TransactionFile(
            file_id=self.file_id,
            user_id=self.user_id,
            file_name="test.csv",
            upload_date=self.upload_date,
            file_size=1024,
            s3_key=f"transactions/{self.user_id}/{self.file_id}.csv",
            processing_status=ProcessingStatus.PENDING,
            file_format=FileFormat.CSV,
            account_id=self.account_id
        )

        # Create sample transaction
        self.transaction = Transaction(
            transaction_id=self.transaction_id,
            user_id=self.user_id,
            file_id=self.file_id,
            account_id=self.account_id,
            date=self.upload_date,
            description="Test Transaction",
            amount=Money(Decimal("100.00"), Currency.USD)
        )

        # Create sample file map with required mappings
        self.file_map = FileMap(
            file_map_id=self.file_map_id,
            user_id=self.user_id,
            account_id=self.account_id,
            name="Test Map",
            mappings=[
                FieldMapping("date", "Date"),
                FieldMapping("description", "Description"),
                FieldMapping("amount", "Amount")
            ]
        )

        # Mock DynamoDB tables
        self.mock_accounts_table = MagicMock()
        self.mock_files_table = MagicMock()
        self.mock_transactions_table = MagicMock()
        self.mock_file_maps_table = MagicMock()

    @patch('utils.db_utils.get_accounts_table')
    def test_get_account(self, mock_get_table):
        """Test retrieving an account."""
        # Setup
        mock_get_table.return_value = self.mock_accounts_table
        self.mock_accounts_table.get_item.return_value = {
            'Item': self.account.to_flat_dict()
        }

        # Execute
        result = get_account(self.account_id)

        # Verify
        self.mock_accounts_table.get_item.assert_called_with(
            Key={'accountId': self.account_id}
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Account)
        if result:  # Type guard for mypy
            self.assertEqual(result.account_id, self.account.account_id)
            self.assertEqual(result.user_id, self.account.user_id)
            self.assertEqual(result.balance.amount, self.account.balance.amount)
            self.assertEqual(result.balance.currency, self.account.balance.currency)

    @patch('utils.db_utils.get_accounts_table')
    def test_get_account_not_found(self, mock_get_table):
        """Test retrieving a non-existent account."""
        # Setup
        mock_get_table.return_value = self.mock_accounts_table
        self.mock_accounts_table.get_item.return_value = {}

        # Execute
        result = get_account(self.account_id)

        # Verify
        self.assertIsNone(result)

    @patch('utils.db_utils.get_accounts_table')
    def test_list_user_accounts(self, mock_get_table):
        """Test listing user accounts."""
        # Setup
        mock_get_table.return_value = self.mock_accounts_table
        self.mock_accounts_table.query.return_value = {
            'Items': [self.account.to_flat_dict()]
        }

        # Execute
        results = list_user_accounts(self.user_id)

        # Verify
        self.mock_accounts_table.query.assert_called_with(
            IndexName='UserIdIndex',
            KeyConditionExpression=Key('userId').eq(self.user_id)
        )
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Account)
        self.assertEqual(results[0].user_id, self.user_id)
        self.assertEqual(results[0].balance.amount, self.account.balance.amount)
        self.assertEqual(results[0].balance.currency, self.account.balance.currency)

    @patch('utils.db_utils.get_accounts_table')
    def test_create_account(self, mock_get_table):
        """Test creating an account."""
        # Setup
        mock_get_table.return_value = self.mock_accounts_table

        # Execute
        create_account(self.account)

        # Verify
        self.mock_accounts_table.put_item.assert_called_with(
            Item=self.account.to_dict()
        )

    @patch('utils.db_utils.get_account')
    @patch('utils.db_utils.get_accounts_table')
    def test_update_account(self, mock_get_table, mock_get_account):
        """Test updating an account."""
        # Setup
        mock_get_table.return_value = self.mock_accounts_table
        mock_get_account.return_value = self.account
        
        updates = {
            'accountName': 'Updated Account',
            'notes': 'Updated notes'
        }

        # Execute
        updated_account = update_account(self.account_id, self.user_id, updates)

        # Verify
        self.assertEqual(updated_account.account_name, 'Updated Account')
        self.assertEqual(updated_account.notes, 'Updated notes')
        self.mock_accounts_table.put_item.assert_called_with(
            Item=updated_account.to_dict()
        )

    @patch('utils.db_utils.get_account')
    @patch('utils.db_utils.get_accounts_table')
    def test_update_account_unauthorized(self, mock_get_table, mock_get_account):
        """Test updating an account without authorization."""
        # Setup
        mock_get_table.return_value = self.mock_accounts_table
        mock_get_account.return_value = self.account
        
        wrong_user_id = str(uuid.uuid4())
        updates = {'accountName': 'Updated Account'}

        # Execute and verify
        with self.assertRaises(NotAuthorized):
            update_account(self.account_id, wrong_user_id, updates)

    @patch('utils.db_utils.get_files_table')
    def test_get_transaction_file(self, mock_get_table):
        """Test retrieving a transaction file."""
        # Setup
        mock_get_table.return_value = self.mock_files_table
        self.mock_files_table.get_item.return_value = {
            'Item': self.transaction_file.to_dict()
        }

        # Execute
        result = get_transaction_file(self.file_id)

        # Verify
        self.mock_files_table.get_item.assert_called_with(
            Key={'fileId': self.file_id}
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, TransactionFile)
        if result:  # Type guard for mypy
            self.assertEqual(result.file_id, self.transaction_file.file_id)

    @patch('utils.db_utils.get_transactions_table')
    def test_list_file_transactions(self, mock_get_table):
        """Test listing transactions for a file."""
        # Setup
        mock_get_table.return_value = self.mock_transactions_table
        self.mock_transactions_table.query.return_value = {
            'Items': [self.transaction.to_dict()]
        }

        # Execute
        results = list_file_transactions(self.file_id)

        # Verify
        self.mock_transactions_table.query.assert_called_with(
            IndexName='FileIdIndex',
            KeyConditionExpression=Key('fileId').eq(self.file_id)
        )
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Transaction)
        self.assertEqual(results[0].file_id, self.file_id)

    @patch('utils.db_utils.get_file_maps_table')
    def test_get_file_map(self, mock_get_table):
        """Test retrieving a file map."""
        # Setup
        mock_get_table.return_value = self.mock_file_maps_table
        self.mock_file_maps_table.get_item.return_value = {
            'Item': self.file_map.to_dict()
        }

        # Execute
        result = get_file_map(self.file_map_id)

        # Verify
        self.mock_file_maps_table.get_item.assert_called_with(
            Key={'fileMapId': self.file_map_id}
        )
        self.assertIsNotNone(result)
        self.assertIsInstance(result, FileMap)
        if result:  # Type guard for mypy
            self.assertEqual(result.file_map_id, self.file_map.file_map_id)

    @patch('utils.db_utils.get_transaction_by_account_and_hash')
    def test_check_duplicate_transaction(self, mock_get_transaction):
        """Test checking for duplicate transactions."""
        # Setup
        mock_get_transaction.return_value = None

        # Execute
        result = check_duplicate_transaction(self.transaction)

        # Verify
        self.assertFalse(result)
        mock_get_transaction.assert_called_with(
            self.transaction.account_id,
            self.transaction.transaction_hash
        )

    @patch('utils.db_utils.get_transaction_file')
    @patch('utils.db_utils.delete_transactions_for_file')
    @patch('utils.db_utils.get_files_table')
    def test_delete_transaction_file(self, mock_get_table, mock_delete_transactions, mock_get_file):
        """Test deleting a transaction file."""
        # Setup
        mock_get_table.return_value = self.mock_files_table
        mock_get_file.return_value = self.transaction_file
        mock_delete_transactions.return_value = 1

        # Execute
        result = delete_transaction_file(self.file_id)

        # Verify
        self.assertTrue(result)
        mock_delete_transactions.assert_called_with(self.file_id)
        self.mock_files_table.delete_item.assert_called_with(
            Key={'fileId': self.file_id}
        )

    @patch('utils.db_utils.get_transactions_table')
    def test_create_transaction(self, mock_get_table):
        """Test creating a transaction."""
        # Setup
        mock_get_table.return_value = self.mock_transactions_table

        # Execute
        result = create_transaction(self.transaction)

        # Verify
        self.mock_transactions_table.put_item.assert_called_with(
            Item=self.transaction.to_dict()
        )
        self.assertEqual(result, self.transaction)

if __name__ == '__main__':
    unittest.main() 