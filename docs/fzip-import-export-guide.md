# FZIP Import/Export System - Complete Design and Implementation Guide

## Overview

This document provides comprehensive design and implementation guidance for the FZIP import/export system in the HouseF3 financial management application. The system enables users to backup their complete application state and restore it in the same or different environment using **FZIP (Financial ZIP) files** as the standardized portable format.

This document combines both the high-level system design and detailed technical implementation guidance to provide a complete reference for building the FZIP import/export functionality.

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

### FZIP System Architecture

```
User Request → FZIP Handler → Export/Import Service → FZIP Package Builder/Parser → Download/Upload URL
                     ↓              ↓                    ↓
                 Auth Check → Data Collection/Validation → FZIP Packaging → Signed URL
```

### FZIP Export Flow
```
User Request → FZIP Export Handler → Data Collector → FZIP Package Builder → Download URL
                     ↓              ↓                    ↓
                 Auth Check → Batch Retrieval → FZIP Packaging → Signed URL
```

### FZIP Import Flow
```
FZIP Upload → FZIP Import Handler → Validation → Transaction → Restoration → Verification
      ↓              ↓             ↓           ↓            ↓            ↓
   S3 Upload → Auth Check → FZIP Schema Check → Begin → Restore Data → Publish Events
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

### FZIP Operations

The system uses a unified `fzip_operations.py` handler that provides all FZIP operations:

#### Export Endpoints

##### Initiate FZIP Export
```http
POST /fzip/export
Content-Type: application/json

{
  "includeAnalytics": false,
  "description": "Monthly backup"
}

Response:
{
  "exportId": "uuid",
  "status": "initiated",
  "estimatedSize": "~25MB",
  "estimatedCompletion": "2024-01-15T10:35:00Z"
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
  "error": "error_message_if_failed"
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
      "description": "Monthly backup"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "hasMore": false
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
  "validateOnly": false
}

Response:
{
  "importId": "uuid",
  "status": "uploaded",
  "message": "FZIP import job created successfully",
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
      "packageSize": null
    }
  ],
  "nextEvaluatedKey": "..."
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
  "completedAt": null
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
  "status": "validating"
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

### Enhanced FZIP Features
- Compressed FZIP packages for reduced storage
- Encrypted FZIP packages for enhanced security
- FZIP format versioning for backward compatibility
- FZIP package validation and repair tools

### Automated Scheduling
- Scheduled automatic FZIP exports
- Integration with backup systems
- Retention policy management

### Advanced Merge Strategies
- Intelligent conflict resolution
- Field-level merge capabilities  
- Custom merge rule configuration

---

# TECHNICAL IMPLEMENTATION GUIDE

This section provides detailed technical guidance for implementing the FZIP import/export system described above.

## Code Structure and Organization

### New Services
```
backend/src/services/
├── export/
│   ├── export_service.py           # Main export orchestration
│   ├── data_collectors/
│   │   ├── account_collector.py    # Account data collection
│   │   ├── transaction_collector.py # Transaction data collection
│   │   ├── category_collector.py   # Category data collection
│   │   ├── file_map_collector.py   # File map data collection
│   │   └── analytics_collector.py  # Analytics data collection
│   ├── fzip_package_builder.py     # FZIP package creation
│   ├── manifest_generator.py       # Manifest file generation
│   └── file_collector.py          # S3 file collection
├── import/
│   ├── import_service.py           # Main import orchestration
│   ├── validators/
│   │   ├── schema_validator.py     # JSON schema validation
│   │   ├── business_validator.py   # Business logic validation
│   │   └── conflict_detector.py    # Conflict detection
│   ├── data_importers/
│   │   ├── account_importer.py     # Account data import
│   │   ├── transaction_importer.py # Transaction data import
│   │   ├── category_importer.py    # Category data import
│   │   └── file_map_importer.py    # File map data import
│   ├── fzip_package_parser.py      # FZIP package parsing
│   └── file_restorer.py           # S3 file restoration
└── common/
    ├── export_import_models.py     # Shared data models
    ├── job_tracker.py             # Job status tracking
    └── utils.py                   # Common utilities
```

