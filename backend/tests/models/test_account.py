"""
Test for Account model enum conversion and serialization.

This test verifies that Account.from_dynamodb_item() properly handles
enum conversion for AccountType and Currency fields.
"""
import uuid
from decimal import Decimal
from typing import Dict, Any

import pytest

from models.account import Account, AccountType
from models.money import Currency


def create_mock_dynamodb_account_data() -> Dict[str, Any]:
    """Create mock DynamoDB account data with string enum values."""
    return {
        'accountId': str(uuid.uuid4()),
        'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
        'accountName': 'Test Checking Account',
        'accountType': 'checking',  # String value from DynamoDB
        'institution': 'Test Bank',
        'balance': Decimal('1234.56'),
        'currency': 'USD',  # String value from DynamoDB
        'notes': 'Test account notes',
        'isActive': True,
        'createdAt': 1749992863526,
        'updatedAt': 1749992863526
    }


class TestAccountEnumConversion:
    """Test Account enum conversion in from_dynamodb_item()."""

    def test_account_from_dynamodb_preserves_account_type_enum(self):
        """
        Test that Account.from_dynamodb_item() preserves AccountType enum objects.
        
        This test verifies that:
        1. AccountType enum objects are preserved (not converted to strings)
        2. .value attribute access works without AttributeError
        3. Enum type checking works correctly
        """
        # Arrange: Mock DynamoDB data with string enum values
        dynamodb_data = create_mock_dynamodb_account_data()
        
        # Act: Convert using from_dynamodb_item
        account = Account.from_dynamodb_item(dynamodb_data)
        
        # Assert: AccountType should be an actual enum object, not a string
        assert account.account_type is not None, "AccountType should not be None"
        assert isinstance(account.account_type, AccountType), \
            f"Expected AccountType enum, got {type(account.account_type)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            account_type_value = account.account_type.value
            assert account_type_value == 'checking', f"Expected 'checking', got {account_type_value}"
        except AttributeError as e:
            pytest.fail(f"AccountType enum should have .value attribute: {e}")
        
        # Use type checking for string-based enums (AccountType inherits from str)
        assert type(account.account_type).__name__ == 'AccountType', \
            f"Expected AccountType type, got {type(account.account_type).__name__}"

    def test_account_from_dynamodb_preserves_currency_enum(self):
        """
        Test that Account.from_dynamodb_item() preserves Currency enum objects.
        
        This test verifies that Currency enums are properly converted from strings.
        """
        # Arrange: Mock DynamoDB data with string enum values
        dynamodb_data = create_mock_dynamodb_account_data()
        
        # Act: Convert using from_dynamodb_item
        account = Account.from_dynamodb_item(dynamodb_data)
        
        # Assert: Currency should be an actual enum object, not a string
        assert account.currency is not None, "Currency should not be None"
        assert isinstance(account.currency, Currency), \
            f"Expected Currency enum, got {type(account.currency)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            currency_value = account.currency.value
            assert currency_value == 'USD', f"Expected 'USD', got {currency_value}"
        except AttributeError as e:
            pytest.fail(f"Currency enum should have .value attribute: {e}")
        
        # Use type checking for string-based enums
        assert type(account.currency).__name__ == 'Currency', \
            f"Expected Currency type, got {type(account.currency).__name__}"

    def test_account_handles_none_currency(self):
        """Test that Account handles None currency correctly."""
        # Arrange: Mock DynamoDB data without currency
        dynamodb_data = create_mock_dynamodb_account_data()
        del dynamodb_data['currency']
        del dynamodb_data['balance']  # Remove balance too since it requires currency
        
        # Act: Convert using from_dynamodb_item
        account = Account.from_dynamodb_item(dynamodb_data)
        
        # Assert: Currency should be None (not cause enum conversion errors)
        assert account.currency is None, "Currency should be None when not provided"

    def test_account_roundtrip_serialization(self):
        """
        Test that Account can be serialized to DynamoDB and deserialized back.
        
        This verifies that:
        1. to_dynamodb_item() converts enums to strings
        2. from_dynamodb_item() converts strings back to enums
        3. The roundtrip preserves all data correctly
        """
        # Arrange: Create an account with enum values
        original_account = Account(
            userId='test-user-123',
            accountName='Test Account',
            accountType=AccountType.SAVINGS,  # Enum object
            currency=Currency.EUR,  # Enum object
            balance=Decimal('5000.00'),
            institution='Test Bank'
        )
        
        # Act: Serialize to DynamoDB format
        dynamodb_item = original_account.to_dynamodb_item()
        
        # Assert: DynamoDB item should have string values for enums
        assert isinstance(dynamodb_item['accountType'], str), \
            "DynamoDB item should have string accountType"
        assert dynamodb_item['accountType'] == 'savings'
        assert isinstance(dynamodb_item['currency'], str), \
            "DynamoDB item should have string currency"
        assert dynamodb_item['currency'] == 'EUR'
        
        # Act: Deserialize back from DynamoDB
        deserialized_account = Account.from_dynamodb_item(dynamodb_item)
        
        # Assert: Deserialized account should have enum objects
        assert isinstance(deserialized_account.account_type, AccountType), \
            "Deserialized account should have AccountType enum"
        assert deserialized_account.account_type == AccountType.SAVINGS
        assert isinstance(deserialized_account.currency, Currency), \
            "Deserialized account should have Currency enum"
        assert deserialized_account.currency == Currency.EUR
        
        # Assert: Other fields should match
        assert deserialized_account.account_name == original_account.account_name
        assert deserialized_account.balance == original_account.balance

    def test_account_model_dump_json_serialization(self):
        """
        Test that Account.model_dump() with mode='json' properly serializes enums.
        """
        # Arrange: Create an account with enum values
        account = Account(
            userId='test-user-123',
            accountName='Test Account',
            accountType=AccountType.CREDIT_CARD,
            currency=Currency.GBP,
            balance=Decimal('2500.50')
        )
        
        # Act: Serialize with mode='json'
        json_dict = account.model_dump(by_alias=True, mode='json')
        
        # Assert: Enums should be serialized as strings
        assert isinstance(json_dict['accountType'], str), \
            "JSON serialization should convert enum to string"
        assert json_dict['accountType'] == 'credit_card'
        assert isinstance(json_dict['currency'], str), \
            "JSON serialization should convert currency to string"
        assert json_dict['currency'] == 'GBP'

    def test_account_all_account_types(self):
        """Test that all AccountType enum values work correctly."""
        account_types = [
            AccountType.CHECKING,
            AccountType.SAVINGS,
            AccountType.CREDIT_CARD,
            AccountType.INVESTMENT,
            AccountType.LOAN,
            AccountType.OTHER
        ]
        
        for account_type in account_types:
            # Arrange: Create account with specific type
            account = Account(
                userId='test-user',
                accountName=f'Test {account_type.value}',
                accountType=account_type
            )
            
            # Assert: Enum is preserved
            assert isinstance(account.account_type, AccountType)
            assert account.account_type == account_type
            
            # Act: Serialize and deserialize
            dynamodb_item = account.to_dynamodb_item()
            deserialized = Account.from_dynamodb_item(dynamodb_item)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.account_type, AccountType)
            assert deserialized.account_type == account_type

    def test_account_all_currencies(self):
        """Test that all Currency enum values work correctly."""
        currencies = [
            Currency.USD,
            Currency.EUR,
            Currency.GBP,
            Currency.CAD,
            Currency.JPY,
            Currency.AUD,
            Currency.CHF,
            Currency.CNY,
            Currency.OTHER
        ]
        
        for currency in currencies:
            # Arrange: Create account with specific currency
            account = Account(
                userId='test-user',
                accountName='Test Account',
                accountType=AccountType.CHECKING,
                currency=currency,
                balance=Decimal('1000.00')
            )
            
            # Assert: Enum is preserved
            assert isinstance(account.currency, Currency)
            assert account.currency == currency
            
            # Act: Serialize and deserialize
            dynamodb_item = account.to_dynamodb_item()
            deserialized = Account.from_dynamodb_item(dynamodb_item)
            
            # Assert: Enum is preserved after roundtrip
            assert isinstance(deserialized.currency, Currency)
            assert deserialized.currency == currency


if __name__ == "__main__":
    # Run the specific test
    pytest.main([__file__, "-v"])

