# Transaction File Handling - Implementation Plan (Minimal Changes)

## Analysis of Current Implementation

Based on review of the current codebase, the core functionality for transaction file handling is mostly implemented, but some refinements are needed to meet the requirements in the documentation. Below is a minimal changes implementation plan focused on enhancing the existing functionality.

## Refactoring Approach for `process_file_with_account`

### Step 1: Initial Setup (1 day)

1. **Create a new module for refactored code**
   - Create a new file `backend/src/services/file_processor_service.py`
   - This will contain all the smaller, focused functions that will replace the monolithic function
   - Start with imports and basic structure

2. **Extract common utility functions**
   - Write the helper functions that will be used by multiple specialized handlers:
     ```python
     def prepare_file_processing(file_id: str, user_id: str) -> TransactionFile:
         """Retrieve file record and validate it exists and belongs to the specified user."""
         
     def determine_file_format(file_record: TransactionFile, content_bytes: bytes) -> FileFormat:
         """Determine or validate the file format."""
         
     def determine_field_mapping(file_record: TransactionFile, user_id: str) -> Optional[FieldMap]:
         """Determine which field mapping to use for the file."""
         
     def parse_file_transactions(account_id: str, content_bytes: bytes, 
                                file_format: FileFormat, 
                                opening_balance: Decimal,
                                field_map: Optional[FieldMap]) -> List[Transaction]:
         """Parse transactions from file content."""
         
     def calculate_running_balances(transactions: List[Transaction], opening_balance: Money) -> None:
         """Update running balances for all transactions in the list."""
         
     def save_transactions(transactions: List[Transaction], 
                          transaction_file: TransactionFile, 
                          user_id: str, 
                          account: Account) -> Tuple[int, int]:
         """Save transactions to the database."""
         
     def update_file_status(transaction_file: TransactionFile, 
                           field_map_id: Optional[str], 
                           transactions: List[Transaction]) -> TransactionFile:
         """Update file metadata after processing."""
         
     def update_transaction_duplicates(transactions: List[Transaction]) -> int:
         """Check for duplicate transactions in a list of transactions."""
     ```

### Step 2: Create Specialized Handlers (2 days)

1. **Process New File Handler**
   ```python
   def process_new_file(file_id: str, content_bytes: bytes, opening_balance: Money, user_id: str) -> Dict[str, Any]:
       """Process a newly uploaded file."""
       # Implementation
   ```

2. **Update File Mapping Handler**
   ```python
   def update_file_mapping(file_id: str, field_map_id: str, user_id: str) -> Dict[str, Any]:
       """Update a file's field mapping and reprocess transactions."""
       # Implementation that includes deleting transactions
   ```

3. **Update Opening Balance Handler**
   ```python
   def update_opening_balance(file_id: str, opening_balance: Money, user_id: str) -> Dict[str, Any]:
       """Update a file's opening balance without reprocessing transactions."""
       # Implementation that preserves transactions
   ```

4. **Change File Account Handler**
   ```python
   def change_file_account(file_id: str, account_id: str, user_id: str) -> Dict[str, Any]:
       """Reassign a file to a different account."""
       # Implementation
   ```

### Step 3: Create Main Entry Function (1/2 day)

1. **Define Main Entry Points**
   ```python
   def process_file(file_id: str, content_bytes: bytes, user_id: str) -> Dict[str, Any]:
       """
       Main entry point for processing a new file.
       
       Args:
           file_id: ID of the file to process
           content_bytes: Raw file content
           user_id: ID of the user who owns the file
           
       Returns:
           API Gateway response with processing results
       """
       return process_new_file(file_id, content_bytes, user_id)

   def remap_file(file_id: str, field_map_id: str, user_id: str) -> Dict[str, Any]:
       """
       Main entry point for updating a file's field mapping.
       
       Args:
           file_id: ID of the file to remap
           field_map_id: ID of the new field map to use
           user_id: ID of the user who owns the file
           
       Returns:
           API Gateway response with remapping results
       """
       return update_file_mapping(file_id, field_map_id, user_id)

   def update_balance(file_id: str, opening_balance: Money, user_id: str) -> Dict[str, Any]:
       """
       Main entry point for updating a file's opening balance.
       
       Args:
           file_id: ID of the file to update
           opening_balance: New opening balance
           user_id: ID of the user who owns the file
           
       Returns:
           API Gateway response with balance update results
       """
       return update_opening_balance(file_id, opening_balance, user_id)

   def reassign_file(file_id: str, account_id: str, user_id: str) -> Dict[str, Any]:
       """
       Main entry point for changing a file's account.
       
       Args:
           file_id: ID of the file to reassign
           account_id: ID of the new account
           user_id: ID of the user who owns the file
           
       Returns:
           API Gateway response with reassignment results
       """
       return change_file_account(file_id, account_id, user_id)
   ```

