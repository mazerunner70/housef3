import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import json
from pydantic import ValidationError

from models.transaction import (
    Transaction, 
    TransactionCategoryAssignment, 
    CategoryAssignmentStatus,
    TransactionCreate,
    TransactionUpdate,
    transaction_to_json
)
from models.account import Currency


class TestTransactionCategoryAssignment:
    """Test cases for TransactionCategoryAssignment model."""

    def test_create_category_assignment(self):
        """Test creating a category assignment."""
        category_id = uuid.uuid4()
        assignment = TransactionCategoryAssignment(categoryId=category_id)
        
        assert assignment.category_id == category_id
        assert assignment.confidence == 100
        assert assignment.status == CategoryAssignmentStatus.SUGGESTED
        assert assignment.is_manual is False
        assert assignment.assigned_at is not None
        assert assignment.confirmed_at is None
        assert assignment.rule_id is None

    def test_confirm_assignment(self):
        """Test confirming a category assignment."""
        category_id = uuid.uuid4()
        assignment = TransactionCategoryAssignment(categoryId=category_id)
        
        # Initially suggested
        assert assignment.status == CategoryAssignmentStatus.SUGGESTED
        assert assignment.confirmed_at is None
        
        # Confirm the assignment
        assignment.confirm_assignment()
        
        assert assignment.status == CategoryAssignmentStatus.CONFIRMED
        assert assignment.confirmed_at is not None

    def test_to_dynamodb_item(self):
        """Test converting assignment to DynamoDB item format."""
        category_id = uuid.uuid4()
        assignment = TransactionCategoryAssignment(
            categoryId=category_id,
            confidence=80,
            status=CategoryAssignmentStatus.CONFIRMED,
            isManual=True,
            ruleId="rule123"
        )
        
        item = assignment.to_dynamodb_item()
        
        assert item["categoryId"] == str(category_id)
        assert item["confidence"] == 80
        assert item["status"] == "confirmed"
        assert item["isManual"] is True
        assert item["ruleId"] == "rule123"

    def test_from_dynamodb_item(self):
        """Test creating assignment from DynamoDB item."""
        category_id = uuid.uuid4()
        item = {
            "categoryId": str(category_id),
            "confidence": 80,
            "status": "confirmed",
            "isManual": True,
            "assignedAt": 1751743054715,
            "confirmedAt": 1751743054715,
            "ruleId": "rule123"
        }
        
        assignment = TransactionCategoryAssignment.from_dynamodb_item(item)
        
        assert assignment.category_id == category_id
        assert assignment.confidence == 80
        assert assignment.status == CategoryAssignmentStatus.CONFIRMED
        assert assignment.is_manual is True
        assert assignment.assigned_at == 1751743054715
        assert assignment.confirmed_at == 1751743054715
        assert assignment.rule_id == "rule123"

    def test_from_dynamodb_item_enum_conversion(self):
        """Test that enum conversion from DynamoDB strings preserves enum objects and .value access works."""
        category_id = uuid.uuid4()
        # Mock DynamoDB data with string enum values (as they come from DynamoDB)
        item = {
            "categoryId": str(category_id),
            "confidence": 90,
            "status": "suggested",  # String value from DynamoDB
            "isManual": False,
            "assignedAt": 1751743054715,
            "ruleId": "rule456"
        }
        
        # Call the conversion method
        assignment = TransactionCategoryAssignment.from_dynamodb_item(item)
        
        # Verify the result objects are actual enum types (not strings)
        assert isinstance(assignment.status, CategoryAssignmentStatus)
        assert type(assignment.status).__name__ == "CategoryAssignmentStatus"
        
        # Test that .value attribute access works without AttributeError
        assert assignment.status.value == "suggested"
        assert assignment.status == CategoryAssignmentStatus.SUGGESTED
        
        # Test with confirmed status as well
        item_confirmed = item.copy()
        item_confirmed["status"] = "confirmed"
        assignment_confirmed = TransactionCategoryAssignment.from_dynamodb_item(item_confirmed)
        
        assert isinstance(assignment_confirmed.status, CategoryAssignmentStatus)
        assert assignment_confirmed.status.value == "confirmed"
        assert assignment_confirmed.status == CategoryAssignmentStatus.CONFIRMED

    def test_from_dynamodb_item_invalid_enum_value(self):
        """Test that invalid enum values from DynamoDB are properly rejected."""
        category_id = uuid.uuid4()
        item = {
            "categoryId": str(category_id),
            "confidence": 90,
            "status": "invalid_status",  # Invalid enum value
            "isManual": False,
            "assignedAt": 1751743054715
        }
        
        # Should raise ValidationError for invalid enum - proper early validation
        with pytest.raises(ValidationError) as exc_info:
            TransactionCategoryAssignment.from_dynamodb_item(item)
        
        # Verify it's an enum validation error
        assert 'status' in str(exc_info.value)


