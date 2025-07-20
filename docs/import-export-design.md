# Import/Export System Design

## Overview

This document describes the design and implementation of a comprehensive import/export system for the HouseF3 financial management application. The system enables users to backup their complete application state and restore it in the same or different environment using **FZIP (Financial ZIP) files**.

## Objectives

1. **Complete State Backup**: Export all user data including accounts, transactions, files, categories, rules, and computed analytics
2. **Portable Restoration**: Import data into any environment while maintaining data integrity
3. **User Security**: Ensure user data isolation and secure handling of sensitive financial information
4. **Scalability**: Handle large datasets efficiently (thousands of transactions, hundreds of files)
5. **Data Consistency**: Maintain all relationships and referential integrity during import/export operations

## Scope

### Data Included in Import/Export

#### Core Entities
- **Accounts**: All financial accounts with metadata, balances, settings
- **Transactions**: All transaction records with amounts, dates, descriptions, category assignments
- **Categories**: Category hierarchy, rules, and configuration
- **File Maps**: Field mapping configurations for transaction file processing
- **Transaction Files**: File metadata and actual file content from S3
- **Analytics Data**: Computed analytics (optional, can be regenerated)

#### Relationships Preserved
- Account ↔ Transactions
- Account ↔ Transaction Files  
- Transactions ↔ Categories (via category assignments)
- Transaction Files ↔ File Maps
- Category hierarchy (parent/child relationships)
- User ownership of all entities

#### Data Excluded
- User authentication/profile data (handled by Cognito)
- System logs and audit trails
- Temporary/cache data

## Technical Architecture

### Unified FZIP System Architecture

```
User Request → FZIP Handler → Export/Import Service → FZIP Package Builder/Parser → Download/Upload URL
                     ↓              ↓                    ↓
                 Auth Check → Data Collection/Validation → FZIP Packaging → Signed URL
```

### Export System Flow
```
User Request → FZIP Export Handler → Data Collector → FZIP Package Builder → Download URL
                     ↓              ↓                    ↓
                 Auth Check → Batch Retrieval → File Packaging → Signed URL
```

### Import System Flow
```
Upload → FZIP Import Handler → Validation → Transaction → Restoration → Verification
   ↓           ↓             ↓           ↓            ↓            ↓
S3 Upload → Auth Check → Schema Check → Begin → Restore Data → Publish Events
```

## Data Format Specification

### FZIP Package Structure

The export package is a **FZIP (Financial ZIP) file** containing:

```
export_[timestamp]_[user_id].fzip
├── manifest.json                 # Export metadata and validation
├── data/
│   ├── accounts.json            # Account entities
│   ├── transactions.json        # Transaction entities  
│   ├── categories.json          # Categories and rules
│   ├── file_maps.json          # Field mapping configurations
│   ├── transaction_files.json   # File metadata
│   └── analytics.json          # Analytics data (optional)
└── files/                      # Original transaction files
    ├── [file_id_1]/
    │   └── [original_filename]
    └── [file_id_2]/
        └── [original_filename]
```

### Manifest Schema

```json
{
  "export_format_version": "1.0",
  "export_timestamp": "2024-01-15T10:30:00Z",
  "user_id": "user_12345",
  "housef3_version": "2.5.0",
  "package_format": "fzip",
  "data_summary": {
    "accounts_count": 5,
    "transactions_count": 2847,
    "categories_count": 45,
    "file_maps_count": 3,
    "transaction_files_count": 12,
    "analytics_included": false
  },
  "checksums": {
    "accounts.json": "sha256:abc123...",
    "transactions.json": "sha256:def456...",
    "categories.json": "sha256:ghi789..."
  },
  "compatibility": {
    "minimum_version": "2.0.0",
    "supported_versions": ["2.0.0", "2.5.0"]
  }
}
```

### Data Entity Schemas

#### Accounts Export Format
```json
{
  "accounts": [
    {
      "accountId": "uuid",
      "accountName": "string",
      "accountType": "checking|savings|credit_card|investment|loan|other",
      "institution": "string",
      "balance": "decimal_string",
      "currency": "USD|EUR|GBP|...",
      "notes": "string",
      "isActive": boolean,
      "defaultFileMapId": "uuid",
      "lastTransactionDate": timestamp_ms,
      "createdAt": timestamp_ms,
      "updatedAt": timestamp_ms
    }
  ]
}
```

