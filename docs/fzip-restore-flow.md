### FZIP Restore Upload Flow

This document explains how a restore package upload is handled end-to-end. Each step has a DID (step id) for easy reference.

#### High level Stages
1. **Upload & Validation**: Create upload url, upload file through frontend, store file in bucket, validate file (schema + business rules), notify frontend of validation status
2. **Summary & User Decision**: Frontend presents validation status and shows summary of file contents (each object type and number of items), user can select "Start Restore" or "Delete"
3. **Restore Processing**: If user selects start, begin unmarshalling data from file into DynamoDB, update job status with progress after each object type, user sees real-time status updates through polling
4. **Terminal State Handling**: 
   - **Success**: Show final status of objects created with counts, provide "Close" button
   - **Failure**: Show user the specific error reason, provide "Retry" and "Abort" options

#### Step IDs

- DID-RST-01: Create restore job (returns S3 presigned POST)
- DID-RST-02: Browser uploads package to S3 via presigned POST
- DID-RST-03: Frontend notifies backend upload complete
- DID-RST-04: Backend handler transitions job to validating and starts restore
- DID-RST-05: Parse uploaded ZIP from restore bucket
- DID-RST-06: Schema validation
- DID-RST-07: Business rules validation
- DID-RST-08: Generate and return summary data for user review
- DID-RST-09: User confirms restore start (manual trigger required)
- DID-RST-10: Restore data in phases (accounts → categories → file maps → transaction files → transactions)
- DID-RST-11: Complete job, emit events
- DID-RST-12: Handle retry/abort operations for failed restores
- DID-RST-13: API Gateway routes and infra wiring

### High-level sequence

```mermaid
sequenceDiagram
autonumber
participant UI as "Frontend (UI)"
participant S3 as "S3 (Restore Packages Bucket)"
participant API as "API Gateway"
participant H as "Lambda Handler (fzip_operations)"
participant S as "Service (fzip_service)"
participant DB as "DynamoDB"

UI->>API: POST /fzip/restore (create)
API->>H: Invoke handler
H->>DB: create_fzip_job (status=restore_uploaded)
H-->>UI: Presigned POST for S3 (uploadUrl)
Note over UI,S3: DID-RST-01

UI->>S3: POST (presigned) file upload
Note over UI,S3: DID-RST-02

UI->>API: POST /fzip/restore/{jobId}/upload
API->>H: Invoke upload handler
Note over UI,H: DID-RST-03

H->>DB: get_fzip_job + update(status=restore_validating, s3Key)
H->>S: start_restore(job, s3Key)
Note over H,S: DID-RST-04

S->>S3: get_object (download uploaded .fzip)
S->>S: parse ZIP (manifest + data/*.json)
Note over S,S3: DID-RST-05

S->>S: validate schema
alt invalid
  S->>DB: update(status=restore_validation_failed)
  S-->>UI: (via polling) status=failed
else valid
  S->>S: validate business rules
  Note over S: DID-RST-06, DID-RST-07
  alt invalid
    S->>DB: update(status=restore_validation_failed)
  else valid
    S->>S: generate summary data
    S->>DB: update(status=restore_awaiting_confirmation, summary)
    S-->>UI: (via polling) status=awaiting_confirmation + summary
    Note over S,DB: DID-RST-08
  end
end

UI->>API: POST /fzip/restore/{jobId}/start (user confirms)
API->>H: Invoke start handler
H->>S: resume_restore(job)
Note over UI,S: DID-RST-09

S->>DB: update(status=restore_processing, progress)
S->>DB: restore entities (phased)
S->>S3: write restored file contents
S->>DB: update(status=restore_completed, results)
S-->>UI: (via polling) status=completed + results
Note over S,DB: DID-RST-10, DID-RST-11
```


