# QIF File Processing Design Document

## Executive Summary

This document outlines the design and implementation plan for adding QIF (Quicken Interchange Format) file processing support to the HouseF3 financial transaction management application. QIF is a text-based format used by Quicken and other financial software for importing/exporting transaction data.

## Current State Analysis

### Frontend Support
✅ **Already Implemented:**
- QIF file extension validation (`.qif` supported in file upload)
- QIF MIME type support (`application/x-quicken`)
- Basic QIF content validation (checks for `!Type:`, `!Account`, etc.)
- UI components recognize QIF as a supported format
- File type detection and validation

### Backend Support  
❌ **Missing Implementation:**
- QIF format not in `FileFormat` enum
- No QIF file format detection in `file_type_selector()`
- No QIF parsing in `parse_transactions()`
- No QIF preview support
- No QIF field mapping

## QIF Format Overview

QIF is a line-based text format where:
- Each line starts with a single character code followed by data
- Records end with `^` (caret)
- Files start with headers like `!Type:Bank`, `!Type:Cash`, etc.
- **Transactions are often in reverse chronological order** (newest first) and must be sorted
- Common transaction fields:
  - `D` = Date
  - `T` = Amount (negative for debits)
  - `P` = Payee/Description
  - `M` = Memo
  - `L` = Category
  - `N` = Check/Reference Number
  - `C` = Cleared Status
  - `^` = End of record

### Sample QIF File
```
!Type:Bank
D1/1/2024
T-150.00
PGrocery Store
MWeekly shopping
LFood:Groceries
^
D1/2/2024
T1500.00
PSalary Deposit
LIncome:Salary
^
```

## Implementation Plan

### Phase 1: Backend Foundation

#### 1.1 Update FileFormat Enum
**File:** `backend/src/models/transaction_file.py`

```python
class FileFormat(str, enum.Enum):
    """Enum for transaction file formats"""
    CSV = "csv"
    OFX = "ofx"
    QFX = "qfx"
    QIF = "qif"  # ← Add this
    PDF = "pdf"
    XLSX = "xlsx"
    OTHER = "other"
    JSON = "json"
    EXCEL = "excel"
```

#### 1.2 Add QIF Detection
**File:** `backend/src/utils/transaction_parser.py`

Update `file_type_selector()`:
```python
def file_type_selector(content: bytes) -> Optional[FileFormat]:
    try:
        text = content.decode('utf-8', errors='ignore').strip()
    except Exception:
        return None

    # Check for QIF markers
    if text.startswith('!Type:') or '!Type:' in text[:100]:
        return FileFormat.QIF
    
    # ... existing OFX/QFX/CSV detection
```

Update `detect_format_from_extension()` in `backend/src/utils/file_analyzer.py`:
```python
format_map = {
    'csv': FileFormat.CSV,
    'ofx': FileFormat.OFX,
    'qfx': FileFormat.QFX,
    'qif': FileFormat.QIF,  # ← Add this
    'pdf': FileFormat.PDF,
    'xlsx': FileFormat.XLSX,
    'xls': FileFormat.EXCEL,
    'json': FileFormat.JSON
}
```

#### 1.3 Create QIF Parser
**File:** `backend/src/utils/transaction_parser.py`

