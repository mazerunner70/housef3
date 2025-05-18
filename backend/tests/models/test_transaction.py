import unittest
from decimal import Decimal
from datetime import datetime
import uuid
import json

from models.transaction import Transaction, validate_transaction_data, transaction_to_json
from models.money import Money, Currency

class TestTransaction(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = str(uuid.uuid4())
        self.file_id = str(uuid.uuid4())
        self.account_id = str(uuid.uuid4())
        self.transaction_id = str(uuid.uuid4())
        self.date = int(datetime.now().timestamp() * 1000)  # milliseconds since epoch
        self.description = "Test transaction"
        self.amount = Money(Decimal("100.50"), Currency.USD)
        self.balance = Money(Decimal("1000.00"), Currency.USD)

        # Create a sample transaction
        self.transaction = Transaction(
            user_id=self.user_id,
            file_id=self.file_id,
            transaction_id=self.transaction_id,
            account_id=self.account_id,
            date=self.date,
            description=self.description,
            amount=self.amount,
            balance=self.balance
        )

    def test_transaction_creation(self):
        """Test basic transaction creation."""
        self.assertEqual(self.transaction.user_id, self.user_id)
        self.assertEqual(self.transaction.file_id, self.file_id)
        self.assertEqual(self.transaction.transaction_id, self.transaction_id)
        self.assertEqual(self.transaction.account_id, self.account_id)
        self.assertEqual(self.transaction.date, self.date)
        self.assertEqual(self.transaction.description, self.description)
        self.assertEqual(self.transaction.amount, self.amount)
        self.assertEqual(self.transaction.balance, self.balance)
        self.assertIsNotNone(self.transaction.transaction_hash)

    def test_transaction_hash_generation(self):
        """Test that transaction hash is generated correctly."""
        # Create two transactions with same core data
        tx1 = Transaction.create(
            account_id=self.account_id,
            user_id=self.user_id,
            file_id=self.file_id,
            date=self.date,
            description=self.description,
            amount=self.amount
        )
        
        tx2 = Transaction.create(
            account_id=self.account_id,
            user_id=self.user_id,
            file_id=self.file_id,
            date=self.date,
            description=self.description,
            amount=self.amount
        )

        # Hashes should be equal even though transaction_ids are different
        self.assertEqual(tx1.transaction_hash, tx2.transaction_hash)
        self.assertNotEqual(tx1.transaction_id, tx2.transaction_id)

    def test_hash_regeneration_on_field_change(self):
        """Test that hash is regenerated when core fields change."""
        original_hash = self.transaction.transaction_hash
        
        # Change description
        self.transaction.description = "Updated description"
        self.assertNotEqual(self.transaction.transaction_hash, original_hash)
        
        # Change amount
        self.transaction.amount = Money(Decimal("200.00"), Currency.USD)
        self.assertNotEqual(self.transaction.transaction_hash, original_hash)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        tx_dict = self.transaction.to_dict()
        
        self.assertEqual(tx_dict["userId"], self.user_id)
        self.assertEqual(tx_dict["fileId"], self.file_id)
        self.assertEqual(tx_dict["transactionId"], self.transaction_id)
        self.assertEqual(tx_dict["accountId"], self.account_id)
        self.assertEqual(tx_dict["date"], self.date)
        self.assertEqual(tx_dict["description"], self.description)
        self.assertEqual(tx_dict["amount"]["amount"], str(self.amount.amount))
        self.assertEqual(tx_dict["amount"]["currency"], self.amount.currency.value)

    def test_from_dict(self):
        """Test creation from dictionary."""
        tx_dict = self.transaction.to_dict()
        new_tx = Transaction.from_dict(tx_dict)
        
        self.assertEqual(new_tx.user_id, self.user_id)
        self.assertEqual(new_tx.file_id, self.file_id)
        self.assertEqual(new_tx.transaction_id, self.transaction_id)
        self.assertEqual(new_tx.account_id, self.account_id)
        self.assertEqual(new_tx.date, self.date)
        self.assertEqual(new_tx.description, self.description)
        self.assertEqual(new_tx.amount, self.amount)
        self.assertEqual(new_tx.transaction_hash, self.transaction.transaction_hash)

    def test_validate_transaction_data(self):
        """Test transaction data validation."""
        # Valid data
        valid_data = {
            "userId": str(uuid.uuid4()),
            "fileId": str(uuid.uuid4()),
            "accountId": str(uuid.uuid4()),
            "transactionId": str(uuid.uuid4()),
            "date": int(datetime.now().timestamp() * 1000),
            "description": "Test transaction",
            "amount": {"amount": "100.50", "currency": "USD"}
        }
        self.assertTrue(validate_transaction_data(valid_data))

        # Test missing required field
        invalid_data = valid_data.copy()
        del invalid_data["description"]
        with self.assertRaises(ValueError):
            validate_transaction_data(invalid_data)

        # Test invalid date
        invalid_data = valid_data.copy()
        invalid_data["date"] = -1
        with self.assertRaises(ValueError):
            validate_transaction_data(invalid_data)

        # Test invalid amount structure
        invalid_data = valid_data.copy()
        invalid_data["amount"] = {"invalid": "structure"}
        with self.assertRaises(ValueError):
            validate_transaction_data(invalid_data)

    def test_transaction_to_json(self):
        """Test JSON serialization."""
        # Test with Transaction object
        json_str = transaction_to_json(self.transaction)
        data = json.loads(json_str)
        
        self.assertEqual(data["userId"], self.user_id)
        self.assertEqual(data["amount"]["amount"], str(self.amount.amount))
        
        # Test with dictionary
        tx_dict = self.transaction.to_dict()
        json_str = transaction_to_json(tx_dict)
        data = json.loads(json_str)
        
        self.assertEqual(data["userId"], self.user_id)
        self.assertEqual(data["amount"]["amount"], str(self.amount.amount))

    def test_optional_fields(self):
        """Test transaction with optional fields."""
        tx = Transaction.create(
            account_id=self.account_id,
            user_id=self.user_id,
            file_id=self.file_id,
            date=self.date,
            description=self.description,
            amount=self.amount,
            memo="Test memo",
            check_number="1234",
            transaction_type="DEBIT",
            status="PENDING"
        )
        
        self.assertEqual(tx.memo, "Test memo")
        self.assertEqual(tx.check_number, "1234")
        self.assertEqual(tx.transaction_type, "DEBIT")
        self.assertEqual(tx.status, "PENDING")

    def test_class_level_access(self):
        """Test that accessing fields at class level raises AttributeError."""
        with self.assertRaises(AttributeError):
            _ = Transaction.amount

        with self.assertRaises(AttributeError):
            _ = Transaction.date

        with self.assertRaises(AttributeError):
            _ = Transaction.description

if __name__ == '__main__':
    unittest.main() 