```mermaid
sequenceDiagram
  autonumber
  participant UI as Frontend (UI)
  participant S3 as S3 (Restore Packages Bucket)
  participant API as API Gateway
  participant H as Lambda Handler (fzip_operations)
  participant S as Service (fzip_service)
  participant DB as DynamoDB

  UI->>API: POST /fzip/restore (create)
  API->>H: Invoke handler
  H->>DB: create_fzip_job (status=restore_uploaded)
  H-->>UI: Presigned POST for S3 (uploadUrl)
  Note over UI,S3: DID-RST-01

  UI->>S3: POST (presigned) file upload
  Note over UI,S3: DID-RST-02

  UI->>API: POST /fzip/restore/{jobId}/upload
  API->>H: Invoke upload handler
  Note over UI,H: DID-RST-03

  H->>DB: get_fzip_job + update(status=restore_validating, s3Key)
  H->>S: start_restore(job, s3Key)
  Note over H,S: DID-RST-04

  S->>S3: get_object (download uploaded .fzip)
  S->>S: parse ZIP (manifest + data/*.json)
  Note over S,S3: DID-RST-05

  S->>S: validate schema
  alt invalid
    S->>DB: update(status=restore_validation_failed)
    S-->>UI: (via polling) status=failed
  else valid
    S->>S: validate business rules
    Note over S: DID-RST-06, DID-RST-07
    alt invalid
      S->>DB: update(status=restore_validation_failed)
    else valid
      S->>S: generate summary data
      S->>DB: update(status=restore_awaiting_confirmation, summary)
      S-->>UI: (via polling) status=awaiting_confirmation + summary
      Note over S,DB: DID-RST-08
    end
  end

  UI->>API: POST /fzip/restore/{jobId}/start (user confirms)
  API->>H: Invoke start handler
  H->>S: resume_restore(job)
  Note over UI,S: DID-RST-09

  S->>DB: update(status=restore_processing, progress)
  S->>DB: restore entities (phased)
  S->>S3: write restored file contents
  S->>DB: update(status=restore_completed, results)
  S-->>UI: (via polling) status=completed + results
  Note over S,DB: DID-RST-10, DID-RST-11
```

### State flow

```mermaid
stateDiagram-v2
  [*] --> restore_uploaded: DID-RST-01
  restore_uploaded --> restore_validating: DID-RST-04
  restore_validating --> restore_validation_failed: DID-RST-06/DID-RST-07 (invalid)
  restore_validating --> restore_validation_passed: DID-RST-06/DID-RST-07 (valid)
  restore_validation_passed --> restore_awaiting_confirmation: DID-RST-08 (generate summary)
  restore_awaiting_confirmation --> restore_processing: DID-RST-09 (user confirms)
  restore_awaiting_confirmation --> restore_cancelled: user deletes/cancels
  restore_processing --> restore_completed: DID-RST-11 (success)
  restore_processing --> restore_failed: error
  restore_failed --> restore_processing: DID-RST-12 (retry)
  restore_failed --> restore_cancelled: DID-RST-12 (abort)
  restore_validation_failed --> restore_cancelled: user abandons
```

### Step details

- DID-RST-01: Create restore job, return presigned POST to S3
  - API: POST `/fzip/restore`
  - Handler creates job with `status=restore_uploaded` and returns `uploadUrl`.

```416:446:backend/src/handlers/fzip_operations.py
def create_fzip_restore_handler(event: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    # ...
    upload_url_data = get_presigned_post_url(
        bucket=restore_bucket,
        key=f"packages/{fzip_job.job_id}.fzip",
        expires_in=3600,
        conditions=[{'content-length-range': [1, 1024 * 1024 * 500]}]
    )
    response = FZIPResponse(
        jobId=fzip_job.job_id,
        # ...
        uploadUrl=upload_url_data
    )
```

- DID-RST-02: Browser uploads to S3 using presigned POST
  - Frontend constructs `FormData` with fields then `file`, posts to S3.

```447:474:frontend/src/services/FZIPService.ts
// Create form data and upload to S3 using presigned POST
const formData = new FormData();
Object.entries(uploadUrl.fields).forEach(([k, v]) => formData.append(k, v));
formData.append('file', file);
const uploadResponse = await fetch(uploadUrl.url, { method: 'POST', body: formData });
if (!uploadResponse.ok) throw new Error(`Upload failed: ${uploadResponse.status} ${uploadResponse.statusText}`);
```