### New Handlers
```
backend/src/handlers/
├── export_operations.py           # Export API endpoints
└── import_operations.py           # Import API endpoints
```

### Database Models
```
backend/src/models/
├── export_job.py                  # Export job tracking
└── import_job.py                  # Import job tracking
```

## Phase 1: Export System Implementation

### Step 1.1: Export Infrastructure (Week 1, Days 1-2)

#### Create Export Job Model
```python
# backend/src/models/export_job.py
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ExportStatus(str, Enum):
    INITIATED = "initiated"
    COLLECTING_DATA = "collecting_data"
    BUILDING_FZIP_PACKAGE = "building_fzip_package"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"

class ExportType(str, Enum):
    COMPLETE = "complete"
    ACCOUNTS_ONLY = "accounts_only"
    TRANSACTIONS_ONLY = "transactions_only"
    CATEGORIES_ONLY = "categories_only"
    DATE_RANGE = "date_range"

class ExportJob(BaseModel):
    export_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="exportId")
    user_id: str = Field(alias="userId")
    status: ExportStatus
    export_type: ExportType = Field(alias="exportType")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requested_at: int = Field(alias="requestedAt")
    completed_at: Optional[int] = Field(default=None, alias="completedAt")
    download_url: Optional[str] = Field(default=None, alias="downloadUrl")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    expires_at: Optional[int] = Field(default=None, alias="expiresAt")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: int = Field(default=0)  # 0-100
```

#### Create Export Operations Handler
```python
# backend/src/handlers/export_operations.py
import json
import logging
import uuid
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

from models.export_job import ExportJob, ExportStatus, ExportType
from services.export.export_service import ExportService
from utils.auth import get_user_from_event
from utils.lambda_utils import create_response, mandatory_body_parameter, optional_body_parameter
from utils.db_utils import create_export_job, get_export_job, update_export_job

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def initiate_export_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Initiate a new export job."""
    try:
        # Parse request parameters
        export_type = optional_body_parameter(event, 'exportType') or 'complete'
        include_analytics = optional_body_parameter(event, 'includeAnalytics') or False
        description = optional_body_parameter(event, 'description')
        
        # Create export job
        export_job = ExportJob(
            userId=user_id,
            status=ExportStatus.INITIATED,
            exportType=ExportType(export_type),
            parameters={
                'includeAnalytics': include_analytics,
                'description': description
            },
            requestedAt=int(datetime.now(timezone.utc).timestamp() * 1000)
        )
        
        # Save to database
        create_export_job(export_job)
        
        # Start async processing
        export_service = ExportService()
        export_service.start_export_async(export_job)
        
        return create_response(201, {
            'exportId': str(export_job.export_id),
            'status': export_job.status.value,
            'estimatedCompletion': calculate_estimated_completion(export_job)
        })
        
    except Exception as e:
        logger.error(f"Error initiating export: {str(e)}")
        return create_response(500, {'error': 'Failed to initiate export'})

def get_export_status_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Get export job status."""
    try:
        export_id = event.get('pathParameters', {}).get('exportId')
        export_job = get_export_job(uuid.UUID(export_id), user_id)
        
        if not export_job:
            return create_response(404, {'error': 'Export job not found'})
            
        return create_response(200, {
            'exportId': str(export_job.export_id),
            'status': export_job.status.value,
            'progress': export_job.progress,
            'downloadUrl': export_job.download_url,
            'expiresAt': export_job.expires_at,
            'error': export_job.error_message
        })
        
    except Exception as e:
        logger.error(f"Error getting export status: {str(e)}")
        return create_response(500, {'error': 'Failed to get export status'})

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main export operations handler."""
    try:
        user = get_user_from_event(event)
        if not user:
            return create_response(401, {"message": "Unauthorized"})
        user_id = user['id']
        
        route = event.get('routeKey')
        
        if route == "POST /export":
            return initiate_export_handler(event, user_id)
        elif route == "GET /export/{exportId}/status":
            return get_export_status_handler(event, user_id)
        elif route == "GET /export/{exportId}/download":
            return get_export_download_handler(event, user_id)
        else:
            return create_response(400, {"message": f"Unsupported route: {route}"})
            
    except Exception as e:
        logger.error(f"Export operations handler error: {str(e)}")
        return create_response(500, {"error": "Internal server error"})
```

