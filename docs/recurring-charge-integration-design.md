# Recurring Charge Detection - Integration Design

**Version:** 1.0  
**Date:** November 2, 2025  
**Related Documents:** `ml-recurring-charge-detection-design.md`

## Overview

This document describes the integration of ML-based recurring charge detection into the existing HouseF3 architecture, using the established consumer pattern and operation tracking system.

### Integration Points

1. **Categories Page**: Primary UI for viewing/managing detected patterns
2. **Consumer Pattern**: Long-running detection tasks
3. **Operation Tracking**: Progress monitoring via workflow system
4. **Feedback Loop**: User corrections feed back to improve detection

---

## Architecture Integration

### System Flow

```
User Triggers Detection (Categories Page)
    ↓
POST /api/recurring-charges/detect
    ↓
Creates Operation Record (WorkflowsTable)
    ↓
Publishes Event → EventBridge
    ↓
Recurring Charge Consumer
    ↓
┌─────────────────────────────────────────────┐
│  1. Load transactions (paginated)           │
│  2. Feature engineering                     │
│  3. DBSCAN clustering                       │
│  4. Pattern analysis                        │
│  5. Confidence scoring                      │
│  6. Save patterns to DB                     │
│  7. Update operation progress (10%, 30%...) │
└─────────────────────────────────────────────┘
    ↓
Frontend Polls Operation Status
    ↓
Display Results in Categories Page
    ↓
User Provides Feedback (Confirm/Reject)
    ↓
Feedback Stored → Improves Future Detection
```

---

## Backend Implementation

### 1. Data Models

#### RecurringChargePattern (Add to existing `models/recurring_charge.py`)

Already defined in main design doc. DynamoDB structure:

```
Table: RecurringChargePatterns
PK: userId
SK: patternId
GSI: patternId-index (for lookups)
```

#### PatternFeedback (New model)

```python
# backend/src/models/recurring_charge.py

class PatternFeedbackType(str, Enum):
    CORRECT = "correct"                    # User confirmed pattern
    INCORRECT = "incorrect"                # False positive
    MISSED_TRANSACTION = "missed_transaction"  # Should be in pattern but wasn't
    FALSE_POSITIVE = "false_positive"      # Transaction shouldn't be in pattern
    AMOUNT_WRONG = "amount_wrong"          # Amount range is wrong
    TEMPORAL_WRONG = "temporal_wrong"      # Temporal pattern is wrong

class PatternFeedback(BaseModel):
    """User feedback on pattern detection"""
    feedback_id: uuid.UUID = Field(default_factory=uuid.uuid4, alias="feedbackId")
    user_id: str = Field(alias="userId")
    pattern_id: uuid.UUID = Field(alias="patternId")
    feedback_type: PatternFeedbackType = Field(alias="feedbackType")
    
    # Optional context
    transaction_id: Optional[uuid.UUID] = Field(default=None, alias="transactionId")
    correction: Optional[Dict[str, Any]] = None  # What user changed
    comment: Optional[str] = None
    
    # Metadata
    created_at: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp() * 1000),
        alias="createdAt"
    )
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={uuid.UUID: str}
    )

# DynamoDB Structure
Table: RecurringChargeFeedback
PK: userId
SK: feedbackId
GSI: patternId-index (get all feedback for a pattern)
```

### 2. Operation Type Addition

```python
# backend/src/services/operation_tracking_service.py

class OperationType(str, Enum):
    FILE_DELETION = "file_deletion"
    FILE_UPLOAD = "file_upload"
    DATA_EXPORT = "data_export"
    ACCOUNT_MIGRATION = "account_migration"
    RECURRING_CHARGE_DETECTION = "recurring_charge_detection"  # NEW

# Add to operation_configs in OperationTrackingService.__init__:

OperationType.RECURRING_CHARGE_DETECTION: {
    'display_name': 'Detecting Recurring Charges',
    'estimated_duration_minutes': 2,  # Depends on transaction count
    'steps': [
        {'name': 'initiated', 'description': 'Starting pattern detection'},
        {'name': 'loading_data', 'description': 'Loading transactions'},
        {'name': 'feature_extraction', 'description': 'Analyzing transaction patterns'},
        {'name': 'clustering', 'description': 'Grouping similar transactions'},
        {'name': 'pattern_analysis', 'description': 'Detecting recurring patterns'},
        {'name': 'saving_patterns', 'description': 'Saving detected patterns'},
        {'name': 'completed', 'description': 'Pattern detection complete'}
    ],
    'cancellable_until': OperationStatus.EXECUTING
}
```

### 3. Recurring Charge Consumer