2. **Update Original Function**
   ```python
   def process_file_with_account(file_id: str, account_id: str, user_id: str) -> Dict[str, Any]:
       """
       Legacy entry point that routes to appropriate handler based on context.
       
       Args:
           file_id: ID of the file to process
           account_id: ID of the account to process with
           user_id: ID of the user who owns the file
           
       Returns:
           API Gateway response with processing results
       """
       # Get file record to determine context
       file_record = prepare_file_processing(file_id, user_id)
       
       if not file_record:
           return handle_error(404, "File not found")
           
       # Route to appropriate handler based on context
       if file_record.account_id != account_id:
           # Account is changing
           return reassign_file(file_id, account_id, user_id)
       elif file_record.processing_status == ProcessingStatus.PENDING:
           # New file processing
           content_bytes = get_file_content(file_id)
           return process_file(file_id, content_bytes, user_id)
       else:
           # Existing file - determine if field map or balance update
           if file_record.field_map_id:
               return remap_file(file_id, file_record.field_map_id, user_id)
           else:
               return update_balance(file_id, file_record.opening_balance, user_id)
   ```

3. **Implementation Notes**
   - Each entry point is focused on a specific use case
   - Entry points handle basic validation and error handling
   - Legacy function routes to appropriate handler based on context
   - All responses use standardized format from `lambda_utils`
   - Logging is consistent across all entry points
   - Error handling follows established patterns

4. **Testing Strategy**
   - Test each entry point independently
   - Verify routing logic in legacy function
   - Test error cases and edge conditions
   - Verify response formats match API Gateway requirements
   - Test with various file types and sizes
   - Verify logging and monitoring

### Step 4: Transition Plan (1 day)

1. **Phase 1: Dual Implementation**
   - Keep the original `process_file_with_account` function
   - Implement the new service module with all refactored functions
   - Create a simple toggle in environment variables to switch between old and new implementation

2. **Phase 2: Testing**
   - Create comprehensive tests for new implementation
   - Test with existing files and verify results match
   - Manually validate edge cases

3. **Phase 3: Switchover**
   - Modify the original function to call the new implementation
   - Keep original function as a thin wrapper for backward compatibility
   - Update all direct callers to use the new implementation

### Step 5: Function-by-Function Implementation Guide

For each extracted function, follow this implementation pattern:

1. **Initial implementation**
   - Identify the relevant section in the original function
   - Extract it to the new function with minimal changes
   - Add appropriate error handling and logging

2. **Testing**
   - Create unit tests for the function
   - Verify it works correctly in isolation
   - Test with edge cases and error conditions

3. **Integration**
   - Connect the function to other refactored functions
   - Test the flow through multiple functions
   - Verify end-to-end functionality matches original

## Phase 1: Improve Logging and Monitoring (1-2 days)

### Enhancement of Logging
- [ ] Add more detailed logging to `delete_transactions_for_file` to track what's being deleted
- [ ] Add transaction counts and status information to all major operations
- [ ] Improve error reporting for failed processing

## Phase 2: Code Refactoring for Maintainability (3-4 days)

### Breaking Down the Monolithic Function
- [ ] Refactor `process_file_with_account` into smaller, more focused functions:
  - [ ] `prepare_file_processing` - Validates file and gets necessary metadata
  - [ ] `determine_field_mapping` - Handles field map selection logic
  - [ ] `parse_file_transactions` - Parses transactions based on file format
  - [ ] `calculate_running_balances` - Updates balances for all transactions
  - [ ] `save_transactions` - Handles saving transactions to the database
  - [ ] `update_file_status` - Updates the file metadata after processing
  - [ ] `update_transaction_duplicates` - Manages duplicate transaction detection

- [ ] Create specialized handlers for different use cases:
  - [ ] `process_new_file` - For initial file processing
  - [ ] `update_file_mapping` - For changing field mapping only (should delete and reprocess transactions)
  - [ ] `update_opening_balance` - For recalculating balances only (should preserve transactions)
  - [ ] `change_file_account` - For reassigning file to different account

## Phase 3: Opening Balance Optimization (2-3 days)

### Enhancing Duplicate Detection for Opening Balance
- [ ] Improve `calculate_opening_balance_from_duplicates` to properly detect when a file overlaps with existing transactions
- [ ] Add logic to handle first/last transaction duplicates to set file opening balance
- [ ] Update transaction reprocessing to avoid deleting transactions when only the opening balance changes

