# Generic Operation Tracking System

## Overview

This system provides a **unified way to track any long-running backend operation** with real-time progress updates, status monitoring, and user-friendly UI components.

## Architecture

```
Frontend                    Backend
┌─────────────────────┐    ┌──────────────────────────────┐
│ React Components    │    │ Operation Tracking Service   │
│ ↕                   │    │ ↕                            │
│ useOperationTracking│ ←→ │ API Endpoints               │
│ ↕                   │    │ ↕                            │
│ OperationService    │    │ Vote Service (for approvals) │
│ (polling)           │    │ ↕                            │
└─────────────────────┘    │ DynamoDB (operation state)   │
                           └──────────────────────────────┘
```

## Usage Examples

### 1. File Deletion with Voting

```tsx
// FileListItem.tsx
import { useState } from 'react';
import { operationTrackingService } from '../services/OperationTrackingService';
import { OperationProgressModal } from '../components/OperationProgressModal';

const FileListItem = ({ file }) => {
  const [operationId, setOperationId] = useState<string | null>(null);
  const [showProgress, setShowProgress] = useState(false);

  const handleDelete = async () => {
    try {
      // Start the deletion process
      const response = await fetch(`/api/files/${file.id}`, {
        method: 'DELETE'
      });
      
      const result = await response.json();
      
      // Start tracking the operation
      setOperationId(result.operationId);
      setShowProgress(true);
      
    } catch (error) {
      console.error('Failed to start deletion:', error);
    }
  };

  return (
    <div className="file-item">
      <span>{file.name}</span>
      <button onClick={handleDelete}>Delete</button>
      
      {operationId && (
        <OperationProgressModal
          operationId={operationId}
          isOpen={showProgress}
          onClose={() => setShowProgress(false)}
          onComplete={() => {
            // Remove file from list
            onFileDeleted(file.id);
          }}
          title="Deleting File"
          mode="full" // or "percent" for simplified view
        />
      )}
    </div>
  );
};
```

### 2. File Upload with Validation (Percent Mode)

```tsx
// FileUpload.tsx
const FileUpload = () => {
  const [operationId, setOperationId] = useState<string | null>(null);
  
  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/files/upload', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    setOperationId(result.operationId);
  };

  return (
    <div>
      <input type="file" onChange={(e) => handleUpload(e.target.files[0])} />
      
      {operationId && (
        <OperationProgressModal
          operationId={operationId}
          isOpen={!!operationId}
          onClose={() => setOperationId(null)}
          title="Processing Upload"
          mode="percent" // Simplified circular progress view
        />
      )}
    </div>
  );
};
```

### 2b. Comparison of Modes

```tsx
// Full Mode - Shows detailed steps, voter status, etc.
<OperationProgressModal
  operationId={operationId}
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  title="Deleting File"
  mode="full" // Default - shows step indicator, voter status, detailed progress
/>

// Percent Mode - Simple circular progress
<OperationProgressModal
  operationId={operationId}
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  title="Processing Upload"
  mode="percent" // Simplified - just shows percentage in a circle
/>
```

### 3. Data Export

```tsx
// DataExport.tsx
const DataExport = () => {
  const {
    progress,
    startTracking,
    isTracking,
    error
  } = useOperationTracking();

  const handleExport = async () => {
    const response = await fetch('/api/data/export', {
      method: 'POST',
      body: JSON.stringify({ format: 'csv', dateRange: '2024' })
    });
    
    const result = await response.json();
    startTracking(result.operationId);
  };

  return (
    <div>
      <button onClick={handleExport} disabled={isTracking}>
        {isTracking ? 'Exporting...' : 'Export Data'}
      </button>
      
      {progress && (
        <div className="export-progress">
          <div>Status: {progress.status}</div>
          <div>Progress: {progress.progressPercentage}%</div>
          {progress.timeRemaining && (
            <div>Time remaining: {progress.timeRemaining}</div>
          )}
        </div>
      )}
    </div>
  );
};
```

### 4. Operations Dashboard

```tsx
// OperationsDashboard.tsx
import { useOperationList } from '../hooks/useOperationTracking';
import { OperationType, OperationStatus } from '../services/OperationTrackingService';

const OperationsDashboard = () => {
  const { operations, loading, refresh } = useOperationList({
    status: [OperationStatus.IN_PROGRESS, OperationStatus.WAITING_FOR_APPROVAL],
    limit: 20
  });

  return (
    <div className="operations-dashboard">
      <h2>Active Operations</h2>
      
      {loading ? (
        <div>Loading...</div>
      ) : (
        <div className="operations-list">
          {operations.map(op => (
            <div key={op.operationId} className="operation-card">
              <h3>{op.displayName}</h3>
              <div className="operation-status">
                <span className={`status-badge ${op.status}`}>
                  {op.status}
                </span>
                <span>{op.progressPercentage}%</span>
              </div>
              {op.timeRemaining && (
                <div>ETA: {op.timeRemaining}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

## Backend Integration

### 1. Update File Operations Handler

```python
# file_operations.py
from services.operation_tracking_service import operation_tracking_service, OperationType, OperationStatus

