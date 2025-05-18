import unittest
from decimal import Decimal
from datetime import datetime
import uuid
import json

from models.account import (
    Account,
    AccountType,
    validate_account_data
)
from models.money import Money, Currency


class TestAccount(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.account_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.account_name = "Test Checking Account"
        self.account_type = AccountType.CHECKING
        self.institution = "Test Bank"
        self.balance = Money(Decimal("1000.50"), Currency.USD)
        self.currency = Currency.USD
        self.notes = "Test account notes"
        self.default_file_map_id = str(uuid.uuid4())
        
        # Create a sample account
        self.account = Account(
            account_id=self.account_id,
            user_id=self.user_id,
            account_name=self.account_name,
            account_type=self.account_type,
            institution=self.institution,
            balance=self.balance,
            currency=self.currency,
            notes=self.notes,
            is_active=True,
            default_file_map_id=self.default_file_map_id
        )

    def test_account_type_enum(self):
        """Test AccountType enum values."""
        self.assertEqual(AccountType.CHECKING.value, "checking")
        self.assertEqual(AccountType.SAVINGS.value, "savings")
        self.assertEqual(AccountType.CREDIT_CARD.value, "credit_card")
        self.assertEqual(AccountType.INVESTMENT.value, "investment")
        self.assertEqual(AccountType.LOAN.value, "loan")
        self.assertEqual(AccountType.OTHER.value, "other")

    def test_account_creation(self):
        """Test basic account creation."""
        self.assertEqual(self.account.account_id, self.account_id)
        self.assertEqual(self.account.user_id, self.user_id)
        self.assertEqual(self.account.account_name, self.account_name)
        self.assertEqual(self.account.account_type, self.account_type)
        self.assertEqual(self.account.institution, self.institution)
        self.assertEqual(self.account.balance, self.balance)
        self.assertEqual(self.account.currency, self.currency)
        self.assertEqual(self.account.notes, self.notes)
        self.assertTrue(self.account.is_active)
        self.assertEqual(self.account.default_file_map_id, self.default_file_map_id)
        self.assertIsNotNone(self.account.created_at)
        self.assertIsNotNone(self.account.updated_at)

    def test_account_create_method(self):
        """Test Account.create class method."""
        account = Account.create(
            user_id=self.user_id,
            account_name=self.account_name,
            account_type=self.account_type,
            institution=self.institution,
            balance=float(self.balance.amount),
            currency=self.currency,
            notes=self.notes,
            default_file_map_id=self.default_file_map_id
        )
        
        self.assertIsInstance(account, Account)
        self.assertIsNotNone(account.account_id)
        self.assertEqual(account.user_id, self.user_id)
        self.assertEqual(account.account_name, self.account_name)
        self.assertEqual(account.account_type, self.account_type)
        self.assertEqual(account.institution, self.institution)
        self.assertEqual(account.balance.amount, self.balance.amount)
        self.assertEqual(account.currency, self.currency)
        self.assertEqual(account.notes, self.notes)
        self.assertTrue(account.is_active)
        self.assertEqual(account.default_file_map_id, self.default_file_map_id)

    def test_account_create_with_defaults(self):
        """Test Account.create with default values."""
        account = Account.create(
            user_id=self.user_id,
            account_name=self.account_name,
            account_type=self.account_type,
            institution=self.institution
        )
        
        self.assertEqual(account.balance.amount, Decimal("0.0"))
        self.assertEqual(account.currency, Currency.USD)
        self.assertIsNone(account.notes)
        self.assertTrue(account.is_active)
        self.assertIsNone(account.default_file_map_id)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        account_dict = self.account.to_dict()
        
        self.assertEqual(account_dict["accountId"], self.account_id)
        self.assertEqual(account_dict["userId"], self.user_id)
        self.assertEqual(account_dict["accountName"], self.account_name)
        self.assertEqual(account_dict["accountType"], self.account_type.value)
        self.assertEqual(account_dict["institution"], self.institution)
        self.assertEqual(account_dict["balance"]["amount"], str(self.balance.amount))
        self.assertEqual(account_dict["balance"]["currency"], self.balance.currency.value)
        self.assertEqual(account_dict["currency"], self.currency.value)
        self.assertEqual(account_dict["notes"], self.notes)
        self.assertTrue(account_dict["isActive"])
        self.assertEqual(account_dict["defaultFileMapId"], self.default_file_map_id)
        self.assertIn("createdAt", account_dict)
        self.assertIn("updatedAt", account_dict)

    def test_from_dict(self):
        """Test creation from dictionary."""
        account_dict = self.account.to_dict()
        new_account = Account.from_dict(account_dict)
        
        self.assertEqual(new_account.account_id, self.account_id)
        self.assertEqual(new_account.user_id, self.user_id)
        self.assertEqual(new_account.account_name, self.account_name)
        self.assertEqual(new_account.account_type, self.account_type)
        self.assertEqual(new_account.institution, self.institution)
        self.assertEqual(new_account.balance, self.balance)
        self.assertEqual(new_account.currency, self.currency)
        self.assertEqual(new_account.notes, self.notes)
        self.assertTrue(new_account.is_active)
        self.assertEqual(new_account.default_file_map_id, self.default_file_map_id)
        self.assertEqual(new_account.created_at, self.account.created_at)
        self.assertEqual(new_account.updated_at, self.account.updated_at)

    def test_update(self):
        """Test updating account fields."""
        new_name = "Updated Account"
        new_balance = Money(Decimal("2000.00"), Currency.USD)
        new_notes = "Updated notes"
        
        original_updated_at = self.account.updated_at
        self.account.update(
            account_name=new_name,
            balance=new_balance,
            notes=new_notes,
            is_active=False
        )
        
        self.assertEqual(self.account.account_name, new_name)
        self.assertEqual(self.account.balance, new_balance)
        self.assertEqual(self.account.notes, new_notes)
        self.assertFalse(self.account.is_active)
        self.assertNotEqual(self.account.updated_at, original_updated_at)

    def test_update_protected_fields(self):
        """Test that protected fields cannot be updated."""
        original_id = self.account.account_id
        original_user_id = self.account.user_id
        original_created_at = self.account.created_at
        
        self.account.update(
            account_id="new_id",
            user_id="new_user_id",
            created_at="new_timestamp"
        )
        
        self.assertEqual(self.account.account_id, original_id)
        self.assertEqual(self.account.user_id, original_user_id)
        self.assertEqual(self.account.created_at, original_created_at)

    def test_validate_account_data(self):
        """Test account data validation."""
        # Test valid data
        valid_data = {
            "accountName": self.account_name,
            "accountType": self.account_type.value,
            "institution": self.institution,
            "userId": self.user_id,
            "balance": str(self.balance.amount),
            "currency": self.currency.value
        }
        self.assertTrue(validate_account_data(valid_data))
        
        # Test missing required field
        invalid_data = valid_data.copy()
        del invalid_data["accountName"]
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Missing required field: accountName", str(cm.exception))
        
        # Test invalid account type
        invalid_data = valid_data.copy()
        invalid_data["accountType"] = "invalid_type"
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Invalid account type", str(cm.exception))
        
        # Test invalid currency
        invalid_data = valid_data.copy()
        invalid_data["currency"] = "INVALID"
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Invalid currency", str(cm.exception))
        
        # Test invalid balance
        invalid_data = valid_data.copy()
        invalid_data["balance"] = "not_a_number"
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Balance must be a valid number", str(cm.exception))

    def test_string_field_length_validation(self):
        """Test validation of string field lengths."""
        # Test account name too long
        invalid_data = {
            "accountName": "a" * 101,  # Exceeds 100 character limit
            "accountType": self.account_type.value,
            "institution": self.institution,
            "userId": self.user_id
        }
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Account name must be 100 characters or less", str(cm.exception))
        
        # Test institution name too long
        invalid_data = {
            "accountName": self.account_name,
            "accountType": self.account_type.value,
            "institution": "a" * 101,  # Exceeds 100 character limit
            "userId": self.user_id
        }
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Institution name must be 100 characters or less", str(cm.exception))
        
        # Test notes too long
        invalid_data = {
            "accountName": self.account_name,
            "accountType": self.account_type.value,
            "institution": self.institution,
            "userId": self.user_id,
            "notes": "a" * 1001  # Exceeds 1000 character limit
        }
        with self.assertRaises(ValueError) as cm:
            validate_account_data(invalid_data)
        self.assertIn("Notes must be 1000 characters or less", str(cm.exception))

    def test_partial_update(self):
        """Test partial update with only some fields."""
        original_name = self.account.account_name
        original_balance = self.account.balance
        
        self.account.update(notes="New notes")
        
        self.assertEqual(self.account.account_name, original_name)
        self.assertEqual(self.account.balance, original_balance)
        self.assertEqual(self.account.notes, "New notes")

if __name__ == '__main__':
    unittest.main() 