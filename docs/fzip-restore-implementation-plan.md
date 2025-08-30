# FZIP Restore Implementation Plan

## Current vs. Desired Flow Analysis

### ✅ **What's Already Implemented**

#### Status Enums and Models
- All required status enums exist in `FZIPStatus`:
  - `RESTORE_UPLOADED`, `RESTORE_VALIDATING`, `RESTORE_VALIDATION_PASSED`, `RESTORE_VALIDATION_FAILED`
  - `RESTORE_PROCESSING`, `RESTORE_COMPLETED`, `RESTORE_FAILED`, `RESTORE_CANCELED`
- `FZIPJob` model has all necessary fields (summary, restore_results, validation_results)
- Response models (`FZIPStatusResponse`) support conditional fields

#### API Endpoints
- ✅ `POST /fzip/restore` - Create restore job with presigned upload URL
- ✅ `POST /fzip/restore/{jobId}/upload` - Notify upload complete, start validation
- ✅ `GET /fzip/restore/{jobId}/status` - Get job status and progress
- ✅ `POST /fzip/restore/{jobId}/start` - Manual start (currently for validation passed)
- ✅ `POST /fzip/restore/{jobId}/cancel` - Cancel job
- ✅ `DELETE /fzip/restore/{jobId}` - Delete job

#### Service Implementation
- ✅ Package parsing from S3
- ✅ Schema validation with basic summary generation
- ✅ Business rules validation
- ✅ Phased restore processing (accounts → categories → file maps → transaction files → transactions)
- ✅ Progress tracking with phase updates
- ✅ Error handling and event emission

### ❌ **What's Missing (Implementation Gaps)**

#### 1. **Missing Status State**
- **Gap**: No `RESTORE_AWAITING_CONFIRMATION` status
- **Current**: Validation automatically proceeds to processing
- **Needed**: Stop after validation, wait for user confirmation

#### 2. **Summary Data Generation**
- **Gap**: Schema validation generates basic counts, but not the detailed summary structure needed for UI
- **Current**: Basic summary in validation results
- **Needed**: Rich summary with item details, file types, date ranges, hierarchy depth

#### 3. **User Confirmation Flow**
- **Gap**: No pause between validation and processing for user review
- **Current**: Validation immediately proceeds to restoration
- **Needed**: Stop at `restore_awaiting_confirmation`, require explicit user start

#### 4. **Retry Functionality**
- **Gap**: No retry endpoint
- **Current**: Only cancel/delete available for failed jobs
- **Needed**: `POST /fzip/restore/{jobId}/retry` endpoint

#### 5. **Enhanced Status Response**
- **Gap**: Status response doesn't conditionally include summary/results based on state
- **Current**: Always includes all fields
- **Needed**: Include summary only when `restore_awaiting_confirmation`, results only when completed

#### 6. **Infrastructure**
- **Gap**: Missing retry endpoint in Terraform configuration

---

## Implementation Plan

### **Phase 1: Core Flow Changes** 🔴 **High Priority**

#### 1.1 Add Missing Status State
**Files**: `backend/src/models/fzip.py`
```python
class FZIPStatus(str, Enum):
    # ... existing statuses ...
    RESTORE_AWAITING_CONFIRMATION = "restore_awaiting_confirmation"
```

#### 1.2 Modify Validation Flow in FZIPService
**Files**: `backend/src/services/fzip_service.py`

**Changes Needed**:
```python
def start_restore(self, restore_job: FZIPJob, package_s3_key: str):
    # ... existing validation logic ...
    
    if business_results['valid']:
        # NEW: Generate detailed summary
        summary_data = self._generate_summary_data(package_data)
        restore_job.summary = summary_data
        
        # NEW: Stop here and wait for user confirmation
        restore_job.status = FZIPStatus.RESTORE_AWAITING_CONFIRMATION
        restore_job.progress = 50
        restore_job.current_phase = "awaiting_user_confirmation"
        update_fzip_job(restore_job)
        
        # DON'T proceed to _restore_data() automatically
        return
```

#### 1.3 Create Summary Data Generation Method
**Files**: `backend/src/services/fzip_service.py`