```python
# backend/src/consumers/recurring_charge_consumer.py

"""
Recurring Charge Detection Consumer

Processes long-running recurring charge detection tasks triggered from the
categories page. Updates operation progress as detection proceeds.

Event Types Processed:
- recurring_charge.detection.requested: Run pattern detection
"""

import json
import logging
import os
import sys
import traceback
from typing import Dict, Any, List, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Fix imports for Lambda environment
try:
    if '/var/task' not in sys.path:
        sys.path.insert(0, '/var/task')
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    logger.info("Successfully adjusted Python path for Lambda environment")
except Exception as e:
    logger.error(f"Import path setup error: {str(e)}")
    raise

from consumers.base_consumer import BaseEventConsumer
from models.events import BaseEvent
from services.recurring_charge_detection_service import RecurringChargeDetectionService
from services.operation_tracking_service import OperationTrackingService, OperationStatus
from utils.db_utils import list_user_transactions

ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'


class RecurringChargeDetectionConsumer(BaseEventConsumer):
    """Consumer for recurring charge detection events"""
    
    DETECTION_EVENT_TYPES = {
        'recurring_charge.detection.requested',
        'recurring_charge.detection.retry'
    }
    
    def __init__(self):
        super().__init__("recurring_charge_consumer")
        self.detection_service = RecurringChargeDetectionService()
        self.operation_service = OperationTrackingService()
    
    def should_process_event(self, event: BaseEvent) -> bool:
        """Only process recurring charge detection events"""
        return event.event_type in self.DETECTION_EVENT_TYPES
    
    def process_event(self, event: BaseEvent) -> None:
        """Run recurring charge detection with progress tracking"""
        try:
            event_type = event.event_type
            user_id = event.user_id
            
            # Extract operation details from event
            operation_id = event.data.get('operationId')
            min_occurrences = event.data.get('minOccurrences', 3)
            min_confidence = event.data.get('minConfidence', 0.6)
            
            logger.info(f"Processing {event_type} event {event.event_id}")
            logger.info(f"Operation ID: {operation_id}, User: {user_id}")
            
            if not operation_id:
                logger.error("No operation ID provided in event")
                return
            
            # Update operation status to EXECUTING
            self.operation_service.update_operation(
                operation_id=operation_id,
                status=OperationStatus.EXECUTING,
                progress_percentage=5,
                current_step_description="Loading transactions"
            )
            
            # Stage 1: Load transactions (5% → 20%)
            logger.info("Loading user transactions")
            transactions = self._load_transactions_with_progress(
                user_id, 
                operation_id,
                start_progress=5,
                end_progress=20
            )
            
            if len(transactions) < min_occurrences:
                logger.info(f"Not enough transactions ({len(transactions)}) for detection")
                self.operation_service.update_operation(
                    operation_id=operation_id,
                    status=OperationStatus.COMPLETED,
                    progress_percentage=100,
                    current_step_description=f"Insufficient data: only {len(transactions)} transactions"
                )
                return
            
            # Stage 2: Feature extraction (20% → 40%)
            self.operation_service.update_operation(
                operation_id=operation_id,
                progress_percentage=20,
                current_step_description="Analyzing transaction patterns"
            )
            
            # Stage 3: Detection (40% → 80%)
            logger.info(f"Running pattern detection on {len(transactions)} transactions")
            patterns = self._detect_patterns_with_progress(
                user_id,
                transactions,
                operation_id,
                min_occurrences=min_occurrences,
                min_confidence=min_confidence,
                start_progress=40,
                end_progress=80
            )
            
            # Stage 4: Save patterns (80% → 95%)
            self.operation_service.update_operation(
                operation_id=operation_id,
                progress_percentage=80,
                current_step_description=f"Saving {len(patterns)} detected patterns"
            )
            
            saved_count = self._save_patterns(user_id, patterns)
            
            # Stage 5: Complete (95% → 100%)
            self.operation_service.update_operation(
                operation_id=operation_id,
                status=OperationStatus.COMPLETED,
                progress_percentage=100,
                current_step_description=f"Detection complete: {saved_count} patterns found",
                context={
                    'patterns_detected': saved_count,
                    'transactions_analyzed': len(transactions)
                }
            )
            
            logger.info(f"✅ Recurring charge detection complete: {saved_count} patterns")
            
        except Exception as e:
            logger.error(f"Error in recurring charge detection: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Update operation to failed status
            if operation_id:
                self.operation_service.update_operation(
                    operation_id=operation_id,
                    status=OperationStatus.FAILED,
                    error_message=str(e)
                )
            
            raise
    
    def _load_transactions_with_progress(
        self, 
        user_id: str, 
        operation_id: str,
        start_progress: int,
        end_progress: int
    ) -> List:
        """Load transactions with progress updates"""
        transactions = []
        last_evaluated_key = None
        batch_size = 1000
        total_batches_estimate = 10  # Estimate, will adjust
        batch_count = 0
        
        while True:
            batch, last_evaluated_key, _ = list_user_transactions(
                user_id,
                limit=batch_size,
                last_evaluated_key=last_evaluated_key
            )
            
            if not batch:
                break
            
            transactions.extend(batch)
            batch_count += 1
            
            # Update progress (linear interpolation)
            progress = start_progress + int(
                (end_progress - start_progress) * 
                min(batch_count / total_batches_estimate, 1.0)
            )
            
            self.operation_service.update_operation(
                operation_id=operation_id,
                progress_percentage=progress,
                current_step_description=f"Loaded {len(transactions)} transactions"
            )
            
            logger.info(f"Loaded batch {batch_count}: {len(batch)} transactions (total: {len(transactions)})")
            
            if not last_evaluated_key:
                break
        
        return transactions
    
    def _detect_patterns_with_progress(
        self,
        user_id: str,
        transactions: List,
        operation_id: str,
        min_occurrences: int,
        min_confidence: float,
        start_progress: int,
        end_progress: int
    ) -> List:
        """Run detection with granular progress updates"""
        
        # The detection service will handle the actual ML work
        # We'll update progress at key stages
        
        # Feature extraction: 40% → 50%
        self.operation_service.update_operation(
            operation_id=operation_id,
            progress_percentage=40,
            current_step_description="Extracting temporal features"
        )
        
        # Clustering: 50% → 65%
        self.operation_service.update_operation(
            operation_id=operation_id,
            progress_percentage=50,
            current_step_description="Clustering similar transactions"
        )
        
        # Pattern analysis: 65% → 80%
        self.operation_service.update_operation(
            operation_id=operation_id,
            progress_percentage=65,
            current_step_description="Analyzing patterns and calculating confidence"
        )
        
        # Run actual detection
        patterns = self.detection_service.detect_recurring_patterns(
            user_id=user_id,
            transactions=transactions
        )
        
        # Filter by criteria
        filtered_patterns = [
            p for p in patterns
            if p.transaction_count >= min_occurrences
            and p.confidence_score >= min_confidence
        ]
        
        logger.info(f"Detected {len(patterns)} patterns, {len(filtered_patterns)} meet criteria")
        
        return filtered_patterns
    
    def _save_patterns(self, user_id: str, patterns: List) -> int:
        """Save patterns to DynamoDB"""
        from utils.db_utils import save_recurring_charge_pattern
        
        saved_count = 0
        for pattern in patterns:
            try:
                save_recurring_charge_pattern(pattern)
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving pattern {pattern.pattern_id}: {str(e)}")
        
        return saved_count


# Lambda handler
from consumers.base_consumer import create_lambda_handler
lambda_handler = create_lambda_handler(RecurringChargeDetectionConsumer)
```

