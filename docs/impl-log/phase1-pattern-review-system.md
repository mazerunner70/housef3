# Phase 1 Implementation Plan: Pattern Review System

## Goal
Enable users to review ML-detected recurring charge patterns, validate the matching criteria, and activate patterns for auto-categorization.

## Current Status

### ✅ Completed (Backend Core)
- [x] Enhanced data models with Phase 1 fields
- [x] PatternStatus enum (DETECTED → CONFIRMED → ACTIVE)
- [x] Criteria builder services (Merchant/Amount/Temporal)
- [x] Pattern validation service
- [x] Pattern review service
- [x] Updated detection service to store matched_transaction_ids
- [x] 39 passing unit tests
- [x] Design documentation

### ✅ Completed (Phase 1A - Infrastructure)
- [x] DynamoDB schema updates (Terraform)
  - Added `status` attribute
  - Created `UserIdStatusIndex` GSI
  - Documented schema changes and migration plan

### ❌ Not Started
- [ ] API endpoints (Lambda handlers)
- [ ] Repository layer (DynamoDB operations)
- [ ] Frontend components
- [ ] Integration tests
- [ ] End-to-end workflow

## Implementation Phases

---

## Phase 1A: Infrastructure & Database (Week 1)

### 1.1 DynamoDB Schema Updates
**Effort**: 2-3 hours  
**Files**: `infrastructure/terraform/dynamo_recurring_charges.tf`

#### Tasks
- [x] Add new fields to RecurringChargePatterns table definition
  - `status` (String) - Added as indexed attribute
  - Non-indexed fields (DynamoDB schema-less):
    - `matchedTransactionIds` (List)
    - `criteriaValidated` (Boolean)
    - `criteriaValidationErrors` (List)
    - `reviewedBy` (String)
    - `reviewedAt` (Number)

- [x] Create new GSI: `UserIdStatusIndex`
  ```hcl
  global_secondary_index {
    name            = "UserIdStatusIndex"
    hash_key        = "userId"
    range_key       = "status"
    projection_type = "ALL"
  }
  ```

- [x] Document schema changes

#### Validation
```bash
cd infrastructure/terraform
terraform plan
terraform apply
```

---

## Phase 1B: Repository Layer (Week 1-2)

### 1.2 Pattern Repository Enhancement
**Effort**: 4-6 hours  
**Files**: 
- `backend/src/repositories/recurring_charge_repository.py` (new or update existing)

#### Tasks
- [ ] Create/update `RecurringChargePatternRepository`
  ```python
  class RecurringChargePatternRepository:
      def get_pattern_by_id(pattern_id: UUID) -> RecurringChargePattern
      def list_patterns_by_user(user_id: str, status: Optional[PatternStatus]) -> List[RecurringChargePattern]
      def create_pattern(pattern: RecurringChargePatternCreate) -> RecurringChargePattern
      def update_pattern(pattern: RecurringChargePattern) -> RecurringChargePattern
      def delete_pattern(pattern_id: UUID) -> bool
  ```

- [ ] Query methods for Phase 1
  ```python
  def get_patterns_for_review(user_id: str) -> List[RecurringChargePattern]:
      """Get all DETECTED patterns for a user."""
      
  def get_active_patterns(user_id: str) -> List[RecurringChargePattern]:
      """Get all ACTIVE patterns for a user."""
  ```

- [ ] Batch operations
  ```python
  def get_patterns_by_ids(pattern_ids: List[UUID]) -> List[RecurringChargePattern]
  def get_transactions_for_pattern(pattern: RecurringChargePattern) -> List[Transaction]:
      """Fetch transactions by matched_transaction_ids."""
  ```

#### Tests
- [ ] Unit tests for repository methods
- [ ] Integration tests with DynamoDB Local
- [ ] Test GSI queries

---

## Phase 1C: API Endpoints (Week 2)