- DID-RST-03: Frontend notifies backend that upload is complete
  - API: POST `/fzip/restore/{jobId}/upload` (no body required)

```475:479:frontend/src/services/FZIPService.ts
await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/upload`, { method: 'POST' });
```

- DID-RST-04: Upload handler transitions job and calls service
  - Validates job exists and is in `restore_uploaded`.
  - Sets `status=restore_validating`, records `s3Key`, calls `start_restore`.

```584:617:backend/src/handlers/fzip_operations.py
def upload_fzip_package_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    restore_job = get_fzip_job(job_id, user_id)
    # ... ensure status == RESTORE_UPLOADED ...
    restore_job.status = FZIPStatus.RESTORE_VALIDATING
    restore_job.s3_key = f"packages/{job_id}.fzip"
    fzip_service_instance.start_restore(restore_job, restore_job.s3_key)
```

- DID-RST-05: Service parses uploaded ZIP from restore bucket
  - Downloads `s3Key` from `FZIP_RESTORE_PACKAGES_BUCKET`.

```572:600:backend/src/services/fzip_service.py
def _parse_package(self, package_s3_key: str) -> Dict[str, Any]:
    package_data = get_object_content(package_s3_key, self.restore_packages_bucket)
    with zipfile.ZipFile(io.BytesIO(package_data), 'r') as zipf:
        manifest_data = zipf.read('manifest.json')
        # read data/*.json, return manifest + data + raw
```

- DID-RST-06: Schema validation

```500:507:backend/src/services/fzip_service.py
schema_results = self._validate_schema(package_data)
if not schema_results['valid']:
    restore_job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
    restore_job.error = "Schema validation failed"
    update_fzip_job(restore_job)
    return
```

- DID-RST-07: Business rules validation
  - Ownership, internal consistency; profile emptiness is pre-checked.

```514:524:backend/src/services/fzip_service.py
business_results = self._validate_business_rules(package_data, restore_job.user_id)
if not business_results['valid']:
    restore_job.status = FZIPStatus.RESTORE_VALIDATION_FAILED
    restore_job.error = "Business validation failed"
    update_fzip_job(restore_job)
    return
```

- DID-RST-08: Generate and return summary data for user review
  - After successful validation, create summary of restore contents for user review.
  - Summary includes counts and details for each object type.

**Summary Data Structure:**
```json
{
  "summary": {
    "accounts": {
      "count": 5,
      "items": [
        {"name": "Checking Account", "type": "checking"},
        {"name": "Savings Account", "type": "savings"}
      ]
    },
    "categories": {
      "count": 25,
      "hierarchyDepth": 3,
      "items": [
        {"name": "Food & Dining", "level": 1, "children": 8},
        {"name": "Transportation", "level": 1, "children": 4}
      ]
    },
    "file_maps": {
      "count": 12,
      "totalSize": "2.4MB"
    },
    "transaction_files": {
      "count": 8,
      "totalSize": "15.2MB",
      "fileTypes": ["csv", "ofx", "qif"]
    },
    "transactions": {
      "count": 1247,
      "dateRange": {
        "earliest": "2023-01-01",
        "latest": "2024-12-31"
      }
    }
  }
}
```

- DID-RST-09: User confirms restore start (manual trigger required)
  - API: POST `/fzip/restore/{jobId}/start`
  - Only allowed when status is `restore_awaiting_confirmation`

- DID-RST-10: Restore data in phases
  - Phases: accounts → categories → file maps → transaction files (including writing bytes to S3) → transactions.

```736:804:backend/src/services/fzip_service.py
def _restore_data(self, restore_job: FZIPJob, package_data: Dict[str, Any]):
    restore_job.current_phase = "restoring_accounts"; update_fzip_job(restore_job)
    self._restore_accounts(...)
    restore_job.current_phase = "restoring_categories"; update_fzip_job(restore_job)
    self._restore_categories(...)
    restore_job.current_phase = "restoring_file_maps"; update_fzip_job(restore_job)
    self._restore_file_maps(...)
    restore_job.current_phase = "restoring_transaction_files"; update_fzip_job(restore_job)
    self._restore_transaction_files(..., package_data)
    restore_job.current_phase = "restoring_transactions"; update_fzip_job(restore_job)
    self._restore_transactions(...)