### 4. Handler: Trigger Detection

```python
# backend/src/handlers/recurring_charge_operations.py

"""
Recurring Charge Operations Handlers

API handlers for:
- Triggering pattern detection (long-running)
- Viewing detected patterns
- Providing feedback on patterns
- Applying patterns to categories
"""

import json
import logging
import uuid
import os
from typing import Dict, Any, List
from datetime import datetime, timezone

from utils.lambda_utils import create_response
from utils.handler_decorators import api_handler, require_user_id
from services.operation_tracking_service import (
    OperationTrackingService, 
    OperationType, 
    OperationStatus
)
from services.event_service import event_service
from utils.db_utils import (
    list_recurring_charge_patterns,
    get_recurring_charge_pattern,
    update_recurring_charge_pattern,
    save_pattern_feedback
)

logger = logging.getLogger(__name__)

ENABLE_EVENT_PUBLISHING = os.environ.get('ENABLE_EVENT_PUBLISHING', 'true').lower() == 'true'


@api_handler
@require_user_id
def trigger_detection_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Trigger recurring charge detection (long-running operation)
    
    POST /api/recurring-charges/detect
    
    Body:
    {
        "minOccurrences": 3,    // Optional
        "minConfidence": 0.6    // Optional
    }
    
    Returns operation ID for tracking progress
    """
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        min_occurrences = body.get('minOccurrences', 3)
        min_confidence = body.get('minConfidence', 0.6)
        
        logger.info(f"Triggering recurring charge detection for user {user_id}")
        
        # Create operation record
        operation_service = OperationTrackingService()
        operation_id = operation_service.create_operation(
            user_id=user_id,
            operation_type=OperationType.RECURRING_CHARGE_DETECTION,
            entity_id=user_id,  # Entity is the user
            context={
                'minOccurrences': min_occurrences,
                'minConfidence': min_confidence,
                'requestedAt': int(datetime.now(timezone.utc).timestamp() * 1000)
            }
        )
        
        logger.info(f"Created operation {operation_id}")
        
        # Publish event to trigger consumer
        if ENABLE_EVENT_PUBLISHING:
            event_service.publish_event(
                event_type='recurring_charge.detection.requested',
                user_id=user_id,
                data={
                    'operationId': operation_id,
                    'minOccurrences': min_occurrences,
                    'minConfidence': min_confidence
                },
                source='recurring_charge_api'
            )
            logger.info(f"Published detection event for operation {operation_id}")
        
        return create_response(202, {
            'message': 'Recurring charge detection started',
            'operationId': operation_id,
            'estimatedDurationMinutes': 2
        })
        
    except Exception as e:
        logger.error(f"Error triggering detection: {str(e)}")
        return create_response(500, {
            'message': 'Failed to start detection',
            'error': str(e)
        })


@api_handler
@require_user_id
def list_patterns_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    List detected recurring charge patterns
    
    GET /api/recurring-charges/patterns?active=true&minConfidence=0.6
    """
    user_id = event['requestContext']['authorizer']['claims']['sub']
    
    try:
        # Parse query parameters
        params = event.get('queryStringParameters') or {}
        active_only = params.get('active', 'true').lower() == 'true'
        min_confidence = float(params.get('minConfidence', '0.0'))
        
        # Get patterns from DB
        patterns = list_recurring_charge_patterns(
            user_id=user_id,
            active_only=active_only
        )
        
        # Filter by confidence
        if min_confidence > 0:
            patterns = [p for p in patterns if p.confidence_score >= min_confidence]
        
        # Sort by confidence (descending)
        patterns.sort(key=lambda p: p.confidence_score, reverse=True)
        
        # Serialize
        patterns_data = [
            {
                'patternId': str(p.pattern_id),
                'merchantPattern': p.merchant_pattern,
                'frequency': p.frequency.value,
                'temporalPattern': p.temporal_pattern_type.value,
                'dayOfWeek': p.day_of_week,
                'dayOfMonth': p.day_of_month,
                'confidence': p.confidence_score,
                'transactionCount': p.transaction_count,
                'amountMean': float(p.amount_mean),
                'amountRange': {
                    'min': float(p.amount_min),
                    'max': float(p.amount_max)
                },
                'firstOccurrence': p.first_occurrence,
                'lastOccurrence': p.last_occurrence,
                'suggestedCategoryId': str(p.suggested_category_id) if p.suggested_category_id else None,
                'autoCategorize': p.auto_categorize,
                'active': p.active
            }
            for p in patterns
        ]
        
        return create_response(200, {
            'patterns': patterns_data,
            'count': len(patterns_data)
        })
        
    except Exception as e:
        logger.error(f"Error listing patterns: {str(e)}")
        return create_response(500, {
            'message': 'Failed to list patterns',
            'error': str(e)
        })


@api_handler
@require_user_id
def submit_feedback_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Submit feedback on a pattern
    
    POST /api/recurring-charges/patterns/{patternId}/feedback
    
    Body:
    {
        "feedbackType": "correct" | "incorrect" | "missed_transaction" | etc.,
        "transactionId": "uuid",  // Optional
        "correction": {...},      // Optional
        "comment": "..."          // Optional
    }
    """
    user_id = event['requestContext']['authorizer']['claims']['sub']
    pattern_id = event['pathParameters']['patternId']
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        feedback_type = body.get('feedbackType')
        transaction_id = body.get('transactionId')
        correction = body.get('correction')
        comment = body.get('comment')
        
        if not feedback_type:
            return create_response(400, {
                'message': 'feedbackType is required'
            })
        
        # Create feedback record
        from models.recurring_charge import PatternFeedback, PatternFeedbackType
        
        feedback = PatternFeedback(
            userId=user_id,
            patternId=uuid.UUID(pattern_id),
            feedbackType=PatternFeedbackType(feedback_type),
            transactionId=uuid.UUID(transaction_id) if transaction_id else None,
            correction=correction,
            comment=comment
        )
        
        # Save feedback
        save_pattern_feedback(feedback)
        
        logger.info(f"Saved feedback for pattern {pattern_id}: {feedback_type}")
        
        # If feedback is "incorrect", deactivate the pattern
        if feedback_type == 'incorrect':
            pattern = get_recurring_charge_pattern(pattern_id, user_id)
            if pattern:
                pattern.active = False
                update_recurring_charge_pattern(pattern)
                logger.info(f"Deactivated pattern {pattern_id} due to negative feedback")
        
        return create_response(200, {
            'message': 'Feedback submitted successfully',
            'feedbackId': str(feedback.feedback_id)
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        return create_response(500, {
            'message': 'Failed to submit feedback',
            'error': str(e)
        })


@api_handler
@require_user_id
def link_pattern_to_category_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Link a pattern to a category and optionally auto-categorize
    
    POST /api/recurring-charges/patterns/{patternId}/link-category
    
    Body:
    {
        "categoryId": "uuid",
        "autoCategorize": true,      // Auto-apply to future transactions
        "applyToExisting": true      // Apply to existing matching transactions
    }
    """
    user_id = event['requestContext']['authorizer']['claims']['sub']
    pattern_id = event['pathParameters']['patternId']
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        category_id = body.get('categoryId')
        auto_categorize = body.get('autoCategorize', False)
        apply_to_existing = body.get('applyToExisting', False)
        
        if not category_id:
            return create_response(400, {
                'message': 'categoryId is required'
            })
        
        # Get pattern
        pattern = get_recurring_charge_pattern(pattern_id, user_id)
        if not pattern:
            return create_response(404, {
                'message': 'Pattern not found'
            })
        
        # Update pattern
        pattern.suggested_category_id = uuid.UUID(category_id)
        pattern.auto_categorize = auto_categorize
        update_recurring_charge_pattern(pattern)
        
        logger.info(f"Linked pattern {pattern_id} to category {category_id}")
        
        # Optionally apply to existing transactions
        transactions_updated = 0
        if apply_to_existing:
            # This would be implemented to find and categorize matching transactions
            # For now, return a placeholder
            logger.info("Applying pattern to existing transactions (not yet implemented)")
        
        return create_response(200, {
            'message': 'Pattern linked to category',
            'transactionsUpdated': transactions_updated,
            'autoCategorize': auto_categorize
        })
        
    except Exception as e:
        logger.error(f"Error linking pattern: {str(e)}")
        return create_response(500, {
            'message': 'Failed to link pattern',
            'error': str(e)
        })
```