**New Method**:
```python
def _generate_summary_data(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate detailed summary for user review"""
    data = package_data['data']
    
    # Analyze accounts
    accounts = data.get('accounts', [])
    account_summary = {
        "count": len(accounts),
        "items": [
            {"name": acc.get('name', 'Unknown'), "type": acc.get('account_type', 'unknown')}
            for acc in accounts[:10]  # Show first 10
        ]
    }
    
    # Analyze categories with hierarchy
    categories = data.get('categories', [])
    category_summary = self._analyze_category_hierarchy(categories)
    
    # Analyze transactions with date range
    transactions = data.get('transactions', [])
    transaction_summary = self._analyze_transaction_range(transactions)
    
    # Analyze files
    file_maps = data.get('file_maps', [])
    transaction_files = data.get('transaction_files', [])
    
    return {
        "accounts": account_summary,
        "categories": category_summary,
        "file_maps": {
            "count": len(file_maps),
            "totalSize": self._calculate_total_size(file_maps)
        },
        "transaction_files": {
            "count": len(transaction_files),
            "totalSize": self._calculate_file_size(transaction_files),
            "fileTypes": list(set(tf.get('file_type', 'unknown') for tf in transaction_files))
        },
        "transactions": transaction_summary
    }
```

#### 1.4 Update Start Handler Logic
**Files**: `backend/src/handlers/fzip_operations.py`

**Changes Needed**:
```python
def start_fzip_restore_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    # Change the status check
    if restore_job.status != FZIPStatus.RESTORE_AWAITING_CONFIRMATION:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'FZIP restore job is not awaiting confirmation. Current status: {restore_job.status.value}'})
        }
    
    # Proceed with restore
    fzip_service_instance.resume_restore(restore_job)
```

### **Phase 2: Enhanced Response Structure** 🟡 **Medium Priority**

#### 2.1 Update Status Response Logic
**Files**: `backend/src/handlers/fzip_operations.py`

**Changes Needed**:
```python
def get_fzip_restore_status_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    # ... existing logic ...
    
    response_data = {
        'jobId': str(restore_job.job_id),
        'status': restore_job.status.value,
        'progress': restore_job.progress,
        'currentPhase': restore_job.current_phase,
        'createdAt': restore_job.created_at,
        'updatedAt': getattr(restore_job, 'updated_at', restore_job.created_at)
    }
    
    # Conditionally include summary when awaiting confirmation
    if restore_job.status == FZIPStatus.RESTORE_AWAITING_CONFIRMATION:
        response_data['summary'] = restore_job.summary
    
    # Conditionally include results when completed
    if restore_job.status == FZIPStatus.RESTORE_COMPLETED:
        response_data['restore_results'] = restore_job.restore_results
    
    # Include error when failed
    if restore_job.is_failed():
        response_data['error'] = restore_job.error
    
    return create_response(200, response_data)
```

### **Phase 3: Retry Functionality** 🟡 **Medium Priority**

#### 3.1 Add Retry Handler
**Files**: `backend/src/handlers/fzip_operations.py`

**New Handler**:
```python
def retry_fzip_restore_handler(event: Dict[str, Any], user_id: str, job_id: str) -> Dict[str, Any]:
    """Handle POST /fzip/restore/{jobId}/retry - Retry failed restore job."""
    try:
        restore_job = get_fzip_job(job_id, user_id)
        if not restore_job:
            return create_response(404, {'error': 'FZIP restore job not found'})
        
        if restore_job.status != FZIPStatus.RESTORE_FAILED:
            return create_response(400, {'error': f'Can only retry failed jobs. Current status: {restore_job.status.value}'})
        
        # Reset job to validation state
        restore_job.status = FZIPStatus.RESTORE_VALIDATING
        restore_job.progress = 0
        restore_job.current_phase = "retrying"
        restore_job.error = None
        restore_job.validation_results = {}
        restore_job.restore_results = {}
        update_fzip_job(restore_job)
        
        # Restart the restore process
        fzip_service_instance.start_restore(restore_job, restore_job.s3_key)
        
        return create_response(200, {
            'jobId': str(restore_job.job_id),
            'status': restore_job.status.value,
            'message': 'Restore job retry initiated'
        })
        
    except Exception as e:
        logger.error(f"Error retrying FZIP restore job: {str(e)}")
        return create_response(500, {'error': f'Failed to retry restore job: {str(e)}'})
```

#### 3.2 Add Retry Route
**Files**: `backend/src/handlers/fzip_operations.py`

