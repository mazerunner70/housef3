import unittest
from decimal import Decimal
from datetime import datetime
from models.account import Currency
from models.transaction import Transaction, Money

class TestTransaction(unittest.TestCase):
    """Test cases for the Transaction class."""

    def setUp(self):
        """Set up test data."""
        self.test_transaction = Transaction(
            transaction_id='test-tx-id',
            user_id='test-user-id',
            file_id='test-file-id',
            account_id='test-account-id',
            date=1716076800000,  # 2024-05-19 00:00:00
            description='Test Transaction',
            amount=Money(amount=Decimal('100.00'), currency=Currency.USD),
            balance=Money(amount=Decimal('1000.00'), currency=Currency.USD),
            import_order=1,
            transaction_type='DEBIT',
            memo='Test memo',
            check_number='123',
            fit_id='fit123',
            status='new'
        )

    def test_transaction_initialization(self):
        """Test that a transaction is initialized correctly."""
        self.assertEqual(self.test_transaction.transaction_id, 'test-tx-id')
        self.assertEqual(self.test_transaction.user_id, 'test-user-id')
        self.assertEqual(self.test_transaction.file_id, 'test-file-id')
        self.assertEqual(self.test_transaction.account_id, 'test-account-id')
        self.assertEqual(self.test_transaction.date, 1716076800000)
        self.assertEqual(self.test_transaction.description, 'Test Transaction')
        self.assertEqual(self.test_transaction.amount.amount, Decimal('100.00'))
        self.assertEqual(self.test_transaction.amount.currency, Currency.USD)
        self.assertEqual(self.test_transaction.balance.amount, Decimal('1000.00'))
        self.assertEqual(self.test_transaction.import_order, 1)
        self.assertEqual(self.test_transaction.transaction_type, 'DEBIT')
        self.assertEqual(self.test_transaction.memo, 'Test memo')
        self.assertEqual(self.test_transaction.check_number, '123')
        self.assertEqual(self.test_transaction.fit_id, 'fit123')
        self.assertEqual(self.test_transaction.status, 'new')

    def test_transaction_field_updates(self):
        """Test that field updates work correctly and trigger hash regeneration."""
        initial_hash = self.test_transaction.transaction_hash
        
        # Update fields
        self.test_transaction.account_id = 'new-account-id'
        self.test_transaction.date = 1716163200000  # 2024-05-20 00:00:00
        self.test_transaction.description = 'New Description'
        self.test_transaction.amount = Money(amount=Decimal('200.00'), currency=Currency.USD)
        
        # Verify updates
        self.assertEqual(self.test_transaction.account_id, 'new-account-id')
        self.assertEqual(self.test_transaction.date, 1716163200000)
        self.assertEqual(self.test_transaction.description, 'New Description')
        self.assertEqual(self.test_transaction.amount.amount, Decimal('200.00'))
        self.assertEqual(self.test_transaction.amount.currency, Currency.USD)
        
        # Verify hash was regenerated
        self.assertNotEqual(self.test_transaction.transaction_hash, initial_hash)

    def test_transaction_create_method(self):
        """Test the create class method."""
        transaction = Transaction.create(
            account_id='new-account',
            user_id='new-user',
            file_id='new-file',
            date=1716076800000,
            description='New Transaction',
            amount=Money(amount=Decimal('150.00'), currency=Currency.USD),
            balance=Money(amount=Decimal('1150.00'), currency=Currency.USD),
            import_order=2,
            transaction_type='CREDIT',
            memo='New memo',
            check_number='456',
            fit_id='fit456',
            status='pending'
        )

        # Verify required fields
        self.assertIsNotNone(transaction.transaction_id)  # Should be auto-generated
        self.assertEqual(transaction.account_id, 'new-account')
        self.assertEqual(transaction.user_id, 'new-user')
        self.assertEqual(transaction.file_id, 'new-file')
        self.assertEqual(transaction.date, 1716076800000)
        self.assertEqual(transaction.description, 'New Transaction')
        self.assertEqual(transaction.amount.amount, Decimal('150.00'))

        # Verify optional fields
        self.assertEqual(transaction.balance.amount, Decimal('1150.00'))
        self.assertEqual(transaction.import_order, 2)
        self.assertEqual(transaction.transaction_type, 'CREDIT')
        self.assertEqual(transaction.memo, 'New memo')
        self.assertEqual(transaction.check_number, '456')
        self.assertEqual(transaction.fit_id, 'fit456')
        self.assertEqual(transaction.status, 'pending')

    def test_transaction_to_dict(self):
        """Test conversion to dictionary."""
        tx_dict = self.test_transaction.to_dict()
        
        # Verify required fields
        self.assertEqual(tx_dict['transactionId'], 'test-tx-id')
        self.assertEqual(tx_dict['accountId'], 'test-account-id')
        self.assertEqual(tx_dict['fileId'], 'test-file-id')
        self.assertEqual(tx_dict['userId'], 'test-user-id')
        self.assertEqual(tx_dict['date'], 1716076800000)
        self.assertEqual(tx_dict['description'], 'Test Transaction')
        self.assertEqual(tx_dict['amount']['amount'], '100.00')
        self.assertEqual(tx_dict['amount']['currency'], 'USD')

        # Verify optional fields
        self.assertEqual(tx_dict['balance']['amount'], '1000.00')
        self.assertEqual(tx_dict['balance']['currency'], Currency.USD)
        self.assertEqual(tx_dict['importOrder'], 1)
        self.assertEqual(tx_dict['transactionType'], 'DEBIT')
        self.assertEqual(tx_dict['memo'], 'Test memo')
        self.assertEqual(tx_dict['checkNumber'], '123')
        self.assertEqual(tx_dict['fitId'], 'fit123')
        self.assertEqual(tx_dict['status'], 'new')

    def test_transaction_from_dict(self):
        """Test creation from dictionary."""
        tx_dict = {
            'transactionId': 'dict-tx-id',
            'accountId': 'dict-account-id',
            'fileId': 'dict-file-id',
            'userId': 'dict-user-id',
            'date': 1716076800000,
            'description': 'Dict Transaction',
            'amount': {'amount': '150.00', 'currency': Currency.USD},
            'balance': {'amount': '1150.00', 'currency': Currency.USD},
            'importOrder': 3,
            'transactionType': 'CREDIT',
            'memo': 'Dict memo',
            'checkNumber': '789',
            'fitId': 'fit789',
            'status': 'completed',
            'createdAt': 1716076800000,
            'updatedAt': 1716163200000
        }
        
        transaction = Transaction.from_dict(tx_dict)
        
        # Verify required fields
        self.assertEqual(transaction.transaction_id, 'dict-tx-id')
        self.assertEqual(transaction.account_id, 'dict-account-id')
        self.assertEqual(transaction.file_id, 'dict-file-id')
        self.assertEqual(transaction.user_id, 'dict-user-id')
        self.assertEqual(transaction.date, 1716076800000)
        self.assertEqual(transaction.description, 'Dict Transaction')
        self.assertEqual(transaction.amount.amount, Decimal('150.00'))
        self.assertEqual(transaction.amount.currency, Currency.USD)

        # Verify optional fields
        self.assertEqual(transaction.balance.amount, Decimal('1150.00'))
        self.assertEqual(transaction.balance.currency, Currency.USD)
        self.assertEqual(transaction.import_order, 3)
        self.assertEqual(transaction.transaction_type, 'CREDIT')
        self.assertEqual(transaction.memo, 'Dict memo')
        self.assertEqual(transaction.check_number, '789')
        self.assertEqual(transaction.fit_id, 'fit789')
        self.assertEqual(transaction.status, 'completed')
        self.assertEqual(transaction.created_at, 1716076800000)
        self.assertEqual(transaction.updated_at, 1716163200000)

if __name__ == '__main__':
    unittest.main() 