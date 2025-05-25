"""
Service module for file processing functionality.
This module contains refactored functionality from the original process_file_with_account function.
"""
import json
import logging
import os
import traceback
from typing import Dict, Any, List, Optional, Tuple, Union
from decimal import Decimal
from dataclasses import dataclass

from datetime import datetime

from handlers.account_operations import create_response
from models import account
from models.account import Account, Currency
from models.money import Money
from models.transaction_file import FileFormat, ProcessingStatus, TransactionFile, transaction_file_to_json
from models.file_map import FileMap
from models.transaction import Transaction
from utils.lambda_utils import handle_error
from utils.transaction_parser import parse_transactions, file_type_selector
from utils.db_utils import (
    create_transaction_file,
    get_transaction_by_account_and_hash,
    get_transaction_file,
    list_account_files,
    list_account_transactions,
    update_account,
    update_transaction,
    update_transaction_file,
    create_transaction,
    delete_transactions_for_file,
    get_file_map,
    list_file_transactions,
    get_transactions_table,
    update_transaction_file_object
)
from utils.file_processor_utils import (
    check_duplicate_transaction,
    get_file_content,
    calculate_opening_balance_from_duplicates
)
from utils.auth import NotAuthorized, NotFound
from services.auth_checks import (
    checked_mandatory_account,
    checked_mandatory_file_map,
    checked_mandatory_transaction_file,
    checked_optional_file_map,
    checked_optional_transaction_file
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class FileProcessorResponse:
    """Response object for file processor operations"""
    message: str
    transactions: Optional[List[Transaction]] = None
    transaction_count: int = 0
    duplicate_count: int = 0
    updated_count: int = 0
    deleted_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "transactions": [tx.to_dict() for tx in self.transactions] if self.transactions else [],
            "transaction_count": self.transaction_count,
            "duplicate_count": self.duplicate_count,
            "updated_count": self.updated_count,
            "deleted_count": self.deleted_count
        }


# Common utility functions

def prepare_file_processing(file_id: str, user_id: str) -> TransactionFile:
    """
    Retrieve file record and validate it exists and belongs to the specified user.
    
    Args:
        file_id: ID of the file to process
        user_id: User ID to validate authorization
        
    Returns:
        TransactionFile if found and authorized
        
    Raises:
        NotAuthorized: If user doesn't match the file's user_id
        NotFound: If file doesn't exist
        ValueError: If file_id or user_id is None or empty
    """
    try:
        if not user_id:
            raise ValueError("User ID is required for integrity checking")
            
        # Use auth utility for authentication and existence check
        return checked_mandatory_transaction_file(file_id, user_id)
        
    except NotAuthorized as e:
        logger.error(f"User {user_id} not authorized to access file {file_id}")
        raise
    except NotFound as e:
        logger.error(f"File {file_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error retrieving file {file_id}: {str(e)}")
        raise


def determine_file_format(transaction_file: TransactionFile, content_bytes: bytes)->TransactionFile:
    """
    Determine or validate the file format.
    
    Args:
        file_record: The file record to check
        content_bytes: The file content as bytes
    """
    try:

        if transaction_file.file_format:
            file_format = transaction_file.file_format
            logger.info(f"Using stored file format: {file_format}")            
        else:
            file_format = file_type_selector(content_bytes)
            logger.info(f"Detected file format: {file_format}")
            # Update file record with detected format
            update_transaction_file(transaction_file.file_id, transaction_file.user_id, {'file_format': file_format})
            transaction_file.file_format = file_format
        
        return transaction_file
    except Exception as e:
        logger.error(f"Error determining file format: {str(e)}")
        return transaction_file


