# Transaction Parsing Feature Implementation Guide

## Overview

This document outlines the step-by-step implementation of a transaction parsing feature for the HouseF3 application. The feature will parse financial files and extract individual transactions, maintaining a running total starting from the opening balance.

## 1. Data Model Design

### 1.1 Create a Transaction Model

First, we need to define the Transaction model to store parsed transaction data.

```python
# backend/src/models/transaction.py

import uuid
from typing import Dict, Any, Optional
from datetime import datetime

class Transaction:
    """
    Represents a single financial transaction parsed from a transaction file.
    """
    def __init__(
        self,
        transaction_id: str,
        file_id: str,
        date: str,
        description: str,
        amount: float,
        running_total: float,
        transaction_type: Optional[str] = None,
        category: Optional[str] = None,
        payee: Optional[str] = None,
        memo: Optional[str] = None,
        check_number: Optional[str] = None,
        reference: Optional[str] = None
    ):
        self.transaction_id = transaction_id
        self.file_id = file_id
        self.date = date
        self.description = description
        self.amount = amount
        self.running_total = running_total
        self.transaction_type = transaction_type
        self.category = category
        self.payee = payee
        self.memo = memo
        self.check_number = check_number
        self.reference = reference
        
    @classmethod
    def create(
        cls,
        file_id: str,
        date: str,
        description: str,
        amount: float,
        running_total: float,
        **kwargs
    ) -> 'Transaction':
        """
        Factory method to create a new transaction with a generated ID.
        """
        return cls(
            transaction_id=str(uuid.uuid4()),
            file_id=file_id,
            date=date,
            description=description,
            amount=amount,
            running_total=running_total,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the transaction object to a dictionary suitable for storage.
        """
        result = {
            "transactionId": self.transaction_id,
            "fileId": self.file_id,
            "date": self.date,
            "description": self.description,
            "amount": str(self.amount),  # Convert to string for DynamoDB
            "runningTotal": str(self.running_total)  # Convert to string for DynamoDB
        }
        
        # Add optional fields if they exist
        if self.transaction_type:
            result["transactionType"] = self.transaction_type
            
        if self.category:
            result["category"] = self.category
            
        if self.payee:
            result["payee"] = self.payee
            
        if self.memo:
            result["memo"] = self.memo
            
        if self.check_number:
            result["checkNumber"] = self.check_number
            
        if self.reference:
            result["reference"] = self.reference
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """
        Create a transaction object from a dictionary (e.g. from DynamoDB).
        """
        return cls(
            transaction_id=data["transactionId"],
            file_id=data["fileId"],
            date=data["date"],
            description=data["description"],
            amount=float(data["amount"]),
            running_total=float(data["runningTotal"]),
            transaction_type=data.get("transactionType"),
            category=data.get("category"),
            payee=data.get("payee"),
            memo=data.get("memo"),
            check_number=data.get("checkNumber"),
            reference=data.get("reference")
        )
```

### 1.2 Set Up the DynamoDB Table

Create a DynamoDB table for storing transactions:

```terraform
# infrastructure/terraform/dynamodb.tf

# Transaction table
resource "aws_dynamodb_table" "transactions" {
  name           = "${var.project_name}-${var.environment}-transactions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "transactionId"
  
  attribute {
    name = "transactionId"
    type = "S"
  }
  
  attribute {
    name = "fileId"
    type = "S"
  }
  
  # GSI to query transactions by file ID
  global_secondary_index {
    name               = "FileIdIndex"
    hash_key           = "fileId"
    projection_type    = "ALL"
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

```

## 2. Database Operations

Add utility functions for transaction operations in `db_utils.py`:

```python
# backend/src/utils/db_utils.py

# Add these imports
from models.transaction import Transaction
from boto3.dynamodb.conditions import Key

# Add these environment variables
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE')
transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)

# Add these functions for transaction operations

def list_file_transactions(file_id: str) -> List[Dict[str, Any]]:
    """
    List all transactions for a specific file.
    
    Args:
        file_id: ID of the file to get transactions for
        
    Returns:
        List of transaction objects
    """
    try:
        response = transactions_table.query(
            IndexName='FileIdIndex',
            KeyConditionExpression=Key('fileId').eq(file_id)
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error listing transactions for file {file_id}: {str(e)}")
        raise

def create_transaction(transaction_data: Dict[str, Any]) -> Transaction:
    """
    Create a new transaction.
    
    Args:
        transaction_data: Dictionary containing transaction data
        
    Returns:
        The created Transaction object
    """
    try:
        # Create a Transaction object
        transaction = Transaction.create(**transaction_data)
        
        # Save to DynamoDB
        transactions_table.put_item(Item=transaction.to_dict())
        
        return transaction
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise

def delete_file_transactions(file_id: str) -> int:
    """
    Delete all transactions for a file.
    
    Args:
        file_id: ID of the file whose transactions should be deleted
        
    Returns:
        Number of deleted transactions
    """
    try:
        # First, get all transactions for the file
        transactions = list_file_transactions(file_id)
        deleted_count = 0
        
        # Delete each transaction
        with transactions_table.batch_writer() as batch:
            for transaction in transactions:
                batch.delete_item(
                    Key={
                        'transactionId': transaction['transactionId']
                    }
                )
                deleted_count += 1
                
        return deleted_count
    except Exception as e:
        logger.error(f"Error deleting transactions for file {file_id}: {str(e)}")
        raise
```