#### Transactions Export Format
```json
{
  "transactions": [
    {
      "transactionId": "uuid",
      "accountId": "uuid", 
      "fileId": "uuid",
      "date": timestamp_ms,
      "description": "string",
      "amount": "decimal_string",
      "currency": "USD|EUR|GBP|...",
      "balance": "decimal_string",
      "importOrder": integer,
      "transactionType": "string",
      "memo": "string",
      "checkNumber": "string",
      "fitId": "string",
      "status": "string",
      "statusDate": "string",
      "transactionHash": integer,
      "categories": [
        {
          "categoryId": "uuid",
          "status": "suggested|confirmed",
          "confidence": float,
          "ruleId": "string",
          "assignedAt": timestamp_ms
        }
      ],
      "primaryCategoryId": "uuid",
      "createdAt": timestamp_ms,
      "updatedAt": timestamp_ms
    }
  ]
}
```

#### Categories Export Format
```json
{
  "categories": [
    {
      "categoryId": "uuid",
      "name": "string",
      "type": "INCOME|EXPENSE",
      "parentCategoryId": "uuid",
      "icon": "string",
      "color": "string",
      "inheritParentRules": boolean,
      "ruleInheritanceMode": "additive|override|disabled",
      "rules": [
        {
          "ruleId": "string",
          "fieldToMatch": "description|payee|memo|amount",
          "condition": "contains|equals|starts_with|ends_with|regex|amount_range",
          "value": "string",
          "caseSensitive": boolean,
          "priority": integer,
          "enabled": boolean,
          "confidence": integer,
          "amountMin": "decimal_string",
          "amountMax": "decimal_string",
          "allowMultipleMatches": boolean,
          "autoSuggest": boolean
        }
      ],
      "createdAt": timestamp_ms,
      "updatedAt": timestamp_ms
    }
  ]
}
```

## API Endpoints

### Unified FZIP Operations

The system uses a unified `fzip_operations.py` handler that provides all FZIP-related functionality:

#### Export Endpoints

##### Initiate FZIP Export
```http
POST /fzip/export
Content-Type: application/json

{
  "includeAnalytics": false,
  "format": "fzip",
  "description": "Monthly backup"
}

Response:
{
  "exportId": "uuid",
  "status": "initiated",
  "estimatedSize": "~25MB",
  "estimatedCompletion": "2024-01-15T10:35:00Z",
  "packageFormat": "fzip"
}
```

##### Check FZIP Export Status
```http
GET /fzip/export/{exportId}/status

Response:
{
  "exportId": "uuid",
  "status": "processing|completed|failed",
  "progress": 75,
  "downloadUrl": "https://presigned-s3-url",
  "expiresAt": "2024-01-15T16:30:00Z",
  "error": "error_message_if_failed",
  "packageFormat": "fzip"
}
```

##### Download FZIP Export
```http
GET /fzip/export/{exportId}/download

Response: 302 Redirect to presigned S3 URL (FZIP file)
```

##### List FZIP Exports
```http
GET /fzip/export?limit=20&offset=0

Response:
{
  "exports": [
    {
      "exportId": "uuid",
      "status": "completed",
      "exportType": "complete",
      "requestedAt": 1642234567000,
      "completedAt": 1642234600000,
      "progress": 100,
      "packageSize": 25000000,
      "description": "Monthly backup",
      "packageFormat": "fzip"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "hasMore": false,
  "packageFormat": "fzip"
}
```

##### Delete FZIP Export
```http
DELETE /fzip/export/{exportId}

Response:
{
  "message": "FZIP export deleted successfully"
}
```

#### Import Endpoints

##### Create FZIP Import Job
```http
POST /fzip/import
Content-Type: application/json

{
  "mergeStrategy": "fail_on_conflict",
  "validateOnly": false,
  "packageFormat": "fzip"
}

Response:
{
  "importId": "uuid",
  "status": "uploaded",
  "message": "FZIP import job created successfully",
  "packageFormat": "fzip",
  "uploadUrl": {
    "url": "https://...",
    "fields": {...}
  }
}
```