### Step 1.2: Export Service Architecture (Week 1, Days 3-5)

#### Main Export Service
```python
# backend/src/services/export/export_service.py
import asyncio
import logging
from typing import List, Dict, Any
import boto3
from datetime import datetime, timezone, timedelta

from models.export_job import ExportJob, ExportStatus
from .data_collectors.account_collector import AccountCollector
from .data_collectors.transaction_collector import TransactionCollector
from .data_collectors.category_collector import CategoryCollector
from .fzip_package_builder import FZIPPackageBuilder
from .manifest_generator import ManifestGenerator
from utils.db_utils import update_export_job
from utils.s3_dao import put_object, get_presigned_url_simple

logger = logging.getLogger()

class ExportService:
    def __init__(self):
        self.account_collector = AccountCollector()
        self.transaction_collector = TransactionCollector()
        self.category_collector = CategoryCollector()
        self.fzip_package_builder = FZIPPackageBuilder()
        self.manifest_generator = ManifestGenerator()
    
    async def start_export_async(self, export_job: ExportJob):
        """Start export processing asynchronously."""
        try:
            # Update status to collecting data
            export_job.status = ExportStatus.COLLECTING_DATA
            export_job.progress = 10
            update_export_job(export_job)
            
            # Collect all data
            data = await self.collect_user_data(export_job)
            
            # Update status to building FZIP package
            export_job.status = ExportStatus.BUILDING_FZIP_PACKAGE
            export_job.progress = 60
            update_export_job(export_job)
            
            # Build FZIP export package
            package_path = await self.fzip_package_builder.build_fzip_package(export_job, data)
            
            # Update status to uploading
            export_job.status = ExportStatus.UPLOADING
            export_job.progress = 80
            update_export_job(export_job)
            
            # Upload to S3 and generate download URL
            download_url = await self.upload_package(export_job, package_path)
            
            # Complete export
            export_job.status = ExportStatus.COMPLETED
            export_job.progress = 100
            export_job.download_url = download_url
            export_job.expires_at = int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp() * 1000)
            export_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            update_export_job(export_job)
            
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            export_job.status = ExportStatus.FAILED
            export_job.error_message = str(e)
            update_export_job(export_job)
    
    async def collect_user_data(self, export_job: ExportJob) -> Dict[str, Any]:
        """Collect all user data for export."""
        user_id = export_job.user_id
        include_analytics = export_job.parameters.get('includeAnalytics', False)
        
        data = {}
        
        # Collect accounts
        data['accounts'] = await self.account_collector.collect_accounts(user_id)
        
        # Collect transactions  
        data['transactions'] = await self.transaction_collector.collect_transactions(user_id)
        
        # Collect categories
        data['categories'] = await self.category_collector.collect_categories(user_id)
        
        # Collect file maps
        data['file_maps'] = await self.file_map_collector.collect_file_maps(user_id)
        
        # Collect transaction files
        data['transaction_files'] = await self.file_collector.collect_transaction_files(user_id)
        
        # Collect analytics if requested
        if include_analytics:
            data['analytics'] = await self.analytics_collector.collect_analytics(user_id)
        
        return data
```