## 3. Transaction Parsing Logic

Implement the transaction parsing logic for different file formats:

```python
# backend/src/utils/transaction_parser.py

import csv
import io
import re
import logging
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from models.transaction_file import FileFormat

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def parse_transactions(content: bytes, 
                       file_format: FileFormat, 
                       opening_balance: float) -> List[Dict[str, Any]]:
    """
    Parse transactions from file content based on the file format.
    
    Args:
        content: The raw file content
        file_format: The format of the file (CSV, OFX, etc.)
        opening_balance: The opening balance to use for running total calculation
        
    Returns:
        List of transaction dictionaries
    """
    if file_format == FileFormat.CSV:
        return parse_csv_transactions(content, opening_balance)
    elif file_format in [FileFormat.OFX, FileFormat.QFX]:
        return parse_ofx_transactions(content, opening_balance)
    else:
        logger.warning(f"Unsupported file format for transaction parsing: {file_format}")
        return []

def parse_csv_transactions(content: bytes, opening_balance: float) -> List[Dict[str, Any]]:
    """
    Parse transactions from CSV file content.
    
    Args:
        content: The raw CSV file content
        opening_balance: The opening balance to use for running total calculation
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode the content
        text_content = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.reader(io.StringIO(text_content))
        
        # Try to determine the header row and column mappings
        header = next(csv_reader, None)
        if not header:
            return []
            
        # Try to identify column positions
        date_col = find_column_index(header, ['date', 'transaction date', 'posted date'])
        desc_col = find_column_index(header, ['description', 'payee', 'memo', 'note'])
        amount_col = find_column_index(header, ['amount', 'transaction amount'])
        
        if date_col is None or desc_col is None or amount_col is None:
            logger.warning("Could not identify required columns in CSV file")
            return []
            
        # Parse transactions
        transactions = []
        running_total = opening_balance
        
        for row in csv_reader:
            if len(row) <= max(date_col, desc_col, amount_col):
                continue  # Skip rows that don't have enough columns
                
            try:
                # Parse date
                date_str = row[date_col].strip()
                # Try multiple date formats
                date = parse_date(date_str)
                if not date:
                    continue
                    
                # Parse description
                description = row[desc_col].strip()
                if not description:
                    continue
                    
                # Parse amount
                amount_str = row[amount_col].strip().replace('$', '').replace(',', '')
                amount = float(amount_str)
                
                # Calculate running total
                running_total += amount
                
                # Create transaction dictionary
                transaction = {
                    'date': date,
                    'description': description,
                    'amount': amount,
                    'running_total': running_total
                }
                
                # Add optional fields if they exist
                type_col = find_column_index(header, ['type', 'transaction type'])
                if type_col is not None and len(row) > type_col:
                    transaction['transaction_type'] = row[type_col].strip()
                    
                category_col = find_column_index(header, ['category', 'classification'])
                if category_col is not None and len(row) > category_col:
                    transaction['category'] = row[category_col].strip()
                    
                memo_col = find_column_index(header, ['memo', 'notes', 'comments'])
                if memo_col is not None and len(row) > memo_col:
                    transaction['memo'] = row[memo_col].strip()
                
                transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error parsing CSV row: {str(e)}")
                continue
                
        return transactions
    except Exception as e:
        logger.error(f"Error parsing CSV transactions: {str(e)}")
        return []

def parse_ofx_transactions(content: bytes, opening_balance: float) -> List[Dict[str, Any]]:
    """
    Parse transactions from OFX/QFX file content.
    
    Args:
        content: The raw OFX/QFX file content
        opening_balance: The opening balance to use for running total calculation
        
    Returns:
        List of transaction dictionaries
    """
    try:
        # Decode content
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            text_content = content.decode('latin-1')
            
        # Check if it's SGML or XML format
        if '<OFX>' in text_content:
            # It's XML-like, try to parse with ElementTree
            return parse_xml_ofx(text_content, opening_balance)
        else:
            # It's SGML-like, use regex to extract transactions
            return parse_sgml_ofx(text_content, opening_balance)
    except Exception as e:
        logger.error(f"Error parsing OFX transactions: {str(e)}")
        return []

def parse_xml_ofx(content: str, opening_balance: float) -> List[Dict[str, Any]]:
    """Parse XML-like OFX content."""
    # This is a simplified implementation - real-world OFX parsing is more complex
    transactions = []
    running_total = opening_balance
    
    try:
        # Extract transaction sections
        transaction_blocks = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', content, re.DOTALL)
        
        for block in transaction_blocks:
            try:
                # Extract transaction details using regex
                date_match = re.search(r'<DTPOSTED>(.*?)</DTPOSTED>', block)
                amount_match = re.search(r'<TRNAMT>(.*?)</TRNAMT>', block)
                name_match = re.search(r'<NAME>(.*?)</NAME>', block) or re.search(r'<MEMO>(.*?)</MEMO>', block)
                memo_match = re.search(r'<MEMO>(.*?)</MEMO>', block)
                type_match = re.search(r'<TRNTYPE>(.*?)</TRNTYPE>', block)
                
                if date_match and amount_match and name_match:
                    # Parse date (format: YYYYMMDD)
                    date_str = date_match.group(1)
                    if len(date_str) >= 8:
                        year = date_str[0:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        date = f"{year}-{month}-{day}"
                    else:
                        date = date_str
                        
                    # Parse amount
                    amount = float(amount_match.group(1))
                    
                    # Calculate running total
                    running_total += amount
                    
                    # Create transaction
                    transaction = {
                        'date': date,
                        'description': name_match.group(1),
                        'amount': amount,
                        'running_total': running_total
                    }
                    
                    # Add optional fields
                    if memo_match and memo_match.group(1) != name_match.group(1):
                        transaction['memo'] = memo_match.group(1)
                        
                    if type_match:
                        transaction['transaction_type'] = type_match.group(1)
                        
                    transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error parsing OFX transaction block: {str(e)}")
                continue
                
        return transactions
    except Exception as e:
        logger.error(f"Error parsing XML OFX: {str(e)}")
        return []

def parse_sgml_ofx(content: str, opening_balance: float) -> List[Dict[str, Any]]:
    """Parse SGML-like OFX content."""
    # This is a simplified implementation - real-world SGML OFX parsing is more complex
    transactions = []
    running_total = opening_balance
    
    try:
        # Find all transaction sections
        transaction_pattern = r'<STMTTRN>(.*?)\s*(?=<STMTTRN>|</BANKTRANLIST>)'
        transaction_blocks = re.findall(transaction_pattern, content, re.DOTALL)
        
        for block in transaction_blocks:
            try:
                # Extract fields using regex
                date_match = re.search(r'DTPOSTED:(.*?)\s', block)
                amount_match = re.search(r'TRNAMT:(.*?)\s', block)
                name_match = re.search(r'NAME:(.*?)\s', block) or re.search(r'MEMO:(.*?)\s', block)
                memo_match = re.search(r'MEMO:(.*?)\s', block)
                type_match = re.search(r'TRNTYPE:(.*?)\s', block)
                
                if date_match and amount_match and name_match:
                    # Parse date (format varies, attempt YYYYMMDD)
                    date_str = date_match.group(1).strip()
                    if len(date_str) >= 8:
                        year = date_str[0:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        date = f"{year}-{month}-{day}"
                    else:
                        date = date_str
                        
                    # Parse amount
                    amount = float(amount_match.group(1).strip())
                    
                    # Calculate running total
                    running_total += amount
                    
                    # Create transaction
                    transaction = {
                        'date': date,
                        'description': name_match.group(1).strip(),
                        'amount': amount,
                        'running_total': running_total
                    }
                    
                    # Add optional fields
                    if memo_match and memo_match.group(1) != name_match.group(1):
                        transaction['memo'] = memo_match.group(1).strip()
                        
                    if type_match:
                        transaction['transaction_type'] = type_match.group(1).strip()
                        
                    transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error parsing SGML OFX transaction: {str(e)}")
                continue
                
        return transactions
    except Exception as e:
        logger.error(f"Error parsing SGML OFX: {str(e)}")
        return []

# Helper functions

def find_column_index(header: List[str], possible_names: List[str]) -> Optional[int]:
    """Find the index of a column with one of the given names."""
    for name in possible_names:
        for i, column in enumerate(header):
            if name.lower() in column.lower():
                return i
    return None

def parse_date(date_str: str) -> Optional[str]:
    """Try to parse a date string in various formats."""
    date_formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y',
        '%Y/%m/%d', '%m/%d/%y', '%d/%m/%y', '%b %d, %Y', '%d %b %Y'
    ]
    
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime('%Y-%m-%d')  # Standardize to ISO format
        except ValueError:
            continue
            
    return date_str  # Return the original if we can't parse it
```

