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
from models.account import Account
from models.money import Money
from models.transaction_file import FileFormat, ProcessingStatus, TransactionFile
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
from utils.auth import checked_mandatory_account, checked_mandatory_field_mapping, checked_mandatory_file, NotAuthorized, NotFound, checked_optional_field_mapping, checked_optional_file

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


def determine_file_format(transaction_file: TransactionFile, content_bytes: bytes):
    """
    Determine or validate the file format.
    
    Args:
        file_record: The file record to check
        content_bytes: The file content as bytes
    """
    try:
        file_format = None
        if transaction_file.file_format:
            try:
                file_format = transaction_file.file_format
                logger.info(f"Using stored file format: {file_format}")
            except ValueError:
                logger.warning(f"Invalid file format stored: {transaction_file.file_format}, will re-detect")
                
        if not file_format:
            file_format = file_type_selector(content_bytes)
            logger.info(f"Detected file format: {file_format}")
            # Update file record with detected format
            update_transaction_file(transaction_file.file_id, {"file_format": file_format.value})
            transaction_file.file_format = file_format

    except Exception as e:
        logger.error(f"Error determining file format: {str(e)}")
        return FileFormat.OTHER


def determine_field_mapping(transaction_file: TransactionFile):
    """
    Determine which field mapping to use for the file.
    
    Args:
        file_record: The file record containing mapping and account info
        
    """
    try:
        field_map = checked_optional_field_mapping(transaction_file.field_map_id, transaction_file.user_id)
        account_id = transaction_file.account_id    
        
        logger.info(f"Determining field mapping - Field map ID: {transaction_file.field_map_id}, Account ID: {transaction_file.account_id}")     

   
        if field_map:
            logger.info(f"Using specified field map {transaction_file.field_map_id} for file {transaction_file.file_id}")
        elif account_id:
            # Try to use account's default field map
            account = checked_mandatory_account(account_id, transaction_file.user_id)
            field_map = get_field_mapping(account.default_field_map_id)
            if field_map:
                logger.info(f"Using account default field map for file {transaction_file.file_id}")
                transaction_file.field_map_id = account.default_field_map_id
            else:
                logger.info(f"No field map found for account {account_id}")
    except Exception as e:
        logger.error(f"Error determining field mapping: {str(e)}")
        return None