##### List FZIP Imports
```http
GET /fzip/import?limit=20&lastEvaluatedKey=...

Response:
{
  "importJobs": [
    {
      "importId": "uuid",
      "status": "uploaded",
      "uploadedAt": 1234567890,
      "progress": 0,
      "currentPhase": "",
      "packageSize": null,
      "packageFormat": "fzip"
    }
  ],
  "nextEvaluatedKey": "...",
  "packageFormat": "fzip"
}
```

##### Get FZIP Import Status
```http
GET /fzip/import/{importId}/status

Response:
{
  "importId": "uuid",
  "status": "processing",
  "progress": 45,
  "currentPhase": "importing_transactions",
  "validationResults": {...},
  "importResults": {...},
  "errorMessage": null,
  "uploadedAt": 1234567890,
  "completedAt": null,
  "packageFormat": "fzip"
}
```

##### Delete FZIP Import Job
```http
DELETE /fzip/import/{importId}

Response: 204 No Content
```

##### Upload FZIP Package
```http
POST /fzip/import/{importId}/upload

Response:
{
  "message": "FZIP import processing started",
  "importId": "uuid",
  "status": "validating",
  "packageFormat": "fzip"
}
```

## Implementation Plan

### Phase 1: Export System (2-3 weeks)

#### Week 1: Core Export Infrastructure
1. **Unified FZIP Handler Lambda**
   - Create `fzip_operations.py` handler
   - Implement FZIP export job management 
   - Add FZIP export status tracking in DynamoDB

2. **Data Collection Service**
   - Create `ExportService` class
   - Implement user data collection methods
   - Add pagination for large datasets

3. **FZIP Package Builder**
   - Implement FZIP package creation
   - Add manifest generation
   - Implement file collection from S3

#### Week 2: Export Data Processing
1. **Entity Exporters**
   - Implement `AccountExporter` class
   - Implement `TransactionExporter` class  
   - Implement `CategoryExporter` class
   - Implement `FileMapExporter` class
   - Implement `TransactionFileExporter` class

2. **File Handling**
   - S3 file collection and packaging
   - Large file streaming and compression
   - Error handling and retry logic

#### Week 3: Export API and Testing
1. **API Integration** 
   - Add FZIP export endpoints to API Gateway
   - Implement authentication and authorization
   - Add FZIP export history tracking

2. **Testing and Optimization**
   - Unit tests for all FZIP export components
   - Integration tests with real data
   - Performance testing with large datasets

### Phase 2: Import System (3-4 weeks)

#### Week 1: Import Infrastructure
1. **Unified FZIP Handler Lambda**
   - Extend `fzip_operations.py` handler with import functionality
   - Implement FZIP import job management
   - Add validation framework

2. **FZIP Package Parser**
   - Implement FZIP package parsing
   - Add manifest validation
   - Implement schema validation

#### Week 2: Data Validation
1. **Validation Engine**
   - Implement `ImportValidator` class
   - Add cross-reference validation
   - Implement business rule validation

2. **Conflict Detection**
   - UUID conflict detection
   - Data consistency checks
   - Merge strategy implementation

#### Week 3: Data Restoration  
1. **Entity Importers**
   - Implement `AccountImporter` class
   - Implement `CategoryImporter` class
   - Implement `TransactionImporter` class
   - Implement `FileMapImporter` class

2. **File Restoration**
   - S3 file upload and restoration
   - File metadata recreation
   - File association restoration

#### Week 4: Import API and Testing
1. **API Integration**
   - Add FZIP import endpoints to API Gateway
   - Implement progress tracking
   - Add rollback capabilities

2. **Testing and Verification**
   - Comprehensive FZIP import/export round-trip tests
   - Data integrity verification
   - Error recovery testing

### Phase 3: Advanced Features (1-2 weeks)

#### Week 1: Enhanced Functionality
1. **Selective Import/Export**
   - Date range filtering
   - Account-specific exports
   - Category-only exports

2. **Analytics Integration**
   - Analytics data export/import
   - Post-import analytics regeneration
   - Performance optimizations

#### Week 2: UI and Documentation
1. **Frontend Integration**
   - FZIP export/import UI components
   - Progress indicators
   - Error handling displays

2. **Documentation and Deployment**
   - User documentation
   - API documentation updates
   - Deployment automation

## Database Schema Changes

### New Tables Required