## 4. Transaction Processing Triggers

### 4.1 Automatic Processing on File Upload

When a file is uploaded and has an opening balance, we need to trigger the transaction parsing automatically. This occurs in two scenarios:

1. When a file is uploaded with an opening balance already specified
2. When an opening balance is added or modified for an existing file

Update the file processor handler to trigger transaction parsing automatically:

```python
# backend/src/handlers/file_processor.py

# Import the transaction parser and database operations
from utils.transaction_parser import parse_transactions
from utils.db_utils import create_transaction, delete_file_transactions

# Update the handler function to include transaction parsing
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process uploaded files to extract metadata and transactions."""
    # ... existing code ...
    
    # Check if opening_balance was detected during analysis
    opening_balance = None
    if 'openingBalance' in update_data and update_data['openingBalance'] is not None:
        opening_balance = float(update_data['openingBalance'])
        logger.info(f"Opening balance detected for file {file_id}: {opening_balance}")
        
        # Trigger transaction parsing automatically when opening balance exists
        process_file_transactions(file_id, content_bytes, detected_format, opening_balance)
    
    # ... continue with existing code ...

def process_file_transactions(file_id: str, content_bytes: bytes, file_format: FileFormat, opening_balance: float) -> int:
    """
    Process a file to extract and save transactions.
    
    Args:
        file_id: ID of the file to process
        content_bytes: File content as bytes
        file_format: Format of the file
        opening_balance: Opening balance to use for running totals
        
    Returns:
        Number of transactions processed
    """
    try:
        # Parse transactions using the utility
        transactions = parse_transactions(
            content_bytes, 
            file_format,
            opening_balance
        )
        
        # Delete any existing transactions for this file
        try:
            delete_file_transactions(file_id)
            logger.info(f"Deleted existing transactions for file {file_id}")
        except Exception as del_error:
            logger.warning(f"Error deleting existing transactions: {str(del_error)}")
        
        # Save new transactions to the database
        transaction_count = 0
        for transaction_data in transactions:
            try:
                # Add the file_id to each transaction
                transaction_data['file_id'] = file_id
                
                # Create and save the transaction
                create_transaction(transaction_data)
                transaction_count += 1
            except Exception as tx_error:
                logger.warning(f"Error creating transaction: {str(tx_error)}")
                
        logger.info(f"Saved {transaction_count} transactions for file {file_id}")
        
        # Update the file record with transaction count
        update_transaction_file(file_id, {
            'transactionCount': str(transaction_count)
        })
        
        return transaction_count
    except Exception as parse_error:
        logger.error(f"Error parsing transactions: {str(parse_error)}")
        return 0
```

