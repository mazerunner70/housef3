## FZIP Restore – Simplified Flow Implementation Plan

## Goal

- **Simplify restore UX** to mirror transaction file upload:
  - Frontend uploads `.fzip` directly to S3 via a presigned POST.
  - S3 object arrival triggers initial validation and registration of a restore job.
  - UI lists restore jobs with validation status; user explicitly starts restore.
  - Long-running restore exposes progress and supports cancel.

## High-level architecture

- **Upload**: Frontend requests presigned POST → uploads to S3 `restore_packages/` bucket.
- **Arrival**: S3 put event triggers a restore consumer Lambda that parses and validates the package, writes a `FZIPJob` with status and `validationResults`.
- **Selection**: UI lists restore jobs; user starts restore for `restore_validation_passed` jobs.
- **Processing**: Backend performs restore in phases with progress updates; cancel is available and observed between phases.

## Backend changes

### 1) API: Presigned upload URL for restore packages

- Endpoint: `POST /fzip/restore/upload-url`
- Handler: in `backend/src/handlers/fzip_operations.py` (new function, routed from the same `handler`).
- Behavior:
  - Generate a presigned POST via `utils.s3_dao.get_presigned_post_url`.
  - Key pattern: `restore_packages/{userId}/{restoreId}.fzip` where `restoreId = uuid4()`.
  - Include metadata fields: `x-amz-meta-userid`, `x-amz-meta-restoreid`.
  - Return `{ url, fields, restoreId, expiresIn }`.

Example response:

```json
{
  "restoreId": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "url": "https://s3.amazonaws.com/housef3-dev-restore-packages",
  "fields": {
    "key": "restore_packages/USER123/9b1d....fzip",
    "x-amz-meta-userid": "USER123",
    "x-amz-meta-restoreid": "9b1d...",
    "policy": "...",
    "x-amz-algorithm": "AWS4-HMAC-SHA256",
    "x-amz-credential": "...",
    "x-amz-date": "...",
    "x-amz-signature": "..."
  },
  "expiresIn": 3600
}
```

Notes:
- Validate key prefix and meta similarly to `get_upload_url_handler` for transaction files.
- Bucket: `FZIP_RESTORE_PACKAGES_BUCKET` env var; fallback to `FZIP_PACKAGES_BUCKET` (as today).

### 2) S3 consumer: validate and register restore jobs

- New Lambda: `backend/src/consumers/restore_consumer.py`.
- Trigger: S3 `ObjectCreated:*` on the restore packages bucket, prefix `restore_packages/`.
- Steps:
  - Read bucket/key/size; parse `userId` from key and/or metadata (`x-amz-meta-userid`).
  - Get `restoreId` from metadata (`x-amz-meta-restoreid`) or derive from key.
  - Build or upsert a `FZIPJob` with:
    - `jobType=restore`, `status=restore_validating`, `s3Key=key`, `progress=10`, `currentPhase="parsing_package"`.
  - Use existing service routines to perform initial validation only:
    - `fzip_service._parse_package(key)`
    - `fzip_service._validate_schema(package)`
    - `fzip_service._validate_business_rules(package, user_id)`
    - `fzip_service._validate_empty_profile(user_id)`
  - Persist `validationResults` and set status:
    - `restore_validation_passed` (progress ~40) or
    - `restore_validation_failed` with `error`.

Notes:
- Do not begin data restoration in this consumer; that happens only after explicit user action.
- Use `utils.db_utils` to create/update the job and preserve existing JSON encoding behavior.

### 3) Start restore processing (reuse, minor adjustments)

- Keep `POST /fzip/restore/{jobId}/start` in `fzip_operations.py`, but now it assumes the job exists from S3 consumer and is in `restore_validation_passed`.
- It should call `fzip_service.resume_restore(restore_job)` to begin long-running phases.

### 4) Cancel restore

- Add enum value in `backend/src/models/fzip.py`:
  - `RESTORE_CANCELED = "restore_canceled"` in `FZIPStatus`.
- Add endpoint: `POST /fzip/restore/{jobId}/cancel` in `fzip_operations.py`.
  - Sets job status to `restore_canceled` and records `error = "Canceled by user"`.
- In `backend/src/services/fzip_service.py`, ensure restore checks for cancel between phases:
  - Before/after each major section in `_restore_data` (accounts, categories, file_maps, files, transactions): re-read job or accept a `should_cancel(job)` helper that reloads status; if canceled, stop and finalize with `restore_canceled`.

### 5) Listing and status (existing)

- Continue using `GET /fzip/restore` and `GET /fzip/restore/{jobId}/status`.
- Ensure responses include `validationResults` and `currentPhase/progress` (already supported by `FZIPStatusResponse`).

## Infrastructure (Terraform)

- S3 event trigger:
  - In `infrastructure/terraform/lambda_consumers.tf` (or similar), add a Lambda for `restore_consumer.py` with permissions to read from restore bucket and write to DynamoDB.
  - In `infrastructure/terraform/s3_file_storage.tf` (or new file for restore packages), add an event notification for `ObjectCreated:*` with prefix `restore_packages/` pointing to the consumer Lambda.
- API Gateway:
  - Add `POST /fzip/restore/upload-url`.
  - Add `POST /fzip/restore/{jobId}/cancel`.