```

- DID-RST-11: Complete job and emit events

```796:811:backend/src/services/fzip_service.py
restore_job.status = FZIPStatus.RESTORE_COMPLETED
restore_job.progress = 100
restore_job.current_phase = "completed"
restore_job.restore_results = results
update_fzip_job(restore_job)
event_service.publish_event(RestoreCompletedEvent(...))
```

**Completion Results Structure:**
```json
{
  "restore_results": {
    "accounts_created": 5,
    "categories_created": 25,
    "file_maps_created": 12,
    "transaction_files_created": 8,
    "transactions_created": 1247,
    "total_processing_time": "45.2s",
    "warnings": []
  }
}
```

- DID-RST-12: Handle retry/abort operations for failed restores
  - **Retry**: POST `/fzip/restore/{jobId}/retry` - Resets job to validation and re-runs
  - **Abort**: DELETE `/fzip/restore/{jobId}` - Cancels job and cleans up resources
  - Only available when status is `restore_failed`

- DID-RST-13: API routes and Lambda wiring
  - All restore routes mapped to the versioned `fzip_operations` Lambda via API Gateway.

```702:749:infrastructure/terraform/api_gateway.tf
# FZIP Restore routes
route_key = "POST /fzip/restore"              # Create new restore job
route_key = "GET /fzip/restore"               # List user's restore jobs
route_key = "GET /fzip/restore/{jobId}/status" # Get job status + progress
route_key = "DELETE /fzip/restore/{jobId}"    # Cancel/abort job
route_key = "POST /fzip/restore/{jobId}/upload" # Notify upload complete
route_key = "POST /fzip/restore/{jobId}/start"  # Confirm restore start
route_key = "POST /fzip/restore/{jobId}/retry"  # Retry failed restore
target = integrations/${aws_apigatewayv2_integration.fzip_operations.id}
```

### Frontend Polling Strategy

The frontend should implement progressive polling to provide real-time updates:

```typescript
// Polling intervals based on job status
const POLLING_INTERVALS = {
  restore_uploaded: 2000,           // Fast while validating
  restore_validating: 1000,         // Fastest during validation
  restore_awaiting_confirmation: 0, // No polling - user action required
  restore_processing: 500,          // Very fast during restore
  restore_completed: 0,             // Stop polling
  restore_failed: 0,                // Stop polling
  restore_cancelled: 0              // Stop polling
};

// Progressive backoff for long-running operations
function getPollingInterval(status: string, elapsedTime: number): number {
  const baseInterval = POLLING_INTERVALS[status] || 5000;
  
  if (status === 'restore_processing' && elapsedTime > 60000) {
    // Slow down after 1 minute of processing
    return Math.min(baseInterval * 2, 2000);
  }
  
  return baseInterval;
}
```

**Status Response Structure:**
```json
{
  "jobId": "job-123",
  "status": "restore_processing",
  "progress": 65,
  "current_phase": "restoring_transactions",
  "summary": { /* Only present when status=restore_awaiting_confirmation */ },
  "restore_results": { /* Only present when status=restore_completed */ },
  "error": "Error message", /* Only present when status=restore_failed */
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:22Z"
}
```

### Buckets and environment

- Restore package is read from `FZIP_RESTORE_PACKAGES_BUCKET` (falls back to `FZIP_PACKAGES_BUCKET`).
  - `FZIPService.restore_packages_bucket`

```63:74:backend/src/services/fzip_service.py
self.fzip_bucket = os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages')
self.restore_packages_bucket = os.environ.get(
  'FZIP_RESTORE_PACKAGES_BUCKET',
  os.environ.get('FZIP_PACKAGES_BUCKET', 'housef3-dev-fzip-packages')
)
```