### 4.2 Handling Opening Balance Changes

When a user changes the opening balance of a file, we need to trigger transaction reprocessing. Add this to the file balance update handler:

```python
# backend/src/handlers/file_operations.py

# Import the process_file_transactions function
from handlers.file_processor import process_file_transactions

# In the update_file_balance_handler function, add this after updating the balance:
def update_file_balance_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Update a file's opening balance."""
    try:
        # ... existing code to validate and get file ...
        
        # After successfully updating the opening balance, trigger transaction reprocessing
        try:
            # Get the file content from S3
            s3_key = file.get('s3Key')
            if not s3_key:
                logger.warning(f"File {file_id} has no S3 key, skipping transaction processing")
            else:
                # Get file content from S3
                response = s3_client.get_object(Bucket=FILE_STORAGE_BUCKET, Key=s3_key)
                content_bytes = response['Body'].read()
                
                # Get file format
                file_format = FileFormat(file.get('fileFormat', 'other'))
                
                # Process transactions with new opening balance
                transaction_count = process_file_transactions(
                    file_id, 
                    content_bytes, 
                    file_format, 
                    opening_balance
                )
                
                # Include transaction count in response
                return create_response(200, {
                    "message": "File opening balance updated successfully and transactions reprocessed",
                    "fileId": file_id,
                    "openingBalance": opening_balance,
                    "transactionCount": transaction_count
                })
        except Exception as process_error:
            logger.error(f"Error processing transactions after balance update: {str(process_error)}")
            # Still return success for the balance update, even if processing failed
            return create_response(200, {
                "message": "File opening balance updated successfully, but error processing transactions",
                "fileId": file_id,
                "openingBalance": opening_balance
            })
            
        # ... existing response code ...
    except Exception as e:
        # ... existing error handling ...
```