### 5. Database Utilities

```python
# backend/src/utils/db_utils.py (additions)

def save_recurring_charge_pattern(pattern: 'RecurringChargePattern') -> None:
    """Save recurring charge pattern to DynamoDB"""
    from models.recurring_charge import RecurringChargePattern
    
    table = boto3.resource('dynamodb').Table(os.environ['RECURRING_PATTERNS_TABLE'])
    
    item = pattern.model_dump(by_alias=True, exclude_none=True)
    
    # Convert to DynamoDB format
    # ... (similar to transaction serialization)
    
    table.put_item(Item=item)


def list_recurring_charge_patterns(
    user_id: str,
    active_only: bool = True
) -> List['RecurringChargePattern']:
    """List all patterns for a user"""
    from models.recurring_charge import RecurringChargePattern
    
    table = boto3.resource('dynamodb').Table(os.environ['RECURRING_PATTERNS_TABLE'])
    
    response = table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    
    patterns = [
        RecurringChargePattern.from_dynamodb_item(item)
        for item in response.get('Items', [])
    ]
    
    if active_only:
        patterns = [p for p in patterns if p.active]
    
    return patterns


def get_recurring_charge_pattern(pattern_id: str, user_id: str) -> Optional['RecurringChargePattern']:
    """Get a specific pattern"""
    # Implementation similar to get_category_by_id_from_db
    pass


def update_recurring_charge_pattern(pattern: 'RecurringChargePattern') -> None:
    """Update an existing pattern"""
    # Implementation similar to update_category_in_db
    pass


def save_pattern_feedback(feedback: 'PatternFeedback') -> None:
    """Save user feedback on a pattern"""
    from models.recurring_charge import PatternFeedback
    
    table = boto3.resource('dynamodb').Table(os.environ['PATTERN_FEEDBACK_TABLE'])
    
    item = feedback.model_dump(by_alias=True, exclude_none=True)
    table.put_item(Item=item)


def get_pattern_feedback(pattern_id: str) -> List['PatternFeedback']:
    """Get all feedback for a pattern"""
    # Query GSI on patternId
    pass
```