## Phase 4: Field Mapping Improvements (3-4 days)

### Refining Field Map Handling
- [ ] Enhance error handling in CSV parser when field maps are missing or incorrect
- [ ] Add validation for field maps to ensure required fields are present
- [ ] Improve UI guidance for users creating field maps

## Phase 5: Error Handling and Recovery (2-3 days)

### Making the System More Robust
- [ ] Add transaction versioning to allow for recovery from failed processing
- [ ] Implement better error reporting in the UI for failed file processing
- [ ] Create a mechanism to retry failed file processing

## Phase 6: Testing and Documentation (2-3 days)

### Ensuring Reliability
- [ ] Create comprehensive test cases for all file handling scenarios
- [ ] Update documentation to match actual implementation
- [ ] Create user guides for handling different file formats

## Implementation Details

### Specific Code Changes Required

1. **Function Separation Example**
   ```python
   # Instead of the monolithic process_file_with_account function,
   # break it down into smaller functions like:
   
   def prepare_file_processing(file_id: str, user_id: str) -> TransactionFile:
       """Retrieve file record and validate it exists and belongs to the specified user."""
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
   
   def determine_field_mapping(file_record: TransactionFile, user_id: str) -> Optional[FieldMap]:
       """Determine which field mapping to use for the file."""
       try:
           field_map = None
           field_map_id = file_record.field_map_id
           account_id = file_record.account_id
           
           logger.info(f"Determining field mapping - Field map ID: {field_map_id}, Account ID: {account_id}")
           
           if field_map_id:
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
   ```

2. **Enhanced `delete_transactions_for_file` Function**
   ```python
   # Add more detailed logging
   try:
       # Get all transactions for the file
       transactions = list_file_transactions(file_id)
       count = len(transactions)
       
       if count > 0:
           logger.info(f"Found {count} transactions to delete for file {file_id}")
           # Log details of first few transactions
           for i, tx in enumerate(transactions[:5]):
               logger.info(f"Deleting transaction: ID={tx.transaction_id}, Date={tx.date}, Amount={tx.amount}, Description={tx.description}")
           if count > 5:
               logger.info(f"... and {count - 5} more transactions")
           
           # Delete transactions in batches
           table = get_transactions_table()
           with table.batch_writer() as batch:
               for transaction in transactions:
                   batch.delete_item(Key={'transactionId': transaction.transaction_id})
           
           logger.info(f"Successfully deleted {count} transactions for file {file_id}")
       else:
           logger.info(f"No transactions found to delete for file {file_id}")
       
       return count
   ```

3. **Enhance `calculate_opening_balance_from_duplicates`**
   ```python
   # Check first and last transactions for duplicates
   if transactions and account_id:
       first_tx = transactions[0]
       last_tx = transactions[-1]
       
       # Generate hashes for first and last transactions
       first_hash = generate_transaction_hash(
           account_id, 
           first_tx['date'], 
           Decimal(str(first_tx['amount'])), 
           first_tx['description']
       )
       
       last_hash = generate_transaction_hash(
           account_id, 
           last_tx['date'], 
           Decimal(str(last_tx['amount'])), 
           last_tx['description']
       )
       
       # Check if they're duplicates
       first_duplicate = get_transaction_by_account_and_hash(account_id, first_hash)
       last_duplicate = get_transaction_by_account_and_hash(account_id, last_hash)
       
       if first_duplicate or last_duplicate:
           # Use the duplicate to calculate opening balance
           # Implementation details depend on exact business logic
   ```

## Testing Plan

1. **Unit Tests**
   - Test each of the refactored small functions independently
   - Test transaction deletion logic when field mapping changes
   - Test transaction preservation when only opening balance changes
   - Test duplicate detection and opening balance calculation
   - Test field mapping with various CSV formats

2. **Integration Tests**
   - Test each specialized handler for different use cases
   - Test end-to-end file upload and processing
   - Test file reprocessing with different changes (account ID, opening balance, field map)
   - Test duplicate transaction handling

3. **Edge Cases**
   - Test with very large files
   - Test with malformed or corrupt files
   - Test concurrent file processing

## Success Criteria

1. Existing transactions are only deleted when field mapping changes
2. Opening balances are correctly calculated from duplicates
3. Field mappings work reliably for various CSV formats
4. Error handling provides clear guidance for users
5. The system is robust against common failure modes
6. Code is modular and easier to maintain with well-defined responsibilities
