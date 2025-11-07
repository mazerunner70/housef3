"""
Test for Transaction enum conversion issues in from_dynamodb_item().

This test reproduces the bug where Transaction.from_dynamodb_item() 
was using model_validate() instead of model_construct(), causing
enum objects to be converted back to strings due to use_enum_values=True.
"""
import uuid
from decimal import Decimal
from typing import Dict, Any

from pydantic import ValidationError
import pytest

from models.transaction import Transaction, TransactionCategoryAssignment, CategoryAssignmentStatus
from models.money import Currency


def create_mock_dynamodb_transaction_data() -> Dict[str, Any]:
    """Create mock DynamoDB transaction data with string enum values."""
    return {
        'transactionId': str(uuid.uuid4()),
        'accountId': str(uuid.uuid4()),
        'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
        'date': 1733875200000,
        'description': 'PAYPAL PAYMENT',
        'amount': Decimal('-23.26'),
        'currency': 'GBP',  # String value from DynamoDB
        'balance': Decimal('69.04'),
        'importOrder': 94,
        'status': 'new',  # String value from DynamoDB
        'statusDate': 'new#1733875200000',
        'transactionHash': 6786073888423522706,
        'categories': [],
        'createdAt': 1749992863526,
        'updatedAt': 1749992863526,
        'fileId': str(uuid.uuid4())
    }


def create_mock_dynamodb_transaction_with_categories() -> Dict[str, Any]:
    """Create mock DynamoDB transaction data with category assignments."""
    base_data = create_mock_dynamodb_transaction_data()
    base_data['categories'] = [
        {
            'categoryId': str(uuid.uuid4()),
            'status': 'suggested',  # String enum value from DynamoDB
            'confidence': 85,
            'assignedAt': 1749992863526,
            'isManual': False
        }
    ]
    base_data['primaryCategoryId'] = base_data['categories'][0]['categoryId']
    return base_data


class TestTransactionEnumConversion:
    """Test Transaction enum conversion in from_dynamodb_item()."""

    def test_transaction_from_dynamodb_preserves_enum_objects(self):
        """
        Test that Transaction.from_dynamodb_item() preserves enum objects.
        
        This test verifies that:
        1. Currency enum objects are preserved (not converted to strings)
        2. .value attribute access works without AttributeError
        3. Enum type checking works correctly
        """
        # Arrange: Mock DynamoDB data with string enum values
        dynamodb_data = create_mock_dynamodb_transaction_data()
        
        # Act: Convert using from_dynamodb_item
        transaction = Transaction.from_dynamodb_item(dynamodb_data)
        
        # Assert: Currency should be an actual enum object, not a string
        assert transaction.currency is not None, "Currency should not be None"
        assert isinstance(transaction.currency, Currency), f"Expected Currency enum, got {type(transaction.currency)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            currency_value = transaction.currency.value
            assert currency_value == 'GBP', f"Expected 'GBP', got {currency_value}"
        except AttributeError as e:
            pytest.fail(f"Currency enum should have .value attribute: {e}")
        
        # Use type checking for string-based enums (Currency inherits from str)
        assert type(transaction.currency).__name__ == 'Currency', \
            f"Expected Currency type, got {type(transaction.currency).__name__}"

    def test_transaction_category_assignments_preserve_enum_objects(self):
        """
        Test that category assignments preserve enum objects.
        
        This test verifies CategoryAssignmentStatus enums are preserved.
        """
        # Arrange: Mock DynamoDB data with category assignments
        dynamodb_data = create_mock_dynamodb_transaction_with_categories()
        
        # Act: Convert using from_dynamodb_item
        transaction = Transaction.from_dynamodb_item(dynamodb_data)
        
        # Assert: Should have one category assignment
        assert len(transaction.categories) == 1, "Should have one category assignment"
        
        category_assignment = transaction.categories[0]
        assert isinstance(category_assignment, TransactionCategoryAssignment), \
            "Should be TransactionCategoryAssignment object"
        
        # Critical test: Status should be an enum object, not a string
        assert isinstance(category_assignment.status, CategoryAssignmentStatus), \
            f"Expected CategoryAssignmentStatus enum, got {type(category_assignment.status)}"
        
        # Critical test: .value attribute should work without AttributeError
        try:
            status_value = category_assignment.status.value
            assert status_value == 'suggested', f"Expected 'suggested', got {status_value}"
        except AttributeError as e:
            pytest.fail(f"CategoryAssignmentStatus enum should have .value attribute: {e}")
        
        # Use type checking for string-based enums
        assert type(category_assignment.status).__name__ == 'CategoryAssignmentStatus', \
            f"Expected CategoryAssignmentStatus type, got {type(category_assignment.status).__name__}"

    def test_transaction_handles_none_currency(self):
        """Test that Transaction handles None currency correctly."""
        # Arrange: Mock DynamoDB data without currency
        dynamodb_data = create_mock_dynamodb_transaction_data()
        del dynamodb_data['currency']  # Remove currency field
        
        # Act: Convert using from_dynamodb_item
        transaction = Transaction.from_dynamodb_item(dynamodb_data)
        
        # Assert: Currency should be None (not cause enum conversion errors)
        assert transaction.currency is None, "Currency should be None when not provided"

    def test_transaction_handles_optional_fields(self):
        """Test that Transaction handles all optional fields correctly."""
        # Arrange: Mock DynamoDB data with minimal required fields
        minimal_data = {
            'transactionId': str(uuid.uuid4()),
            'accountId': str(uuid.uuid4()),
            'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
            'fileId': str(uuid.uuid4()),  # Required field
            'date': 1733875200000,
            'description': 'TEST TRANSACTION',
            'amount': Decimal('100.00'),
            'categories': []
        }
        
        # Act: Convert using from_dynamodb_item
        transaction = Transaction.from_dynamodb_item(minimal_data)
        
        # Assert: Should create transaction successfully
        assert transaction.transaction_id is not None
        assert transaction.description == 'TEST TRANSACTION'
        assert transaction.amount == Decimal('100.00')
        assert transaction.currency is None  # Optional field
        assert transaction.balance is None   # Optional field
        assert len(transaction.categories) == 0

    def test_enum_conversion_with_model_validate_vs_model_construct(self):
        """
        Demonstrate the difference between model_validate and model_construct.
        
        This test shows why model_construct is necessary when use_enum_values=True.
        """
        # Arrange: Create a Currency enum object
        currency_enum = Currency('GBP')
        data_with_enum = {
            'transactionId': str(uuid.uuid4()),
            'accountId': str(uuid.uuid4()),
            'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
            'fileId': str(uuid.uuid4()),  # Required field
            'date': 1733875200000,
            'description': 'TEST',
            'amount': Decimal('100.00'),
            'currency': currency_enum,  # Already an enum object
            'categories': []
        }
        
        # Act & Assert: model_construct preserves enum objects
        transaction_construct = Transaction.model_construct(**data_with_enum)
        assert isinstance(transaction_construct.currency, Currency), \
            "model_construct should preserve enum objects"
        assert transaction_construct.currency.value == 'GBP'
        
        # Act & Assert: model_validate converts enums to strings (due to use_enum_values=True)
        # Note: This would cause issues in the old code
        transaction_validate = Transaction.model_validate(data_with_enum)
        # With use_enum_values=True, this might convert the enum back to string internally
        # but the field validator should convert it back to enum
        assert isinstance(transaction_validate.currency, Currency), \
            "Field validator should convert back to enum"