#### Data Collectors
```python
# backend/src/services/export/data_collectors/account_collector.py
from typing import List, Dict, Any
import logging
from utils.db_utils import list_user_accounts

logger = logging.getLogger()

class AccountCollector:
    async def collect_accounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect all user accounts for export."""
        try:
            accounts = list_user_accounts(user_id)
            return [account.model_dump(by_alias=True) for account in accounts]
        except Exception as e:
            logger.error(f"Error collecting accounts: {str(e)}")
            raise

# backend/src/services/export/data_collectors/transaction_collector.py
from typing import List, Dict, Any
import logging
from utils.db_utils import list_user_transactions

logger = logging.getLogger()

class TransactionCollector:
    async def collect_transactions(self, user_id: str) -> List[Dict[str, Any]]:
        """Collect all user transactions for export."""
        try:
            transactions = []
            last_evaluated_key = None
            batch_size = 1000
            
            # Paginate through all transactions
            while True:
                batch, last_evaluated_key, _ = list_user_transactions(
                    user_id,
                    limit=batch_size,
                    last_evaluated_key=last_evaluated_key,
                    uncategorized_only=False
                )
                
                if not batch:
                    break
                
                # Convert to export format
                for transaction in batch:
                    transactions.append(transaction.model_dump(by_alias=True))
                
                if not last_evaluated_key:
                    break
                    
            logger.info(f"Collected {len(transactions)} transactions for export")
            return transactions
            
        except Exception as e:
            logger.error(f"Error collecting transactions: {str(e)}")
            raise
```

### Step 1.3: FZIP Package Builder (Week 2, Days 1-3)

```python
# backend/src/services/export/fzip_package_builder.py
import zipfile
import json
import tempfile
import os
import logging
from typing import Dict, Any, List
from .manifest_generator import ManifestGenerator
from .file_collector import FileCollector

logger = logging.getLogger()

class FZIPPackageBuilder:
    def __init__(self):
        self.manifest_generator = ManifestGenerator()
        self.file_collector = FileCollector()
    
    async def build_fzip_package(self, export_job, data: Dict[str, Any]) -> str:
        """Build FZIP package with all export data."""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            package_path = os.path.join(temp_dir, f"export_{export_job.export_id}.fzip")
            
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add manifest
                manifest = self.manifest_generator.generate_manifest(export_job, data)
                zipf.writestr('manifest.json', json.dumps(manifest, indent=2))
                
                # Add data files
                zipf.writestr('data/accounts.json', json.dumps({'accounts': data['accounts']}, indent=2))
                zipf.writestr('data/transactions.json', json.dumps({'transactions': data['transactions']}, indent=2))
                zipf.writestr('data/categories.json', json.dumps({'categories': data['categories']}, indent=2))
                zipf.writestr('data/file_maps.json', json.dumps({'file_maps': data['file_maps']}, indent=2))
                zipf.writestr('data/transaction_files.json', json.dumps({'transaction_files': data['transaction_files']}, indent=2))
                
                if 'analytics' in data:
                    zipf.writestr('data/analytics.json', json.dumps({'analytics': data['analytics']}, indent=2))
                
                # Add actual files from S3
                await self._add_transaction_files(zipf, data['transaction_files'])
            
            return package_path
            
        except Exception as e:
            logger.error(f"Error building FZIP package: {str(e)}")
            raise
    
    async def _add_transaction_files(self, zipf: zipfile.ZipFile, transaction_files: List[Dict]):
        """Add actual transaction files from S3 to the FZIP package."""
        for file_metadata in transaction_files:
            try:
                file_id = file_metadata['fileId']
                file_name = file_metadata['fileName']
                s3_key = file_metadata['s3Key']
                
                # Download file content from S3
                file_content = self.file_collector.get_file_content_from_s3(s3_key)
                if file_content:
                    # Add to FZIP under files/[file_id]/[filename]
                    zipf.writestr(f'files/{file_id}/{file_name}', file_content)
                else:
                    logger.warning(f"Could not retrieve file content for {file_id}")
                    
            except Exception as e:
                logger.error(f"Error adding file {file_metadata.get('fileId')}: {str(e)}")
                # Continue with other files
```

## Phase 2: Import System Implementation

