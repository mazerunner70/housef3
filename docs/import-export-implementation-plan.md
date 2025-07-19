# Import/Export Implementation Plan

## Technical Implementation Guide

This document provides detailed technical guidance for implementing the import/export system described in `import-export-design.md`.

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
│   ├── package_builder.py          # ZIP package creation
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
│   ├── package_parser.py           # ZIP package parsing
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
    BUILDING_PACKAGE = "building_package"
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
from .package_builder import PackageBuilder
from .manifest_generator import ManifestGenerator
from utils.db_utils import update_export_job
from utils.s3_dao import put_object, get_presigned_url_simple

logger = logging.getLogger()

class ExportService:
    def __init__(self):
        self.account_collector = AccountCollector()
        self.transaction_collector = TransactionCollector()
        self.category_collector = CategoryCollector()
        self.package_builder = PackageBuilder()
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
            
            # Update status to building package
            export_job.status = ExportStatus.BUILDING_PACKAGE
            export_job.progress = 60
            update_export_job(export_job)
            
            # Build export package
            package_path = await self.build_package(export_job, data)
            
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

### Step 1.3: Package Builder (Week 2, Days 1-3)

```python
# backend/src/services/export/package_builder.py
import zipfile
import json
import tempfile
import os
import logging
from typing import Dict, Any
from .manifest_generator import ManifestGenerator
from .file_collector import FileCollector

logger = logging.getLogger()

class PackageBuilder:
    def __init__(self):
        self.manifest_generator = ManifestGenerator()
        self.file_collector = FileCollector()
    
    async def build_package(self, export_job, data: Dict[str, Any]) -> str:
        """Build ZIP package with all export data."""
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp()
            package_path = os.path.join(temp_dir, f"export_{export_job.export_id}.zip")
            
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
            logger.error(f"Error building package: {str(e)}")
            raise
    
    async def _add_transaction_files(self, zipf: zipfile.ZipFile, transaction_files: List[Dict]):
        """Add actual transaction files from S3 to the package."""
        for file_metadata in transaction_files:
            try:
                file_id = file_metadata['fileId']
                file_name = file_metadata['fileName']
                s3_key = file_metadata['s3Key']
                
                # Download file content from S3
                file_content = self.file_collector.get_file_content_from_s3(s3_key)
                if file_content:
                    # Add to ZIP under files/[file_id]/[filename]
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
from .package_parser import PackageParser
from .data_importers.account_importer import AccountImporter
from .data_importers.transaction_importer import TransactionImporter
from models.import_job import ImportJob, ImportStatus

logger = logging.getLogger()

class ImportService:
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.business_validator = BusinessValidator()
        self.package_parser = PackageParser()
        self.account_importer = AccountImporter()
        self.transaction_importer = TransactionImporter()
    
    async def start_import_async(self, import_job: ImportJob, package_s3_key: str):
        """Start import processing asynchronously."""
        try:
            # Parse package
            import_job.status = ImportStatus.VALIDATING
            import_job.current_phase = "parsing_package"
            import_job.progress = 10
            update_import_job(import_job)
            
            package_data = await self.package_parser.parse_package(package_s3_key)
            
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
        """Import all data from the package."""
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
      PACKAGE_BUCKET     = aws_s3_bucket.export_packages.id
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
      PACKAGE_BUCKET     = aws_s3_bucket.export_packages.id
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
        
        # Export data
        export_service = ExportService()
        export_job = create_test_export_job(user_id)
        package_path = await export_service.process_export(export_job)
        
        # Clear user data
        # ... cleanup code ...
        
        # Import data
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
# backend/src/services/export/package_builder.py
class PackageBuilder:
    async def build_large_package(self, export_job, data: Dict[str, Any]) -> str:
        """Build package with memory-efficient streaming."""
        import tempfile
        
        # Use temporary file to avoid memory limits
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
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
    
    def record_package_size(self, size_bytes: int):
        """Record export package size."""
        self.cloudwatch.put_metric_data(
            Namespace='HouseF3/ExportImport',
            MetricData=[
                {
                    'MetricName': 'PackageSize',
                    'Value': size_bytes,
                    'Unit': 'Bytes',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
```

## Deployment Checklist

### Phase 1 Deployment
- [ ] Deploy export job DynamoDB table
- [ ] Deploy export operations Lambda
- [ ] Update API Gateway routes
- [ ] Deploy export package S3 bucket
- [ ] Test export functionality end-to-end
- [ ] Monitor CloudWatch logs and metrics

### Phase 2 Deployment  
- [ ] Deploy import job DynamoDB table
- [ ] Deploy import operations Lambda
- [ ] Update API Gateway routes for import
- [ ] Test import functionality end-to-end
- [ ] Test complete export-import roundtrip
- [ ] Performance test with large datasets

### Phase 3 Deployment
- [ ] Deploy frontend UI components
- [ ] Update user documentation
- [ ] Deploy monitoring dashboards
- [ ] Set up automated alerts
- [ ] Conduct user acceptance testing
- [ ] Release to production

This implementation plan provides the detailed technical guidance needed to build the complete import/export system while maintaining code quality, performance, and reliability standards. 