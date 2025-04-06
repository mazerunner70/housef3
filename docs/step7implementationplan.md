# Step 7 Implementation Plan: Optional Account-File Association

## Overview
This document outlines the plan for implementing optional associations between transaction files and accounts in the housef3 application. Files can exist independently or be linked to specific accounts based on user needs.

## Database Schema Changes

1. **Modify transaction_files table**:
   - Add an optional `account_id` field as a foreign key to the accounts table
   - Ensure this field can be null to support standalone files
   - Create a new GSI (Global Secondary Index) on the `account_id` field for efficient querying
   - Update any existing indices to include the new field where appropriate

## Database Utility Functions (utils/db_utils.py)

2. **Enhance transaction file operations**:
   - Update `create_transaction_file` to accept an optional `account_id` parameter
   - Add a new function `list_account_files(account_id)` to retrieve files for a specific account
   - Keep all existing file operations working for files without account associations
   - Ensure proper error handling for invalid account associations

3. **Update transaction file model**:
   - Modify `TransactionFile` class to include the optional account_id field
   - Update `to_dict()` and `from_dict()` methods to handle the new field
   - Add validation for account association in `validate_transaction_file_data`

## Lambda Handler Updates

4. **Update file_operations.py**:
   - Modify the file creation endpoint to accept an optional account_id
   - Add validation to ensure the user owns the account when associating files
   - Keep all standalone file operations working unchanged
   - Ensure proper error responses for invalid account associations

5. **Enhance account_operations.py**:
   - Add a new handler for the `GET /accounts/{id}/files` endpoint
   - Implement file upload functionality specific to accounts via `POST /accounts/{id}/files` 
   - Add validation to ensure users can only access files for their own accounts
   - Implement proper error handling and responses

## API Gateway Configuration

6. **Add new routes**:
   - `GET /accounts/{id}/files` - List all files for a specific account
   - `POST /accounts/{id}/files` - Upload a file and associate it with an account

7. **Update API documentation**:
   - Document the new endpoints with request/response examples
   - Explain the optional nature of account-file associations
   - Provide usage recommendations for different scenarios

## Frontend Integration (if applicable)

8. **Update UI components**:
   - Add file management sections to account detail views
   - Create interfaces for uploading files directly to accounts
   - Show linked files in account views
   - Maintain the standalone file management interface

## Testing Strategy

9. **Unit tests**:
   - Test the database utility functions with and without account associations
   - Verify proper validation of account ownership
   - Ensure null account_ids are handled correctly

10. **Integration tests**:
   - Update `test_account_operations.sh` to test the new account file endpoints
   - Verify files can be created with and without account associations
   - Test listing files by account
   - Confirm proper error handling for invalid scenarios

11. **End-to-end tests**:
   - Test the complete file upload flow with account association
   - Verify files appear correctly in account-specific views
   - Ensure standalone files continue to work as before

## Implementation Sections

1. Start with database schema changes and utility functions
2. Update Lambda handlers to support the new association pattern
3. Configure API Gateway with the new routes
4. Implement frontend changes if applicable
5. Create comprehensive tests for all scenarios
6. Deploy changes incrementally, starting with development environment

## Rollback Plan

1. Revert database schema changes if issues are detected
2. Have backup Lambda code ready for quick redeployment
3. Document specific rollback steps for each component

## Timeline

- Database changes: 1 day
- Utility function updates: 1 day
- Lambda handler implementation: 2 days
- Testing and validation: 2 days
- Deployment and monitoring: 1 day

Total estimated time: 7 working days 