def determine_file_map(transaction_file: TransactionFile) -> Optional[FileMap]:
    """
    Determine which file map to use for the file.
    
    Args:
        file_record: The file record containing mapping and account info
        
    Returns:
        FileMap if found, None otherwise
    """
    try:
        # First try to get the file map specified in the file record
        file_map = checked_optional_file_map(transaction_file.file_map_id, transaction_file.user_id)
        
        logger.info(f"Determining file map - File map ID: {transaction_file.file_map_id}, Account ID: {transaction_file.account_id}")     

        if file_map:
            logger.info(f"Using specified file map {transaction_file.file_map_id} for file {transaction_file.file_id}")
            return file_map
            
        # If no file map specified but we have an account, try to get the account's default map
        if transaction_file.account_id:
            account = checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)
            if account.default_file_map_id:
                file_map = get_file_map(account.default_file_map_id)
                if file_map:
                    logger.info(f"Using account default file map for file {transaction_file.file_id}")
                    transaction_file.file_map_id = account.default_file_map_id
                    return file_map
                    
            logger.info(f"No file map found for account {transaction_file.account_id}")
            
        return None
            
    except Exception as e:
        logger.error(f"Error determining file map: {str(e)}")
        raise  # Re-raise the exception to be handled by the caller


def parse_file_transactions(
    transaction_file: TransactionFile,
    content_bytes: bytes, 
) -> Optional[List[Transaction]]:
    """
    Parse transactions from file content.
    
    Args:
        account_id: The account ID to use
        content_bytes: The file content as bytes
        file_format: The format of the file
        opening_balance: The opening balance to use
        file_map: Optional field mapping configuration
        
    Returns:
        List of transactions
        
    Raises:
        ValueError: If parsing fails or no transactions could be parsed
    """
    try:
        # Validate required parameters
        if not checked_optional_file_map(transaction_file.file_map_id, transaction_file.user_id):
            return None
        
            
        # Parse transactions using the utility
        transactions = parse_transactions(
            transaction_file,
            content_bytes
        )
        
        if not transactions:
            logger.warning(f"No transactions could be parsed from file {transaction_file.file_id}")
            return None
            
        logger.info(f"Successfully parsed {len(transactions)} transactions")
        return transactions
    except Exception as e:
        logger.error(f"Error parsing transactions: {str(e)}")
        raise


def calculate_running_balances(transactions: List[Transaction], opening_balance: Optional[Money]) -> None:
    """
    Update running balances for all transactions in the list.
    Modifies the transactions in place.
    
    Args:
        transactions: List of transaction dictionaries to update
        opening_balance: Opening balance to start calculations from
    """
    try:
        if not opening_balance:
            logger.warning("No opening balance provided, skipping running balance calculation")
            return None
        current_balance = opening_balance
        for tx in transactions:
            current_balance += tx.amount
            tx.balance = current_balance
        logger.info(f"Calculated running balances starting from {opening_balance}")
    except Exception as e:
        logger.error(f"Error calculating running balances: {str(e)}")
        raise


def create_transactions(
    transactions: List[Transaction], 
    transaction_file: TransactionFile
) -> Tuple[int, int]:
    """
    Save transactions to the database.
    
    Args:
        transactions: List of transactions to save
        transaction_file: TransactionFile object
        user_id: ID of the user who owns the file
        account: Account object
        
    Returns:
        Tuple of (total transaction count, duplicate count)
    """
    try:
        checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)
        checked_mandatory_transaction_file(transaction_file.file_id, transaction_file.user_id)
        transaction_count = 0
        duplicate_count = 0

        # warn if duplicate detetcion has not yet been run oin this list of transactions
        if not transaction_file.duplicate_count:
            logger.warning(f"Duplicate detection has not yet been run on file {transaction_file.file_id}") 
            duplicate_count = update_transaction_duplicates(transactions)
            update_transaction_file(transaction_file.file_id, transaction_file.user_id, {'duplicate_count': duplicate_count})
            logger.info(f"Late duplicate detection! Updated duplicate count for file {transaction_file.file_id} to {duplicate_count}")
        
        for transaction in transactions:
            try:
                # Add the file_id and user_id to each transaction
                transaction.file_id = transaction_file.file_id
                transaction.user_id = transaction_file.user_id
                                
                # Create and save the transaction
                create_transaction(transaction)
                transaction_count += 1
            except Exception as tx_error:
                logger.error(f"Error creating transaction: {str(tx_error)}")
                logger.error(f"Transaction data that caused error: {transaction}")
                
        logger.info(f"Saved {transaction_count} transactions for file {transaction_file.file_id}")
        return transaction_count, duplicate_count
    except Exception as e:
        logger.error(f"Error saving transactions: {str(e)}")
        raise