**Route Addition**:
```python
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # ... existing routes ...
    elif route == "POST /fzip/restore/{jobId}/retry":
        job_id = event.get('pathParameters', {}).get('jobId')
        return retry_fzip_restore_handler(event, user_id, job_id)
```

### **Phase 4: Infrastructure Updates** 🟢 **Low Priority**

#### 4.1 Add Retry Route to Terraform
**Files**: `infrastructure/terraform/api_gateway.tf`

**Addition**:
```hcl
resource "aws_apigatewayv2_route" "fzip_restore_retry" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /fzip/restore/{jobId}/retry"
  target    = "integrations/${aws_apigatewayv2_integration.fzip_operations.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}
```

### **Phase 5: Frontend Implementation** 🔴 **Critical for User Experience**

#### 5.1 Update FZIP Service Types
**Files**: `frontend/src/services/FZIPService.ts`

**Add New Status Type**:
```typescript
export type FZIPRestoreStatus = 
  | 'restore_uploaded' 
  | 'restore_validating'
  | 'restore_validation_failed'
  | 'restore_awaiting_confirmation'  // NEW
  | 'restore_processing'
  | 'restore_completed'
  | 'restore_failed'
  | 'restore_cancelled';

export interface FZIPRestoreSummary {
  accounts: {
    count: number;
    items: Array<{
      name: string;
      type: string;
    }>;
  };
  categories: {
    count: number;
    hierarchyDepth: number;
    items: Array<{
      name: string;
      level: number;
      children: number;
    }>;
  };
  file_maps: {
    count: number;
    totalSize: string;
  };
  transaction_files: {
    count: number;
    totalSize: string;
    fileTypes: string[];
  };
  transactions: {
    count: number;
    dateRange?: {
      earliest: string;
      latest: string;
    };
  };
}

export interface FZIPRestoreResults {
  accounts_created: number;
  categories_created: number;
  file_maps_created: number;
  transaction_files_created: number;
  transactions_created: number;
  total_processing_time: string;
  warnings: string[];
}

export interface FZIPRestoreStatusResponse {
  jobId: string;
  status: FZIPRestoreStatus;
  progress: number;
  currentPhase?: string;
  createdAt: number;
  updatedAt?: number;
  summary?: FZIPRestoreSummary;      // Only when awaiting confirmation
  restore_results?: FZIPRestoreResults; // Only when completed
  error?: string;                    // Only when failed
}
```

#### 5.2 Add Confirmation and Retry Methods
**Files**: `frontend/src/services/FZIPService.ts`

**New Service Methods**:
```typescript
// Confirm restore start after user reviews summary
export const confirmRestoreStart = async (restoreId: string): Promise<void> => {
  await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/start`, {
    method: 'POST'
  });
};