```python
def parse_qif_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    """
    Parse transactions from QIF file content.
    
    Args:
        transaction_file: TransactionFile object with metadata
        content: The raw QIF file content
        
    Returns:
        List of Transaction objects
    """
    try:
        if not transaction_file.file_map_id:
            logger.warning(f"File map is required for QIF transaction parsing")
            return []
            
        file_map = checked_mandatory_file_map(transaction_file.file_map_id, transaction_file.user_id)
        
        # Decode content
        text_content = content.decode('utf-8')
        logger.info("Parsing QIF content with field mapping")
        
        transactions = []
        current_transaction = {}
        balance = transaction_file.opening_balance if transaction_file.opening_balance else Decimal(0)
        import_order = 1
        
        lines = text_content.splitlines()
        i = 0
        
        # Skip to transaction data (past headers)
        while i < len(lines) and not lines[i].startswith('D'):
            i += 1
            
        # Parse each transaction
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
                
            if line == '^':
                # End of transaction - process it
                if current_transaction:
                    transaction = create_transaction_from_qif(
                        transaction_file, current_transaction, balance, import_order, file_map
                    )
                    if transaction:
                        transactions.append(transaction)
                        balance = transaction.balance if transaction.balance else balance + transaction.amount
                        import_order += 1
                current_transaction = {}
            else:
                # Parse field
                if len(line) >= 2:
                    field_code = line[0]
                    field_value = line[1:]
                    current_transaction[field_code] = field_value
            
            i += 1
        
        # Process any remaining transaction
        if current_transaction:
            transaction = create_transaction_from_qif(
                transaction_file, current_transaction, balance, import_order, file_map
            )
            if transaction:
                transactions.append(transaction)
        
        # Sort transactions by date in ascending order
        # QIF files often have transactions in reverse chronological order
        transactions.sort(key=lambda tx: tx.date if tx.date else 0)
        
        # Recalculate running balances after sorting
        if transaction_file.opening_balance and transactions:
            current_balance = transaction_file.opening_balance
            for i, tx in enumerate(transactions):
                current_balance += tx.amount
                tx.balance = current_balance
                tx.import_order = i + 1  # Update import order after sorting
        
        logger.info(f"Successfully parsed and sorted {len(transactions)} QIF transactions")
        return transactions
        
    except Exception as e:
        logger.error(f"Error parsing QIF transactions: {str(e)}")
        return []


def create_transaction_from_qif(
    transaction_file: TransactionFile, 
    qif_data: Dict[str, str], 
    balance: Decimal, 
    import_order: int, 
    file_map: FileMap
) -> Transaction:
    """Create a transaction from QIF field data using field mapping."""
    try:
        # Apply user's field mapping directly to QIF field codes
        # qif_data contains field codes like {'D': '1/1/2024', 'T': '-150.00', 'P': 'Grocery Store'}
        row_data = apply_field_mapping(qif_data, file_map)
        
        if not row_data:
            raise ValueError("Field mapping returned empty result")
            
        # Parse date
        date_str = str(row_data.get('date', ''))
        date_ms = parse_qif_date(date_str)
        
        # Parse amount
        amount_str = str(row_data.get('amount', '0')).replace(',', '')
        amount = Decimal(amount_str)
        
        # Update balance
        new_balance = balance + amount
        
        # Create transaction
        transaction = Transaction.create(
            account_id=transaction_file.account_id,
            user_id=transaction_file.user_id,
            file_id=transaction_file.file_id,
            date=date_ms,
            description=row_data.get('description', '').strip(),
            amount=amount,
            currency=transaction_file.currency,
            balance=new_balance,
            import_order=import_order,
            memo=row_data.get('memo'),
            check_number=row_data.get('checkNumber'),
            status=map_qif_cleared_status(row_data.get('clearedStatus'))
        )
        
        return transaction
        
    except Exception as e:
        raise ValueError(f"Error creating QIF transaction: {str(e)}")


def parse_qif_date(date_str: str) -> int:
    """Parse QIF date formats and return milliseconds since epoch."""
    # QIF supports various date formats
    qif_date_formats = [
        "%m/%d/%Y",    # 1/15/2024
        "%m/%d/%y",    # 1/15/24  
        "%m/%d'%y",    # 1/15'24 (Quicken format)
        "%m/ %d/%y",   # 1/ 1/24 (spaces)
        "%Y-%m-%d",    # 2024-01-15
        "%d/%m/%Y",    # 15/01/2024
        "%d/%m/%y"     # 15/01/24
    ]
    
    for fmt in qif_date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
            
    raise ValueError(f"Invalid QIF date format: {date_str}")


def map_qif_cleared_status(status: Optional[str]) -> Optional[str]:
    """Map QIF cleared status to internal format."""
    if not status:
        return None
    status = status.strip().upper()
    if status in ['*', 'R']:
        return 'reconciled'
    elif status in ['X', 'C']:
        return 'cleared'
    return 'uncleared'
```