def update_file_status(
    transaction_file: TransactionFile, 
    transactions : List[Transaction]
):
    """
    Update file metadata after processing.
    
    Args:
        transaction_file: TransactionFile object to update
        transactions: List of transactions processed
        
    Returns:
        Updated TransactionFile object
    """


    try:
        transaction_file.processing_status = ProcessingStatus.PROCESSED
        transaction_file.processed_date = int(datetime.now().timestamp() * 1000)
        transaction_file.transaction_count = len(transactions)
        transaction_file.date_range_start = transactions[0].date
        transaction_file.date_range_end = transactions[-1].date
        transaction_file.opening_balance = (transactions[0].balance  - transactions[0].amount ) if transactions[0].balance and transactions[0].amount else None

            
        updated_file = update_transaction_file(transaction_file.file_id, transaction_file.user_id, transaction_file.to_dict())
        logger.info(f"Updated file status for {transaction_file.file_id} to PROCESSED")
        return updated_file
    except Exception as e:
        logger.error(f"Error updating file status: {str(e)}")
        raise


def update_transaction_duplicates(
    transactions: List[Transaction]
) -> int:
    """
    Check for duplicate transactions in a list of transactions.
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Number of duplicate transactions
    """
    try:
        if not transactions:
            return 0
            
        logger.info(f"Checking for duplicate transactions")
        duplicate_count = 0
        for transaction in transactions:
            is_duplicate = check_duplicate_transaction(transaction)
            if is_duplicate:
                    transaction.status = 'duplicate'
                    duplicate_count += 1
            else:
                transaction.status = 'new'

        return duplicate_count
    except Exception as e:
        logger.error(f"Error in duplicate detection: {str(e)}")
        return 0
    
def determine_opening_balance_from_transaction_overlap(transactions: List[Transaction], currency: Optional[Currency]) -> Optional[Money]:
    """
    Determine the opening balance for a new file based on the overlap with existing transactions.
    
    Args:
        transactions: List of existing transactions
    
    Returns:
        Money object representing the opening balance or None if no overlap is found
    """
    try:
        if not transactions:
            return None
        if not currency:
            return None
        logger.info(f"Determining opening balance from transaction overlap")
            
        first_transaction = min(transactions, key=lambda tx: tx.import_order or 0)
        last_transaction = max(transactions, key=lambda tx: tx.import_order or 0)
        
        # Handle duplicates
        if first_transaction.status == 'duplicate':
            matching_transaction = get_transaction_by_account_and_hash(first_transaction.account_id, first_transaction.transaction_hash if first_transaction.transaction_hash else 1)
            if matching_transaction and matching_transaction.balance and matching_transaction.amount:
                logger.info(f"First transaction is duplicate, using balance {matching_transaction.balance} - amount {matching_transaction.amount}")
                money = matching_transaction.balance - matching_transaction.amount
                return money if money.currency else Money(Decimal(money.amount), currency)
                
        if last_transaction.status == 'duplicate':
            matching_transaction = get_transaction_by_account_and_hash(last_transaction.account_id, last_transaction.transaction_hash if last_transaction.transaction_hash else 1)
            if matching_transaction and matching_transaction.balance:
                total_amount = sum([tx.amount for tx in transactions], Money(Decimal(0), currency)) 
                logger.info(f"Last transaction is duplicate, using balance {matching_transaction.balance} - amount {total_amount}")
                money = matching_transaction.balance - total_amount
                return money if money.currency else Money(Decimal(money.amount), currency)
        logger.info(f"No opening balance found from transaction overlap")        
        return None
    except Exception as e:
        logger.error(f"Error determining opening balance: {str(e)}")
        return None