class TestTransaction:
    """Test cases for Transaction model."""

    def test_create_transaction(self):
        """Test creating a transaction using the create class method."""
        user_id = "test-user-123"
        file_id = uuid.uuid4()
        account_id = uuid.uuid4()
        date = int(datetime.now(timezone.utc).timestamp() * 1000)
        description = "Test transaction"
        amount = Decimal("100.50")
        currency = Currency.USD
        
        create_data = TransactionCreate(
            userId=user_id,
            fileId=file_id,
            accountId=account_id,
            date=date,
            description=description,
            amount=amount,
            currency=currency
        )
        transaction = Transaction.create(create_data)
        
        assert transaction.user_id == user_id
        assert transaction.file_id == file_id
        assert transaction.account_id == account_id
        assert transaction.date == date
        assert transaction.description == description
        assert transaction.amount == amount
        assert transaction.currency == currency
        assert transaction.transaction_id is not None
        assert transaction.created_at is not None
        assert transaction.updated_at is not None
        assert transaction.transaction_hash is not None

    def test_transaction_serialization_with_categories(self):
        """Test transaction serialization with the provided transaction data."""
        # Create the transaction with provided data
        user_id = '2602f254-70f1-7064-c637-fd69dbe4e8b3'
        file_id = uuid.UUID('2c2d3e15-93fd-4144-b9ca-ec11ea705f84')
        transaction_id = uuid.UUID('1d942779-18fe-4b45-b3f6-25e7fcb98a14')
        account_id = uuid.UUID('4fdbd757-53b4-4a58-a2d4-551c2419149a')
        date = 1717632000000
        description = 'SAINSBURYS.CO.UK \tON 05 JUN BCC'
        amount = Decimal('-87.28')
        currency = Currency.GBP
        balance = Decimal('-1907.49')
        import_order = 51
        status = 'new'
        created_at = 1751102003161
        updated_at = 1751102003161
        transaction_hash = 10275845125054951334
        
        # Create the category assignment
        category_id = uuid.UUID('7dc86e92-5450-415a-9b1f-f4ebbc4d7c4c')
        category_assignment = TransactionCategoryAssignment(
            categoryId=category_id,
            confidence=100,
            status=CategoryAssignmentStatus.CONFIRMED,
            isManual=True,
            assignedAt=1751743054715,
            confirmedAt=1751743054715,
            ruleId=None
        )
        
        # Create the transaction
        transaction = Transaction(
            userId=user_id,
            fileId=file_id,
            transactionId=transaction_id,
            accountId=account_id,
            date=date,
            description=description,
            amount=amount,
            currency=currency,
            balance=balance,
            importOrder=import_order,
            status=status,
            createdAt=created_at,
            updatedAt=updated_at,
            transactionHash=transaction_hash,
            categories=[category_assignment],
            primaryCategoryId=category_id
        )
        
        # Test serialization to DynamoDB format
        dynamodb_item = transaction.to_dynamodb_item()
        
        # Verify the basic fields
        assert dynamodb_item['userId'] == user_id
        assert dynamodb_item['fileId'] == str(file_id)
        assert dynamodb_item['transactionId'] == str(transaction_id)
        assert dynamodb_item['accountId'] == str(account_id)
        assert dynamodb_item['date'] == date
        assert dynamodb_item['description'] == description
        assert dynamodb_item['amount'] == amount  # Decimal object is returned as-is
        assert dynamodb_item['currency'] == currency.value
        assert dynamodb_item['balance'] == balance  # Decimal object is returned as-is
        assert dynamodb_item['importOrder'] == import_order
        assert dynamodb_item['status'] == status
        assert dynamodb_item['createdAt'] == created_at
        assert dynamodb_item['updatedAt'] == updated_at
        assert dynamodb_item['transactionHash'] == transaction_hash
        assert dynamodb_item['primaryCategoryId'] == str(category_id)
        
        # Verify category assignments
        assert len(dynamodb_item['categories']) == 1
        category_item = dynamodb_item['categories'][0]
        assert category_item['categoryId'] == str(category_id)
        assert category_item['confidence'] == 100
        assert category_item['status'] == 'confirmed'
        assert category_item['isManual'] is True
        assert category_item['assignedAt'] == 1751743054715
        assert category_item['confirmedAt'] == 1751743054715
        assert 'ruleId' not in category_item  # Should be excluded due to None
        
        # Test JSON serialization
        json_str = transaction_to_json(transaction)
        parsed_json = json.loads(json_str)
        
        # Verify JSON structure
        assert parsed_json['userId'] == user_id
        assert parsed_json['transactionId'] == str(transaction_id)
        assert parsed_json['amount'] == str(amount)
        assert parsed_json['currency'] == currency.value
        assert len(parsed_json['categories']) == 1
        
        # Test deserialization from DynamoDB
        reconstructed = Transaction.from_dynamodb_item(dynamodb_item)
        
        assert reconstructed.user_id == user_id
        assert reconstructed.file_id == file_id
        assert reconstructed.transaction_id == transaction_id
        assert reconstructed.account_id == account_id
        assert reconstructed.date == date
        assert reconstructed.description == description
        assert reconstructed.amount == amount
        assert reconstructed.currency == currency
        assert reconstructed.balance == balance
        assert reconstructed.import_order == import_order
        assert reconstructed.status == status
        assert reconstructed.created_at == created_at
        assert reconstructed.updated_at == updated_at
        assert reconstructed.transaction_hash == transaction_hash
        assert reconstructed.primary_category_id == category_id
        
        # Verify category assignments were reconstructed correctly
        assert len(reconstructed.categories) == 1
        reconstructed_category = reconstructed.categories[0]
        assert reconstructed_category.category_id == category_id
        assert reconstructed_category.confidence == 100
        assert reconstructed_category.status == CategoryAssignmentStatus.CONFIRMED
        assert reconstructed_category.is_manual is True
        assert reconstructed_category.assigned_at == 1751743054715
        assert reconstructed_category.confirmed_at == 1751743054715
        assert reconstructed_category.rule_id is None

    def test_add_category_suggestion(self):
        """Test adding a category suggestion."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        category_id = uuid.uuid4()
        transaction.add_category_suggestion(category_id, confidence=80, rule_id="rule123")
        
        assert len(transaction.categories) == 1
        assignment = transaction.categories[0]
        assert assignment.category_id == category_id
        assert assignment.confidence == 80
        assert assignment.status == CategoryAssignmentStatus.SUGGESTED
        assert assignment.is_manual is False
        assert assignment.rule_id == "rule123"
        assert transaction.needs_category_review is True

    def test_confirm_category_assignment(self):
        """Test confirming a category assignment."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        category_id = uuid.uuid4()
        transaction.add_category_suggestion(category_id, confidence=80)
        
        # Confirm the assignment
        success = transaction.confirm_category_assignment(category_id, set_as_primary=True)
        
        assert success is True
        assert transaction.primary_category_id == category_id
        assignment = transaction.categories[0]
        assert assignment.status == CategoryAssignmentStatus.CONFIRMED
        assert assignment.confirmed_at is not None
        assert transaction.needs_category_review is False

    def test_add_manual_category(self):
        """Test adding a manual category."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        category_id = uuid.uuid4()
        transaction.add_manual_category(category_id, set_as_primary=True)
        
        assert len(transaction.categories) == 1
        assignment = transaction.categories[0]
        assert assignment.category_id == category_id
        assert assignment.confidence == 100
        assert assignment.status == CategoryAssignmentStatus.CONFIRMED
        assert assignment.is_manual is True
        assert assignment.confirmed_at is not None
        assert transaction.primary_category_id == category_id

    def test_remove_category_assignment(self):
        """Test removing a category assignment."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        category_id = uuid.uuid4()
        transaction.add_manual_category(category_id, set_as_primary=True)
        
        # Remove the category
        success = transaction.remove_category_assignment(category_id)
        
        assert success is True
        assert len(transaction.categories) == 0
        assert transaction.primary_category_id is None

    def test_category_properties(self):
        """Test category-related properties."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        suggested_category = uuid.uuid4()
        confirmed_category = uuid.uuid4()
        
        transaction.add_category_suggestion(suggested_category)
        transaction.add_manual_category(confirmed_category, set_as_primary=True)
        
        # Test properties
        assert len(transaction.confirmed_categories) == 1
        assert len(transaction.suggested_categories) == 1
        assert transaction.needs_category_review is True
        assert transaction.manual_category is True
        assert transaction.category_id == confirmed_category

    def test_set_primary_category(self):
        """Test setting a primary category."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        category_id1 = uuid.uuid4()
        category_id2 = uuid.uuid4()
        
        transaction.add_manual_category(category_id1)
        transaction.add_manual_category(category_id2)
        
        # Set primary category
        success = transaction.set_primary_category(category_id2)
        
        assert success is True
        assert transaction.primary_category_id == category_id2

    def test_transaction_hash_recalculation(self):
        """Test that transaction hash is recalculated when key fields change."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        original_hash = transaction.transaction_hash
        
        # Change a key field
        transaction.description = "Updated description"
        
        # Hash should be recalculated
        assert transaction.transaction_hash != original_hash

    def test_transaction_validation(self):
        """Test transaction validation."""
        # Test with valid data
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        assert transaction.user_id == "test-user"
        assert transaction.date == 1717632000000
        assert transaction.amount == Decimal("100.00")
        
        # Test with invalid timestamp
        with pytest.raises(ValueError, match="Timestamp must be a positive integer"):
            invalid_data = TransactionCreate(
                userId="test-user",
                fileId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=-1,  # Invalid negative timestamp
                description="Test transaction",
                amount=Decimal("100.00"),
                currency=Currency.USD
            )
            Transaction.create(invalid_data)


class TestTransactionCreate:
    """Test cases for TransactionCreate model."""

    def test_create_transaction_dto(self):
        """Test creating a TransactionCreate DTO."""
        user_id = "test-user-123"
        file_id = uuid.uuid4()
        account_id = uuid.uuid4()
        date = 1717632000000
        description = "Test transaction"
        amount = Decimal("100.50")
        currency = Currency.USD
        
        dto = TransactionCreate(
            userId=user_id,
            fileId=file_id,
            accountId=account_id,
            date=date,
            description=description,
            amount=amount,
            currency=currency
        )
        
        assert dto.user_id == user_id
        assert dto.file_id == file_id
        assert dto.account_id == account_id
        assert dto.date == date
        assert dto.description == description
        assert dto.amount == amount
        assert dto.currency == currency

    def test_create_transaction_dto_validation(self):
        """Test TransactionCreate DTO validation."""
        with pytest.raises(ValueError, match="Timestamp must be a positive integer"):
            TransactionCreate(
                userId="test-user",
                fileId=uuid.uuid4(),
                accountId=uuid.uuid4(),
                date=-1,  # Invalid negative timestamp
                description="Test transaction",
                amount=Decimal("100.00"),
                currency=Currency.USD
            )


class TestTransactionUpdate:
    """Test cases for TransactionUpdate model."""

    def test_update_transaction_dto(self):
        """Test creating a TransactionUpdate DTO."""
        dto = TransactionUpdate(
            description="Updated description",
            amount=Decimal("200.00")
        )
        
        assert dto.description == "Updated description"
        assert dto.amount == Decimal("200.00")
        assert dto.date is None  # Optional field not set

    def test_update_transaction_dto_validation(self):
        """Test TransactionUpdate DTO validation."""
        with pytest.raises(ValueError, match="Timestamp must be a positive integer"):
            TransactionUpdate(
                date=-1  # Invalid negative timestamp
            )


class TestTransactionSerialization:
    """Test cases for transaction serialization functions."""

    def test_transaction_to_json(self):
        """Test transaction_to_json function."""
        create_data = TransactionCreate(
            userId="test-user",
            fileId=uuid.uuid4(),
            accountId=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.50"),
            currency=Currency.USD
        )
        transaction = Transaction.create(create_data)
        
        json_str = transaction_to_json(transaction)
        parsed = json.loads(json_str)
        
        assert parsed['userId'] == "test-user"
        assert parsed['date'] == 1717632000000
        assert parsed['description'] == "Test transaction"
        assert parsed['amount'] == "100.50"
        assert parsed['currency'] == "USD"

    def test_transaction_to_json_with_dict(self):
        """Test transaction_to_json function with dictionary input."""
        transaction_dict = {
            'userId': 'test-user',
            'fileId': str(uuid.uuid4()),
            'accountId': str(uuid.uuid4()),
            'date': 1717632000000,
            'description': 'Test transaction',
            'amount': '100.50',
            'currency': 'USD'
        }
        
        json_str = transaction_to_json(transaction_dict)
        parsed = json.loads(json_str)
        
        assert parsed['userId'] == "test-user"
        assert parsed['amount'] == "100.50"

    def test_transaction_to_json_invalid_input(self):
        """Test transaction_to_json function with invalid input."""
        with pytest.raises(TypeError, match="Input must be a Transaction object"):
            transaction_to_json("invalid input")  # type: ignore

    def test_from_dynamodb_item_decimal_conversion(self):
        """Test that Decimal values from DynamoDB are properly converted to int for timestamp fields."""
        from decimal import Decimal
        
        # Mock DynamoDB data with Decimal values (as they come from DynamoDB)
        dynamodb_data = {
            'userId': 'test-user',
            'fileId': str(uuid.uuid4()),
            'accountId': str(uuid.uuid4()),
            'date': Decimal('1751810806504'),  # This was in the error message
            'description': 'Test transaction',
            'amount': Decimal('100.50'),
            'currency': 'USD',
            'createdAt': Decimal('1751810806504'),
            'updatedAt': Decimal('1751810806505'),
            'transactionHash': Decimal('12345'),
            'importOrder': Decimal('1'),
            'categories': [{
                'categoryId': str(uuid.uuid4()),
                'confidence': Decimal('100'),  # This was in the error message
                'status': 'suggested',
                'assignedAt': Decimal('1751810806504'),
                'confirmedAt': Decimal('1751810806506')
            }]
        }
        
        # This should not raise any Pydantic serialization warnings
        transaction = Transaction.from_dynamodb_item(dynamodb_data)
        
        # Verify the types are correct (int, not Decimal)
        assert isinstance(transaction.date, int)
        assert isinstance(transaction.created_at, int)
        assert isinstance(transaction.updated_at, int)
        assert isinstance(transaction.transaction_hash, int)
        assert isinstance(transaction.import_order, int)
        
        # Verify category assignment types
        assert len(transaction.categories) == 1
        category = transaction.categories[0]
        assert isinstance(category.confidence, int)
        assert isinstance(category.assigned_at, int)
        assert isinstance(category.confirmed_at, int)
        
        # Verify the serialization doesn't produce warnings about Decimal values
        serialized = transaction.model_dump(by_alias=True, exclude_none=True)
        
        # These should be int types now, not Decimal
        assert type(serialized['date']).__name__ == 'int'
        assert type(serialized['createdAt']).__name__ == 'int'
        assert type(serialized['updatedAt']).__name__ == 'int'

    def test_from_dynamodb_item_uuid_conversion(self):
        """Test that UUID string fields from DynamoDB are properly converted to UUID objects."""
        # Mock DynamoDB data with string UUID values (as they come from DynamoDB)
        file_id_str = '12345678-1234-1234-1234-123456789012'
        transaction_id_str = '87654321-4321-4321-4321-210987654321'
        account_id_str = '11111111-2222-3333-4444-555555555555'
        primary_category_id_str = '99999999-8888-7777-6666-555555555555'
        
        dynamodb_data = {
            'userId': 'test-user',
            'fileId': file_id_str,  # String UUID from DynamoDB
            'transactionId': transaction_id_str,  # String UUID from DynamoDB
            'accountId': account_id_str,  # String UUID from DynamoDB
            'date': 1640995200000,
            'description': 'Test transaction',
            'amount': Decimal('100.50'),
            'currency': 'USD',
            'primaryCategoryId': primary_category_id_str,  # String UUID from DynamoDB
            'categories': [{
                'categoryId': '77777777-6666-5555-4444-333333333333',  # String UUID from DynamoDB
                'confidence': 100,
                'status': 'confirmed',
                'isManual': True,
                'assignedAt': 1640995200000,
                'confirmedAt': 1640995200001
            }]
        }
        
        # This should not raise any Pydantic serialization warnings about UUID types
        transaction = Transaction.from_dynamodb_item(dynamodb_data)
        
        # Verify the UUID fields are actual UUID objects, not strings
        assert isinstance(transaction.file_id, uuid.UUID)
        assert isinstance(transaction.transaction_id, uuid.UUID)
        assert isinstance(transaction.account_id, uuid.UUID)
        assert isinstance(transaction.primary_category_id, uuid.UUID)
        
        # Verify the UUID values are correct
        assert transaction.file_id == uuid.UUID(file_id_str)
        assert transaction.transaction_id == uuid.UUID(transaction_id_str)
        assert transaction.account_id == uuid.UUID(account_id_str)
        assert transaction.primary_category_id == uuid.UUID(primary_category_id_str)
        
        # Verify category assignment UUID is also converted
        assert len(transaction.categories) == 1
        category = transaction.categories[0]
        assert isinstance(category.category_id, uuid.UUID)
        assert category.category_id == uuid.UUID('77777777-6666-5555-4444-333333333333')
        
        # Verify the serialization doesn't produce warnings about UUID types
        # This was the original issue - Pydantic expected UUID objects but got strings
        serialized = transaction.model_dump(by_alias=True, mode='json')
        
        # These should serialize to strings without warnings
        assert serialized['fileId'] == file_id_str
        assert serialized['transactionId'] == transaction_id_str
        assert serialized['accountId'] == account_id_str
        assert serialized['primaryCategoryId'] == primary_category_id_str
        assert serialized['categories'][0]['categoryId'] == '77777777-6666-5555-4444-333333333333'
        
        # Test that the transaction can be used in operations that trigger serialization
        # (like the update_transaction call in mark_as_transfer_pair)
        try:
            # This should not raise PydanticSerializationUnexpectedValue warnings
            json_output = transaction.model_dump_json(by_alias=True)
            parsed = json.loads(json_output)
            assert parsed['fileId'] == file_id_str
            assert parsed['transactionId'] == transaction_id_str
            assert parsed['accountId'] == account_id_str
        except Exception as e:
            pytest.fail(f"Transaction serialization failed: {e}")

    def test_from_dynamodb_item_invalid_uuid_handling(self):
        """Test that invalid UUID strings are properly rejected."""
        dynamodb_data = {
            'userId': 'test-user',
            'fileId': 'invalid-uuid-string',  # Invalid UUID
            'transactionId': '87654321-4321-4321-4321-210987654321',  # Valid UUID
            'accountId': '11111111-2222-3333-4444-555555555555',  # Valid UUID
            'date': 1640995200000,
            'description': 'Test transaction',
            'amount': Decimal('100.50'),
            'currency': 'USD'
        }
        
        # Should raise ValidationError for invalid UUID - proper early validation
        with pytest.raises(ValidationError) as exc_info:
            Transaction.from_dynamodb_item(dynamodb_data)
        
        # Verify it's a UUID validation error
        assert 'fileId' in str(exc_info.value) 