### Step 2.1: Import Infrastructure (Week 3, Days 1-2)

#### Create Import Job Model
```python
# backend/src/models/import_job.py
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid

class ImportStatus(str, Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MergeStrategy(str, Enum):
    FAIL_ON_CONFLICT = "fail_on_conflict"
    OVERWRITE = "overwrite"
    SKIP_EXISTING = "skip_existing"

class ImportJob(BaseModel):
    import_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="importId")
    user_id: str = Field(alias="userId")
    status: ImportStatus
    merge_strategy: MergeStrategy = Field(alias="mergeStrategy")
    uploaded_at: int = Field(alias="uploadedAt")
    completed_at: Optional[int] = Field(default=None, alias="completedAt")
    package_size: Optional[int] = Field(default=None, alias="packageSize")
    validation_results: Dict[str, Any] = Field(default_factory=dict, alias="validationResults")
    import_results: Dict[str, Any] = Field(default_factory=dict, alias="importResults")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    progress: int = Field(default=0)
    current_phase: str = Field(default="", alias="currentPhase")
```

### Step 2.2: Import Service Architecture (Week 3, Days 3-5)

```python
# backend/src/services/import/import_service.py
import logging
from typing import Dict, Any
from .validators.schema_validator import SchemaValidator
from .validators.business_validator import BusinessValidator
from .fzip_package_parser import FZIPPackageParser
from .data_importers.account_importer import AccountImporter
from .data_importers.transaction_importer import TransactionImporter
from models.import_job import ImportJob, ImportStatus

logger = logging.getLogger()

class ImportService:
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.business_validator = BusinessValidator()
        self.fzip_package_parser = FZIPPackageParser()
        self.account_importer = AccountImporter()
        self.transaction_importer = TransactionImporter()
    
    async def start_import_async(self, import_job: ImportJob, package_s3_key: str):
        """Start import processing asynchronously."""
        try:
            # Parse FZIP package
            import_job.status = ImportStatus.VALIDATING
            import_job.current_phase = "parsing_fzip_package"
            import_job.progress = 10
            update_import_job(import_job)
            
            package_data = await self.fzip_package_parser.parse_fzip_package(package_s3_key)
            
            # Validate schema
            import_job.current_phase = "validating_schema"
            import_job.progress = 20
            update_import_job(import_job)
            
            schema_results = await self.schema_validator.validate(package_data)
            import_job.validation_results['schema'] = schema_results
            
            if not schema_results['valid']:
                import_job.status = ImportStatus.VALIDATION_FAILED
                update_import_job(import_job)
                return
            
            # Validate business rules
            import_job.current_phase = "validating_business_rules"
            import_job.progress = 30
            update_import_job(import_job)
            
            business_results = await self.business_validator.validate(
                package_data, import_job.user_id, import_job.merge_strategy
            )
            import_job.validation_results['business'] = business_results
            
            if not business_results['valid']:
                import_job.status = ImportStatus.VALIDATION_FAILED
                update_import_job(import_job)
                return
            
            import_job.status = ImportStatus.VALIDATION_PASSED
            import_job.progress = 40
            update_import_job(import_job)
            
            # Begin data import
            await self.import_data(import_job, package_data)
            
        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            import_job.status = ImportStatus.FAILED
            import_job.error_message = str(e)
            update_import_job(import_job)
    
    async def import_data(self, import_job: ImportJob, package_data: Dict[str, Any]):
        """Import all data from the FZIP package."""
        try:
            import_job.status = ImportStatus.PROCESSING
            results = {}
            
            # Import in dependency order
            
            # 1. Import accounts first
            import_job.current_phase = "importing_accounts"
            import_job.progress = 50
            update_import_job(import_job)
            
            account_results = await self.account_importer.import_accounts(
                package_data['accounts'], import_job.user_id, import_job.merge_strategy
            )
            results['accounts'] = account_results
            
            # 2. Import categories
            import_job.current_phase = "importing_categories"
            import_job.progress = 60
            update_import_job(import_job)
            
            category_results = await self.category_importer.import_categories(
                package_data['categories'], import_job.user_id, import_job.merge_strategy
            )
            results['categories'] = category_results
            
            # 3. Import file maps
            import_job.current_phase = "importing_file_maps"
            import_job.progress = 70
            update_import_job(import_job)
            
            file_map_results = await self.file_map_importer.import_file_maps(
                package_data['file_maps'], import_job.user_id, import_job.merge_strategy
            )
            results['file_maps'] = file_map_results
            
            # 4. Import transaction files
            import_job.current_phase = "importing_transaction_files"
            import_job.progress = 80
            update_import_job(import_job)
            
            file_results = await self.file_importer.import_transaction_files(
                package_data['transaction_files'], import_job.user_id, import_job.merge_strategy
            )
            results['transaction_files'] = file_results
            
            # 5. Import transactions
            import_job.current_phase = "importing_transactions"
            import_job.progress = 90
            update_import_job(import_job)
            
            transaction_results = await self.transaction_importer.import_transactions(
                package_data['transactions'], import_job.user_id, import_job.merge_strategy
            )
            results['transactions'] = transaction_results
            
            # Complete import
            import_job.status = ImportStatus.COMPLETED
            import_job.progress = 100
            import_job.current_phase = "completed"
            import_job.import_results = results
            import_job.completed_at = int(datetime.now(timezone.utc).timestamp() * 1000)
            update_import_job(import_job)
            
        except Exception as e:
            logger.error(f"Error during data import: {str(e)}")
            raise
```