---

## Frontend Implementation

### 1. Service Layer

```typescript
// frontend/src/services/recurringChargeService.ts

import { api } from './api';

export interface RecurringChargePattern {
  patternId: string;
  merchantPattern: string;
  frequency: string;
  temporalPattern: string;
  dayOfWeek?: number;
  dayOfMonth?: number;
  confidence: number;
  transactionCount: number;
  amountMean: number;
  amountRange: {
    min: number;
    max: number;
  };
  firstOccurrence: number;
  lastOccurrence: number;
  suggestedCategoryId?: string;
  autoCategorize: boolean;
  active: boolean;
}

export interface DetectionRequest {
  minOccurrences?: number;
  minConfidence?: number;
}

export interface DetectionResponse {
  operationId: string;
  estimatedDurationMinutes: number;
}

export const recurringChargeService = {
  /**
   * Trigger recurring charge detection (long-running)
   */
  async triggerDetection(request: DetectionRequest = {}): Promise<DetectionResponse> {
    const response = await api.post('/recurring-charges/detect', request);
    return response.data;
  },

  /**
   * List detected patterns
   */
  async listPatterns(options: {
    active?: boolean;
    minConfidence?: number;
  } = {}): Promise<RecurringChargePattern[]> {
    const params = new URLSearchParams();
    if (options.active !== undefined) {
      params.append('active', String(options.active));
    }
    if (options.minConfidence !== undefined) {
      params.append('minConfidence', String(options.minConfidence));
    }

    const response = await api.get(`/recurring-charges/patterns?${params}`);
    return response.data.patterns;
  },

  /**
   * Submit feedback on a pattern
   */
  async submitFeedback(
    patternId: string,
    feedback: {
      feedbackType: 'correct' | 'incorrect' | 'missed_transaction' | 'false_positive';
      transactionId?: string;
      correction?: Record<string, any>;
      comment?: string;
    }
  ): Promise<void> {
    await api.post(`/recurring-charges/patterns/${patternId}/feedback`, feedback);
  },

  /**
   * Link pattern to category
   */
  async linkToCategory(
    patternId: string,
    categoryId: string,
    options: {
      autoCategorize?: boolean;
      applyToExisting?: boolean;
    } = {}
  ): Promise<void> {
    await api.post(`/recurring-charges/patterns/${patternId}/link-category`, {
      categoryId,
      ...options
    });
  }
};
```

### 2. Categories Page Integration

