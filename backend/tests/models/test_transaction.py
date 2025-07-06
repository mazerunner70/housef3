import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import json

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
            "confidence": 0.8,
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
        
        transaction = Transaction.create(
            user_id=user_id,
            file_id=file_id,
            account_id=account_id,
            date=date,
            description=description,
            amount=amount,
            currency=currency
        )
        
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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
        category_id = uuid.uuid4()
        transaction.add_manual_category(category_id, set_as_primary=True)
        
        # Remove the category
        success = transaction.remove_category_assignment(category_id)
        
        assert success is True
        assert len(transaction.categories) == 0
        assert transaction.primary_category_id is None

    def test_category_properties(self):
        """Test category-related properties."""
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
        original_hash = transaction.transaction_hash
        
        # Change a key field
        transaction.description = "Updated description"
        
        # Hash should be recalculated
        assert transaction.transaction_hash != original_hash

    def test_transaction_validation(self):
        """Test transaction validation."""
        # Test with valid data
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.00"),
            currency=Currency.USD
        )
        
        assert transaction.user_id == "test-user"
        assert transaction.date == 1717632000000
        assert transaction.amount == Decimal("100.00")
        
        # Test with invalid timestamp
        with pytest.raises(ValueError, match="Timestamp must be a positive integer"):
            Transaction.create(
                user_id="test-user",
                file_id=uuid.uuid4(),
                account_id=uuid.uuid4(),
                date=-1,  # Invalid negative timestamp
                description="Test transaction",
                amount=Decimal("100.00"),
                currency=Currency.USD
            )


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
        transaction = Transaction.create(
            user_id="test-user",
            file_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            date=1717632000000,
            description="Test transaction",
            amount=Decimal("100.50"),
            currency=Currency.USD
        )
        
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