### 1.3 Pattern Review API Handler
**Effort**: 6-8 hours  
**Files**: 
- `backend/src/handlers/recurring_charge_operations.py` (new)

#### Endpoints to Build

**1. List Patterns for Review**
```python
GET /recurring-patterns
Query params: ?status=detected&userId={userId}

Handler: list_patterns_handler()
Response: {
  "patterns": [
    {
      "patternId": "...",
      "merchantPattern": "NETFLIX",
      "status": "detected",
      "transactionCount": 12,
      "confidenceScore": 0.94,
      ...
    }
  ]
}
```

**2. Get Pattern Details with Matched Transactions**
```python
GET /recurring-patterns/{patternId}
Query params: ?includeTransactions=true

Handler: get_pattern_details_handler()
Response: {
  "pattern": { ... },
  "matchedTransactions": [
    {
      "transactionId": "...",
      "date": 1731628800000,
      "description": "NETFLIX.COM",
      "amount": -14.99,
      ...
    }
  ],
  "criteriaAnalysis": {
    "merchantSuggestion": {
      "pattern": "NETFLIX",
      "matchType": "contains",
      "confidence": 0.85
    },
    "amountSuggestion": {
      "mean": 15.19,
      "suggestedTolerance": 10.0
    },
    "temporalSuggestion": {
      "frequency": "monthly",
      "dayOfMonth": 15,
      "suggestedTolerance": 2
    }
  }
}
```

**3. Validate Pattern Criteria**
```python
POST /recurring-patterns/{patternId}/validate

Handler: validate_pattern_handler()
Request: (optional) {
  "merchantPattern": "NETFLIX",
  "amountTolerancePct": 15.0,
  "toleranceDays": 3
}
Response: {
  "isValid": true,
  "perfectMatch": true,
  "originalCount": 12,
  "criteriaMatchCount": 12,
  "missingFromCriteria": [],
  "extraFromCriteria": [],
  "warnings": [],
  "suggestions": ["Criteria perfectly match original cluster"]
}
```

**4. Review Pattern (Confirm/Reject/Edit)**
```python
POST /recurring-patterns/{patternId}/review

Handler: review_pattern_handler()
Request: {
  "action": "confirm" | "reject" | "edit",
  "editedMerchantPattern": "NETFLIX.*STREAMING", // optional
  "editedAmountTolerancePct": 15.0, // optional
  "editedToleranceDays": 3, // optional
  "editedSuggestedCategoryId": "...", // optional
  "notes": "Looks good", // optional
  "activateImmediately": true
}
Response: {
  "pattern": { ...updated pattern... },
  "validation": { ...validation result if confirmed/edited... }
}
```

**5. Activate Pattern**
```python
POST /recurring-patterns/{patternId}/activate

Handler: activate_pattern_handler()
Response: {
  "pattern": { ...updated pattern with status=ACTIVE... }
}
```

**6. Pause/Resume Pattern**
```python
POST /recurring-patterns/{patternId}/pause
POST /recurring-patterns/{patternId}/resume

Handler: toggle_pattern_handler()
Response: {
  "pattern": { ...updated pattern... }
}
```

