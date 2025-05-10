"""
Service module for file processing functionality.
This module contains refactored functionality from the original process_file_with_account function.
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from decimal import Decimal
from dataclasses import dataclass

from datetime import datetime

from models.account import Account
from models.money import Money
from models.transaction_file import FileFormat, ProcessingStatus, TransactionFile
from models.field_map import FieldMap
from models.transaction import Transaction
from utils.transaction_parser import parse_transactions, file_type_selector
from utils.db_utils import (
    get_transaction_file,
    update_transaction_file,
    create_transaction,
    delete_transactions_for_file,
    get_field_mapping,
    get_account_default_field_map,
    list_file_transactions,
    get_transactions_table
)
from utils.file_processor_utils import (
    check_duplicate_transaction,
    get_file_content,
    calculate_opening_balance_from_duplicates
)
from utils.auth import checked_mandatory_account, checked_mandatory_file, NotAuthorized, NotFound, checked_optional_field_mapping

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
        return checked_mandatory_file(file_id, user_id)
        
    except NotAuthorized as e:
        logger.error(f"User {user_id} not authorized to access file {file_id}")
        raise
    except NotFound as e:
        logger.error(f"File {file_id} not found")
        raise
    except Exception as e:
        logger.error(f"Error retrieving file {file_id}: {str(e)}")
        raise


def determine_file_format(file_record: TransactionFile, content_bytes: bytes) -> FileFormat:
    """
    Determine or validate the file format.
    
    Args:
        file_record: The file record to check
        content_bytes: The file content as bytes
        
    Returns:
        The determined FileFormat
    """
    try:
        file_format = None
        if file_record.file_format:
            try:
                file_format = FileFormat(file_record.file_format)
                logger.info(f"Using stored file format: {file_format}")
            except ValueError:
                logger.warning(f"Invalid file format stored: {file_record.file_format}, will re-detect")
                
        if not file_format:
            file_format = file_type_selector(content_bytes)
            logger.info(f"Detected file format: {file_format}")
            # Update file record with detected format
            update_transaction_file(file_record.file_id, {"file_format": file_format.value})
            
        return file_format
    except Exception as e:
        logger.error(f"Error determining file format: {str(e)}")
        return FileFormat.OTHER


def determine_field_mapping(file_record: TransactionFile, user_id: str) -> Optional[FieldMap]:
    """
    Determine which field mapping to use for the file.
    
    Args:
        file_record: The file record containing mapping and account info
        
    Returns:
        FieldMap if found, None otherwise
    """
    try:
        field_map = None
        field_map_id = file_record.field_map_id
        account_id = file_record.account_id
        
        logger.info(f"Determining field mapping - Field map ID: {field_map_id}, Account ID: {account_id}")
        

            # Use specified field map
        field_map = checked_optional_field_mapping(field_map_id, user_id)
        if field_map:
            logger.info(f"Using specified field map {field_map_id} for file {file_record.file_id}")
        elif account_id:
            # Try to use account's default field map
            account = checked_mandatory_account(account_id, user_id)
            field_map = get_field_mapping(account.default_field_map_id)
            if field_map:
                logger.info(f"Using account default field map for file {file_record.file_id}")
                
        return field_map
    except Exception as e:
        logger.error(f"Error determining field mapping: {str(e)}")
        return None


def parse_file_transactions(
    account_id: str,
    content_bytes: bytes, 
    file_format: FileFormat, 
    opening_balance: Decimal,
    field_map: Optional[FieldMap]
) -> List[Transaction]:
    """
    Parse transactions from file content.
    
    Args:
        account_id: The account ID to use
        content_bytes: The file content as bytes
        file_format: The format of the file
        opening_balance: The opening balance to use
        field_map: Optional field mapping configuration
        
    Returns:
        List of transactions
        
    Raises:
        ValueError: If parsing fails or no transactions could be parsed
    """
    try:
        # Validate that field map exists for CSV format
        if file_format == FileFormat.CSV and not field_map:
            raise ValueError("Field map required for CSV files")
            
        # Parse transactions using the utility
        transactions = parse_transactions(
            account_id,
            content_bytes, 
            file_format,
            opening_balance,
            field_map
        )
        
        if not transactions:
            raise ValueError("No transactions could be parsed from file")
            
        logger.info(f"Successfully parsed {len(transactions)} transactions")
        return transactions
    except Exception as e:
        logger.error(f"Error parsing transactions: {str(e)}")
        raise


def calculate_running_balances(transactions: List[Transaction], opening_balance: Money) -> None:
    """
    Update running balances for all transactions in the list.
    Modifies the transactions in place.
    
    Args:
        transactions: List of transaction dictionaries to update
        opening_balance: Opening balance to start calculations from
    """
    try:
        current_balance = opening_balance
        for tx in transactions:
            current_balance += tx.amount
            tx.balance = current_balance
        logger.info(f"Calculated running balances starting from {opening_balance}")
    except Exception as e:
        logger.error(f"Error calculating running balances: {str(e)}")
        raise


def save_transactions(
    transactions: List[Transaction], 
    transaction_file: TransactionFile, 
    user_id: str, 
    account: Account
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
        checked_mandatory_account(account.account_id, user_id)
        checked_mandatory_file(transaction_file.file_id, user_id)
        transaction_count = 0
        duplicate_count = 0

        # warn if duplicate detetcion has not yet been run oin this list of transactions
        if not transaction_file.duplicate_count:
            logger.warning(f"Duplicate detection has not yet been run on file {transaction_file.file_id}") 
            duplicate_count = update_transaction_duplicates(transactions)
            transaction_file.duplicate_count = duplicate_count
            update_transaction_file(transaction_file)
            logger.info(f"Late duplicate detection! Updated duplicate count for file {transaction_file.file_id} to {duplicate_count}")
        
        for transaction in transactions:
            try:
                # Add the file_id and user_id to each transaction
                transaction.file_id = transaction_file.file_id
                transaction.user_id = user_id
                                
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
    field_map_id: Optional[str], 
    transactions : List[Transaction]
):
    """
    Update file metadata after processing.
    
    Args:
        transaction_file: TransactionFile object to update
        field_map_id: Optional ID of the field map used
        transactions: List of transactions processed
        
    Returns:
        Updated TransactionFile object
    """


    try:
        transaction_file.processing_status = ProcessingStatus.PROCESSED
        transaction_file.processed_date = datetime.now().isoformat()
        transaction_file.transaction_count = len(transactions)
        transaction_file.date_range_start = transactions[0].date
        transaction_file.date_range_end = transactions[-1].date
        transaction_file.opening_balance = transactions[0].balance-transactions[0].amount

            
        updated_file = update_transaction_file(transaction_file)
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