```typescript
// frontend/src/components/domain/categories/components/RecurringChargesTab.tsx

import React, { useState, useEffect } from 'react';
import { recurringChargeService, RecurringChargePattern } from '@/services/recurringChargeService';
import { WorkflowProgressModal } from '@/components/ui/WorkflowProgressModal';
import './RecurringChargesTab.css';

export const RecurringChargesTab: React.FC = () => {
  const [patterns, setPatterns] = useState<RecurringChargePattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [detectionInProgress, setDetectionInProgress] = useState(false);
  const [operationId, setOperationId] = useState<string | null>(null);
  const [minConfidence, setMinConfidence] = useState(0.6);

  useEffect(() => {
    loadPatterns();
  }, []);

  const loadPatterns = async () => {
    try {
      setLoading(true);
      const data = await recurringChargeService.listPatterns({
        active: true,
        minConfidence: 0.5
      });
      setPatterns(data);
    } catch (error) {
      console.error('Failed to load patterns:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDetectPatterns = async () => {
    try {
      const response = await recurringChargeService.triggerDetection({
        minOccurrences: 3,
        minConfidence: minConfidence
      });

      setOperationId(response.operationId);
      setDetectionInProgress(true);
    } catch (error) {
      console.error('Failed to trigger detection:', error);
      alert('Failed to start pattern detection');
    }
  };

  const handleDetectionComplete = () => {
    setDetectionInProgress(false);
    setOperationId(null);
    // Reload patterns
    loadPatterns();
  };

  const handleConfirmPattern = async (patternId: string) => {
    try {
      await recurringChargeService.submitFeedback(patternId, {
        feedbackType: 'correct'
      });
      alert('Pattern confirmed!');
      loadPatterns();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  const handleRejectPattern = async (patternId: string) => {
    try {
      await recurringChargeService.submitFeedback(patternId, {
        feedbackType: 'incorrect'
      });
      alert('Pattern rejected and deactivated');
      loadPatterns();
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    }
  };

  return (
    <div className="recurring-charges-tab">
      <div className="header">
        <h2>Recurring Charges</h2>
        <button 
          className="detect-button"
          onClick={handleDetectPatterns}
          disabled={detectionInProgress}
        >
          {detectionInProgress ? 'Detecting...' : '🔍 Detect Patterns'}
        </button>
      </div>

      <div className="controls">
        <label>
          Minimum Confidence:
          <input 
            type="range"
            min="0.5"
            max="0.95"
            step="0.05"
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
          />
          <span>{(minConfidence * 100).toFixed(0)}%</span>
        </label>
      </div>

      {loading ? (
        <div className="loading">Loading patterns...</div>
      ) : (
        <div className="patterns-list">
          {patterns.length === 0 ? (
            <div className="empty-state">
              <p>No recurring charge patterns detected yet.</p>
              <button onClick={handleDetectPatterns}>
                Run Detection
              </button>
            </div>
          ) : (
            patterns.map(pattern => (
              <PatternCard
                key={pattern.patternId}
                pattern={pattern}
                onConfirm={() => handleConfirmPattern(pattern.patternId)}
                onReject={() => handleRejectPattern(pattern.patternId)}
              />
            ))
          )}
        </div>
      )}

      {/* Progress tracking modal */}
      {detectionInProgress && operationId && (
        <WorkflowProgressModal
          workflowId={operationId}
          isOpen={true}
          onClose={() => setDetectionInProgress(false)}
          onComplete={handleDetectionComplete}
          title="Detecting Recurring Charges"
        />
      )}
    </div>
  );
};

interface PatternCardProps {
  pattern: RecurringChargePattern;
  onConfirm: () => void;
  onReject: () => void;
}

const PatternCard: React.FC<PatternCardProps> = ({ pattern, onConfirm, onReject }) => {
  const [expanded, setExpanded] = useState(false);

  const formatFrequency = (freq: string) => {
    return freq.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatTemporalPattern = (type: string, dayOfWeek?: number, dayOfMonth?: number) => {
    if (type === 'first_working_day') return 'First working day of month';
    if (type === 'last_working_day') return 'Last working day of month';
    if (type === 'day_of_week' && dayOfWeek !== undefined) {
      const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
      return `Every ${days[dayOfWeek]}`;
    }
    if (type === 'day_of_month' && dayOfMonth) {
      return `Day ${dayOfMonth} of each month`;
    }
    return type.replace('_', ' ');
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.7) return 'medium';
    return 'low';
  };

  return (
    <div className="pattern-card">
      <div className="pattern-header" onClick={() => setExpanded(!expanded)}>
        <div className="pattern-main">
          <h3>{pattern.merchantPattern}</h3>
          <div className="pattern-meta">
            <span className="frequency">{formatFrequency(pattern.frequency)}</span>
            <span className="amount">${pattern.amountMean.toFixed(2)}</span>
            <span className={`confidence ${getConfidenceColor(pattern.confidence)}`}>
              {(pattern.confidence * 100).toFixed(0)}% confident
            </span>
          </div>
        </div>
        <div className="pattern-actions">
          <button 
            className="confirm-button"
            onClick={(e) => { e.stopPropagation(); onConfirm(); }}
          >
            ✓ Confirm
          </button>
          <button 
            className="reject-button"
            onClick={(e) => { e.stopPropagation(); onReject(); }}
          >
            ✗ Reject
          </button>
        </div>
      </div>

      {expanded && (
        <div className="pattern-details">
          <div className="detail-row">
            <strong>Temporal Pattern:</strong>
            <span>{formatTemporalPattern(pattern.temporalPattern, pattern.dayOfWeek, pattern.dayOfMonth)}</span>
          </div>
          <div className="detail-row">
            <strong>Amount Range:</strong>
            <span>${pattern.amountRange.min.toFixed(2)} - ${pattern.amountRange.max.toFixed(2)}</span>
          </div>
          <div className="detail-row">
            <strong>Occurrences:</strong>
            <span>{pattern.transactionCount} transactions</span>
          </div>
          <div className="detail-row">
            <strong>Period:</strong>
            <span>
              {new Date(pattern.firstOccurrence).toLocaleDateString()} - {new Date(pattern.lastOccurrence).toLocaleDateString()}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
```

### 3. Add Tab to Categories Page

```typescript
// frontend/src/components/domain/categories/CategoriesView.tsx

import { RecurringChargesTab } from './components/RecurringChargesTab';

// Add to tabs:
const tabs = [
  { id: 'categories', label: 'Categories', component: CategoriesTab },
  { id: 'rules', label: 'Rules', component: RulesTab },
  { id: 'recurring', label: 'Recurring Charges', component: RecurringChargesTab }, // NEW
];
```

### 4. Styling