#### Implementation Structure
```python
# backend/src/handlers/recurring_charge_operations.py

from models.recurring_charge import (
    RecurringChargePattern,
    PatternStatus,
    PatternReviewAction
)
from repositories.recurring_charge_repository import RecurringChargePatternRepository
from repositories.transaction_repository import TransactionRepository
from services.recurring_charges.pattern_validation_service import PatternValidationService
from services.recurring_charges.pattern_review_service import PatternReviewService
from services.recurring_charges.criteria_builders import (
    MerchantCriteriaBuilder,
    AmountCriteriaBuilder,
    TemporalCriteriaBuilder
)

def list_patterns_handler(event, context):
    """GET /recurring-patterns"""
    user_id = get_user_id_from_event(event)
    status = event.get('queryStringParameters', {}).get('status')
    
    repo = RecurringChargePatternRepository()
    patterns = repo.list_patterns_by_user(user_id, status)
    
    return success_response({
        'patterns': [p.model_dump(by_alias=True) for p in patterns]
    })

def get_pattern_details_handler(event, context):
    """GET /recurring-patterns/{patternId}"""
    pattern_id = UUID(event['pathParameters']['patternId'])
    include_txs = event.get('queryStringParameters', {}).get('includeTransactions') == 'true'
    
    pattern_repo = RecurringChargePatternRepository()
    pattern = pattern_repo.get_pattern_by_id(pattern_id)
    
    response = {'pattern': pattern.model_dump(by_alias=True)}
    
    if include_txs and pattern.matched_transaction_ids:
        tx_repo = TransactionRepository()
        transactions = tx_repo.get_transactions_by_ids(pattern.matched_transaction_ids)
        response['matchedTransactions'] = [tx.model_dump(by_alias=True) for tx in transactions]
        
        # Generate criteria suggestions
        response['criteriaAnalysis'] = generate_criteria_suggestions(transactions)
    
    return success_response(response)

def validate_pattern_handler(event, context):
    """POST /recurring-patterns/{patternId}/validate"""
    pattern_id = UUID(event['pathParameters']['patternId'])
    body = json.loads(event['body']) if event.get('body') else {}
    
    pattern_repo = RecurringChargePatternRepository()
    pattern = pattern_repo.get_pattern_by_id(pattern_id)
    
    # Apply any temporary edits for validation
    if body:
        pattern = apply_temporary_edits(pattern, body)
    
    # Get all user transactions for validation
    tx_repo = TransactionRepository()
    all_transactions = tx_repo.get_transactions_by_user(pattern.user_id)
    
    # Validate
    validator = PatternValidationService()
    result = validator.validate_pattern_criteria(pattern, all_transactions)
    
    return success_response(result.model_dump(by_alias=True))

def review_pattern_handler(event, context):
    """POST /recurring-patterns/{patternId}/review"""
    pattern_id = UUID(event['pathParameters']['patternId'])
    user_id = get_user_id_from_event(event)
    body = json.loads(event['body'])
    
    # Get pattern and transactions
    pattern_repo = RecurringChargePatternRepository()
    tx_repo = TransactionRepository()
    
    pattern = pattern_repo.get_pattern_by_id(pattern_id)
    all_transactions = tx_repo.get_transactions_by_user(user_id)
    
    # Create review action
    review_action = PatternReviewAction(
        patternId=pattern_id,
        userId=user_id,
        action=body['action'],
        editedMerchantPattern=body.get('editedMerchantPattern'),
        editedAmountTolerancePct=body.get('editedAmountTolerancePct'),
        editedToleranceDays=body.get('editedToleranceDays'),
        editedSuggestedCategoryId=body.get('editedSuggestedCategoryId'),
        notes=body.get('notes'),
        activateImmediately=body.get('activateImmediately', False)
    )
    
    # Process review
    review_service = PatternReviewService()
    updated_pattern, validation = review_service.review_pattern(
        pattern, review_action, all_transactions
    )
    
    # Save
    pattern_repo.update_pattern(updated_pattern)
    
    response = {'pattern': updated_pattern.model_dump(by_alias=True)}
    if validation:
        response['validation'] = validation.model_dump(by_alias=True)
    
    return success_response(response)
```

#### Tests
- [ ] Unit tests for each handler
- [ ] Integration tests with mocked repositories
- [ ] Authorization tests (user can only access own patterns)

---

## Phase 1D: Lambda & API Gateway Configuration (Week 2)

### 1.4 Infrastructure for New Endpoints
**Effort**: 2-3 hours  
**Files**: `infrastructure/terraform/lambda.tf`, `infrastructure/terraform/api_gateway.tf`