def test_transaction_uuid_fields_conversion_from_dynamodb():
    """Test that Transaction.from_dynamodb_item converts UUID string fields to proper UUID objects."""
    # Create mock data with string UUID values like DynamoDB stores
    transaction_id_str = 'a529f328-46ca-4317-aae8-42b7f5b7418f'
    account_id_str = '683f1901-22e8-48ad-bf52-6b148be3c8ee'
    file_id_str = '5d127560-106f-477f-90cf-091594ff8645'
    primary_category_id_str = '1d735469-15a4-4ade-afb7-745080399219'
    
    mock_data = {
        'transactionId': transaction_id_str,  # String from DynamoDB
        'accountId': account_id_str,         # String from DynamoDB
        'fileId': file_id_str,               # String from DynamoDB
        'primaryCategoryId': primary_category_id_str,  # String from DynamoDB
        'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
        'date': 1733875200000,
        'description': 'TEST TRANSACTION',
        'amount': Decimal('-23.26'),
        'currency': 'GBP',
        'categories': [],
        'createdAt': 1749992863526,
        'updatedAt': 1749992863526
    }
    
    # Convert using from_dynamodb_item
    transaction = Transaction.from_dynamodb_item(mock_data)
    
    # Verify all UUID fields are converted to actual UUID objects, not strings
    assert isinstance(transaction.transaction_id, uuid.UUID)
    assert isinstance(transaction.account_id, uuid.UUID)
    assert isinstance(transaction.file_id, uuid.UUID)
    assert isinstance(transaction.primary_category_id, uuid.UUID)
    
    # Verify the UUID values match the original strings
    assert str(transaction.transaction_id) == transaction_id_str
    assert str(transaction.account_id) == account_id_str
    assert str(transaction.file_id) == file_id_str
    assert str(transaction.primary_category_id) == primary_category_id_str
    
    # Test that model_dump with mode='json' serialization works correctly
    # This is the issue - model_dump() without mode='json' returns UUID objects
    serialized_python = transaction.model_dump(by_alias=True)
    serialized_json = transaction.model_dump(by_alias=True, mode='json')
    
    # Without mode='json', UUID fields remain as UUID objects (problematic)
    assert isinstance(serialized_python['transactionId'], uuid.UUID)
    assert isinstance(serialized_python['accountId'], uuid.UUID)
    
    # With mode='json', UUID fields are properly converted to strings
    assert isinstance(serialized_json['transactionId'], str)
    assert isinstance(serialized_json['accountId'], str)
    assert serialized_json['transactionId'] == transaction_id_str
    assert serialized_json['accountId'] == account_id_str
    assert serialized_json['fileId'] == file_id_str
    assert serialized_json['primaryCategoryId'] == primary_category_id_str


def test_transaction_uuid_fields_with_invalid_uuids():
    """Test that Transaction.from_dynamodb_item properly validates and rejects invalid UUID strings."""
    mock_data = {
        'transactionId': 'invalid-uuid-string',  # Invalid UUID
        'accountId': '683f1901-22e8-48ad-bf52-6b148be3c8ee',  # Valid UUID
        'fileId': '',  # Empty string
        'primaryCategoryId': None,  # None value
        'userId': 'd6d21224-5041-704e-9705-0e9a48538059',
        'date': 1733875200000,
        'description': 'TEST TRANSACTION',
        'amount': Decimal('-23.26'),
        'categories': [],
        'createdAt': 1749992863526,
        'updatedAt': 1749992863526
    }
    
    # Should raise ValidationError for invalid UUIDs - this is proper early validation
    with pytest.raises(ValidationError) as exc_info:
        Transaction.from_dynamodb_item(mock_data)
    
    # Verify it's a UUID validation error
    error_str = str(exc_info.value)
    assert 'transactionId' in error_str or 'fileId' in error_str, \
        "ValidationError should mention the invalid UUID field"


if __name__ == "__main__":
    # Run the specific test
    pytest.main([__file__, "-v"])