### 4.3 Frontend Integration for Balance Changes

Update the FileList component to handle transaction count updates when the opening balance is changed:

```typescript
// In the handleSaveBalance function in FileList.tsx
const handleSaveBalance = async (fileId: string) => {
  // ... existing validation code ...
  
  setSavingBalanceFileId(fileId);
  setError(null);
  
  try {
    // Call the API to update the file's opening balance
    const response = await updateFileBalance(fileId, balanceValue);
    
    // Update the file in our local state, including transaction count if returned
    const updatedFiles = files.map(file => {
      if (file.fileId === fileId) {
        return {
          ...file,
          openingBalance: balanceValue,
          // Update transaction count if provided in the response
          transactionCount: response.transactionCount !== undefined 
            ? response.transactionCount 
            : file.transactionCount
        };
      }
      return file;
    });
    
    setFiles(updatedFiles);
    setEditingBalanceFileId(null);
    setBalanceInput('');
    
    // If transactions were processed, show a success message
    if (response.transactionCount !== undefined) {
      setSuccess(`Opening balance updated and ${response.transactionCount} transactions processed`);
    }
  } catch (error) {
    // ... existing error handling ...
  }
};
```

### 4.4 Update the FileService to Return Transaction Count

Update the updateFileBalance function in FileService.ts to return the transaction count:

```typescript
// frontend/src/services/FileService.ts

// Update the return type to include transactionCount
interface UpdateBalanceResponse {
  fileId: string;
  openingBalance: number;
  transactionCount?: number;
}

// Update file opening balance
export const updateFileBalance = async (fileId: string, openingBalance: number): Promise<UpdateBalanceResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/${fileId}/balance`, {
      method: 'POST',
      body: JSON.stringify({ openingBalance })
    });
    return response;
  } catch (error) {
    console.error('Error updating file balance:', error);
    throw error;
  }
};
```

## 5. Frontend Implementation

### 5.1 Create Transaction Service

Create a new service for transaction operations:

```typescript
// frontend/src/services/TransactionService.ts

import { authenticatedRequest } from '../utils/api';

// API endpoint for transactions
const API_ENDPOINT = `${import.meta.env.VITE_API_ENDPOINT}/transactions`;

// Transaction interface
export interface Transaction {
  transactionId: string;
  fileId: string;
  date: string;
  description: string;
  amount: number;
  runningTotal: number;
  transactionType?: string;
  category?: string;
  payee?: string;
  memo?: string;
  checkNumber?: string;
  reference?: string;
}

// Response interface for transaction list
export interface TransactionListResponse {
  transactions: Transaction[];
  metadata: {
    totalTransactions: number;
    fileId: string;
    fileName?: string;
  };
}

// Get transactions for a file
export const getFileTransactions = async (fileId: string): Promise<TransactionListResponse> => {
  try {
    const response = await authenticatedRequest(`${API_ENDPOINT}/file/${fileId}`);
    return response;
  } catch (error) {
    console.error('Error fetching file transactions:', error);
    throw error;
  }
};

// Default export
export default {
  getFileTransactions
};
```

### 5.2 Create Transaction Table Component

Create a component to display file transactions:

```tsx
// frontend/src/components/TransactionList.tsx

import React, { useState, useEffect } from 'react';
import { Transaction, getFileTransactions } from '../services/TransactionService';
import './TransactionList.css';

interface TransactionListProps {
  fileId: string;
  fileName?: string;
  openingBalance?: number;
  onClose: () => void;
}