#### Tasks
- [ ] Create `recurring-charge-operations` Lambda function
- [ ] Configure API Gateway routes
  ```
  GET    /recurring-patterns
  GET    /recurring-patterns/{patternId}
  POST   /recurring-patterns/{patternId}/validate
  POST   /recurring-patterns/{patternId}/review
  POST   /recurring-patterns/{patternId}/activate
  POST   /recurring-patterns/{patternId}/pause
  POST   /recurring-patterns/{patternId}/resume
  ```
- [ ] Set up Lambda permissions for DynamoDB access
- [ ] Configure CORS
- [ ] Add to Cognito authorizer

---

## Phase 1E: Frontend Components (Week 3-4)

### 1.5 Pattern Review UI
**Effort**: 12-16 hours  
**Files**: New frontend components

#### Component Structure
```
frontend/src/
├── business/recurring-patterns/
│   ├── PatternReviewList.tsx          # List of patterns awaiting review
│   ├── PatternReviewDetail.tsx        # Detail view with matched transactions
│   ├── PatternCriteriaBuilder.tsx     # Edit/validate criteria
│   ├── PatternValidationResult.tsx    # Show validation warnings/suggestions
│   └── MatchedTransactionsList.tsx    # Table of matched transactions
├── layouts/
│   └── PatternReviewLayout.tsx        # Overall layout for pattern review
└── services/
    └── recurringPatternService.ts     # API calls to backend
```

#### 1.5.1 Pattern Review List
**Component**: `PatternReviewList.tsx`

Features:
- [ ] Fetch patterns with status=DETECTED
- [ ] Display pattern cards with key info
- [ ] Click to view details
- [ ] Quick actions (confirm/reject)
- [ ] Filter/sort options

```tsx
interface PatternReviewListProps {
  userId: string;
}

export const PatternReviewList: React.FC<PatternReviewListProps> = ({ userId }) => {
  const [patterns, setPatterns] = useState<RecurringChargePattern[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchPatternsForReview(userId).then(setPatterns);
  }, [userId]);
  
  return (
    <div className="pattern-review-list">
      <h2>Patterns Awaiting Review ({patterns.length})</h2>
      {patterns.map(pattern => (
        <PatternCard 
          key={pattern.patternId}
          pattern={pattern}
          onClick={() => navigate(`/patterns/${pattern.patternId}`)}
        />
      ))}
    </div>
  );
};
```

#### 1.5.2 Pattern Detail View
**Component**: `PatternReviewDetail.tsx`

Features:
- [ ] Show pattern summary
- [ ] Display all matched transactions in table
- [ ] Show auto-generated criteria
- [ ] Validate criteria button
- [ ] Edit criteria inline
- [ ] Confirm/reject/activate actions

```tsx
interface PatternReviewDetailProps {
  patternId: string;
}

export const PatternReviewDetail: React.FC<PatternReviewDetailProps> = ({ patternId }) => {
  const [pattern, setPattern] = useState<RecurringChargePattern | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [validation, setValidation] = useState<PatternCriteriaValidation | null>(null);
  
  useEffect(() => {
    fetchPatternDetails(patternId, true).then(data => {
      setPattern(data.pattern);
      setTransactions(data.matchedTransactions);
    });
  }, [patternId]);
  
  const handleValidate = async () => {
    const result = await validatePattern(patternId);
    setValidation(result);
  };
  
  const handleReview = async (action: string) => {
    await reviewPattern(patternId, { action, activateImmediately: true });
    navigate('/patterns');
  };
  
  return (
    <div className="pattern-detail">
      <PatternSummary pattern={pattern} />
      <MatchedTransactionsList transactions={transactions} />
      <PatternCriteriaBuilder pattern={pattern} onEdit={setPattern} />
      <PatternValidationResult validation={validation} />
      
      <div className="actions">
        <Button onClick={handleValidate}>Validate Criteria</Button>
        <Button onClick={() => handleReview('confirm')} variant="primary">
          Confirm & Activate
        </Button>
        <Button onClick={() => handleReview('reject')} variant="danger">
          Reject
        </Button>
      </div>
    </div>
  );
};
```