## Database Infrastructure Updates

### Step 3.1: Terraform Configuration

```hcl
# infrastructure/terraform/dynamo_export_jobs.tf
resource "aws_dynamodb_table" "export_jobs" {
  name           = "${var.project_name}-${var.environment}-export-jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "exportId"

  attribute {
    name = "exportId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "requestedAt"
    type = "N"
  }

  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "requestedAt"
    projection_type    = "ALL"
  }

  # TTL for automatic cleanup
  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-export-jobs"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# infrastructure/terraform/dynamo_import_jobs.tf
resource "aws_dynamodb_table" "import_jobs" {
  name           = "${var.project_name}-${var.environment}-import-jobs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "importId"

  attribute {
    name = "importId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "uploadedAt"
    type = "N"
  }

  global_secondary_index {
    name               = "UserIdIndex"
    hash_key           = "userId"
    range_key          = "uploadedAt"
    projection_type    = "ALL"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-import-jobs"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}
```

### Step 3.2: Lambda Configuration

```hcl
# infrastructure/terraform/lambda_export_import.tf
resource "aws_lambda_function" "export_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-export-operations"
  handler          = "handlers/export_operations.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 900  # 15 minutes for large exports
  memory_size     = 1024
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      EXPORT_JOBS_TABLE   = aws_dynamodb_table.export_jobs.name
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE    = aws_dynamodb_table.categories.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      FZIP_BUCKET         = aws_s3_bucket.fzip_storage.id
    }
  }
}

resource "aws_lambda_function" "import_operations" {
  filename         = "../../backend/lambda_deploy.zip"
  function_name    = "${var.project_name}-${var.environment}-import-operations"
  handler          = "handlers/import_operations.handler"
  runtime          = "python3.10"
  role            = aws_iam_role.lambda_exec.arn
  timeout         = 900  # 15 minutes for large imports
  memory_size     = 1024
  source_code_hash = base64encode(local.source_code_hash)
  depends_on      = [null_resource.prepare_lambda]
  
  environment {
    variables = {
      ENVIRONMENT         = var.environment
      IMPORT_JOBS_TABLE   = aws_dynamodb_table.import_jobs.name
      ACCOUNTS_TABLE      = aws_dynamodb_table.accounts.name
      TRANSACTIONS_TABLE  = aws_dynamodb_table.transactions.name
      CATEGORIES_TABLE    = aws_dynamodb_table.categories.name
      FILE_STORAGE_BUCKET = aws_s3_bucket.file_storage.id
      FZIP_BUCKET         = aws_s3_bucket.fzip_storage.id
    }
  }
}
```