const TransactionList: React.FC<TransactionListProps> = ({ 
  fileId, 
  fileName, 
  openingBalance, 
  onClose 
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load transactions when component mounts
  useEffect(() => {
    const loadTransactions = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await getFileTransactions(fileId);
        setTransactions(data.transactions || []);
      } catch (error) {
        console.error('Error loading transactions:', error);
        setError(error instanceof Error ? error.message : 'Failed to load transactions');
        setTransactions([]);
      } finally {
        setLoading(false);
      }
    };
    
    loadTransactions();
  }, [fileId]);

  // Format amount as currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  // Format date
  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (error) {
      return dateString;
    }
  };

  return (
    <div className="transaction-list-container">
      <div className="transaction-list-header">
        <h2>{fileName ? `Transactions: ${fileName}` : 'File Transactions'}</h2>
        <button className="close-button" onClick={onClose}>×</button>
      </div>
      
      {/* Opening balance section */}
      {openingBalance !== undefined && (
        <div className="opening-balance">
          <span className="balance-label">Opening Balance:</span>
          <span className="balance-value">{formatCurrency(openingBalance)}</span>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="transaction-list-error">
          <span className="error-icon">⚠️</span> {error}
        </div>
      )}
      
      {/* Loading indicator */}
      {loading ? (
        <div className="loading-transactions">Loading transactions...</div>
      ) : (
        <>
          {transactions.length === 0 ? (
            <div className="no-transactions">
              No transactions found for this file.
            </div>
          ) : (
            <div className="transaction-table-container">
              <table className="transaction-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Type</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Running Total</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map(transaction => (
                    <tr key={transaction.transactionId}>
                      <td>{formatDate(transaction.date)}</td>
                      <td className="description-cell">{transaction.description}</td>
                      <td>{transaction.transactionType || '—'}</td>
                      <td>{transaction.category || '—'}</td>
                      <td className={`amount-cell ${transaction.amount < 0 ? 'negative' : 'positive'}`}>
                        {formatCurrency(transaction.amount)}
                      </td>
                      <td className="total-cell">{formatCurrency(transaction.runningTotal)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          
          <div className="transaction-count">
            {transactions.length} transaction{transactions.length !== 1 ? 's' : ''}
          </div>
        </>
      )}
    </div>
  );
};

export default TransactionList;
```

### 5.3 Add CSS for Transaction List

Create styling for the transaction list:

```css
/* frontend/src/components/TransactionList.css */

.transaction-list-container {
  max-width: 1000px;
  margin: 20px auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.transaction-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.transaction-list-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #999;
  cursor: pointer;
  padding: 0 8px;
}

.close-button:hover {
  color: #666;
}

.opening-balance {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 15px;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.balance-label {
  font-weight: bold;
  margin-right: 10px;
}

.balance-value {
  font-family: 'Courier New', monospace;
  font-weight: 500;
}

.transaction-list-error {
  background-color: #fff8f8;
  color: #d9534f;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
  border-left: 4px solid #d9534f;
}

.loading-transactions, .no-transactions {
  text-align: center;
  padding: 40px 0;
  color: #666;
  font-style: italic;
}

.transaction-table-container {
  overflow-x: auto;
  margin-bottom: 15px;
}

.transaction-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.transaction-table th {
  background-color: #f5f5f5;
  padding: 10px;
  text-align: left;
  border-bottom: 2px solid #ddd;
  position: sticky;
  top: 0;
}

.transaction-table td {
  padding: 10px;
  border-bottom: 1px solid #eee;
  vertical-align: middle;
}

.transaction-table tr:hover {
  background-color: #f9f9f9;
}

.description-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.amount-cell {
  text-align: right;
  font-family: 'Courier New', monospace;
}

.amount-cell.positive {
  color: #28a745;
}

.amount-cell.negative {
  color: #dc3545;
}

.total-cell {
  text-align: right;
  font-family: 'Courier New', monospace;
  font-weight: 700;
}

.transaction-count {
  text-align: right;
  color: #666;
  font-size: 14px;
  margin-top: 10px;
}

/* Modal styles for when shown as a modal */
.transaction-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.transaction-modal .transaction-list-container {
  max-height: 90vh;
  overflow-y: auto;
  margin: 0;
  width: 90%;
  max-width: 1200px;
}
```

### 5.4 Update FileList Component

Modify the FileList component to add a "View Transactions" button when a file has transactions:

```tsx
// frontend/src/components/FileList.tsx

// Add this to the imports
import TransactionList from './TransactionList';

// Add these state variables to the FileList component
const [viewingTransactionsForFile, setViewingTransactionsForFile] = useState<string | null>(null);
const [transactionModalFile, setTransactionModalFile] = useState<FileMetadata | null>(null);

// Add this function to handle viewing transactions
const handleViewTransactions = (file: FileMetadata) => {
  setViewingTransactionsForFile(file.fileId);
  setTransactionModalFile(file);
};

// Add this function to close the modal
const handleCloseTransactionModal = () => {
  setViewingTransactionsForFile(null);
  setTransactionModalFile(null);
};

// Update the file actions column in the file table to include a View Transactions button
<td className="file-actions">
  <button 
    className="download-button"
    onClick={() => handleDownloadFile(file.fileId)}
    disabled={downloadingFileId === file.fileId}
  >
    {downloadingFileId === file.fileId ? '...' : 'Download'}
  </button>
  
  {/* Add this button for files with transactions */}
  {file.transactionCount && Number(file.transactionCount) > 0 && (
    <button 
      className="transactions-button"
      onClick={() => handleViewTransactions(file)}
      title={`View ${file.transactionCount} transactions`}
    >
      Transactions
    </button>
  )}
  
  <button 
    className="delete-button"
    onClick={() => handleDeleteFile(file.fileId)}
    disabled={deletingFileId === file.fileId}
  >
    {deletingFileId === file.fileId ? '...' : 'Delete'}
  </button>
</td>

// Add the TransactionList modal to the end of the component (before the closing JSX tag)
{viewingTransactionsForFile && transactionModalFile && (
  <div className="transaction-modal">
    <TransactionList
      fileId={viewingTransactionsForFile}
      fileName={transactionModalFile.fileName}
      openingBalance={transactionModalFile.openingBalance}
      onClose={handleCloseTransactionModal}
    />
  </div>
)}
```

### 5.5 Update FileList CSS

Add styling for the transactions button:

```css
/* frontend/src/components/FileList.css */

/* Add this to the existing CSS file */
.transactions-button {
  padding: 6px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: bold;
  transition: background-color 0.3s ease;
  background-color: #6c757d;
  color: white;
  margin: 0 5px;
}

.transactions-button:hover {
  background-color: #5a6268;
}
```

### 5.6 Update FileMetadata Interface

Update the FileMetadata interface to include transactionCount:

```typescript
// frontend/src/services/FileService.ts

export interface FileMetadata {
  fileId: string;
  fileName: string;
  contentType: string;
  fileSize: number;
  uploadDate: string;
  fileFormat?: string;
  processingStatus?: string;
  accountId?: string;
  accountName?: string;
  openingBalance?: number;
  transactionCount?: number;  // Add this field
  // ...other fields
}
```

## 6. Backend API Implementation

Create the transaction API handlers:

```python
# backend/src/handlers/transaction_operations.py

import json
import logging
import os
from typing import Dict, Any, List

import boto3
from boto3.dynamodb.conditions import Key

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import models and utils
from models.transaction import Transaction
from utils.db_utils import list_file_transactions, get_transaction_file

# Initialize clients
dynamodb = boto3.resource('dynamodb')

# Get environment variables
TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE')
transactions_table = dynamodb.Table(TRANSACTIONS_TABLE)

def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create an API Gateway response object."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body)
    }

def get_user_from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract user information from the event."""
    try:
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {}).get("jwt", {})
        claims = authorizer.get("claims", {})
        
        user_sub = claims.get("sub")
        if not user_sub:
            return None
        
        return {
            "id": user_sub,
            "email": claims.get("email", "unknown"),
            "auth_time": claims.get("auth_time")
        }
    except Exception as e:
        logger.error(f"Error extracting user from event: {str(e)}")
        return None

def list_file_transactions_handler(event: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """List transactions for a specific file."""
    try:
        # Get file ID from path parameters
        file_id = event.get('pathParameters', {}).get('fileId')
        
        if not file_id:
            return create_response(400, {"message": "File ID is required"})
            
        # Get the file to ensure it exists and belongs to the user
        file = get_transaction_file(file_id)
        if not file:
            return create_response(404, {"message": "File not found"})
            
        if file.get('userId') != user['id']:
            return create_response(403, {"message": "Access denied. You do not own this file"})
            
        # Get transactions for the file
        transactions = list_file_transactions(file_id)
        
        # Format response
        return create_response(200, {
            "transactions": transactions,
            "metadata": {
                "totalTransactions": len(transactions),
                "fileId": file_id,
                "fileName": file.get('fileName')
            }
        })
    except Exception as e:
        logger.error(f"Error listing transactions: {str(e)}")
        return create_response(500, {"message": "Error listing transactions"})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for transaction operations."""
    logger.info(f"Processing request with event: {json.dumps(event)}")
    
    # Handle preflight OPTIONS request
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return create_response(200, {"message": "OK"})
    
    # Extract user information
    user = get_user_from_event(event)
    if not user:
        logger.error("No user found in token")
        return create_response(401, {"message": "Unauthorized"})
    
    # Get the HTTP method and route
    method = event.get("requestContext", {}).get("http", {}).get("method", "").upper()
    route = event.get("routeKey", "")
    
    # Handle based on route
    if route == "GET /transactions/file/{fileId}":
        return list_file_transactions_handler(event, user)
    else:
        return create_response(400, {"message": f"Unsupported route: {route}"})
```

## 7. API Gateway and Infrastructure Updates

### 7.1 Add Transaction Lambda Function

Add a new Lambda function for transaction operations:

```terraform
# infrastructure/terraform/lambda.tf

# Transaction operations Lambda
resource "aws_lambda_function" "transaction_operations" {
  function_name = "${var.project_name}-${var.environment}-transaction-operations"
  handler       = "handlers.transaction_operations.handler"
  runtime       = "python3.9"
  role          = aws_iam_role.lambda_exec.arn
  filename      = data.archive_file.lambda_code.output_path
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
      TRANSACTIONS_TABLE = aws_dynamodb_table.transactions.name
      FILES_TABLE = aws_dynamodb_table.transaction_files.name
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# CloudWatch Log Group for transaction operations
resource "aws_cloudwatch_log_group" "transaction_operations" {
  name              = "/aws/lambda/${aws_lambda_function.transaction_operations.function_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}
```

### 7.2 Add API Gateway Routes

Add API Gateway routes for transaction operations:

```terraform
# infrastructure/terraform/api_gateway.tf

# Transaction Operations Integration
resource "aws_apigatewayv2_integration" "transaction_operations" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.transaction_operations.invoke_arn
  payload_format_version = "2.0"
  description           = "Lambda integration for transaction operations endpoints"
}

# File transactions listing route
resource "aws_apigatewayv2_route" "list_file_transactions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /transactions/file/{fileId}"
  target             = "integrations/${aws_apigatewayv2_integration.transaction_operations.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

# Lambda permission for transaction operations
resource "aws_lambda_permission" "transaction_operations" {
  statement_id  = "AllowAPIGatewayInvokeTransactions"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transaction_operations.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*/transactions*"
}
```

### 7.3 Update the TransactionFile Model

Update the TransactionFile model to include transactionCount:

```python
# backend/src/models/transaction_file.py

# In the __init__ method, add:
self.transaction_count = transaction_count

# In the to_dict method, add:
if self.transaction_count is not None:
    result["transactionCount"] = str(self.transaction_count)

# In the from_dict method, add:
if "transactionCount" in data:
    file.transaction_count = int(data["transactionCount"])
```

## 8. Testing

### 8.1 Create Test Files

Create sample test files with different formats to test transaction parsing:

1. CSV file with example transactions
2. OFX/QFX file with example transactions

### 8.2 Test File Processing

1. Upload test files through the UI
2. Add opening balance to files
3. Verify that transactions are parsed and displayed correctly
4. Test the "View Transactions" functionality
5. Verify that changing the opening balance re-processes transactions

### 8.3 Test Data Accuracy

1. Verify that running totals are calculated correctly
2. Verify that transaction details match the source file
3. Test with various financial institutions' file formats
4. Verify handling of different date formats and currencies

## 9. Conclusion

This implementation provides a comprehensive solution for parsing and displaying transactions from financial files. The feature enhances the application by allowing users to:

1. Automatically parse transactions from supported file formats
2. View a detailed list of transactions for each file
3. Track running totals starting from the opening balance
4. Re-process transactions when the opening balance changes

The architecture follows a clean separation of concerns:
- Data models for transactions in both backend and frontend
- Transaction parsing logic in the file processor
- Database operations for transaction storage and retrieval
- UI components for displaying transactions
- API endpoints for transaction operations

This feature significantly adds value to the financial file management capabilities of the application, allowing users to work with their financial data more effectively.

## 10. Transaction Processing Workflow

The transaction processing feature is designed to work automatically with minimal user intervention:

1. **Initial File Upload Process**:
   - User uploads a financial file (CSV, OFX, QFX)
   - System extracts an opening balance if possible
   - If an opening balance is present, transactions are automatically parsed
   - The file is saved with metadata including transaction count

2. **Adding Opening Balance Manually**:
   - For files where opening balance wasn't automatically detected
   - User adds an opening balance via the UI
   - System immediately triggers transaction parsing in the background
   - File is updated with transaction count and transactions become viewable

3. **Modifying Opening Balance**:
   - User modifies an existing opening balance
   - System automatically:
     1. Deletes all existing transactions for the file
     2. Re-parses the file with the new opening balance
     3. Saves the new transactions with updated running totals
     4. Updates the transaction count on the file

4. **Transaction Viewing**:
   - Transaction button appears only for files with parsed transactions
   - Opening balance is shown at the top of the transaction list
   - Transactions maintain running totals starting from the opening balance

This workflow ensures that transactions are always consistent with the opening balance, and users can easily modify the opening balance if needed, with the system automatically handling the recalculation of all transaction running totals.