#### 1.4 Update Main Parser Router
**File:** `backend/src/utils/transaction_parser.py`

```python
def parse_transactions(transaction_file: TransactionFile, content: bytes) -> Optional[List[Transaction]]:
    if transaction_file.file_map_id:
        if transaction_file.file_format == FileFormat.CSV:
            return parse_csv_transactions(transaction_file, content)
        elif transaction_file.file_format in [FileFormat.OFX, FileFormat.QFX]:
            return parse_ofx_transactions(transaction_file, content)
        elif transaction_file.file_format == FileFormat.QIF:  # ← Add this
            return parse_qif_transactions(transaction_file, content)
        else:
            logger.warning(f"Unsupported file format for transaction parsing: {transaction_file.file_format}")
            return []
    else: 
        logger.warning(f"File map is required for transaction parsing: {transaction_file.file_map_id}")
        return None
```

### Phase 2: Preview Support

#### 2.1 Add QIF Preview Parser
**File:** `backend/src/handlers/file_operations.py`

```python
from datetime import datetime

def parse_qif_preview(content: str) -> Dict[str, Any]:
    """Parse QIF content and return preview data with actual QIF field codes as columns."""
    try:
        transactions_data = []
        total_rows = 0
        all_fields = set()
        
        lines = content.splitlines()
        current_transaction = {}
        
        # First pass: collect all field codes present in the file
        for line in lines:
            line = line.strip()
            if not line or line.startswith('!'):
                continue
                
            if line == '^':
                # End of transaction
                if current_transaction:
                    all_fields.update(current_transaction.keys())
                    transactions_data.append(current_transaction.copy())
                    total_rows += 1
                current_transaction = {}
            elif len(line) >= 2:
                field_code = line[0]
                field_value = line[1:]
                current_transaction[field_code] = field_value
        
        # Process any remaining transaction
        if current_transaction:
            all_fields.update(current_transaction.keys())
            transactions_data.append(current_transaction.copy())
            total_rows += 1
        
        # Create columns from actual QIF field codes found in file
        # Sort to ensure consistent ordering: D, T, P, M, L, N, C, then others
        priority_fields = ['D', 'T', 'P', 'M', 'L', 'N', 'C']
        columns = []
        
        # Add priority fields first if they exist
        for field in priority_fields:
            if field in all_fields:
                columns.append(field)
                all_fields.remove(field)
        
        # Add any remaining fields alphabetically
        columns.extend(sorted(all_fields))
        
        # Sort transactions by date for preview (QIF files often have reverse chronological order)
        def parse_qif_date_for_sorting(date_str):
            """Parse QIF date for sorting purposes."""
            if not date_str:
                return 0
            try:
                # Try common QIF date formats for sorting
                for fmt in ["%m/%d/%Y", "%m/%d/%y", "%m/%d'%y", "%m/ %d/%y"]:
                    try:
                        return datetime.strptime(date_str.strip(), fmt).timestamp()
                    except ValueError:
                        continue
                return 0
            except:
                return 0
        
        transactions_data.sort(key=lambda tx: parse_qif_date_for_sorting(tx.get('D', '')))
        
        # Format data for preview - ensure all transactions have all columns
        formatted_data = []
        for transaction in transactions_data[:10]:  # Limit to first 10
            formatted_transaction = {}
            for col in columns:
                formatted_transaction[col] = transaction.get(col, '')
            formatted_data.append(formatted_transaction)
        
        return {
            'columns': columns,
            'data': formatted_data,
            'totalRows': total_rows,
            'message': f'Preview of first {len(formatted_data)} QIF transactions.' if formatted_data else 'No transactions found in QIF file.'
        }
        
    except Exception as e:
        logger.error(f"Error parsing QIF preview: {str(e)}")
        return {
            'columns': [],
            'data': [],
            'totalRows': 0,
            'message': f'Error parsing QIF file: {str(e)}'
        }
```