#### 1.5.3 Criteria Builder
**Component**: `PatternCriteriaBuilder.tsx`

Features:
- [ ] Show current criteria
- [ ] Edit merchant pattern
- [ ] Adjust amount tolerance slider
- [ ] Adjust date tolerance
- [ ] Real-time preview of what will match
- [ ] Link to regex help (for advanced users)

#### 1.5.4 Matched Transactions Table
**Component**: `MatchedTransactionsList.tsx`

Features:
- [ ] Sortable table
- [ ] Click row to see transaction details
- [ ] Show match/no-match indicator if validation run
- [ ] Pagination if many transactions

#### 1.5.5 API Service
**File**: `recurringPatternService.ts`

```typescript
export const recurringPatternService = {
  async listPatternsForReview(userId: string, status?: string) {
    const params = new URLSearchParams({ userId });
    if (status) params.append('status', status);
    
    const response = await api.get(`/recurring-patterns?${params}`);
    return response.data.patterns;
  },
  
  async getPatternDetails(patternId: string, includeTransactions: boolean = true) {
    const params = includeTransactions ? '?includeTransactions=true' : '';
    const response = await api.get(`/recurring-patterns/${patternId}${params}`);
    return response.data;
  },
  
  async validatePattern(patternId: string, edits?: any) {
    const response = await api.post(`/recurring-patterns/${patternId}/validate`, edits);
    return response.data;
  },
  
  async reviewPattern(patternId: string, action: PatternReviewAction) {
    const response = await api.post(`/recurring-patterns/${patternId}/review`, action);
    return response.data;
  },
  
  async activatePattern(patternId: string) {
    const response = await api.post(`/recurring-patterns/${patternId}/activate`);
    return response.data;
  }
};
```

---

## Phase 1F: Integration & Testing (Week 4)

### 1.6 End-to-End Testing
**Effort**: 6-8 hours

#### Tasks
- [ ] Create test data (seed patterns and transactions)
- [ ] E2E test: Detect pattern → Review → Validate → Confirm → Activate
- [ ] E2E test: Detect pattern → Edit criteria → Validate → Confirm
- [ ] E2E test: Detect pattern → Reject
- [ ] Test validation warnings (false positives/negatives)
- [ ] Test authorization (users can't access other users' patterns)
- [ ] Performance testing (100+ patterns, 1000+ transactions)

### 1.7 Integration Tests
- [ ] Repository + DynamoDB integration
- [ ] Handler + Repository integration
- [ ] Frontend + Backend API integration

---

## Phase 1G: Documentation & Deployment (Week 4)

### 1.8 Documentation
**Effort**: 3-4 hours

- [ ] API documentation (OpenAPI/Swagger)
- [ ] User guide for pattern review
- [ ] Admin guide for troubleshooting
- [ ] Update design docs with final implementation details

### 1.9 Deployment
**Effort**: 2-3 hours

- [ ] Deploy Terraform changes (DynamoDB schema)
- [ ] Deploy Lambda functions
- [ ] Deploy frontend
- [ ] Smoke test in dev environment
- [ ] Deploy to production

---

## Implementation Timeline

### Week 1: Infrastructure & Backend Foundation
- **Mon-Tue**: DynamoDB schema updates, Terraform
- **Wed-Thu**: Repository layer
- **Fri**: Repository tests

### Week 2: API Development
- **Mon-Tue**: API handlers (list, get details, validate)
- **Wed-Thu**: API handlers (review, activate, pause)
- **Fri**: Handler tests, Lambda/API Gateway config

### Week 3: Frontend Development
- **Mon-Tue**: Pattern list + detail components
- **Wed-Thu**: Criteria builder + validation UI
- **Fri**: Matched transactions table, polish