def process_new_file(transaction_file: TransactionFile, content_bytes: bytes) -> FileProcessorResponse:
    """Process a newly uploaded file."""
    account = checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)
    if not transaction_file.user_id:
        raise ValueError("User ID is required")
    # Determine file format
    determine_file_format(transaction_file, content_bytes)
    
    # only parse if the file format and file map and account id are set
    if transaction_file.file_format and transaction_file.file_map_id and transaction_file.account_id:
        transactions = parse_file_transactions(
            transaction_file,
            content_bytes
        )
    
    
    # Parse transactions
    transactions = parse_file_transactions(
        transaction_file,
        content_bytes
    ) if transaction_file.file_format and transaction_file.file_map_id  and transaction_file.account_id and transaction_file.opening_balance else None
    if transactions:
        transaction_file.currency = transactions[0].amount.currency
        update_transaction_duplicates(transactions)
        if not transaction_file.currency:
            raise ValueError("Currency is required")
        # Determine opening balance from transaction overlap
        opening_balance = determine_opening_balance_from_transaction_overlap(transactions, transaction_file.currency)
        transaction_file.opening_balance = opening_balance if opening_balance else transaction_file.opening_balance
        # Calculate running balances
        if transaction_file.opening_balance:
            calculate_running_balances(transactions, transaction_file.opening_balance)
        
        # Save transactions
        transaction_count, duplicate_count = create_transactions(
            transactions,
            transaction_file
        )
        
        # Update file status
        update_file_status(transaction_file, transactions)
    
    return FileProcessorResponse(
        message="File processed successfully",
        transaction_count=transaction_count if transactions else 0,
        duplicate_count=duplicate_count if transactions else 0,
        transactions=transactions
    )

def update_file_mapping(old_transaction_file: TransactionFile, new_transaction_file: TransactionFile) -> FileProcessorResponse:
    """Update a file's field mapping and reprocess transactions."""
    try:   
        # Get field map
        new_field_map: FileMap = checked_mandatory_file_map(new_transaction_file.file_map_id, new_transaction_file.user_id)
        account = checked_mandatory_account(new_transaction_file.account_id, new_transaction_file.user_id)
        logger.info(f"Comparing file mapping new {new_transaction_file.file_map_id} with old {old_transaction_file.file_map_id}")
        # Check if field mapping has changed
        should_reprocess = (
            old_transaction_file.file_map_id != new_field_map.file_map_id and
            new_transaction_file.opening_balance is not None
        )
        logger.info(f"Should reprocess: {should_reprocess}")
        if should_reprocess:
            # Get file content
            content_bytes = get_file_content(new_transaction_file.file_id)
            if not content_bytes:
                raise NotFound("File content not found")
                
            # Delete existing transactions
            logger.info(f"Field mapping has changed for file {new_transaction_file.file_id} - deleting existing transactions")
            deleted_count = delete_transactions_for_file(new_transaction_file.file_id)
            
            # Process with new mapping
            transactions = parse_file_transactions(
                new_transaction_file,
                content_bytes
            )
            currency = transactions[0].amount.currency if transactions else new_transaction_file.currency 
            if not currency:
                raise ValueError("Currency is required")
            logger.info(f"Processing with new mapping for file {new_transaction_file.file_id} and currency {currency}")
            if transactions:
                duplicate_count = update_transaction_duplicates(transactions)
                logger.info(f"Duplicate count: {duplicate_count}")
                # Determine opening balance from transaction overlap
                opening_balance = determine_opening_balance_from_transaction_overlap(transactions, currency)
                logger.info(f"Opening balance: {opening_balance}")
                new_transaction_file.opening_balance = opening_balance if opening_balance else new_transaction_file.opening_balance
                # Calculate running balances
                if new_transaction_file.opening_balance:
                    calculate_running_balances(transactions, new_transaction_file.opening_balance)
                else:
                    raise ValueError("Opening balance is required to calculate running balances")
                
                # Save transactions
                transaction_count, _ = create_transactions(
                    transactions,
                    new_transaction_file
                )
                
                # Update file status
                update_file_status(new_transaction_file, transactions)
                
                return FileProcessorResponse(
                    transactions=transactions,
                    transaction_count=transaction_count,
                    duplicate_count=duplicate_count,
                    deleted_count=deleted_count,
                    message="Field map updated, transactions reprocessed"
                )
            else:
                return FileProcessorResponse(
                    transactions=[],
                    transaction_count=0,
                    duplicate_count=0,
                    deleted_count=deleted_count,
                    message="No transactions found after reprocessing"
                )
        else:
        # If field map hasn't changed, just update the mapping
            update_transaction_file(new_transaction_file.file_id, new_transaction_file.user_id, {'file_map_id': new_transaction_file.file_map_id})
            logger.info(f"transaction reprocessing not needed for file {new_transaction_file.file_id}, just updated the mapping to {new_transaction_file.file_map_id}   ")
        transactions = list_file_transactions(new_transaction_file.file_id)
        return FileProcessorResponse(
            transactions=transactions,
            transaction_count=len(transactions) if transactions else 0,
            duplicate_count=0,
            deleted_count=0,
            message="Field map is unchanged, no reprocessing needed"
        )
            
    except Exception as e:
        logger.error(f"Error remapping file: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        raise Exception(f"Error remapping file: {str(e)}")

def update_opening_balance(transaction_file: TransactionFile) -> FileProcessorResponse:
    """Update a file's opening balance without reprocessing transactions."""

    if not transaction_file.opening_balance:
        raise ValueError("New opening balance is required")
    return create_file(transaction_file)
        
    # old_transaction_file = checked_mandatory_transaction_file(transaction_file.file_id, transaction_file.user_id)
    # if not old_transaction_file.opening_balance:
    #     raise ValueError("Old opening balance is required")
        
    # balance_change = transaction_file.opening_balance - old_transaction_file.opening_balance
        
    # # Update all transactions from account adding balance change to the balance
    # if not transaction_file.account_id:
    #     raise ValueError("Account ID is required")
        
    # transactions = list_account_transactions(transaction_file.account_id)
    
    # # Update transactions in database
    # for tx in transactions:
    #     if tx.balance:
    #         tx.balance += balance_change
    #         update_transaction(tx)
    
    # transaction_files = list_account_files(transaction_file.account_id)
    # for file in transaction_files:
    #     if file.opening_balance:
    #         update_transaction_file(file.file_id, file.user_id, {'opening_balance': file.opening_balance})
    
    # return FileProcessorResponse(
    #     message="Opening balance updated successfully",
    #     transaction_count=len(transactions)
    # )
    

def change_file_account(transaction_file: TransactionFile) -> FileProcessorResponse:
    """Reassign a file to a different account."""

    # Get old transaction_file
    old_transaction_file = checked_mandatory_transaction_file(transaction_file.file_id, transaction_file.user_id)
    if not transaction_file.currency:
        raise ValueError("Currency is required")
    # Validate new account
    account = checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)

    # Update file record with new account ID
    update_transaction_file(transaction_file.file_id, transaction_file.user_id, {'account_id': transaction_file.account_id})

    # Get existing transactions
    transactions = list_file_transactions(transaction_file.file_id)
    if transactions:
        update_transaction_duplicates(transactions)
        # Determine opening balance from transaction overlap
        opening_balance = determine_opening_balance_from_transaction_overlap(transactions, transaction_file.currency)
        transaction_file.opening_balance = opening_balance if opening_balance else transaction_file.opening_balance
        # Calculate running balances
        if transaction_file.opening_balance:
            calculate_running_balances(transactions, transaction_file.opening_balance)
        # Update account ID for all transactions
        for tx in transactions:
            tx.account_id = account.account_id
            update_transaction(tx)
            
    return FileProcessorResponse(
        message="File account updated successfully",
        transactions=transactions,
        transaction_count=len(transactions) if transactions else 0
    )
        