## Testing Strategy

### Unit Tests
```python
# backend/tests/services/test_export_service.py
import pytest
from unittest.mock import Mock, patch
from services.export.export_service import ExportService
from models.export_job import ExportJob, ExportStatus, ExportType

class TestExportService:
    @pytest.fixture
    def export_service(self):
        return ExportService()
    
    @pytest.fixture
    def sample_export_job(self):
        return ExportJob(
            userId="test_user",
            status=ExportStatus.INITIATED,
            exportType=ExportType.COMPLETE,
            requestedAt=1642234567000
        )
    
    @patch('services.export.data_collectors.account_collector.AccountCollector.collect_accounts')
    async def test_collect_user_data(self, mock_collect_accounts, export_service, sample_export_job):
        mock_collect_accounts.return_value = [{'accountId': 'test_account'}]
        
        data = await export_service.collect_user_data(sample_export_job)
        
        assert 'accounts' in data
        assert len(data['accounts']) == 1
        mock_collect_accounts.assert_called_once_with("test_user")
```

### Integration Tests
```python
# backend/tests/integration/test_export_import_roundtrip.py
import pytest
from services.export.export_service import ExportService
from services.import.import_service import ImportService

class TestExportImportRoundtrip:
    async def test_complete_export_import_cycle(self):
        """Test that export->import preserves all data correctly."""
        # Setup test data
        user_id = "test_user"
        
        # Create test accounts, transactions, categories
        # ... setup code ...
        
        # Export data to FZIP
        export_service = ExportService()
        export_job = create_test_export_job(user_id)
        package_path = await export_service.process_export(export_job)
        
        # Clear user data
        # ... cleanup code ...
        
        # Import data from FZIP
        import_service = ImportService()
        import_job = create_test_import_job(user_id)
        await import_service.process_import(import_job, package_path)
        
        # Verify all data was restored correctly
        # ... verification code ...
```

## Performance Optimizations

### Batch Processing
```python
# backend/src/services/export/data_collectors/transaction_collector.py
class TransactionCollector:
    async def collect_transactions_optimized(self, user_id: str) -> List[Dict[str, Any]]:
        """Optimized transaction collection with parallel processing."""
        import asyncio
        
        # Get total count first
        total_count = await self.get_user_transaction_count(user_id)
        
        # Calculate optimal batch size
        batch_size = min(1000, max(100, total_count // 10))
        
        # Process in parallel batches
        tasks = []
        for offset in range(0, total_count, batch_size):
            task = asyncio.create_task(
                self.collect_transaction_batch(user_id, offset, batch_size)
            )
            tasks.append(task)
        
        # Wait for all batches
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        transactions = []
        for batch in batch_results:
            transactions.extend(batch)
        
        return transactions
```

### Memory Management
```python
# backend/src/services/export/fzip_package_builder.py
class FZIPPackageBuilder:
    async def build_large_fzip_package(self, export_job, data: Dict[str, Any]) -> str:
        """Build FZIP package with memory-efficient streaming."""
        import tempfile
        
        # Use temporary file to avoid memory limits
        with tempfile.NamedTemporaryFile(suffix='.fzip', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                # Write data in chunks
                await self._write_data_chunks(zipf, data)
                
                # Stream files directly from S3
                await self._stream_files_from_s3(zipf, data['transaction_files'])
        
        return temp_file.name
```

## Monitoring and Alerting