#### 2.2 Update Preview Handler
**File:** `backend/src/handlers/file_operations.py`

```python
def get_file_preview_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    # ... existing code ...
    
    elif file.file_format == FileFormat.QIF:  # ← Add this case
        content_bytes = get_object_content(file.s3_key)
        if content_bytes is None:
            return handle_error(500, "Error reading file content from S3.")

        try:
            content_str = content_bytes.decode('utf-8')
            preview_data = parse_qif_preview(content_str)
            
            return create_response(200, {
                'fileId': file_id,
                'fileName': file.file_name,
                'fileFormat': file.file_format.value,
                'columns': preview_data['columns'],
                'data': preview_data['data'],
                'totalRows': preview_data['totalRows'],
                'message': preview_data['message']
            })
        except Exception as parse_e:
            logger.error(f"Error parsing QIF file {file_id}: {str(parse_e)}")
            return handle_error(400, f"Error parsing QIF file: {str(parse_e)}")
    
    elif file.file_format in [FileFormat.OFX, FileFormat.QFX]:
        # ... existing OFX/QFX code ...
```

### Phase 3: Field Mapping Strategy

#### 3.1 QIF Field Mapping Approach

**Critical Requirement:** The preview must show actual QIF field codes (D, T, P, M, L, N, C) as column names, not friendly names, so the frontend field mapping interface can work properly.

**Why this matters:**
- Frontend uses preview column names to populate field mapping dropdowns
- Users need to see the actual QIF field codes to understand what they're mapping
- QIF field codes are standardized, unlike CSV column names which vary by institution

**Standard QIF Field Codes:**
- `D` = Date
- `T` = Transaction amount  
- `P` = Payee/Description
- `M` = Memo
- `L` = Category
- `N` = Number (check number, reference)
- `C` = Cleared status
- `S` = Split category (for split transactions)
- `E` = Split memo
- `$` = Split amount

#### 3.2 Default Field Mappings

Since QIF has a standardized field structure, we should create default field mappings for common QIF fields.

#### 3.3 Create Default QIF Field Map
**File:** `backend/src/utils/default_field_maps.py` (new file)

```python
from models.file_map import FileMap, FieldMapping
from models.transaction_file import FileFormat

def create_default_qif_field_map(user_id: str) -> FileMap:
    """Create a default field mapping for QIF files using actual QIF field codes."""
    
    mappings = [
        FieldMapping(source_field="D", target_field="date"),        # Date
        FieldMapping(source_field="T", target_field="amount"),      # Transaction amount
        FieldMapping(source_field="P", target_field="description"), # Payee/Description
        FieldMapping(source_field="M", target_field="memo"),        # Memo
        FieldMapping(source_field="L", target_field="category"),    # Category
        FieldMapping(source_field="N", target_field="checkNumber"), # Number/Check
        FieldMapping(source_field="C", target_field="status")       # Cleared status
    ]
    
    return FileMap(
        user_id=user_id,
        name="Default QIF Mapping",
        description="Standard field mapping for QIF files using QIF field codes",
        file_format=FileFormat.QIF,
        mappings=mappings
    )
```

### Phase 4: Frontend Enhancements

The frontend already has basic QIF support, but we should ensure the validation properly handles QIF content structure.

#### 4.1 Enhanced QIF Validation
**File:** `frontend/src/new-ui/utils/fileValidation.ts`