def create_file(transaction_file: TransactionFile) -> FileProcessorResponse:
    """
    Main entry point for processing a file.
    
    Args:
        file_id: ID of the file to process
        content_bytes: Raw file content
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with processing results
    """

    # Create the file record
    create_transaction_file(transaction_file)
    logger.info(f"Created file metadata in DynamoDB: {json.dumps(transaction_file_to_json(transaction_file))}")
    content_bytes = get_file_content(transaction_file.file_id)
    if not content_bytes:
        raise NotFound("File content not found")
        
    return process_new_file(transaction_file, content_bytes)
        
def set_defaults_from_account(transaction_file: TransactionFile)->TransactionFile:
    """
    If account_id set, use defaults from account
    """
    if transaction_file.account_id:
        account = checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)
        transaction_file.currency = account.currency if not transaction_file.currency else transaction_file.currency
        transaction_file.file_map_id = account.default_file_map_id if not transaction_file.file_map_id else transaction_file.file_map_id
    return transaction_file

def set_defaults_into_account(transaction_file: TransactionFile)->Account:

    """
    If account_id set, use defaults from account
    """
    if transaction_file.account_id:
        account = checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)
        update = {}
        if transaction_file.currency:
            update['currency'] = transaction_file.currency
        if transaction_file.file_map_id:
            update['default_file_map_id'] = transaction_file.file_map_id
        logger.info(f"Updating account {account.account_id} with {update}")
        if update:  
            update_account(account.account_id, account.user_id, update)
    return account