### CloudWatch Metrics
```python
# backend/src/services/common/metrics.py
import boto3
from datetime import datetime

class ExportImportMetrics:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
    
    def record_export_duration(self, duration_seconds: float, success: bool):
        """Record export processing duration."""
        self.cloudwatch.put_metric_data(
            Namespace='HouseF3/ExportImport',
            MetricData=[
                {
                    'MetricName': 'ExportDuration',
                    'Dimensions': [
                        {'Name': 'Success', 'Value': str(success)}
                    ],
                    'Value': duration_seconds,
                    'Unit': 'Seconds',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
    
    def record_fzip_package_size(self, size_bytes: int):
        """Record FZIP export package size."""
        self.cloudwatch.put_metric_data(
            Namespace='HouseF3/ExportImport',
            MetricData=[
                {
                    'MetricName': 'FZIPPackageSize',
                    'Value': size_bytes,
                    'Unit': 'Bytes',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
```

## Deployment Checklist

### Phase 1 Deployment - ✅ **MOSTLY COMPLETE (~80%)**
- [x] Deploy export job DynamoDB table *(Uses unified `fzip_jobs` table)*
- [x] Deploy export operations Lambda *(Deployed as `export_operations`)*
- [x] Update API Gateway routes *(Export routes: POST/GET /export configured)*
- [x] Deploy FZIP package S3 bucket *(Deployed as `fzip_packages` bucket)*
- [ ] **Test export functionality end-to-end** ⚠️ *PRIORITY: Test existing system*
- [ ] **Monitor CloudWatch logs and metrics** ⚠️ *NEEDS SETUP*

### Phase 2 Deployment - 🔄 **PARTIALLY COMPLETE (~25%)**  
- [x] Deploy import job DynamoDB table *(Uses unified `fzip_jobs` table)*
- [ ] **Deploy import operations Lambda** ❌ *MISSING: Need import Lambda function*
- [ ] **Update API Gateway routes for import** ❌ *MISSING: Need import API routes*
- [ ] Test import functionality end-to-end *(Blocked by missing Lambda/routes)*
- [ ] Test complete export-import roundtrip *(Blocked by missing import functionality)*
- [ ] Performance test with large datasets *(Blocked by missing import functionality)*

### Phase 3 Deployment - ❌ **NOT STARTED (0%)**
- [ ] Deploy frontend UI components *(Has transaction file import UI, but no FZIP export/import UI)*
- [ ] Update user documentation
- [ ] Deploy monitoring dashboards
- [ ] Set up automated alerts
- [ ] Conduct user acceptance testing
- [ ] Release to production

## Current Implementation Status

### ✅ **What's Already Built**
- **Unified FZIP Service** (`fzip_service.py`) - Complete with export/import functionality
- **FZIP Models** (`models/fzip.py`) - All data structures defined
- **Database Integration** (`db_utils.py`) - FZIP job management functions
- **Infrastructure** - DynamoDB table, S3 bucket, export Lambda deployed
- **Export API** - Routes and handlers configured
- **FZIP Operations Handler** (`handlers/fzip_operations.py`) - Complete unified handler

### 🔄 **Next Priority Tasks** 
1. **Test Export Functionality** - The export system is built but needs end-to-end testing
2. **Add Import API Routes** - Configure import endpoints in API Gateway
3. **Deploy Import Lambda** - Either create separate import Lambda or extend existing
4. **Build Frontend UI** - Create FZIP export/import user interface
5. **Setup Monitoring** - CloudWatch dashboards and alerts

### 📊 **Overall Progress: ~35% Complete**
The foundation is solid with a unified FZIP system that's more comprehensive than originally planned. The export functionality appears ready for testing, while import functionality needs API routing and possibly Lambda deployment to be fully operational.

## Conclusion

This comprehensive FZIP import/export system provides users with complete control over their financial data while maintaining security, performance, and data integrity. The **FZIP (Financial ZIP) format** ensures portability and standardization across environments. The unified `fzip_operations.py` handler provides a cohesive API for all FZIP-related operations. 

The phased implementation approach ensures robust testing and validation at each stage, delivering a reliable solution for data portability and backup needs. The detailed technical guidance provided above enables development teams to build this system with confidence, following established patterns and best practices for scalable cloud-native applications. 