```css
/* frontend/src/components/domain/categories/components/RecurringChargesTab.css */

.recurring-charges-tab {
  padding: 20px;
}

.recurring-charges-tab .header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.recurring-charges-tab .detect-button {
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.recurring-charges-tab .detect-button:hover {
  background: #45a049;
}

.recurring-charges-tab .detect-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.recurring-charges-tab .controls {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 4px;
}

.recurring-charges-tab .controls label {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recurring-charges-tab .controls input[type="range"] {
  flex: 1;
}

.recurring-charges-tab .patterns-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.pattern-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s;
}

.pattern-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.pattern-header {
  padding: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.pattern-main h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.pattern-meta {
  display: flex;
  gap: 15px;
  font-size: 14px;
  color: #666;
}

.pattern-meta .frequency {
  text-transform: capitalize;
}

.pattern-meta .confidence {
  padding: 2px 8px;
  border-radius: 3px;
  font-weight: bold;
}

.pattern-meta .confidence.high {
  background: #e8f5e9;
  color: #2e7d32;
}

.pattern-meta .confidence.medium {
  background: #fff3e0;
  color: #f57c00;
}

.pattern-meta .confidence.low {
  background: #ffebee;
  color: #c62828;
}

.pattern-actions {
  display: flex;
  gap: 10px;
}

.pattern-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.confirm-button {
  background: #4CAF50;
  color: white;
}

.confirm-button:hover {
  background: #45a049;
}

.reject-button {
  background: #f44336;
  color: white;
}

.reject-button:hover {
  background: #da190b;
}

.pattern-details {
  padding: 15px;
  border-top: 1px solid #e0e0e0;
  background: #fafafa;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
}

.detail-row strong {
  color: #333;
}

.detail-row span {
  color: #666;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.empty-state button {
  margin-top: 20px;
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
```

---

## Infrastructure

### DynamoDB Tables

```hcl
# infrastructure/modules/dynamodb/recurring_patterns.tf

resource "aws_dynamodb_table" "recurring_charge_patterns" {
  name           = "${var.environment}-recurring-charge-patterns"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "userId"
  range_key      = "patternId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "patternId"
    type = "S"
  }

  attribute {
    name = "patternId_gsi"
    type = "S"
  }

  global_secondary_index {
    name            = "patternId-index"
    hash_key        = "patternId_gsi"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = false  # Set true if want auto-expiry
  }

  tags = {
    Name        = "${var.environment}-recurring-charge-patterns"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "pattern_feedback" {
  name           = "${var.environment}-pattern-feedback"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "userId"
  range_key      = "feedbackId"

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "feedbackId"
    type = "S"
  }

  attribute {
    name = "patternId"
    type = "S"
  }

  global_secondary_index {
    name            = "patternId-index"
    hash_key        = "patternId"
    projection_type = "ALL"
  }

  tags = {
    Name        = "${var.environment}-pattern-feedback"
    Environment = var.environment
  }
}
```

### Lambda Functions

```hcl
# infrastructure/modules/lambda/recurring_charge_consumer.tf

resource "aws_lambda_function" "recurring_charge_consumer" {
  function_name = "${var.environment}-recurring-charge-consumer"
  role          = aws_iam_role.recurring_charge_consumer_role.arn
  handler       = "consumers.recurring_charge_consumer.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300  # 5 minutes (detection can take time)
  memory_size   = 1024 # 1GB for ML processing

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      RECURRING_PATTERNS_TABLE = var.recurring_patterns_table_name
      PATTERN_FEEDBACK_TABLE   = var.pattern_feedback_table_name
      WORKFLOWS_TABLE          = var.workflows_table_name
      EVENT_BUS_NAME           = var.event_bus_name
      ENABLE_EVENT_PUBLISHING  = "true"
      LOG_LEVEL                = "INFO"
    }
  }

  layers = [
    aws_lambda_layer_version.ml_dependencies.arn  # scikit-learn, pandas, numpy
  ]

  tags = {
    Name        = "${var.environment}-recurring-charge-consumer"
    Environment = var.environment
  }
}

# ML Dependencies Layer
resource "aws_lambda_layer_version" "ml_dependencies" {
  filename            = "lambda-layers/ml-dependencies.zip"
  layer_name          = "${var.environment}-ml-dependencies"
  compatible_runtimes = ["python3.12"]

  description = "ML libraries: scikit-learn, pandas, numpy, holidays"
}

# EventBridge Rule
resource "aws_eventbridge_rule" "recurring_charge_detection" {
  name           = "${var.environment}-recurring-charge-detection"
  description    = "Trigger recurring charge detection consumer"
  event_bus_name = var.event_bus_name

  event_pattern = jsonencode({
    "detail-type" = [
      "recurring_charge.detection.requested",
      "recurring_charge.detection.retry"
    ]
  })
}

resource "aws_eventbridge_target" "recurring_charge_consumer" {
  rule           = aws_eventbridge_rule.recurring_charge_detection.name
  event_bus_name = var.event_bus_name
  arn            = aws_lambda_function.recurring_charge_consumer.arn
}

resource "aws_lambda_permission" "allow_eventbridge_recurring_charge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recurring_charge_consumer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_eventbridge_rule.recurring_charge_detection.arn
}
```

### API Gateway Routes