### Week 4: Testing & Deployment
- **Mon-Tue**: Integration tests
- **Wed**: E2E tests
- **Thu**: Documentation
- **Fri**: Deployment + smoke testing

---

## Success Criteria

### Functional Requirements
- [ ] Users can view detected patterns
- [ ] Users can see all transactions that matched a pattern
- [ ] Users can validate criteria show correct results
- [ ] Users can confirm patterns with valid criteria
- [ ] Users can edit criteria and re-validate
- [ ] Users can reject patterns
- [ ] Confirmed patterns can be activated
- [ ] Active patterns show in separate view

### Non-Functional Requirements
- [ ] API responds in < 500ms for pattern list
- [ ] API responds in < 1s for pattern details with transactions
- [ ] Frontend renders smoothly with 50+ patterns
- [ ] No data loss during review process
- [ ] Proper error handling and user feedback

### Quality Requirements
- [ ] 80%+ test coverage on new code
- [ ] All linter checks pass
- [ ] API documentation complete
- [ ] User guide available

---

## Risk Mitigation

### Risk 1: DynamoDB Schema Migration
**Risk**: Existing patterns don't have new fields  
**Mitigation**: 
- Default values in `from_dynamodb_item()` already handle missing fields
- Status defaults to DETECTED
- matched_transaction_ids defaults to None (acceptable for old patterns)

### Risk 2: Performance with Large Transaction Lists
**Risk**: Users with thousands of transactions, validation is slow  
**Mitigation**:
- Cache transaction queries
- Limit validation to time window around pattern occurrence
- Add pagination to matched transactions

### Risk 3: Complex Criteria Editing
**Risk**: Users might create invalid regex patterns  
**Mitigation**:
- Simple UI by default (no regex exposed)
- Validate regex on backend before saving
- Show preview of what matches before confirming

---

## Post-Phase 1 Enhancements

### Phase 2: Auto-Categorization (Next)
- [ ] Pattern matching service
- [ ] Batch categorization
- [ ] Apply patterns to new transactions automatically

### Future Enhancements
- [ ] Pattern effectiveness tracking
- [ ] Pattern suggestions based on user feedback
- [ ] Bulk pattern approval
- [ ] Pattern templates
- [ ] Export/import patterns

---

## File Checklist

### Backend Files to Create/Modify
- [ ] `infrastructure/terraform/dynamo_recurring_charges.tf` - Schema updates
- [ ] `backend/src/repositories/recurring_charge_repository.py` - Repository
- [ ] `backend/src/handlers/recurring_charge_operations.py` - API handlers
- [ ] `infrastructure/terraform/lambda.tf` - Lambda config
- [ ] `infrastructure/terraform/api_gateway.tf` - API routes
- [ ] Tests for all above

### Frontend Files to Create
- [ ] `frontend/src/business/recurring-patterns/PatternReviewList.tsx`
- [ ] `frontend/src/business/recurring-patterns/PatternReviewDetail.tsx`
- [ ] `frontend/src/business/recurring-patterns/PatternCriteriaBuilder.tsx`
- [ ] `frontend/src/business/recurring-patterns/PatternValidationResult.tsx`
- [ ] `frontend/src/business/recurring-patterns/MatchedTransactionsList.tsx`
- [ ] `frontend/src/layouts/PatternReviewLayout.tsx`
- [ ] `frontend/src/services/recurringPatternService.ts`
- [ ] Tests for all above

---

## Getting Started

**Next immediate step**: Start with Phase 1A (Infrastructure)

```bash
# 1. Create feature branch
git checkout -b feature/phase1-pattern-review

# 2. Update DynamoDB schema
cd infrastructure/terraform
# Edit dynamo_recurring_charges.tf
terraform plan
terraform apply

# 3. Create repository layer
cd ../../backend/src/repositories
# Create recurring_charge_repository.py
# Write tests

# 4. Continue with API handlers...
```

Would you like me to start implementing any specific phase?