#### Export Jobs Table
```sql
Table: housef3-{env}-export-jobs
PK: exportId (S)
Attributes:
  - userId (S) 
  - status (S) # initiated|processing|completed|failed
  - exportType (S) # complete|selective
  - exportFormat (S) # fzip|json
  - requestedAt (N)
  - completedAt (N) 
  - downloadUrl (S)
  - packageSize (N)
  - expiresAt (N)
  - error (S)
  - parameters (M) # export configuration

GSI: UserIdIndex (userId, requestedAt)
```

#### Import Jobs Table  
```sql
Table: housef3-{env}-import-jobs
PK: importId (S)
Attributes:
  - userId (S)
  - status (S) # uploaded|validating|processing|completed|failed
  - importFormat (S) # fzip|json
  - uploadedAt (N)
  - completedAt (N)
  - packageSize (N) 
  - validationResults (M)
  - importResults (M)
  - error (S)
  - mergeStrategy (S)

GSI: UserIdIndex (userId, uploadedAt)
```

## Security Considerations

### Data Protection
1. **User Isolation**: All FZIP export/import operations are strictly user-scoped
2. **Encryption**: All FZIP packages encrypted in transit and at rest
3. **Access Control**: Presigned URLs with short expiration times
4. **Audit Logging**: All FZIP import/export operations logged for security auditing

### Privacy Compliance
1. **Data Minimization**: Only necessary data included in FZIP exports
2. **Right to Portability**: Full data export supports GDPR compliance
3. **Secure Deletion**: FZIP export packages automatically deleted after expiration

## Performance Considerations

### Scalability
1. **Batch Processing**: Large datasets processed in configurable batches
2. **Streaming**: Large files streamed to avoid memory limitations
3. **Async Processing**: Long-running operations handled asynchronously
4. **Compression**: FZIP compression reduces package sizes

### Resource Management
1. **Lambda Limits**: Processing split across multiple invocations if needed
2. **Memory Usage**: Efficient streaming to minimize memory footprint
3. **Timeout Handling**: Graceful handling of Lambda timeout limits

## Error Handling and Recovery

### Export Error Scenarios
1. **Data Access Errors**: Retry with exponential backoff
2. **S3 Upload Failures**: Automatic retry and error reporting
3. **FZIP Package Size Limits**: Automatic splitting of large exports
4. **Timeout Handling**: Checkpoint and resume capability

### Import Error Scenarios  
1. **Validation Failures**: Detailed error reporting and guidance
2. **Partial Import Failures**: Transaction rollback for data consistency
3. **Duplicate Data**: Configurable merge strategies
4. **File Upload Errors**: Retry mechanisms and progress preservation

## Monitoring and Observability

### Metrics
1. **FZIP Export Success Rate**: Percentage of successful FZIP exports
2. **FZIP Import Success Rate**: Percentage of successful FZIP imports  
3. **Processing Time**: Average time for FZIP export/import operations
4. **FZIP Package Sizes**: Distribution of FZIP export package sizes
5. **Error Rates**: Categorized error rates and trends

### Alerting
1. **High Error Rates**: Alert on elevated failure rates
2. **Long Processing Times**: Alert on operations exceeding SLA
3. **Storage Usage**: Monitor S3 storage for FZIP export packages
4. **Security Events**: Alert on suspicious FZIP import/export patterns

## Future Enhancements

### Incremental Exports
- Delta exports containing only changes since last export
- Optimized for regular backup scenarios
- Reduced FZIP package sizes and processing time

### Multi-Format Support
- CSV export for analytics and reporting
- JSON API format for system integration
- Database dump format for direct database restoration
- **FZIP format** as the primary portable format

### Automated Scheduling
- Scheduled automatic FZIP exports
- Integration with backup systems
- Retention policy management

### Advanced Merge Strategies
- Intelligent conflict resolution
- Field-level merge capabilities  
- Custom merge rule configuration

## Conclusion

This comprehensive import/export system provides users with complete control over their financial data while maintaining security, performance, and data integrity. The **FZIP (Financial ZIP) format** ensures portability and standardization across environments. The unified `fzip_operations.py` handler provides a cohesive API for all FZIP-related operations. The phased implementation approach ensures robust testing and validation at each stage, delivering a reliable solution for data portability and backup needs. 