```typescript
/**
 * Enhanced QIF content validation
 */
export const validateQIFContent = async (file: File): Promise<{ isValid: boolean; warnings?: string[] }> => {
  if (!file.name.toLowerCase().endsWith('.qif')) {
    return { isValid: true };
  }

  try {
    const chunk = file.slice(0, 2048);
    const text = await chunk.text();
    
    const warnings: string[] = [];
    
    // Check for QIF type header
    const hasTypeHeader = /!Type:(Bank|Cash|CCard|Invst|Oth A|Oth L)/.test(text);
    
    // Check for transaction structure
    const hasTransactionData = text.includes('D') && text.includes('T') && text.includes('^');
    
    // Check for account header (multi-account files)
    const hasAccountHeader = text.includes('!Account');
    
    if (!hasTypeHeader && !hasAccountHeader) {
      warnings.push('No QIF type header found - file may not be valid QIF format');
    }
    
    if (!hasTransactionData) {
      warnings.push('No transaction data detected in file preview');
    }
    
    // Check for potential encoding issues
    if (text.includes('�') || text.includes('\ufffd')) {
      warnings.push('File may have encoding issues - ensure it is saved as plain text');
    }
    
    const isValid = hasTypeHeader || hasAccountHeader || hasTransactionData;
    
    return {
      isValid,
      warnings: warnings.length > 0 ? warnings : undefined
    };
    
  } catch (error) {
    console.warn('Could not validate QIF content:', error);
    return { 
      isValid: true,
      warnings: ['Could not validate file content - proceeding with caution']
    };
  }
};
```

## Testing Strategy

### Unit Tests
1. **QIF Parser Tests** - Test various QIF formats and edge cases
2. **Date Parsing Tests** - Test different QIF date formats
3. **Field Mapping Tests** - Test field mapping with QIF data
4. **Preview Tests** - Test QIF preview generation

### Integration Tests
1. **End-to-end file processing** - Upload → Parse → Import → Verify
2. **Error handling** - Malformed QIF files, encoding issues
3. **Multi-account QIF files** - Test files with multiple accounts

### Test Data
Create sample QIF files covering:
- Basic bank transactions
- Investment transactions  
- Multi-account exports
- Split transactions
- Various date formats
- Different QIF variants
- **Transactions in reverse chronological order** (common QIF export format)
- **Mixed date order** to test sorting functionality

## Error Handling

### Common QIF Issues
1. **Date Format Variations** - Handle multiple date formats gracefully
2. **Transaction Order** - QIF files often have transactions in reverse chronological order
3. **Encoding Problems** - Support various text encodings
4. **Malformed Records** - Skip invalid records, continue processing
5. **Missing Required Fields** - Provide meaningful error messages
6. **Currency Handling** - QIF doesn't specify currency explicitly

### Error Recovery
- Log detailed parsing errors for debugging
- Continue processing valid records when encountering invalid ones
- Provide clear user feedback on what went wrong
- Suggest fixes for common issues

## Performance Considerations

1. **Large File Handling** - Stream processing for large QIF files
2. **Memory Usage** - Process transactions in batches
3. **Preview Efficiency** - Only parse first portion for preview
4. **Field Mapping Cache** - Cache field mappings for reuse

## Migration Strategy

### Phase 1: Backend Foundation (1-2 weeks)
- Add QIF to FileFormat enum
- Implement QIF detection and parsing
- Add preview support
- Create unit tests

### Phase 2: Field Mapping (1 week)  
- Create default QIF field mappings
- Test with various QIF file formats
- Integration testing

### Phase 3: Frontend Polish (1 week)
- Enhance QIF validation
- Improve error messaging
- End-to-end testing

### Phase 4: Documentation and Launch (1 week)
- Update user documentation
- Create migration guides
- Performance testing
- Production deployment

## Success Metrics

1. **Functionality**: Users can successfully import QIF files from major financial institutions
2. **Reliability**: 95%+ success rate for well-formed QIF files  
3. **Usability**: Clear error messages and intuitive field mapping
4. **Performance**: Process typical QIF files (1000 transactions) in <5 seconds

## Conclusion

Adding QIF support will significantly expand the application's compatibility with financial software and institutions. The implementation leverages existing architecture patterns while adding robust QIF-specific parsing and validation. The phased approach ensures thorough testing and minimizes risk during deployment. 