- IAM:
  - Allow consumer Lambda `s3:GetObject`, `s3:HeadObject` on restore bucket prefix.
  - Allow DynamoDB R/W on FZIP jobs table.

## Frontend changes

### 1) Service API (`frontend/src/services/FZIPService.ts`)

- Add:
  - `getFZIPRestoreUploadUrl(): Promise<{ restoreId: string; url: string; fields: Record<string,string>; expiresIn: number }>`
  - `cancelFZIPRestore(restoreId: string): Promise<void>`
- Keep existing:
  - `listFZIPRestoreJobs`, `getFZIPRestoreStatus`, `startFZIPRestoreProcessing`.
- Remove usage of old create/upload endpoints in the new flow (keep functions for compatibility if needed).

### 2) Upload UI (`frontend/src/new-ui/components/FZIPRestoreUpload.tsx`)

- Replace current two-step "create job + notify upload complete" with:
  - Call `getFZIPRestoreUploadUrl()`.
  - POST file to S3 using returned `url` and `fields` (same strategy as transaction file upload), with AbortController for cancel.
  - On success: show info "Uploaded; validation will start automatically" and trigger list refresh.

### 3) Restore list UI (`frontend/src/new-ui/components/FZIPRestoreList.tsx`)

- Show items with statuses: `Validation Passed`, `Validation Failed`, `Processing`, `Completed`, `Canceled`, `Failed`.
- Enable "Start Restore" only for `restore_validation_passed`.
- While `Processing`, show `Cancel` that calls `cancelFZIPRestore`.
- Continue polling `getFZIPRestoreStatus` for active jobs.

## Data model updates

- `backend/src/models/fzip.py`:
  - Add `RESTORE_CANCELED` to `FZIPStatus`.
  - Optionally add a `canceled: bool` flag to `FZIPJob` (or rely solely on status).
- Ensure JSON responses include new status string; frontend enum mirroring must be updated.

## Detailed implementation steps

1) Models
   - [x] Add `RESTORE_CANCELED` to `FZIPStatus` and update any status formatting helpers.
   - [x] Update frontend `FZIPRestoreStatus` to include `restore_canceled`.

2) Backend API
   - [x] Implement `post_fzip_restore_upload_url_handler` in `fzip_operations.py` using `get_presigned_post_url`.
   - [x] Wire route in `fzip_operations.handler` for `POST /fzip/restore/upload-url`.
   - [x] Implement `cancel_fzip_restore_handler` and route `POST /fzip/restore/{jobId}/cancel`.

3) Restore consumer Lambda
   - [x] Create `backend/src/consumers/restore_consumer.py` with S3 event handler.
   - [x] Parse metadata and key to determine `userId` and `restoreId`.
   - [x] Create/update `FZIPJob` with `RESTORE_VALIDATING`, run validation, then set to `RESTORE_VALIDATION_PASSED` or `RESTORE_VALIDATION_FAILED` and persist `validationResults`.

4) Service cancel checks
   - [x] In `FZIPService._restore_data`, before each phase, re-fetch job by id and exit early with `RESTORE_CANCELED` if status changed.
   - [x] Ensure idempotency and safe early exit.

5) Terraform
   - [x] Add consumer Lambda + permissions.
   - [x] Add S3 event notification on restore bucket (prefix `restore_packages/`).
   - [x] Add API routes/methods for new endpoints.

6) Frontend services
   - [x] Add `getFZIPRestoreUploadUrl` and `cancelFZIPRestore` in `FZIPService.ts`.
   - [x] Update `formatRestoreStatus` to include Canceled.

7) Frontend UI
   - [x] Update `FZIPRestoreUpload.tsx` to use presigned upload and show immediate feedback.
   - [x] Update `FZIPRestoreList.tsx` to show statuses, enable Start and Cancel appropriately, keep polling.
   - [x] Update `FZIPRestoreView.tsx` to remove reliance on old create/upload flow.

8) Backward compatibility (optional)
   - [x] Keep old `POST /fzip/restore` and `/upload` handlers for a deprecation period (hidden in UI).
   - [x] Add metrics to observe usage before removal.

## Testing plan

- Unit tests
  - [x] Model: enum round-tripping and JSON serialization for `RESTORE_CANCELED`.
  - [x] Handlers: upload URL generation; cancel handler state transitions.
  - [x] Consumer: S3 event parsing; validation pass/fail paths; DB writes.
  - [x] Service: cancel-aware early exit behavior.

- Integration tests (backend)
  - [ ] Upload → S3 event → validation → job listed with correct status and results.
  - [ ] Start restore → progress updates → completes; cancel mid-way → transitions to `restore_canceled`.

- Frontend tests
  - [x] Upload component uses presigned POST and handles cancel.
  - [x] List shows correct actions per status; Start and Cancel wire correctly; polling updates UI.

## Rollout

- Deploy backend first (new endpoints + consumer + model changes).
- Deploy infra changes (S3 notifications, IAM, API routes).
- Deploy frontend after backend is live.
- Keep old endpoints temporarily to avoid breaking older clients during transition.

## Acceptance criteria

- Users can upload `.fzip` via presigned POST; uploads trigger validation automatically.
- Restore jobs appear with validation results; Start enabled only when passed.
- Restore progress is visible; Cancel stops processing and marks job as canceled.
- No UI step required to “notify upload complete.”
- All changes adhere to existing project structure and conventions.


