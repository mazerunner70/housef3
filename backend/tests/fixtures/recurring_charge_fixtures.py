"""
Test fixtures and factory functions for recurring charge detection.

Provides convenient factory functions for creating test data including
accounts, transactions, and common recurring charge scenarios.
"""

from typing import List, Dict, Optional
import uuid
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from models.transaction import Transaction
from models.account import Account, AccountType


def create_test_account(
    user_id: str = "test-user",
    account_type: AccountType = AccountType.CHECKING,
    account_name: str = "Test Account",
    institution: str = "Test Bank",
    first_transaction_days_ago: int = 365,
    is_active: bool = True
) -> Account:
    """
    Create a test account with sensible defaults.
    
    Args:
        user_id: User ID for the account
        account_type: Type of account
        account_name: Human-readable account name
        institution: Financial institution name
        first_transaction_days_ago: Days ago for first transaction date
        is_active: Whether account is active
        
    Returns:
        Account object ready for testing
    """
    first_tx_date = datetime.now(timezone.utc) - timedelta(days=first_transaction_days_ago)
    
    return Account(
        userId=user_id,
        accountId=uuid.uuid4(),
        accountName=account_name,
        accountType=account_type,
        institution=institution,
        firstTransactionDate=int(first_tx_date.timestamp() * 1000),
        is_active=is_active
    )


def create_transaction(
    user_id: str,
    account_id: uuid.UUID,
    date: datetime,
    description: str,
    amount: Decimal,
    file_id: Optional[uuid.UUID] = None
) -> Transaction:
    """
    Create a single test transaction.
    
    Args:
        user_id: User ID
        account_id: Account UUID
        date: Transaction date
        description: Transaction description
        amount: Transaction amount (negative for expenses)
        file_id: Optional file ID (generates random if None)
        
    Returns:
        Transaction object
    """
    return Transaction(
        userId=user_id,
        fileId=file_id or uuid.uuid4(),
        accountId=account_id,
        date=int(date.timestamp() * 1000),
        description=description,
        amount=amount
    )


def create_monthly_transactions(
    user_id: str,
    account_id: uuid.UUID,
    merchant: str,
    amount: Decimal,
    start_date: Optional[datetime] = None,
    count: int = 12,
    day_of_month: int = 15,
    amount_variance: float = 0.0
) -> List[Transaction]:
    """
    Create a series of monthly transactions on a specific day.
    
    Args:
        user_id: User ID
        account_id: Account UUID
        merchant: Merchant/description base name
        amount: Base transaction amount
        start_date: Start date (defaults to 12 months ago)
        count: Number of transactions to create
        day_of_month: Day of month for transactions
        amount_variance: Random variance as fraction (0.0 = no variance, 0.1 = ±10%)
        
    Returns:
        List of Transaction objects
    """
    import random
    
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=365)
    
    transactions = []
    
    for i in range(count):
        # Calculate date (roughly monthly, accounting for month boundaries)
        date = start_date + timedelta(days=30 * i)
        # Adjust to specific day of month
        try:
            date = date.replace(day=day_of_month)
        except ValueError:
            # Handle months with fewer days (e.g., Feb 30)
            from calendar import monthrange
            _, last_day = monthrange(date.year, date.month)
            date = date.replace(day=min(day_of_month, last_day))
        
        # Apply amount variance if specified
        if amount_variance > 0:
            variance = random.uniform(-amount_variance, amount_variance)
            varied_amount = amount * (1 + Decimal(str(variance)))
        else:
            varied_amount = amount
        
        tx = Transaction(
            userId=user_id,
            fileId=uuid.uuid4(),
            accountId=account_id,
            date=int(date.timestamp() * 1000),
            description=f"{merchant} {i+1:03d}",
            amount=varied_amount
        )
        transactions.append(tx)
    
    return transactions