@app.route('/files/<file_id>', methods=['DELETE'])
def delete_file_handler(file_id: str):
    user_id = get_current_user_id()
    
    # Start operation tracking
    operation_id = operation_tracking_service.start_operation(
        operation_type=OperationType.FILE_DELETION,
        entity_id=file_id,
        user_id=user_id,
        context={
            'fileName': file.name,
            'fileSize': file.size,
            'transactionCount': file.transaction_count
        }
    )
    
    # Update to waiting for approval
    operation_tracking_service.update_operation_status(
        operation_id=operation_id,
        status=OperationStatus.WAITING_FOR_APPROVAL,
        progress_percentage=10,
        current_step=1,
        step_description="Collecting approval votes"
    )
    
    # Publish deletion request event (existing voting logic)
    delete_request_event = FileDeletionRequestedEvent(
        user_id=user_id,
        file_id=file_id,
        request_id=operation_id,  # Use operation_id as request_id
        # ... other fields
    )
    event_service.publish_event(delete_request_event)
    
    return {
        'operationId': operation_id,
        'status': 'initiated',
        'message': 'File deletion started'
    }, 202
```

### 2. Update Vote Service Integration

```python
# vote_service.py - update to integrate with operation tracking
def record_vote(self, workflow_type: str, entity_id: str, request_id: str, 
               voter: str, decision: str, reason: str = '') -> Optional[str]:
    
    # Existing vote recording logic...
    final_decision = # ... existing logic
    
    # Update operation tracking
    if workflow_type == 'file.deletion':
        if final_decision == 'approved':
            operation_tracking_service.update_operation_status(
                operation_id=request_id,
                status=OperationStatus.APPROVED,
                progress_percentage=75,
                current_step=2,
                step_description="All approvals received, starting deletion"
            )
        elif final_decision == 'denied':
            operation_tracking_service.update_operation_status(
                operation_id=request_id,
                status=OperationStatus.DENIED,
                progress_percentage=0,
                error_message=f"Denied by {voter}: {reason}"
            )
    
    return final_decision
```

### 3. Add Operation Status API

```python
# New API endpoints
@app.route('/operations/<operation_id>/status', methods=['GET'])
def get_operation_status(operation_id: str):
    user_id = get_current_user_id()
    status = operation_tracking_service.get_operation_status(operation_id)
    
    if not status:
        return {'error': 'Operation not found'}, 404
    
    # Verify user owns this operation
    if status.get('context', {}).get('userId') != user_id:
        return {'error': 'Unauthorized'}, 403
    
    return status

@app.route('/operations', methods=['GET'])
def list_user_operations():
    user_id = get_current_user_id()
    
    # Parse query parameters
    status_filter = request.args.get('status', '').split(',') if request.args.get('status') else None
    operation_type_filter = request.args.get('operationType', '').split(',') if request.args.get('operationType') else None
    limit = int(request.args.get('limit', 50))
    
    operations = operation_tracking_service.list_user_operations(
        user_id=user_id,
        status_filter=[OperationStatus(s) for s in status_filter] if status_filter else None,
        operation_type_filter=[OperationType(t) for t in operation_type_filter] if operation_type_filter else None,
        limit=limit
    )
    
    return operations

@app.route('/operations/<operation_id>/cancel', methods=['POST'])
def cancel_operation(operation_id: str):
    user_id = get_current_user_id()
    data = request.get_json()
    reason = data.get('reason', 'Cancelled by user')
    
    success = operation_tracking_service.cancel_operation(operation_id, user_id, reason)
    
    return {'success': success}
```

## Benefits

### ✅ **For Developers:**
- **🔄 Reusable**: Same system for all long-running operations
- **🧪 Testable**: Easy to mock and test
- **📊 Consistent**: Standardized progress tracking
- **🔧 Configurable**: Easy to add new operation types

### ✅ **For Users:**
- **👁️ Transparent**: See exactly what's happening
- **⏱️ Predictable**: Know how long operations will take
- **🚫 Controllable**: Cancel operations when possible
- **📱 Responsive**: Non-blocking UI experience

### ✅ **For Operations:**
- **📈 Monitorable**: Track all operations in one place
- **🔍 Debuggable**: Full audit trail of operation steps
- **📊 Metrics**: Operation success rates and timing
- **🚨 Alertable**: Can alert on failed operations

This system transforms any long-running backend process into a **user-friendly, trackable operation** with minimal code changes!