```hcl
# Add to API Gateway configuration

resource "aws_apigatewayv2_route" "trigger_detection" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /recurring-charges/detect"
  target    = "integrations/${aws_apigatewayv2_integration.recurring_charge_handler.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "list_patterns" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /recurring-charges/patterns"
  target    = "integrations/${aws_apigatewayv2_integration.recurring_charge_handler.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "submit_feedback" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /recurring-charges/patterns/{patternId}/feedback"
  target    = "integrations/${aws_apigatewayv2_integration.recurring_charge_handler.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "link_category" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /recurring-charges/patterns/{patternId}/link-category"
  target    = "integrations/${aws_apigatewayv2_integration.recurring_charge_handler.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.cognito.id
}
```

---

## Deployment Steps

### Phase 1: Backend Foundation

1. **Create Data Models**
   - `backend/src/models/recurring_charge.py`
   - Add to `__init__.py`

2. **Add DynamoDB Tables**
   - Create Terraform configurations
   - Apply infrastructure changes
   - Update environment variables

3. **Create ML Dependencies Layer**
   ```bash
   cd backend/lambda-layers/ml-dependencies
   pip install -t python/ scikit-learn pandas numpy holidays
   zip -r ml-dependencies.zip python/
   ```

4. **Add DB Utilities**
   - Update `backend/src/utils/db_utils.py`

### Phase 2: Consumer & Services

1. **Create Detection Service**
   - `backend/src/services/recurring_charge_detection_service.py`
   - `backend/src/services/recurring_charge_feature_service.py`

2. **Create Consumer**
   - `backend/src/consumers/recurring_charge_consumer.py`

3. **Update Operation Tracking**
   - Add operation type to `operation_tracking_service.py`

4. **Create Handlers**
   - `backend/src/handlers/recurring_charge_operations.py`

5. **Deploy Backend**
   ```bash
   cd backend
   ./scripts/build.sh
   terraform apply
   ```

### Phase 3: Frontend Integration

1. **Create Service**
   - `frontend/src/services/recurringChargeService.ts`

2. **Create Components**
   - `frontend/src/components/domain/categories/components/RecurringChargesTab.tsx`
   - CSS styling

3. **Integrate with Categories Page**
   - Add tab to `CategoriesView.tsx`

4. **Deploy Frontend**
   ```bash
   cd frontend
   npm run build
   # Deploy to S3/CloudFront
   ```

### Phase 4: Testing & Refinement

1. **Test with Real Data**
   - Run detection on test user
   - Verify patterns detected
   - Check confidence scores

2. **UI/UX Refinement**
   - Test workflow progress modal
   - Refine confidence thresholds
   - Improve pattern display

3. **Performance Optimization**
   - Monitor Lambda execution times
   - Optimize clustering parameters
   - Add caching if needed

---

## Usage Flow

### User Perspective

1. **Trigger Detection**
   - Navigate to Categories → Recurring Charges tab
   - Click "Detect Patterns" button
   - Modal shows progress: Loading → Analyzing → Detecting → Complete

2. **Review Patterns**
   - See list of detected patterns
   - Each pattern shows:
     - Merchant name
     - Frequency (monthly, weekly, etc.)
     - Amount and confidence
     - Temporal pattern (day 15, last working day, etc.)

3. **Provide Feedback**
   - **Confirm**: Mark pattern as correct
   - **Reject**: Mark as incorrect (auto-deactivates)
   - Feedback improves future detection

4. **Link to Category**
   - Click pattern to expand
   - Link to existing category
   - Optionally enable auto-categorization
   - Optionally apply to existing transactions

---

## Monitoring & Metrics

### CloudWatch Metrics

```python
# Add to consumer
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='HouseF3/RecurringCharges',
    MetricData=[
        {
            'MetricName': 'PatternsDetected',
            'Value': len(patterns),
            'Unit': 'Count'
        },
        {
            'MetricName': 'DetectionDuration',
            'Value': duration_seconds,
            'Unit': 'Seconds'
        },
        {
            'MetricName': 'TransactionsAnalyzed',
            'Value': len(transactions),
            'Unit': 'Count'
        },
        {
            'MetricName': 'AverageConfidence',
            'Value': avg_confidence,
            'Unit': 'None'
        }
    ]
)
```

### Key Metrics to Track

- **Detection Performance**
  - Execution time per user
  - Patterns detected per execution
  - Average confidence score
  - Error rate

- **User Engagement**
  - Detection triggers per day
  - Pattern confirmations vs rejections
  - Feedback submission rate
  - Category linkage rate

- **Accuracy** (from feedback)
  - Precision: confirmed / (confirmed + rejected)
  - False positive rate
  - User satisfaction

---

## Future Enhancements

### Phase 2 (Post-Launch)

1. **Automatic Retraining**
   - Weekly recalibration based on feedback
   - Parameter auto-tuning
   - Supervised learning layer

2. **Smart Notifications**
   - Alert on missed recurring charges
   - Notify of amount changes
   - Budget impact warnings

3. **Pattern Predictions**
   - Show next expected occurrence
   - Predict upcoming expenses
   - Cash flow forecasting

4. **Merchant Intelligence**
   - Build shared merchant database
   - Cross-user pattern learning
   - Category suggestions from community

---

## Success Criteria

The integration is successful when:

1. ✅ Users can trigger detection from Categories page
2. ✅ Progress is visible in real-time modal
3. ✅ Patterns display with actionable information
4. ✅ Feedback loop is smooth and intuitive
5. ✅ Detection completes in < 3 minutes for typical users
6. ✅ Initial accuracy ≥ 70%
7. ✅ User satisfaction ≥ 4.0/5.0

---

**Document Version:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-02 | System | Initial integration design |