def parse_file_transactions(
    account_id: str,
    content_bytes: bytes, 
    file_format: FileFormat, 
    opening_balance: Decimal,
    field_map: Optional[FileMap]
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
        # if any params None then exit without tryuing to parse
        if not account_id or not content_bytes or not file_format or not opening_balance or not field_map:
            logger.info(f"Missing required parameters: {account_id}, {content_bytes}, {file_format}, {opening_balance}, {field_map}")
            return []            
        
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
    
def determine_opening_balances_from_transaction_overlap(transactions: List[Transaction]) -> Money:
    """
    Determine the opening balance for a new file based on the overlap with existing transactions.
    
    Args:
        transactions: List of existing transactions
    
    Returns:
        Money object representing the opening balance or None if no overlap is found
    """
    try:
        # Get the first and last transaction 
        first_transaction = min(tx.import_order for tx in transactions)
        last_transaction = max(tx.import_order for tx in transactions)
        
        # if the first transaction is a duplicate, then retrieve the matching transaction and calculate the opening balance as that record's balance - amount
        if transactions[first_transaction].status == 'duplicate':
            matching_transaction = get_transaction_by_account_and_hash(transactions[first_transaction].account_id, transactions[first_transaction].hash)
            opening_balance = matching_transaction.balance - matching_transaction.amount
            return opening_balance
        
        # if the last transaction is a duplicate, then retrieve the matching transaction and calculate the opening balance as that record's balance - sum of amounts across all transactions in the list
        if transactions[last_transaction].status == 'duplicate':
            matching_transaction = get_transaction_by_account_and_hash(transactions[last_transaction].account_id, transactions[last_transaction].hash)
            opening_balance = matching_transaction.balance - sum(tx.amount for tx in transactions)
            return opening_balance
        
        # if there is no overlap, return None
        return None

    except Exception as e:
        logger.error(f"Error determining opening balance: {str(e)}")


def process_new_file(transaction_file: TransactionFile, content_bytes: bytes) -> Dict[str, Any]:
    """Process a newly uploaded file."""
    try:
        # Determine file format
        determine_file_format(transaction_file, content_bytes)
        
        # Get field mapping
        determine_field_mapping(transaction_file)
        
        # Parse transactions
        transactions = parse_file_transactions(
            transaction_file.account_id,
            content_bytes,
            transaction_file.file_format,
            transaction_file.opening_balance,
            transaction_file.field_map
        )
        if transactions:
            update_transaction_duplicates(transactions)

            # Determine opening balance from transaction overlap
            opening_balance = determine_opening_balances_from_transaction_overlap(transactions)
            transaction_file.opening_balance = opening_balance if opening_balance else transaction_file.opening_balance
            # Calculate running balances
            calculate_running_balances(transactions, transaction_file.opening_balance)
            
            # Save transactions
            transaction_count, duplicate_count = save_transactions(
                transactions,
                transaction_file,
                transaction_file.user_id,
                transaction_file.account
            )
            
            # Update file status
            update_file_status(transaction_file, transactions)
        
        return create_response(200, {
            "message": "File processed successfully",
            "transactionCount": transaction_count if transactions else 0,
            "duplicateCount": duplicate_count if transactions else 0,
            "fileId": transaction_file.file_id,
            "file": transaction_file.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error processing file2: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error processing file2: {str(e)}")

def update_file_mapping(transaction_file: TransactionFile) -> List[Transaction]:
    """Update a file's field mapping and reprocess transactions."""
    try:
        # Get field map
        field_map = checked_mandatory_field_mapping(transaction_file.field_map_id, transaction_file.user_id)
           
        # Check if field mapping has changed
        should_reprocess = (
            transaction_file.field_map_id != field_map.field_map_id or
            transaction_file.field_map_id is None
        )
        
        if should_reprocess:
            # Get file content
            content_bytes = get_file_content(transaction_file.file_id)
            if not content_bytes:
                return handle_error(404, "File content not found")
                
            # Delete existing transactions
            logger.info(f"Field mapping has changed for file {transaction_file.file_id} - deleting existing transactions")
            delete_transactions_for_file(transaction_file.file_id)
            
            # Process with new mapping
            transactions = parse_file_transactions(
                transaction_file.account_id,
                content_bytes,
                transaction_file.file_format,
                transaction_file.opening_balance,
                field_map
            )
            
        if transactions:
            update_transaction_duplicates(transactions)

            # Determine opening balance from transaction overlap
            opening_balance = determine_opening_balances_from_transaction_overlap(transactions)
            transaction_file.opening_balance = opening_balance if opening_balance else transaction_file.opening_balance
            # Calculate running balances
            calculate_running_balances(transactions, transaction_file.opening_balance)
            
            # Save transactions
            transaction_count, duplicate_count = save_transactions(
                transactions,
                transaction_file,
                transaction_file.user_id,
                transaction_file.account
            )
            
            # Update file status
            update_file_status(transaction_file, transactions)
            
            return create_response(200, {
                "message": "File remapped successfully",
                "transactionCount": transaction_count,
                "duplicateCount": duplicate_count
            })
        else:
            return create_response(200, {
                "message": "Field map is unchanged, no reprocessing needed"
            })
            
    except Exception as e:
        logger.error(f"Error remapping file: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error remapping file: {str(e)}")

def update_opening_balance(transaction_file: TransactionFile):
    """Update a file's opening balance without reprocessing transactions."""
    try:
        # Get and validate file record
        old_transaction_file = checked_mandatory_file(transaction_file.file_id, transaction_file.user_id)

        balance_change = transaction_file.opening_balance - old_transaction_file.opening_balance
            
        # Update all transactions from account adding balance change to the balance

        transactions = list_account_transactions(transaction_file.account_id)
                    
        # Update transactions in database
        for tx in transactions:
            tx.balance += balance_change
            update_transaction_file(tx)
        
        transaction_files = list_account_files(transaction_file.account_id)
        for file in transaction_files:
            file.opening_balance = file.opening_balance + balance_change
            update_transaction_file(file)
        
        return create_response(200, {
            "message": "Opening balance updated successfully",
            "transactionCount": len(transactions)
        })
        
    except Exception as e:
        logger.error(f"Error updating opening balance: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error updating opening balance: {str(e)}")

def change_file_account(transaction_file: TransactionFile):
    """Reassign a file to a different account."""
    try:
        # Get old transaction_file
        old_transaction_file = checked_mandatory_file(transaction_file.file_id, transaction_file.user_id)

        # Validate new account
        account = checked_mandatory_account(transaction_file.account_id, transaction_file.user_id)
   
        # Update file record with new account ID
        update_transaction_file(transaction_file)
    
        # Get existing transactions
        transactions = list_file_transactions(transaction_file.file_id)
        if transactions:
            update_transaction_duplicates(transactions)
            # Determine opening balance from transaction overlap
            opening_balance = determine_opening_balances_from_transaction_overlap(transactions)
            transaction_file.opening_balance = opening_balance if opening_balance else transaction_file.opening_balance
            # Calculate running balances
            calculate_running_balances(transactions, transaction_file.opening_balance)
            # Update account ID for all transactions
            for tx in transactions:
                tx.account_id = transaction_file.account_id
                update_transaction_file(tx)
                
        return create_response(200, {
            "message": "File account updated successfully",
            "transactionCount": len(transactions) if transactions else 0,
            "file": transaction_file.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error changing file account: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error changing file account: {str(e)}")

def process_file(transaction_file: TransactionFile) -> Dict[str, Any]:
    """
    Main entry point for processing a new file.
    
    Args:
        file_id: ID of the file to process
        content_bytes: Raw file content
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with processing results
    """
    try:
        # Create the file record
        create_transaction_file(transaction_file)
        logger.info(f"Created file metadata in DynamoDB: {json.dumps(transaction_file.to_dict())}")
        content_bytes = get_file_content(transaction_file.file_id)
        if not content_bytes:
            return handle_error(404, "File content not found")
            
        return process_new_file(transaction_file, content_bytes)
        
    except Exception as e:
        logger.error(f"Error in process_file: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error processing file1: {str(e)}")

def remap_file(transaction_file: TransactionFile) -> Dict[str, Any]:
    """
    Main entry point for updating a file's field mapping.
    
    Args:
        file_id: ID of the file to remap
        field_map_id: ID of the new field map to use
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with remapping results
    """
    try:
        return update_file_mapping(transaction_file)
    except Exception as e:
        logger.error(f"Error in remap_file: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error remapping file: {str(e)}")

def update_balance(transaction_file: TransactionFile) -> Dict[str, Any]:
    """
    Main entry point for updating a file's opening balance.
    
    Args:
        file_id: ID of the file to update
        opening_balance: New opening balance
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with balance update results
    """
    try:
        return update_opening_balance(transaction_file)
    except Exception as e:
        logger.error(f"Error in update_balance: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error updating balance: {str(e)}")

def reassign_file(transaction_file: TransactionFile) -> Dict[str, Any]:
    """
    Main entry point for changing a file's account.
    
    Args:
        file_id: ID of the file to reassign
        account_id: ID of the new account
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with reassignment results
    """
    try:
        return change_file_account(transaction_file)
    except Exception as e:
        logger.error(f"Error in reassign_file: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error reassigning file: {str(e)}")

def process_file_with_account(transaction_file: TransactionFile) -> Dict[str, Any]:
    """
    Legacy entry point that routes to appropriate handler based on context.
    
    Args:
        file_id: ID of the file to process
        account_id: ID of the account to process with
        user_id: ID of the user who owns the file
        
    Returns:
        API Gateway response with processing results
    """
    try:
        old_transaction_file = checked_optional_file(transaction_file.file_id, transaction_file.user_id)

        if not old_transaction_file and transaction_file.processing_status == ProcessingStatus.PENDING:
            return process_file(transaction_file)

        # Route to appropriate handler based on context
        if transaction_file.account_id != old_transaction_file.account_id:
            # Account is changing
            return reassign_file(transaction_file)
            # determine if field map or balance update
        if transaction_file.field_map_id != old_transaction_file.field_map_id:
            return remap_file(transaction_file)
        if transaction_file.opening_balance != old_transaction_file.opening_balance:
            return update_balance(transaction_file)
                
    except Exception as e:
        logger.error(f"Error in process_file_with_account: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return handle_error(500, f"Error processing file with account: {str(e)}")