def create_weekly_transactions(
    user_id: str,
    account_id: uuid.UUID,
    merchant: str,
    amount: Decimal,
    start_date: Optional[datetime] = None,
    count: int = 12,
    day_of_week: int = 1  # 0=Monday, 6=Sunday
) -> List[Transaction]:
    """
    Create a series of weekly transactions on a specific day of week.
    
    Args:
        user_id: User ID
        account_id: Account UUID
        merchant: Merchant/description base name
        amount: Transaction amount
        start_date: Start date (defaults to 12 weeks ago)
        count: Number of transactions to create
        day_of_week: Day of week (0=Monday, 6=Sunday)
        
    Returns:
        List of Transaction objects
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(weeks=12)
    
    # Adjust start_date to the specified day of week
    days_ahead = day_of_week - start_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    start_date = start_date + timedelta(days=days_ahead)
    
    transactions = []
    
    for i in range(count):
        date = start_date + timedelta(weeks=i)
        tx = Transaction(
            userId=user_id,
            fileId=uuid.uuid4(),
            accountId=account_id,
            date=int(date.timestamp() * 1000),
            description=f"{merchant} WEEK {i+1}",
            amount=amount
        )
        transactions.append(tx)
    
    return transactions


def create_test_scenario(scenario_type: str = "credit_card_subscription") -> Dict:
    """
    Create complete test scenarios with accounts and transactions.
    
    Args:
        scenario_type: Type of scenario to create. Options:
            - "credit_card_subscription": Monthly Netflix on credit card
            - "checking_utility": Monthly utility bill on checking account
            - "salary_deposit": Bi-weekly salary on checking account
            - "savings_transfer": Monthly transfer to savings
            - "mixed_accounts": Transactions across multiple accounts
            
    Returns:
        Dictionary with 'account', 'transactions', and 'accounts_map' keys
    """
    scenarios = {
        "credit_card_subscription": _create_credit_card_subscription_scenario,
        "checking_utility": _create_checking_utility_scenario,
        "salary_deposit": _create_salary_deposit_scenario,
        "savings_transfer": _create_savings_transfer_scenario,
        "mixed_accounts": _create_mixed_accounts_scenario,
    }
    
    if scenario_type not in scenarios:
        raise ValueError(
            f"Unknown scenario type: {scenario_type}. "
            f"Available: {list(scenarios.keys())}"
        )
    
    return scenarios[scenario_type]()


def _create_credit_card_subscription_scenario() -> Dict:
    """Netflix subscription on credit card."""
    user_id = "test-user"
    account = create_test_account(
        user_id=user_id,
        account_type=AccountType.CREDIT_CARD,
        account_name="Rewards Credit Card",
        institution="Chase"
    )
    
    transactions = create_monthly_transactions(
        user_id=user_id,
        account_id=account.account_id,
        merchant="NETFLIX",
        amount=Decimal("-15.99"),
        count=12,
        day_of_month=5
    )
    
    return {
        "account": account,
        "transactions": transactions,
        "accounts_map": {account.account_id: account}
    }


def _create_checking_utility_scenario() -> Dict:
    """Electric utility bill on checking account."""
    user_id = "test-user"
    account = create_test_account(
        user_id=user_id,
        account_type=AccountType.CHECKING,
        account_name="Personal Checking",
        institution="Wells Fargo"
    )
    
    transactions = create_monthly_transactions(
        user_id=user_id,
        account_id=account.account_id,
        merchant="ELECTRIC COMPANY",
        amount=Decimal("-120.50"),
        count=12,
        day_of_month=20,
        amount_variance=0.15  # Bills vary by ~15%
    )
    
    return {
        "account": account,
        "transactions": transactions,
        "accounts_map": {account.account_id: account}
    }


def _create_salary_deposit_scenario() -> Dict:
    """Bi-weekly salary deposits."""
    user_id = "test-user"
    account = create_test_account(
        user_id=user_id,
        account_type=AccountType.CHECKING,
        account_name="Main Checking",
        institution="Bank of America"
    )
    
    start_date = datetime.now(timezone.utc) - timedelta(days=365)
    transactions = []
    
    for i in range(26):  # 26 bi-weekly periods in a year
        date = start_date + timedelta(weeks=2 * i)
        # Paychecks on Fridays
        days_to_friday = (4 - date.weekday()) % 7
        date = date + timedelta(days=days_to_friday)
        
        tx = Transaction(
            userId=user_id,
            fileId=uuid.uuid4(),
            accountId=account.account_id,
            date=int(date.timestamp() * 1000),
            description=f"PAYROLL DEPOSIT {i+1}",
            amount=Decimal("2500.00")
        )
        transactions.append(tx)
    
    return {
        "account": account,
        "transactions": transactions,
        "accounts_map": {account.account_id: account}
    }


def _create_savings_transfer_scenario() -> Dict:
    """Monthly automatic savings transfer."""
    user_id = "test-user"
    account = create_test_account(
        user_id=user_id,
        account_type=AccountType.SAVINGS,
        account_name="Emergency Savings",
        institution="Ally Bank"
    )
    
    transactions = create_monthly_transactions(
        user_id=user_id,
        account_id=account.account_id,
        merchant="AUTOMATIC TRANSFER",
        amount=Decimal("500.00"),  # Positive = deposit
        count=12,
        day_of_month=1
    )
    
    return {
        "account": account,
        "transactions": transactions,
        "accounts_map": {account.account_id: account}
    }


def _create_mixed_accounts_scenario() -> Dict:
    """Multiple recurring patterns across different accounts."""
    user_id = "test-user"
    
    # Create accounts
    credit_card = create_test_account(
        user_id=user_id,
        account_type=AccountType.CREDIT_CARD,
        account_name="Visa Credit",
        institution="Chase"
    )
    
    checking = create_test_account(
        user_id=user_id,
        account_type=AccountType.CHECKING,
        account_name="Main Checking",
        institution="Wells Fargo"
    )
    
    # Create transactions for each account
    netflix_txs = create_monthly_transactions(
        user_id=user_id,
        account_id=credit_card.account_id,
        merchant="NETFLIX",
        amount=Decimal("-15.99"),
        count=12,
        day_of_month=5
    )
    
    spotify_txs = create_monthly_transactions(
        user_id=user_id,
        account_id=credit_card.account_id,
        merchant="SPOTIFY",
        amount=Decimal("-9.99"),
        count=12,
        day_of_month=12
    )
    
    rent_txs = create_monthly_transactions(
        user_id=user_id,
        account_id=checking.account_id,
        merchant="RENT PAYMENT",
        amount=Decimal("-1500.00"),
        count=12,
        day_of_month=1
    )
    
    all_transactions = netflix_txs + spotify_txs + rent_txs
    
    return {
        "accounts": [credit_card, checking],
        "transactions": all_transactions,
        "accounts_map": {
            credit_card.account_id: credit_card,
            checking.account_id: checking
        }
    }