// Retry failed restore
export const retryRestore = async (restoreId: string): Promise<void> => {
  await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/retry`, {
    method: 'POST'
  });
};

// Enhanced status polling with conditional data
export const getRestoreStatus = async (restoreId: string): Promise<FZIPRestoreStatusResponse> => {
  const response = await authenticatedRequest(`${API_ENDPOINT}/fzip/restore/${restoreId}/status`);
  return response;
};
```

#### 5.3 Update Polling Strategy Hook
**Files**: `frontend/src/new-ui/hooks/useFZIPRestore.ts`

**Enhanced Polling Logic**:
```typescript
export const useFZIPRestoreStatus = (restoreId: string | null) => {
  const [status, setStatus] = useState<FZIPRestoreStatusResponse | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  // Progressive polling intervals based on status
  const getPollingInterval = (status: FZIPRestoreStatus, elapsedTime: number): number => {
    const intervals = {
      restore_uploaded: 2000,
      restore_validating: 1000,
      restore_awaiting_confirmation: 0,  // Stop polling - user action required
      restore_processing: 500,
      restore_completed: 0,              // Stop polling
      restore_failed: 0,
      restore_cancelled: 0
    };

    const baseInterval = intervals[status] || 5000;
    
    // Slow down after 1 minute of processing
    if (status === 'restore_processing' && elapsedTime > 60000) {
      return Math.min(baseInterval * 2, 2000);
    }
    
    return baseInterval;
  };

  useEffect(() => {
    if (!restoreId) return;

    let intervalId: NodeJS.Timeout | null = null;
    const startTime = Date.now();

    const poll = async () => {
      try {
        const response = await getRestoreStatus(restoreId);
        setStatus(response);

        const elapsedTime = Date.now() - startTime;
        const nextInterval = getPollingInterval(response.status, elapsedTime);
        
        if (nextInterval > 0) {
          intervalId = setTimeout(poll, nextInterval);
        } else {
          setIsPolling(false);
        }
      } catch (error) {
        console.error('Polling error:', error);
        setIsPolling(false);
      }
    };

    setIsPolling(true);
    poll();

    return () => {
      if (intervalId) clearTimeout(intervalId);
      setIsPolling(false);
    };
  }, [restoreId]);

  return { status, isPolling };
};
```

#### 5.4 Create Summary Display Component
**Files**: `frontend/src/new-ui/components/fzip/FZIPRestoreSummary.tsx`

**New Component**:
```tsx
import React from 'react';
import { FZIPRestoreSummary } from '../../services/FZIPService';
import './FZIPRestoreSummary.css';

interface Props {
  summary: FZIPRestoreSummary;
  onConfirm: () => void;
  onCancel: () => void;
  isConfirming?: boolean;
}

export const FZIPRestoreSummary: React.FC<Props> = ({ 
  summary, 
  onConfirm, 
  onCancel, 
  isConfirming = false 
}) => {
  return (
    <div className="fzip-restore-summary">
      <div className="summary-header">
        <h3>Restore Package Summary</h3>
        <p>Review what will be restored to your account:</p>
      </div>

      <div className="summary-sections">
        {/* Accounts Section */}
        <div className="summary-section">
          <h4>Accounts ({summary.accounts.count})</h4>
          {summary.accounts.items.length > 0 && (
            <ul className="item-list">
              {summary.accounts.items.map((account, index) => (
                <li key={index}>
                  <span className="item-name">{account.name}</span>
                  <span className="item-type">({account.type})</span>
                </li>
              ))}
              {summary.accounts.count > summary.accounts.items.length && (
                <li className="more-items">
                  ...and {summary.accounts.count - summary.accounts.items.length} more
                </li>
              )}
            </ul>
          )}
        </div>

        {/* Categories Section */}
        <div className="summary-section">
          <h4>Categories ({summary.categories.count})</h4>
          <p className="hierarchy-info">
            Hierarchy Depth: {summary.categories.hierarchyDepth} levels
          </p>
          {summary.categories.items.length > 0 && (
            <ul className="item-list">
              {summary.categories.items.map((category, index) => (
                <li key={index}>
                  <span className="item-name">{category.name}</span>
                  <span className="children-count">
                    ({category.children} subcategories)
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Transactions Section */}
        <div className="summary-section">
          <h4>Transactions ({summary.transactions.count})</h4>
          {summary.transactions.dateRange && (
            <p className="date-range">
              From {summary.transactions.dateRange.earliest} to {summary.transactions.dateRange.latest}
            </p>
          )}
        </div>

        {/* Files Section */}
        <div className="summary-section">
          <h4>Files</h4>
          <div className="file-stats">
            <div className="file-stat">
              <span>File Maps: {summary.file_maps.count}</span>
              <span>({summary.file_maps.totalSize})</span>
            </div>
            <div className="file-stat">
              <span>Transaction Files: {summary.transaction_files.count}</span>
              <span>({summary.transaction_files.totalSize})</span>
            </div>
            {summary.transaction_files.fileTypes.length > 0 && (
              <div className="file-types">
                Types: {summary.transaction_files.fileTypes.join(', ')}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="summary-actions">
        <button 
          className="btn-secondary" 
          onClick={onCancel}
          disabled={isConfirming}
        >
          Cancel Restore
        </button>
        <button 
          className="btn-primary" 
          onClick={onConfirm}
          disabled={isConfirming}
        >
          {isConfirming ? 'Starting Restore...' : 'Start Restore'}
        </button>
      </div>
    </div>
  );
};
```

#### 5.5 Create Results Display Component
**Files**: `frontend/src/new-ui/components/fzip/FZIPRestoreResults.tsx`

**New Component**:
```tsx
import React from 'react';
import { FZIPRestoreResults } from '../../services/FZIPService';
import './FZIPRestoreResults.css';

interface Props {
  results: FZIPRestoreResults;
  onClose: () => void;
}

export const FZIPRestoreResults: React.FC<Props> = ({ results, onClose }) => {
  return (
    <div className="fzip-restore-results">
      <div className="results-header">
        <h3>✅ Restore Completed Successfully!</h3>
        <p>Your data has been restored. Here's what was created:</p>
      </div>

      <div className="results-grid">
        <div className="result-item">
          <span className="result-count">{results.accounts_created}</span>
          <span className="result-label">Accounts</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.categories_created}</span>
          <span className="result-label">Categories</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.file_maps_created}</span>
          <span className="result-label">File Maps</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.transaction_files_created}</span>
          <span className="result-label">Transaction Files</span>
        </div>
        <div className="result-item">
          <span className="result-count">{results.transactions_created}</span>
          <span className="result-label">Transactions</span>
        </div>
      </div>

      <div className="processing-time">
        <p>Processing completed in {results.total_processing_time}</p>
      </div>

      {results.warnings.length > 0 && (
        <div className="warnings-section">
          <h4>⚠️ Warnings</h4>
          <ul>
            {results.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="results-actions">
        <button className="btn-primary" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
};
```

#### 5.6 Create Retry/Error Display Component
**Files**: `frontend/src/new-ui/components/fzip/FZIPRestoreError.tsx`

**New Component**:
```tsx
import React from 'react';
import './FZIPRestoreError.css';

interface Props {
  error: string;
  onRetry: () => void;
  onAbort: () => void;
  isRetrying?: boolean;
}

export const FZIPRestoreError: React.FC<Props> = ({ 
  error, 
  onRetry, 
  onAbort, 
  isRetrying = false 
}) => {
  return (
    <div className="fzip-restore-error">
      <div className="error-header">
        <h3>❌ Restore Failed</h3>
        <p>The restore process encountered an error:</p>
      </div>

      <div className="error-message">
        <code>{error}</code>
      </div>

      <div className="error-actions">
        <button 
          className="btn-secondary" 
          onClick={onAbort}
          disabled={isRetrying}
        >
          Abort Restore
        </button>
        <button 
          className="btn-primary" 
          onClick={onRetry}
          disabled={isRetrying}
        >
          {isRetrying ? 'Retrying...' : 'Retry Restore'}
        </button>
      </div>
    </div>
  );
};
```

#### 5.7 Update Main Restore View
**Files**: `frontend/src/new-ui/views/FZIPRestoreView.tsx`

**Enhanced State Management**:
```tsx
import React, { useState } from 'react';
import { useFZIPRestoreStatus } from '../hooks/useFZIPRestore';
import { confirmRestoreStart, retryRestore, deleteRestoreJob } from '../../services/FZIPService';
import { FZIPRestoreSummary } from '../components/fzip/FZIPRestoreSummary';
import { FZIPRestoreResults } from '../components/fzip/FZIPRestoreResults';
import { FZIPRestoreError } from '../components/fzip/FZIPRestoreError';

export const FZIPRestoreView: React.FC = () => {
  const [restoreId, setRestoreId] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const { status } = useFZIPRestoreStatus(restoreId);

  const handleConfirmRestore = async () => {
    if (!restoreId) return;
    
    setIsConfirming(true);
    try {
      await confirmRestoreStart(restoreId);
    } catch (error) {
      console.error('Failed to confirm restore:', error);
    } finally {
      setIsConfirming(false);
    }
  };

  const handleRetry = async () => {
    if (!restoreId) return;
    
    setIsRetrying(true);
    try {
      await retryRestore(restoreId);
    } catch (error) {
      console.error('Failed to retry restore:', error);
    } finally {
      setIsRetrying(false);
    }
  };

  const handleAbort = async () => {
    if (!restoreId) return;
    
    try {
      await deleteRestoreJob(restoreId);
      setRestoreId(null);
    } catch (error) {
      console.error('Failed to abort restore:', error);
    }
  };

  const handleClose = () => {
    setRestoreId(null);
  };

  // Render different components based on status
  if (!status) return <div>Loading...</div>;

  return (
    <div className="fzip-restore-view">
      {status.status === 'restore_awaiting_confirmation' && status.summary && (
        <FZIPRestoreSummary
          summary={status.summary}
          onConfirm={handleConfirmRestore}
          onCancel={handleAbort}
          isConfirming={isConfirming}
        />
      )}

      {status.status === 'restore_completed' && status.restore_results && (
        <FZIPRestoreResults
          results={status.restore_results}
          onClose={handleClose}
        />
      )}

      {status.status === 'restore_failed' && status.error && (
        <FZIPRestoreError
          error={status.error}
          onRetry={handleRetry}
          onAbort={handleAbort}
          isRetrying={isRetrying}
        />
      )}

      {/* Progress display for processing states */}
      {(['restore_validating', 'restore_processing'].includes(status.status)) && (
        <div className="restore-progress">
          <h3>Restore in Progress</h3>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <p>{status.currentPhase}</p>
          <p>{status.progress}% complete</p>
        </div>
      )}
    </div>
  );
};
```

#### 5.8 Required CSS Files
**Files**: `frontend/src/new-ui/components/fzip/*.css`

**New Stylesheets Needed**:
- `FZIPRestoreSummary.css` - Summary display styling
- `FZIPRestoreResults.css` - Results grid and success styling  
- `FZIPRestoreError.css` - Error display and retry button styling
- Update `FZIPRestoreView.css` - Progress bar and state-specific styling

**Key Styling Requirements**:
- Summary sections with clear visual hierarchy
- Results grid with prominent counts
- Error states with clear call-to-action buttons
- Progress indicators that match existing design system
- Responsive design for mobile/tablet
- Consistent with existing FZIP component styles

---

## Implementation Priority & Dependencies

### **🔴 Critical Path (Must implement first)**
1. **Phase 1** (Backend Core): Add missing status, summary generation, validation flow changes ✅ **COMPLETED**
2. **Phase 5.1-5.3** (Frontend Core): Types, service methods, polling hook

### **🟡 High Priority (For complete user experience)**
3. **Phase 5.4-5.7** (Frontend UI): Summary, results, error components, main view
4. **Phase 2** (Backend Enhancement): Enhanced status responses

### **🟢 Secondary Features**
5. **Phase 3** (Backend Retry): Retry functionality
6. **Phase 4** (Infrastructure): Terraform updates

### **Dependencies**
- Phase 5.1-5.3 (Frontend Core) depends on Phase 1 (Backend Core) ✅
- Phase 5.4-5.7 (Frontend UI) depends on Phase 5.1-5.3 (Frontend Core) 
- Phase 2 (Enhanced responses) can be developed in parallel with Frontend UI
- Phase 3 (Retry) should be done after Phase 5 (Frontend) is working
- Phase 4 (Infrastructure) should be done after Phase 3

### **Critical Integration Point**
- Backend Phase 1 ✅ + Frontend Phase 5.1-5.3 = **Minimal working user confirmation flow**
- Frontend Phase 5.4-5.7 = **Complete user experience**

---

## Testing Strategy

### **Unit Tests Needed**
1. `test_fzip_service.py`:
   - Test `_generate_summary_data()` method
   - Test validation flow stops at awaiting confirmation
   - Test resume from awaiting confirmation

2. `test_fzip_handlers.py`:
   - Test status response includes summary conditionally
   - Test retry handler functionality
   - Test start handler with new status check

### **Integration Tests**
1. End-to-end restore flow with user confirmation
2. Retry failed restore scenarios
3. Status polling during different phases

### **Frontend Integration**
- Update frontend to handle new `restore_awaiting_confirmation` status
- Implement summary display UI
- Add retry/abort buttons for failed states
- Update polling strategy per documentation

**Detailed Frontend Changes Needed - See Phase 5 below**

---

## Estimated Implementation Time

- **Phase 1** (Backend Core): 2-3 days ✅ **COMPLETED**
- **Phase 5** (Frontend): 3-4 days
  - Phase 5.1-5.3 (Core): 1-2 days
  - Phase 5.4-5.7 (UI Components): 2 days
- **Phase 2** (Backend Enhancement): 1 day  
- **Phase 3** (Retry): 1-2 days
- **Phase 4** (Infrastructure): 0.5 days
- **Testing & Integration**: 2-3 days

**Total**: 9.5-13.5 days
**Remaining** (after Phase 1): 7.5-10.5 days

---

## Risk Assessment

### **Low Risk**
- Status enum addition (backward compatible)
- Summary data generation (new functionality)
- Enhanced status responses (additive)

### **Medium Risk** 
- Validation flow change (changes existing behavior)
- Retry functionality (new state transitions)

### **Mitigation Strategies**
- Implement feature flags for new flow
- Thorough testing of state transitions
- Gradual rollout with monitoring
- Backup/rollback plan for validation flow changes