def update_file_object(transaction_file: TransactionFile, transations: List[Transaction])->TransactionFile:
    """
    Update the transaction file object with new metadata, eg, start end date, transactioncount, opening balance, currency
    """
    transaction_file.date_range_start = transations[0].date
    transaction_file.date_range_end = transations[-1].date
    transaction_file.transaction_count = len(transations)
    return transaction_file

def update_file(old_transaction_file: Optional[TransactionFile], transaction_file: TransactionFile) -> FileProcessorResponse:
    """
    Update a file's metadata and cascade updates to transactions and other files.
    Steps:
    1. set defaults from account where known
    2. delete existing transactions
    3. re parse the file with the current filemap, opening balance, and currency where known
    4. check new transactions are duplicates
    5. calculate opening balance if possible from duplicates   
    6. calculate running balances
    7. update the transaction file object with new metadata, eg, start end date, transactioncount, opening balance, currency
    8. feed defaults back into account
    9. update account db object, transaction file db object and delete old transaction objects write out fresh db objects
    10. return an approriate response object
    """
    logger.info(f"Updating from transaction file {old_transaction_file} to {transaction_file}")
    try:
        transaction_file = set_defaults_from_account(transaction_file)
        if not old_transaction_file:
            create_transaction_file(transaction_file)
        if old_transaction_file:
            delete_transactions_for_file(old_transaction_file.file_id)
        transactions = reparse_file(transaction_file)
        transaction_file.transaction_count = len(transactions) if transactions else 0
        if transactions:
            transaction_file.duplicate_count = update_transaction_duplicates(transactions)
            if transaction_file.duplicate_count > 0:
                opening_balance = determine_opening_balance_from_transaction_overlap(transactions, transaction_file.currency)
                transaction_file.opening_balance = opening_balance if opening_balance else transaction_file.opening_balance
                calculate_running_balances(transactions, transaction_file.opening_balance)
            update_file_object(transaction_file, transactions)
        if transactions and transaction_file.opening_balance and transaction_file.currency:
            create_transactions(transactions, transaction_file)
        set_defaults_into_account(transaction_file)
        update_transaction_file_object(transaction_file)
        return FileProcessorResponse(
            message="File updated successfully",
            transaction_count=transaction_file.transaction_count,
            duplicate_count=transaction_file.duplicate_count if transaction_file.duplicate_count else 0,
            transactions=transactions
        )
    except Exception as e:
        logger.error(f"Error updating file: {str(e)}")
        raise

def reparse_file(transaction_file: TransactionFile) -> Optional[List[Transaction]]:
    """transaction_count=len(transactions) if transactions else 0
    Reparse a file with the current filemap, opening balance, and currency where known
    Steps:
    1. load file from S3
    2. parse file with the current filemap, opening balance, and currency where known
    3. return the transaction list 
    """
    try:
        content_bytes = get_file_content(transaction_file.file_id)
        if not content_bytes:
            raise NotFound("File content not found")
        return parse_file_transactions(transaction_file, content_bytes)
    except Exception as e:
        logger.error(f"Error reparsing file: {str(e)}")
        #show stack trace
        logger.error(traceback.format_exc())
        raise


def upsert_file(old_transaction_file: Optional[TransactionFile], transaction_file: TransactionFile) -> FileProcessorResponse:
    """
    Upsert a file's metadata and cascade updates to transactions and other files.
    """
    transaction_file = set_defaults_from_account(transaction_file)
    if not old_transaction_file:
        create_transaction_file(transaction_file)
    return update_file(old_transaction_file, transaction_file)




def process_file(transaction_file: TransactionFile) -> FileProcessorResponse:
    """
    Legacy entry point that routes to appropriate handler based on context.
    
    Args:
        file_id: ID of the file to process
        account_id: ID of the account to process with
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with processing results
    """
    logger.info(f"Processing file {transaction_file}")
    old_transaction_file = checked_optional_transaction_file(transaction_file.file_id, transaction_file.user_id)
    return upsert_file(old_transaction_file, transaction_file)

                


