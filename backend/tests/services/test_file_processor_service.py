import pytest
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from models.transaction import Transaction, TransactionCreate
from models.transaction_file import TransactionFile
from models.account import Account, AccountType, Currency
from services.file_processor_service import create_transactions
from utils.db_utils import update_account

def test_create_transactions_updates_account_balance(mocker):
    """Test that create_transactions updates the account's balance with the latest transaction's balance."""
    # Mock dependencies
    mock_account = Account(
        userId="test-user",
        accountId=uuid.uuid4(),
        accountName="Test Account",
        accountType=AccountType.CHECKING,
        currency=Currency.USD,
        balance=Decimal("1000.00")
    )
    
    mock_transaction_file = TransactionFile(
        userId="test-user",
        fileName="test.qif",
        fileSize=1000,
        s3Key="test/test.qif",
        accountId=mock_account.account_id,
        currency=Currency.USD
    )
    
    # Create test transactions with different dates and balances
    transactions = [
        Transaction.create(TransactionCreate(
            userId="test-user",
            fileId=mock_transaction_file.file_id,
            accountId=mock_account.account_id,
            date=1641024000000,  # 2022-01-01
            description="Transaction 1",
            amount=Decimal("-50.00"),
            currency=Currency.USD,
            balance=Decimal("950.00")
        )),
        Transaction.create(TransactionCreate(
            userId="test-user",
            fileId=mock_transaction_file.file_id,
            accountId=mock_account.account_id,
            date=1641110400000,  # 2022-01-02
            description="Transaction 2",
            amount=Decimal("-30.00"),
            currency=Currency.USD,
            balance=Decimal("920.00")
        )),
        Transaction.create(TransactionCreate(
            userId="test-user",
            fileId=mock_transaction_file.file_id,
            accountId=mock_account.account_id,
            date=1641196800000,  # 2022-01-03
            description="Transaction 3",
            amount=Decimal("-20.00"),
            currency=Currency.USD,
            balance=Decimal("900.00")
        ))
    ]
    
    # Mock the checked_mandatory_account function to return our mock account
    mocker.patch(
        'services.file_processor_service.checked_mandatory_account',
        return_value=mock_account
    )
    
    # Mock the checked_mandatory_transaction_file function
    mocker.patch(
        'services.file_processor_service.checked_mandatory_transaction_file',
        return_value=mock_transaction_file
    )
    
    # Mock update_transaction_duplicates to return 0 duplicates
    mocker.patch(
        'services.file_processor_service.update_transaction_duplicates',
        return_value=0
    )
    
    # Mock update_transaction_file
    mock_update_transaction_file = mocker.patch('services.file_processor_service.update_transaction_file')
    
    # Mock update_account to capture the update data
    mock_update_account = mocker.patch('services.file_processor_service.update_account')
    
    # Call the function under test
    create_transactions(transactions, mock_transaction_file)
    
    # Verify that update_account was called with the correct data
    mock_update_account.assert_called_once_with(
        mock_account.account_id,
        mock_account.user_id,
        {
            'last_transaction_date': 1641196800000,  # Latest transaction date
            'balance': Decimal("900.00")  # Latest transaction balance
        }
    ) 